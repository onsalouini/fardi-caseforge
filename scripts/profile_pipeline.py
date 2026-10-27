"""B2 — profil du pipeline linguistique sur le dev (jamais le test) ; rapport ``reports/lotb_pipeline_linguistique.md``.

    python -m scripts.profile_pipeline

Pour chaque tokeniseur : temps par passage (par ``doc_lang``) et plafond F1 stricte des spans gold alignés sur ses
tokens (``token_ceiling``). Tokeniseurs comparés :

- ``cfdata`` : ``cfdata.common.tokenize`` (celui des fichiers BIO du Lot A) ;
- ``cfdata+strip`` : idem, puis ``strip_arabic_proclitics`` sur chaque span reconverti ;
- ``spacy/stanza`` : ``caseforge.extraction.nlp.parse`` (spaCy fr / en, stanza ar, mixte par phrase) ;
- ``stanza+strip`` : idem, puis ``strip_arabic_proclitics``.

Liste aussi les 20 entités gold le plus souvent coupées au milieu d'un token par ``cfdata.common.tokenize``.
Sorties : ``results/lotb/b2_profile.json`` et le rapport.
"""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from collections.abc import Callable
from statistics import mean
from typing import Any

from caseforge.eval.data import REPORTS, RESULTS, charger_dev, ecrire_json
from caseforge.eval.ner_metrics import token_ceiling
from caseforge.extraction.bio import aligner_sur_tokens
from caseforge.extraction.nlp import (
    MODELES_SPACY,
    PROCLITIQUES,
    doc_depuis_stanza,
    est_repli,
    offsets,
    parse,
    pipeline,
    strip_arabic_proclitics,
)
from cfdata.common import tokenize

LANGS = ("fr", "ar", "en")
Offsets = list[tuple[int, int]]


def f(x: float) -> str:
    """Nombre à 3 décimales, virgule décimale."""
    return f"{x:.3f}".replace(".", ",")


def _table(entete: list[str], lignes: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(entete) + " |", "|" + "---|" * len(entete)] + [
        "| " + " | ".join(r) + " |" for r in lignes
    ]


def _chrono(fn: Callable[[], Any]) -> tuple[Any, float]:
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0


def _coupe(e: dict, offs: Offsets) -> str | None:
    """« début », « fin » ou « début+fin » si une borne de l'entité tombe au milieu d'un token, sinon None."""
    debut = any(s < e["start"] < t for s, t in offs)
    fin = any(s < e["end"] < t for s, t in offs)
    return "début+fin" if debut and fin else "début" if debut else "fin" if fin else None


PONCTUATION_ARABE = "،؛؟"


def _causes(e: dict, text: str, offs: Offsets) -> list[str]:
    """Cause de chaque borne coupée : proclitique collé (début), ponctuation arabe collée, ou autre."""
    out = []
    if any(s < e["start"] < t for s, t in offs):
        out.append("début : proclitique collé" if text[e["start"] - 1] in PROCLITIQUES else "début : autre")
    if any(s < e["end"] < t for s, t in offs):
        out.append("fin : ponctuation arabe collée" if text[e["end"]] in PONCTUATION_ARABE else "fin : autre")
    return out


def _retrouvee(e: dict, offs: Offsets, text: str, post: bool) -> bool:
    """Vrai si l'entité, alignée seule sur les tokens (et éventuellement corrigée), redonne exactement ses bornes."""
    al = aligner_sur_tokens([e], offs)
    if len(al) != 1:
        return False
    s, t = al[0]["start"], al[0]["end"]
    if post:
        s, t = strip_arabic_proclitics(text, s, t)
    return (s, t) == (e["start"], e["end"])


def mesurer() -> dict[str, Any]:
    """Tokenise le dev avec chaque tokeniseur, chronomètre et calcule les plafonds."""
    gold = charger_dev()
    # chargement des pipelines hors chronomètre
    for lang in ("fr", "en", "ar"):
        pipeline(lang)
    import spacy_stanza

    stanza_tok = spacy_stanza.load_pipeline("ar", processors="tokenize,mwt", verbose=False, download_method=None)
    parse(gold[0]["text"], gold[0]["lang"])

    offs: dict[str, dict[str, Offsets]] = {"cfdata": {}, "spacy/stanza": {}}
    temps: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    ecarts_tok_stanza = 0
    texte_reecrit = 0
    for g in gold:
        pid, text, dl = g["passage_id"], g["text"], g["doc_lang"]
        toks, dt = _chrono(lambda text=text: tokenize(text))
        offs["cfdata"][pid] = [(s, e) for _, s, e in toks]
        temps["cfdata"][dl].append(dt)
        doc, dt = _chrono(lambda g=g: parse(g["text"], g["lang"]))
        offs["spacy/stanza"][pid] = offsets(doc)
        temps["spacy/stanza (analyse complète)"][dl].append(dt)
        if g["lang"] == "ar":
            d2, dt = _chrono(lambda text=text: doc_depuis_stanza(stanza_tok, text))
            temps["stanza tokenize+mwt seul"][dl].append(dt)
            ecarts_tok_stanza += [(t.idx, t.idx + len(t.text)) for t in d2 if not t.is_space] != offsets(doc)
            # Doc produit par spacy-stanza lui-même : son texte diffère-t-il de l'original ?
            texte_reecrit += stanza_tok(text).text != text

    configs = {
        "cfdata": ("cfdata", False),
        "cfdata+strip": ("cfdata", True),
        "spacy/stanza": ("spacy/stanza", False),
        "stanza+strip": ("spacy/stanza", True),
    }
    plafonds = {
        nom: token_ceiling(
            gold,
            tokenize_fn=lambda g, base=base: offs[base][g["passage_id"]],
            post_fn=strip_arabic_proclitics if post else None,
        )
        for nom, (base, post) in configs.items()
    }
    n_tokens = {
        base: {dl: sum(len(offs[base][g["passage_id"]]) for g in gold if g["doc_lang"] == dl) for dl in LANGS}
        for base in offs
    }

    # entités coupées au milieu d'un token par cfdata.common.tokenize
    coupees: Counter = Counter()
    detail: dict[tuple, dict[str, Any]] = {}
    n_coupees: dict[str, Counter] = {base: Counter() for base in offs}
    n_ent: Counter = Counter()
    causes: Counter = Counter()
    for g in gold:
        for e in g["entities"]:
            n_ent[g["doc_lang"]] += 1
            for base in offs:
                if _coupe(e, offs[base][g["passage_id"]]):
                    n_coupees[base][g["doc_lang"]] += 1
            ou = _coupe(e, offs["cfdata"][g["passage_id"]])
            if not ou:
                continue
            cle = (e["label"], e["text"], g["doc_lang"])
            coupees[cle] += 1
            d = detail.setdefault(
                cle, {"exemple": g["passage_id"], "bornes": Counter(), "stanza_coupe": 0, **{c: 0 for c in configs}}
            )
            d["bornes"][ou] += 1
            for c in _causes(e, g["text"], offs["cfdata"][g["passage_id"]]):
                causes[c] += 1
            d["stanza_coupe"] += bool(_coupe(e, offs["spacy/stanza"][g["passage_id"]]))
            for nom, (base, post) in configs.items():
                d[nom] += _retrouvee(e, offs[base][g["passage_id"]], g["text"], post)
    top = [
        {
            "label": lab,
            "texte": txt,
            "doc_lang": dl,
            "occurrences_coupees": n,
            "exemple": detail[(lab, txt, dl)]["exemple"],
            "bornes": dict(detail[(lab, txt, dl)]["bornes"]),
            "coupee_par_stanza": detail[(lab, txt, dl)]["stanza_coupe"],
            "retrouvee": {c: detail[(lab, txt, dl)][c] for c in configs},
        }
        for (lab, txt, dl), n in sorted(coupees.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    ]
    return {
        "n_passages": {dl: sum(g["doc_lang"] == dl for g in gold) for dl in LANGS},
        "n_entites": dict(n_ent),
        "repli_ar": est_repli("ar"),
        "modeles": {**MODELES_SPACY, "ar": "stanza ar (UD PADT), via spacy-stanza"},
        "temps_ms_par_passage": {k: {dl: 1000 * mean(v) for dl, v in d.items()} for k, d in temps.items()},
        "stanza_tokenize_seul_tokens_differents": ecarts_tok_stanza,
        "spacy_stanza_texte_reecrit": texte_reecrit,
        "causes_coupure_cfdata": dict(causes),
        "plafonds": plafonds,
        "n_tokens": n_tokens,
        "entites_coupees": {base: dict(c) for base, c in n_coupees.items()},
        "n_entites_coupees_distinctes": len(coupees),
        "top20_coupees_cfdata": top,
    }


def rapport(m: dict[str, Any]) -> str:
    """Rédige le rapport Markdown à partir des mesures."""
    pl = m["plafonds"]
    meilleur_ar = max(pl, key=lambda k: pl[k]["par_langue"]["ar"])
    t = m["temps_ms_par_passage"]
    L = [
        "# Lot B · B2 — Pipeline linguistique multilingue",
        "",
        f"Mesures sur le dev uniquement ({sum(m['n_passages'].values())} passages : "
        + ", ".join(f"{k} {v}" for k, v in m["n_passages"].items())
        + " ; test gelé non lu). Script : `scripts/profile_pipeline.py` ; module : `caseforge/extraction/nlp.py`.",
        "",
        "## 1. Choix des outils",
        "",
        "| Langue | Outil | Pourquoi |",
        "|---|---|---|",
        "| fr | spaCy `fr_core_news_md` | Pipeline entraîné (tokeniseur à règles, étiquetage, lemmes, dépendances), "
        "rapide sur CPU, offsets de caractères conservés (`token.idx`), vecteurs de mots inclus (taille md) utiles "
        "aux règles par similarité. |",
        "| en | spaCy `en_core_web_md` | Mêmes raisons ; même API que le français, donc même code de règles "
        "(`Matcher`, `EntityRuler`). |",
        "| ar | stanza `ar` (UD PADT) via `spacy-stanza` | spaCy n'a pas de pipeline arabe entraîné : "
        '`spacy.blank("ar")` ne fait que découper sur les blancs et la ponctuation. Stanza segmente les '
        "proclitiques (و، ف، ب، ل، ك) en mots séparés (« multi-word tokens ») et fournit étiquettes et "
        "dépendances UD ; `spacy-stanza` l'expose comme un `Doc` spaCy, donc la même API que fr / en. |",
        "| mixte | découpage en phrases + `cfdata.common.detect_lang` | Les passages mixtes alternent les langues "
        "phrase par phrase (code-switching) ; chaque phrase va au pipeline de sa langue, puis les tokens sont "
        "réunis dans un seul `Doc` (attribut `token._.lang`). |",
        "",
        'Repli : si stanza ou son modèle est indisponible, `parse` passe explicitement à `spacy.blank("ar")` avec un '
        f"avertissement (repli actif pendant cette mesure : {'oui' if m['repli_ar'] else 'non'}). `parse` vérifie que "
        "le texte du `Doc` et l'offset de chaque token correspondent au texte d'origine.",
        "",
        "Contraintes de versions : `spacy-stanza` 1.0.4 (dernière version) exige `stanza < 1.7`, et stanza 1.6 ne "
        "charge pas ses modèles avec torch ≥ 2.6 (`torch.load(weights_only=True)` par défaut). D'où l'épinglage "
        "`stanza==1.6.1` et `torch==2.5.1` dans `requirements-lotb.txt`. Stanza charge alors ses modèles avec "
        "`weights_only=False` (désérialisation pickle) : à réserver aux modèles téléchargés depuis le dépôt officiel "
        "de stanza.",
        "",
        "Écartés pour l'instant : CAMeL Tools et Farasa (segmentation arabe de référence, mais API et formats "
        "propres, sans `Doc` spaCy) ; le tokeniseur du modèle XLM-R (sous-mots, sans offsets de mots ni analyse "
        "syntaxique) relève du Lot C. Ils pourront être comparés avec le même protocole de plafond.",
        "",
        "## 2. Plafond F1 stricte par tokeniseur",
        "",
        "Plafond = F1 stricte des spans gold une fois alignés sur les tokens (un token chevauché par une entité lui "
        "appartient entièrement), puis reconvertis en caractères. C'est le meilleur score strict possible pour un "
        "modèle qui étiquette ces tokens. « +strip » applique `strip_arabic_proclitics` à chaque span reconverti "
        "(guide v2, cas 10 : و ف ب ل ك retirés en tête, « ال » conservé).",
        "",
    ]
    L += _table(
        ["Tokeniseur", "Global", "fr", "ar", "en", "syn_", "lib_"],
        [
            [
                nom,
                f(v["global"]),
                *[f(v["par_langue"][k]) for k in LANGS],
                f(v["par_source"]["syn"]),
                f(v["par_source"]["lib"]),
            ]
            for nom, v in pl.items()
        ],
    )
    ec = m["entites_coupees"]
    L += [
        "",
        "Entités gold dont une borne tombe au milieu d'un token :",
        "",
    ]
    L += _table(
        ["Tokeniseur", *[f"{k} (sur {m['n_entites'][k]})" for k in LANGS], "Tokens fr / ar / en"],
        [
            [
                base,
                *[str(ec[base].get(k, 0)) for k in LANGS],
                " / ".join(str(m["n_tokens"][base][k]) for k in LANGS),
            ]
            for base in ec
        ],
    )
    L += [
        "",
        "## 3. Coût en temps",
        "",
        "Temps moyen par passage, pipelines déjà chargés (CPU, une seule exécution, ordre de grandeur).",
        "",
    ]
    L += _table(
        ["Traitement", *LANGS],
        [[k, *[f"{v[dl]:.2f} ms".replace(".", ",") if dl in v else "—" for dl in LANGS]] for k, v in t.items()],
    )
    L += [
        "",
        "« spacy/stanza (analyse complète) » inclut étiquetage, lemmes et dépendances ; « stanza tokenize+mwt seul » "
        "ne garde que la segmentation (tokens identiques à l'analyse complète sur "
        f"{m['n_passages']['ar'] - m['stanza_tokenize_seul_tokens_differents']} passages arabes sur "
        f"{m['n_passages']['ar']}).",
        "",
        f"Correction nécessaire : sur {m['spacy_stanza_texte_reecrit']} des {m['n_passages']['ar']} passages arabes, "
        "le `Doc` produit par `spacy-stanza` 1.0.4 a un texte différent de l'original (mots d'un token composé "
        "réécrits, « للشركة » -> « ل الشركة »), donc des offsets faux. `parse` reconstruit le `Doc` arabe depuis la "
        "sortie stanza (`doc_depuis_stanza`) et vérifie les offsets de chaque token.",
        "",
        "## 4. Les 20 entités le plus souvent coupées par `cfdata.common.tokenize`",
        "",
        f"{m['n_entites_coupees_distinctes']} entités distinctes (étiquette, texte, langue) ont au moins une "
        "occurrence coupée. Colonnes « retrouvée » : nombre d'occurrences dont les bornes exactes sont retrouvées "
        "après alignement avec chaque tokeniseur. Chaque entité n'apparaît qu'une fois coupée : le classement suit "
        "l'ordre des étiquettes et du texte.",
        "",
        "Causes des bornes coupées par `cfdata.common.tokenize` :",
        "",
    ]
    L += _table(["Cause", "Bornes"], [[k, str(v)] for k, v in sorted(m["causes_coupure_cfdata"].items())])
    L += [
        "",
        "La regex de `cfdata.common.tokenize` accepte tout le bloc Unicode arabe (U+0600–U+06FF) dans un mot : la "
        "virgule « ، », le point-virgule « ؛ » et le point d'interrogation « ؟ » arabes y appartiennent et restent "
        "collés au mot qui précède (« دينار؛ »), comme les proclitiques au mot qui suit. `cfdata/` étant figé, le "
        "Lot B ne le corrige pas : il utilise ses propres tokens (`parse`).",
        "",
    ]
    L += _table(
        [
            "Entité",
            "Étiquette",
            "Langue",
            "Coupées",
            "Borne coupée",
            "Exemple",
            "Retrouvée cfdata+strip",
            "Coupée par stanza/spaCy",
            "Retrouvée stanza+strip",
        ],
        [
            [
                x["texte"].replace("|", "/"),
                x["label"],
                x["doc_lang"],
                str(x["occurrences_coupees"]),
                ", ".join(f"{k} {v}" for k, v in x["bornes"].items()),
                x["exemple"],
                str(x["retrouvee"]["cfdata+strip"]),
                str(x["coupee_par_stanza"]),
                str(x["retrouvee"]["stanza+strip"]),
            ]
            for x in m["top20_coupees_cfdata"]
        ],
    )
    ar = {k: pl[k]["par_langue"]["ar"] for k in pl}
    L += [
        "",
        "## 5. Recommandation pour les lots B et C",
        "",
        f"- **Arabe** : plafond {f(ar['cfdata'])} avec `cfdata.common.tokenize`, {f(ar['cfdata+strip'])} avec "
        f"strip, {f(ar['spacy/stanza'])} avec stanza et {f(ar['stanza+strip'])} avec stanza + strip. Meilleure "
        f"configuration mesurée : **{meilleur_ar}**.",
        f"- **Français / anglais** : plafond {f(pl['cfdata']['par_langue']['fr'])} / "
        f"{f(pl['cfdata']['par_langue']['en'])} avec `cfdata.common.tokenize` contre "
        f"{f(pl['spacy/stanza']['par_langue']['fr'])} / {f(pl['spacy/stanza']['par_langue']['en'])} avec spaCy : "
        "le tokeniseur n'y est pas le facteur limitant.",
        "- **Lot B (règles)** : travailler sur le `Doc` de `parse` (lemmes, étiquettes, dépendances, même API dans "
        "les trois langues) et appliquer `strip_arabic_proclitics` à toute entité arabe produite. Les règles "
        "s'appuient sur des offsets de caractères, donc aucun plafond lié aux tokens ne les contraint si la borne "
        "finale est corrigée.",
        "- **Lot C (modèles BIO)** : la meilleure configuration arabe ci-dessus fixe le plafond strict ; entraîner sur "
        "un BIO recalculé avec ces tokens (et non sur `*.bio.jsonl`, construit avec `cfdata.common.tokenize`) "
        "relève ce plafond, au prix du temps de segmentation stanza indiqué en section 3 (« tokenize+mwt seul » "
        "suffit pour la segmentation). Toujours rapporter le plafond à côté du score (`token_ceiling`).",
        "",
    ]
    return "\n".join(L)


def main() -> None:
    """Mesure, enregistre le JSON et écrit le rapport."""
    m = mesurer()
    ecrire_json(RESULTS / "b2_profile.json", m)
    (REPORTS / "lotb_pipeline_linguistique.md").write_text(rapport(m), encoding="utf-8")
    for nom, v in m["plafonds"].items():
        print(
            f"plafond {nom:<13} global {v['global']:.3f} · " + " ".join(f"{k} {v['par_langue'][k]:.3f}" for k in LANGS)
        )
    for k, v in m["temps_ms_par_passage"].items():
        print(f"temps {k:<34} " + " ".join(f"{dl} {v[dl]:.2f} ms" for dl in LANGS if dl in v))
    print(
        "entités coupées:",
        m["entites_coupees"],
        "| tokens stanza seul ≠ analyse :",
        m["stanza_tokenize_seul_tokens_differents"],
    )


if __name__ == "__main__":
    main()
