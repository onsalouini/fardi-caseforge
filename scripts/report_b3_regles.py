"""B3 — rapport ``reports/lotb_regles_spacy.md`` : règles spaCy / stanza contre B1 (``cfdata.prelabel``) et le CRF.

    python -m scripts.run_b3_regles && python -m scripts.report_b3_regles

Métrique principale : mode token, micro et macro (9) (``CLAUDE.md``, section 6) ; strict et partiel en annexe.
Dev et validation croisée ``lib_`` : scores seulement. Les exemples d'erreurs viennent du TRAIN, jamais du dev.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import Any

from caseforge.eval.bootstrap import paired_bootstrap
from caseforge.eval.data import FINAL, REPORTS, RESULTS, charger_dev, ecrire_json
from caseforge.eval.ner_metrics import MODES, entites_mots, evaluate, tags_mots
from caseforge.extraction.rules import COUCHES
from caseforge.labels import LABELS
from cfdata.common import read_jsonl, tokenize

LANGUES = ("fr", "ar", "en")
SOURCES = ("syn", "lib")
N_ERREURS = 30
_ARTICLE_OU_GENERIQUE = re.compile(
    r"^(?:la|le|les|l'|the)\s|(?:\s|^)(?:site|usine|plant|factory)(?:\s|$)|^(?:مدينة|موقع|مصنع)\s", re.I
)
_PROCLITIQUE_AR = re.compile(r"^[وفبلك](?:ال|م)")


def f(x: float) -> str:
    """Nombre à 3 décimales, virgule décimale."""
    return f"{x:.3f}".replace(".", ",")


def _me(x: dict[str, float]) -> str:
    return f"{f(x['moyenne'])} ± {f(x['ecart_type'])}"


def _table(entete: list[str], lignes: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(entete) + " |", "|" + "---|" * len(entete)] + [
        "| " + " | ".join(r) + " |" for r in lignes
    ]


def _tok(res: dict[str, Any], cle: str = "global", k: str | None = None) -> dict[str, Any]:
    t = res["token"]
    return t[cle] if k is None else t[cle][k]


# ---------- Couverture par règle ----------
def _spans(rows: list[dict]) -> list[tuple[int, int, str]]:
    return [(e["start"], e["end"], e["label"]) for e in rows]


def couverture(gold: list[dict], pred: list[dict]) -> dict[str, dict[str, Any]]:
    """Prédictions et précision (mode token : entité exacte au niveau des mots) par ``rule_id``."""
    pmap = {p["passage_id"]: p for p in pred}
    c: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for g in gold:
        G = entites_mots(tags_mots(g["text"], _spans(g["entities"])))
        for e in pmap[g["passage_id"]]["entities"]:
            E = entites_mots(tags_mots(g["text"], _spans([e])))
            c[e["rule_id"]][0] += 1
            c[e["rule_id"]][1] += bool(E) and E <= G
    total = sum(v[0] for v in c.values())
    return {
        r: {"n": n, "part": n / total if total else 0.0, "precision": ok / n if n else 0.0}
        for r, (n, ok) in sorted(c.items(), key=lambda x: -x[1][0])
    }


# ---------- Erreurs du train ----------
def _surface(text: str, offs: list[tuple[int, int]], e: tuple[int, int, str]) -> str:
    return text[offs[e[0]][0] : offs[e[1] - 1][1]]


def _extrait(text: str, s: int, e: int, marge: int = 35) -> str:
    avant = ("…" if s > marge else "") + text[max(0, s - marge) : s]
    apres = text[e : e + marge] + ("…" if e + marge < len(text) else "")
    return f"{avant}[{text[s:e]}]{apres}".replace("\n", " / ").replace("|", "/")


def cause(kind: str, label: str, gold_surface: str, label_pred: str | None = None) -> str:
    """Cause d'une erreur du train, d'après sa forme (heuristique documentée dans le rapport)."""
    if kind == "étiquette":
        return f"confusion d'étiquette ({label} prédit {label_pred})"
    if kind == "bordure":
        if label in {"SITE", "ORG"} and (
            _ARTICLE_OU_GENERIQUE.search(gold_surface) or _PROCLITIQUE_AR.match(gold_surface)
        ):
            return "écart gold / guide v2 (article, mot générique ou proclitique dans le gold)"
        if len(gold_surface.split()) >= 6:
            return "proposition longue du gold (rédaction libre)"
        return "bordure du span (expansion trop courte ou trop longue)"
    if kind == "manqué":
        if label in {"EQUIPEMENT", "PROCESSUS", "PRODUIT"}:
            return "vocabulaire absent des lexiques"
        if len(gold_surface.split()) >= 6:
            return "proposition longue du gold (rédaction libre)"
        return "aucune règle ne couvre la forme"
    return "inventé : déclencheur hors contexte"


def erreurs_train(train: list[dict], pred: list[dict]) -> list[dict[str, Any]]:
    """Erreurs du mode token sur le train, une par entité gold manquée ou mal bornée et par prédiction inventée."""
    pmap = {p["passage_id"]: p for p in pred}
    out = []
    for g in train:
        text = g["text"]
        offs = [(s, e) for _, s, e in tokenize(text)]
        G = entites_mots(tags_mots(text, _spans(g["entities"])))
        pe = pmap[g["passage_id"]]["entities"]
        P = entites_mots(tags_mots(text, _spans(pe)))
        regle = {}
        for e in pe:
            for x in entites_mots(tags_mots(text, _spans([e]))):
                regle[x] = e["rule_id"]
        for x in sorted(G - P):
            chev = [p for p in P if p[0] < x[1] and x[0] < p[1]]
            meme = [p for p in chev if p[2] == x[2]]
            kind = "bordure" if meme else ("étiquette" if chev else "manqué")
            p = (meme or chev or [None])[0]
            surf = _surface(text, offs, x)
            out.append(
                {
                    "passage_id": g["passage_id"],
                    "type": kind,
                    "label": x[2],
                    "gold": _extrait(text, offs[x[0]][0], offs[x[1] - 1][1]),
                    "pred": _surface(text, offs, p) if p else "—",
                    "rule_id": regle.get(p, "—") if p else "—",
                    "cause": cause(kind, x[2], surf, p[2] if p else None),
                }
            )
        for p in sorted(P - G):
            if any(x[0] < p[1] and p[0] < x[1] for x in G):
                continue  # déjà compté côté gold (bordure ou étiquette)
            out.append(
                {
                    "passage_id": g["passage_id"],
                    "type": "inventé",
                    "label": p[2],
                    "gold": "—",
                    "pred": _extrait(text, offs[p[0]][0], offs[p[1] - 1][1]),
                    "rule_id": regle.get(p, "—"),
                    "cause": cause("inventé", p[2], ""),
                }
            )
    return out


def echantillon(erreurs: list[dict], n: int = N_ERREURS) -> list[dict]:
    """Échantillon déterministe : tour de rôle entre causes ; dans une cause, entre (étiquette, source)."""
    par_cause: dict[str, list[dict]] = {}
    groupes: dict[str, dict[tuple[str, str], list[dict]]] = defaultdict(lambda: defaultdict(list))
    for e in sorted(erreurs, key=lambda e: e["passage_id"]):
        groupes[e["cause"]][(e["label"], e["passage_id"][:3])].append(e)
    for c, g in groupes.items():
        ordre: list[dict] = []
        while any(g.values()):
            for k in sorted(g):
                if g[k]:
                    ordre.append(g[k].pop(0))
        par_cause[c] = ordre
    out: list[dict] = []
    while len(out) < n and any(par_cause.values()):
        for k in sorted(par_cause, key=lambda k: -len(par_cause[k])):
            if par_cause[k] and len(out) < n:
                out.append(par_cause[k].pop(0))
    return out


def ecarts_gold_guide(train: list[dict]) -> dict[str, int]:
    """Spans gold du train contraires au guide v2 (section 6 et cas 10), comptés par forme."""
    c: Counter[str] = Counter()
    for g in train:
        for e in g["entities"]:
            if e["label"] == "SITE":
                c["SITE"] += 1
                gen = bool(_ARTICLE_OU_GENERIQUE.search(e["text"]))
                c["SITE avec article ou mot générique (« la ZI de … », « … site », « مدينة … »)"] += gen
            if e["label"] in {"SITE", "ORG"} and _PROCLITIQUE_AR.match(e["text"]):
                c[f"{e['label']} arabe avec proclitique"] += 1
    return dict(c)


# ---------- Rapport ----------
def main() -> None:  # noqa: C901 - rapport linéaire, section par section
    """Calcule les comparaisons et écrit le rapport."""
    dev = charger_dev()
    train = read_jsonl(FINAL / "train.jsonl")
    b3 = read_jsonl(RESULTS / "b3_regles_dev.jsonl")
    b1 = read_jsonl(RESULTS / "b1_prelabel_dev.jsonl")
    crf = read_jsonl(RESULTS / "b1_crf_dev.jsonl")
    R3, R1, RC = evaluate(dev, b3), evaluate(dev, b1), evaluate(dev, crf)
    ablations = {c: evaluate(dev, read_jsonl(RESULTS / f"b3_regles_dev_sans_{c}.jsonl")) for c in COUCHES}
    cv3 = json.loads((RESULTS / "b3_regles_lib_cv.json").read_text(encoding="utf-8"))
    cv1 = json.loads((RESULTS / "b1_prelabel_lib_cv_token.json").read_text(encoding="utf-8"))
    cv_abl = json.loads((RESULTS / "b3_regles_ablation_lib_cv.json").read_text(encoding="utf-8"))
    boot = {
        f"{nom}_{a}": paired_bootstrap(dev, base, b3, mode="token", average=a)
        for nom, base in (("B1", b1), ("CRF", crf))
        for a in ("micro", "macro_9")
    }
    ecrire_json(RESULTS / "b3_bootstrap.json", boot)
    pred_train = read_jsonl(RESULTS / "b3_regles_train.jsonl")
    R3_train = evaluate(train, pred_train)
    cov_dev, cov_train = couverture(dev, b3), couverture(train, pred_train)
    errs = erreurs_train(train, pred_train)
    ecarts = ecarts_gold_guide(train)
    ecrire_json(
        RESULTS / "b3_regles_resume.json",
        {
            "dev_token": {k: R3["token"][k] for k in ("global", "par_etiquette", "par_langue", "par_source", "mixtes")},
            "train_token_global": R3_train["token"]["global"],
            "couverture_dev": cov_dev,
            "couverture_train": cov_train,
            "erreurs_train_par_cause": Counter(e["cause"] for e in errs),
            "ecarts_gold_guide_train": ecarts,
        },
    )

    systemes = (("B3 règles", R3), ("B1 règles", R1), ("CRF", RC))
    L: list[str] = [
        "# Lot B · B3 — Extraction par règles (regex, matchers, `DependencyMatcher`) sur le dev",
        "",
        f"Dev uniquement ({R3['n_passages']} passages, {R3['n_documents']} documents ; test gelé non lu ; texte du dev "
        "jamais lu : seuls ses scores sont utilisés). **Métrique principale : mode token, micro et macro (9)** "
        "(`CLAUDE.md`, section 6) ; strict et partiel en annexe A. Spécification : `docs/guide_annotation_v2.md`. "
        "Code : `caseforge/extraction/rules/` (`extract_rules(text, lang)`), configuration `configs/rules.yaml`, "
        "lexiques `data/lexicons/*.txt` (source en tête de chaque fichier ; aucune recopie de `cfdata/pools.py`). "
        "Analyse : `caseforge.extraction.nlp.parse` (spaCy fr / en, stanza ar).",
        "",
        "Comparaison : B1 = `cfdata.prelabel` ; CRF = `exemples/baseline_crf.py` (B1). Mêmes prédictions B1 / CRF que "
        "dans `reports/lotb_baseline_regles.md`.",
        "",
        "## 0. Chiffre à battre : B1 en validation croisée `lib_` (mode token)",
        "",
    ]
    L += _table(
        ["Système", "F1 micro (plis)", "F1 macro (9) (plis)", "Regroupé", "fr", "ar", "en"],
        [
            [
                nom,
                _me(cv["token"]["f1_micro"]),
                _me(cv["token"]["f1_macro_9"]),
                f(cv["token"]["regroupe_f1_micro"]),
                *[_me(cv["token"]["par_langue"][k]) for k in LANGUES],
            ]
            for nom, cv in (("B1 règles (à battre)", cv1), ("B3 règles", cv3))
        ],
    )
    L += [
        "",
        f"{cv3['n_plis']} plis, un document `lib_` de train ou de dev laissé de côté par pli ({cv3['n_passages']} "
        "passages, `data/lotb/lib_cv_folds.json`). Les règles n'apprennent rien des plis : la CV mesure seulement la "
        "variabilité entre documents. **Estimation optimiste pour B3** : les documents `lib_` du train ont été lus "
        "pendant la conception des règles (le guide et le train sont les seules sources autorisées). Le dev reste "
        "l'estimation honnête, et la seule part de la CV jamais lue est celle des documents `lib_` du dev.",
        "",
        "## 1. Résultat global (dev, mode token)",
        "",
    ]
    L += _table(
        ["Système", "P micro", "R micro", "F1 micro", "F1 macro (9)", "F1 macro (présentes)"],
        [
            [
                nom,
                f(_tok(r)["micro"]["p"]),
                f(_tok(r)["micro"]["r"]),
                f(_tok(r)["micro"]["f1"]),
                f(_tok(r)["macro_9"]["f1"]),
                f(_tok(r)["macro_presentes"]["f1"]),
            ]
            for nom, r in systemes
        ],
    )
    L += [
        "",
        "Pour mémoire, sur le train (ensemble de conception, optimiste) : B3 token micro "
        f"{f(R3_train['token']['global']['micro']['f1'])}, "
        f"macro (9) {f(R3_train['token']['global']['macro_9']['f1'])}.",
        "",
        "## 2. Par étiquette (dev, mode token)",
        "",
    ]
    L += _table(
        ["Étiquette", "Gold", "B3 P", "B3 R", "B3 F1", "B1 F1", "CRF F1"],
        [
            [
                lab,
                str(R3["token"]["par_etiquette"][lab]["support_gold"]),
                f(R3["token"]["par_etiquette"][lab]["p"]),
                f(R3["token"]["par_etiquette"][lab]["r"]),
                f(R3["token"]["par_etiquette"][lab]["f1"]),
                f(R1["token"]["par_etiquette"][lab]["f1"]),
                f(RC["token"]["par_etiquette"][lab]["f1"]),
            ]
            for lab in LABELS
        ],
    )
    for titre, cle, cles in (
        ("## 3. Par langue (dev, `doc_lang`, mode token)", "par_langue", LANGUES),
        ("## 4. Par source (dev, mode token)", "par_source", SOURCES),
    ):
        L += ["", titre, ""]
        L += _table(
            [
                "Tranche",
                "Passages",
                "Gold",
                "B3 micro",
                "B3 macro (9)",
                "B1 micro",
                "B1 macro (9)",
                "CRF micro",
                "CRF macro (9)",
            ],
            [
                [
                    k,
                    str(_tok(R3, cle, k)["n_passages"]),
                    str(_tok(R3, cle, k)["support_gold"]),
                    *[
                        x
                        for _, r in systemes
                        for x in (f(_tok(r, cle, k)["micro"]["f1"]), f(_tok(r, cle, k)["macro_9"]["f1"]))
                    ],
                ]
                for k in cles
            ],
        )
    mx = {nom: r["token"]["mixtes"] for nom, r in systemes}
    L += ["", "Annexe — passages mixtes (`lang == mixte`, mode token), effectifs et erreurs seulement :", ""]
    L += _table(
        ["Système", "Passages", "Gold", "Manqués (fn)", "Inventés (fp)"],
        [[nom, str(m["n_passages"]), str(m["support_gold"]), str(m["fn"]), str(m["fp"])] for nom, m in mx.items()],
    )
    L += ["", f"n = {mx['B3 règles']['n_passages']} < 30 : aucune conclusion sur la F1.", ""]

    L += ["## 5. Bootstrap apparié (dev, mode token)", ""]
    b0 = next(iter(boot.values()))
    L += _table(
        ["Comparaison", "Moyenne", "Base", "B3", "Δ (B3 − base)", "IC 95 %", "p (unilatérale)"],
        [
            [
                f"B3 contre {k.split('_')[0]}",
                "micro" if b["average"] == "micro" else "macro (9)",
                f(b["f1_a"]),
                f(b["f1_b"]),
                f(b["delta"]),
                f"[{f(b['ic95'][0])} ; {f(b['ic95'][1])}]",
                f"{b['p_value']:.3f}".replace(".", ","),
            ]
            for k, b in boot.items()
        ],
    )
    L += [
        "",
        f"Tirage avec remise de {b0['n_documents']} documents (`doc_id`), {b0['n_resamples']} rééchantillonnages, "
        f"graine {b0['seed']} ; p = probabilité que B3 ne soit pas meilleur que la base.",
        "",
        "## 6. Ablation couche par couche",
        "",
    ]
    lignes = [
        [
            "B3 complet",
            f(_tok(R3)["micro"]["f1"]),
            f(_tok(R3)["macro_9"]["f1"]),
            "—",
            _me(cv3["token"]["f1_micro"]),
            f(cv3["token"]["regroupe_f1_micro"]),
        ]
    ]
    for c in COUCHES:
        r = ablations[c]
        lignes.append(
            [
                f"sans {c}",
                f(_tok(r)["micro"]["f1"]),
                f(_tok(r)["macro_9"]["f1"]),
                f(_tok(r)["micro"]["f1"] - _tok(R3)["micro"]["f1"]),
                _me(cv_abl[c]["token"]["f1_micro"]),
                f(cv_abl[c]["token"]["regroupe_f1_micro"]),
            ]
        )
    L += _table(
        [
            "Configuration",
            "Dev micro",
            "Dev macro (9)",
            "Δ micro (dev)",
            "CV `lib_` micro (plis)",
            "CV `lib_` regroupé",
        ],
        lignes,
    )
    L += [
        "",
        "« sans résolution » : pas de rognage, ni de proclitiques, ni de filtre des génériques, ni de priorité ; seuls "
        "les doublons exacts sont retirés (les chevauchements restent, et le BIO garde la dernière entité par mot).",
        "",
        "## 7. Couverture et précision par règle (`rule_id`)",
        "",
        "Part des prédictions et précision en mode token (entité exacte au niveau des mots). Une règle à faible "
        "précision sur le dev **et** sur le train est candidate au retrait ; on ne retire rien sur le seul dev.",
        "",
    ]
    regles = sorted(set(cov_dev) | set(cov_train), key=lambda r: -cov_train.get(r, {"n": 0})["n"])
    L += _table(
        ["rule_id", "Dev n", "Dev part", "Dev précision", "Train n", "Train précision"],
        [
            [
                f"`{r}`",
                str(cov_dev.get(r, {"n": 0})["n"]),
                f(cov_dev[r]["part"]) if r in cov_dev else "—",
                f(cov_dev[r]["precision"]) if r in cov_dev else "—",
                str(cov_train.get(r, {"n": 0})["n"]),
                f(cov_train[r]["precision"]) if r in cov_train else "—",
            ]
            for r in regles
        ],
    )
    nuisibles = [
        r
        for r in regles
        if r in cov_dev and r in cov_train and cov_dev[r]["precision"] < 0.5 and cov_train[r]["precision"] < 0.5
    ]
    L += [
        "",
        "Règles sous 0,5 de précision sur le dev et sur le train : "
        + (", ".join(f"`{r}`" for r in nuisibles) if nuisibles else "aucune")
        + ".",
        "",
        f"## 8. Erreurs du TRAIN ({N_ERREURS}, classées par cause)",
        "",
        "Exemples tirés du train uniquement (le texte du dev n'est jamais lu). Erreurs du mode token : « manqué » = "
        "entité gold sans prédiction qui la chevauche ; « bordure » = même étiquette, mots différents ; « étiquette » "
        "= chevauchement d'une autre étiquette ; « inventé » = prédiction sans aucune entité gold. Cause attribuée par "
        "une heuristique sur la forme du span (`cause` dans le script). Répartition sur toutes les erreurs du train :",
        "",
    ]
    rep = Counter(e["cause"] for e in errs)
    L += _table(["Cause", "Erreurs"], [[k, str(v)] for k, v in rep.most_common()])
    L += [""]
    L += _table(
        ["Passage", "Type", "Étiquette", "Gold (en contexte)", "Prédiction", "rule_id", "Cause"],
        [
            [e["passage_id"], e["type"], e["label"], e["gold"], e["pred"], f"`{e['rule_id']}`", e["cause"]]
            for e in echantillon(errs)
        ],
    )
    L += [
        "",
        "## 9. Écarts entre le gold du train et le guide v2 (défaut du Lot A, non corrigé)",
        "",
        "Les règles suivent le guide v2 : le mot générique (« site », « usine », « plant ») et l'article restent hors "
        "du SITE (section 6, « Ksar Hellal site »), les proclitiques arabes hors du span (cas 10 : « بمدينة صفاقس » -> "
        "« صفاقس »). Le gold du train ne le fait pas toujours :",
        "",
    ]
    L += _table(["Forme (train)", "Spans gold"], [[k, str(v)] for k, v in sorted(ecarts.items())])
    L += [
        "",
        "Ces écarts coûtent des bordures en mode token et en strict ; ils sont signalés dans `experiments.md` "
        "(CLAUDE.md, section 1 : on ne corrige pas `data/final/`). Autre écart vu dans le train : « NCR-0932 », "
        "exemple de DONNEE_SENSIBLE du guide, n'est pas annoté dans un en-tête de rapport.",
        "",
        "## Annexe A — Modes strict et partiel (dev)",
        "",
    ]
    L += _table(
        ["Système", "Mode", "P micro", "R micro", "F1 micro", "F1 macro (9)"],
        [
            [
                nom,
                m,
                f(r[m]["global"]["micro"]["p"]),
                f(r[m]["global"]["micro"]["r"]),
                f(r[m]["global"]["micro"]["f1"]),
                f(r[m]["global"]["macro_9"]["f1"]),
            ]
            for nom, r in systemes
            for m in MODES
            if m != "token"
        ],
    )
    L += [""]
    L += _table(
        ["Étiquette", "B3 strict", "B3 partiel", "B1 strict", "CRF strict"],
        [
            [
                lab,
                f(R3["strict"]["par_etiquette"][lab]["f1"]),
                f(R3["partiel"]["par_etiquette"][lab]["f1"]),
                f(R1["strict"]["par_etiquette"][lab]["f1"]),
                f(RC["strict"]["par_etiquette"][lab]["f1"]),
            ]
            for lab in LABELS
        ],
    )
    for titre, cle, cles in (("Par langue", "par_langue", LANGUES), ("Par source", "par_source", SOURCES)):
        L += ["", f"**{titre}**", ""]
        L += _table(
            ["Tranche", "B3 strict", "B3 partiel", "B1 strict", "CRF strict"],
            [
                [
                    k,
                    f(R3["strict"][cle][k]["micro"]["f1"]),
                    f(R3["partiel"][cle][k]["micro"]["f1"]),
                    f(R1["strict"][cle][k]["micro"]["f1"]),
                    f(RC["strict"][cle][k]["micro"]["f1"]),
                ]
                for k in cles
            ],
        )
    L += [""]
    (REPORTS / "lotb_regles_spacy.md").write_text("\n".join(L), encoding="utf-8")
    print(f"Rapport écrit : {REPORTS / 'lotb_regles_spacy.md'}")
    _imprimer(systemes, boot, cv1, cv3, ablations, R3)


def _imprimer(systemes: Any, boot: dict, cv1: dict, cv3: dict, ablations: dict, R3: dict) -> None:
    """Chiffres clés pour le journal (aucun texte de passage)."""
    for nom, r in systemes:
        t = r["token"]
        print(
            f"{nom}: micro {t['global']['micro']['f1']:.3f} macro9 {t['global']['macro_9']['f1']:.3f} | "
            + " ".join(
                f"{k} {t['par_langue'][k]['micro']['f1']:.3f}/{t['par_langue'][k]['macro_9']['f1']:.3f}"
                for k in LANGUES
            )
            + " | "
            + " ".join(
                f"{k} {t['par_source'][k]['micro']['f1']:.3f}/{t['par_source'][k]['macro_9']['f1']:.3f}"
                for k in SOURCES
            )
        )
        print("   " + " ".join(f"{lab} {t['par_etiquette'][lab]['f1']:.3f}" for lab in LABELS))
    for nom, cv in (("B1", cv1), ("B3", cv3)):
        print(
            f"lib CV {nom}: micro {cv['token']['f1_micro']['moyenne']:.3f}±{cv['token']['f1_micro']['ecart_type']:.3f} "
            f"macro9 {cv['token']['f1_macro_9']['moyenne']:.3f}±{cv['token']['f1_macro_9']['ecart_type']:.3f} "
            f"regroupé {cv['token']['regroupe_f1_micro']:.3f} | "
            + " ".join(f"{k} {cv['token']['par_langue'][k]['moyenne']:.3f}" for k in LANGUES)
        )
    for k, b in boot.items():
        print(f"bootstrap {k}: delta {b['delta']:.3f} IC [{b['ic95'][0]:.3f}; {b['ic95'][1]:.3f}] p {b['p_value']:.3f}")
    for c, r in ablations.items():
        print(
            f"sans {c}: micro {r['token']['global']['micro']['f1']:.3f} "
            f"macro9 {r['token']['global']['macro_9']['f1']:.3f}"
        )
    print(f"strict {R3['strict']['global']['micro']['f1']:.3f} partiel {R3['partiel']['global']['micro']['f1']:.3f}")


if __name__ == "__main__":
    main()
