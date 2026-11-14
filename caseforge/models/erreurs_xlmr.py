"""Lot C (Silver) · Analyse d'erreurs du NER XLM-R fine-tuné, sur le DEV (prédictions déjà calculées).

    python -m caseforge.models.erreurs_xlmr

Entrées : `data/final/dev.jsonl` (gold) et `reports/predictions/xlmr_dev_s{13,42,2026}.jsonl` (XLM-R complet,
3 graines). Aucune donnée de test n'est lue. Sortie : `reports/lotC_erreurs_xlmr.md`.

Chaque entité est classée avec l'appariement du harnais (`caseforge/eval/ner_metrics.py`), au caractère :
  - correcte : mêmes bornes et même étiquette (appariement strict) ;
  - bornes : même étiquette, bornes différentes (chevauchement d'au moins un caractère) ;
  - étiquette : chevauchement avec une prédiction d'une autre étiquette (confusion) ;
  - manquée : aucune prédiction ne la chevauche ;
  - en trop : prédiction qui ne chevauche aucune entité de référence.
Une entité sensible (`SENSITIVE_LABELS`) manquée est une fuite potentielle pour l'anonymisation (Lot B).
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path

from caseforge.eval.data import charger_dev
from caseforge.eval.ner_metrics import _greedy, _spans, completer_predictions, match_strict, source_of
from caseforge.labels import LABELS, SENSITIVE_LABELS
from cfdata.common import read_jsonl

GRAINES = (13, 42, 2026)
PREDICTIONS = "reports/predictions/xlmr_dev_s{}.jsonl"
TROP = "en trop"
CATEGORIES = ("bornes", "étiquette", "manquée", TROP)
LANGUES = ("fr", "ar", "en")
SOURCES = ("syn", "lib")
Span = tuple[int, int, str]
Apparieur = Callable[[Sequence[Span], Sequence[Span]], list[tuple[int, int]]]


def classer(gold: Sequence[Span], pred: Sequence[Span]) -> list[tuple[str, Span | None, Span | None]]:
    """Catégorie de chaque entité gold et de chaque prédiction : (catégorie, gold, prédiction)."""
    etapes: list[tuple[str, Apparieur]] = [
        ("correcte", match_strict),
        ("bornes", lambda g, p: _greedy(g, p, meme_etiquette=True)),
        ("étiquette", lambda g, p: _greedy(g, p, meme_etiquette=False)),
    ]
    sortie: list[tuple[str, Span | None, Span | None]] = []
    restes_g, restes_p = list(range(len(gold))), list(range(len(pred)))
    for categorie, apparier in etapes:
        sous_g, sous_p = [gold[i] for i in restes_g], [pred[j] for j in restes_p]
        paires = apparier(sous_g, sous_p)
        sortie += [(categorie, sous_g[i], sous_p[j]) for i, j in paires]
        pris_g, pris_p = {restes_g[i] for i, _ in paires}, {restes_p[j] for _, j in paires}
        restes_g = [i for i in restes_g if i not in pris_g]
        restes_p = [j for j in restes_p if j not in pris_p]
    sortie += [("manquée", gold[i], None) for i in restes_g]
    sortie += [(TROP, None, pred[j]) for j in restes_p]
    return sortie


def erreurs(gold_rows: list[dict], graine: int) -> list[dict]:
    """Toutes les entités classées d'une graine, avec le contexte du passage."""
    preds, _ = completer_predictions(gold_rows, read_jsonl(PREDICTIONS.format(graine)))
    sortie = []
    for g, p in zip(gold_rows, preds, strict=True):
        for categorie, sg, sp in classer(_spans(g), _spans(p)):
            span = sg if sg is not None else sp
            sortie.append(
                {
                    "categorie": categorie,
                    "gold": sg,
                    "pred": sp,
                    "label": span[2] if span else "",
                    "langue": g["doc_lang"],
                    "source": source_of(g["doc_id"]),
                    "passage_id": g["passage_id"],
                    "texte": g["text"],
                }
            )
    return sortie


def coupe_un_mot(texte: str, span: Span | None) -> bool:
    """La prédiction commence ou finit au milieu d'un mot (frontière de sous-mot mal reconvertie en caractères)."""
    if span is None:
        return False
    debut, fin = span[0], span[1]
    coupe_debut = 0 < debut < len(texte) and texte[debut - 1].isalnum() and texte[debut].isalnum()
    coupe_fin = 0 < fin < len(texte) and texte[fin - 1].isalnum() and texte[fin].isalnum()
    return coupe_debut or coupe_fin


def extrait(texte: str, span: Span | None) -> str:
    """Texte d'un span, prêt pour un tableau Markdown, suivi de son étiquette."""
    if span is None:
        return "–"
    return texte[span[0] : span[1]].replace("|", "/").replace("\n", " ") + f" ({span[2]})"


def tableau(titre: str, lignes: Sequence[str], compte: Counter, colonnes: Sequence[str]) -> list[str]:
    """Tableau Markdown : une ligne par groupe, une colonne par catégorie, puis le total des erreurs."""
    out = [f"| {titre} | " + " | ".join(colonnes) + " | Erreurs |", "|---|" + "---|" * (len(colonnes) + 1)]
    for ligne in lignes:
        valeurs = [compte[(ligne, c)] for c in colonnes]
        out.append(f"| {ligne} | " + " | ".join(map(str, valeurs)) + f" | {sum(valeurs[1:])} |")
    return out


def exemples(cas: list[dict], n: int) -> list[dict]:
    """n exemples au plus, en alternant documents simulés et textes libres."""
    syn, lib = [e for e in cas if e["source"] == "syn"], [e for e in cas if e["source"] == "lib"]
    alternes = [e for paire in zip(syn, lib, strict=False) for e in paire]
    return (alternes + syn[len(lib) :] + lib[len(syn) :])[:n]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="reports/lotC_erreurs_xlmr.md")
    ap.add_argument("--exemples", type=int, default=3, help="exemples par catégorie et par langue (graine 42)")
    args = ap.parse_args()

    gold = charger_dev()
    par_graine = {g: erreurs(gold, g) for g in GRAINES}
    e42 = par_graine[42]
    colonnes = ("correcte", *CATEGORIES)
    nb = {g: sum(e["categorie"] != "correcte" for e in es) for g, es in par_graine.items()}
    lignes = [
        "# Lot C · Analyse d'erreurs du NER XLM-R fine-tuné (dev)",
        "",
        "XLM-R base fine-tuné (Lot C, `caseforge/models/xlmr_ner.py`), prédictions "
        "`reports/predictions/xlmr_dev_s*.jsonl`, gold `data/final/dev.jsonl`. Le test gelé n'est pas utilisé. "
        "Appariement au caractère, comme le harnais (`caseforge/eval/ner_metrics.py`) : correcte (strict), bornes, "
        "étiquette (confusion), manquée, en trop. Script : `python -m caseforge.models.erreurs_xlmr`.",
        "",
        "Erreurs par graine : " + " ; ".join(f"{g} : {n}" for g, n in nb.items()) + ". Les tableaux suivants portent "
        "sur la graine 42 ; les catégories sont stables d'une graine à l'autre (section 5).",
        "",
        "## 1. Par étiquette (graine 42)",
        "",
    ]
    lignes += tableau("Étiquette", LABELS, Counter((e["label"], e["categorie"]) for e in e42), colonnes)
    lignes += ["", "## 2. Par langue (graine 42)", ""]
    lignes += tableau("Langue", LANGUES, Counter((e["langue"], e["categorie"]) for e in e42), colonnes)
    lignes += ["", "## 3. Par source (graine 42)", ""]
    lignes += tableau("Source", SOURCES, Counter((e["source"], e["categorie"]) for e in e42), colonnes)
    confusions = Counter((e["gold"][2], e["pred"][2]) for e in e42 if e["categorie"] == "étiquette")
    lignes += ["", "## 4. Confusions d'étiquette (graine 42)", "", "| Gold → prédit | n |", "|---|---|"]
    lignes += [f"| {g} → {p} | {n} |" for (g, p), n in confusions.most_common(10)]
    sens = [e for e in e42 if e["categorie"] == "manquée" and e["label"] in SENSITIVE_LABELS]
    lignes += [
        "",
        f"Entités **sensibles manquées** (fuite potentielle si XLM-R anonymisait seul) : {len(sens)} "
        f"({', '.join(f'{lab} {n}' for lab, n in Counter(e['label'] for e in sens).most_common())}).",
        "",
        "## 5. Stabilité sur les 3 graines",
        "",
        "| Catégorie | " + " | ".join(f"graine {g}" for g in GRAINES) + " |",
        "|---|" + "---|" * len(GRAINES),
    ]
    for c in colonnes:
        valeurs = [str(sum(e["categorie"] == c for e in par_graine[g])) for g in GRAINES]
        lignes.append(f"| {c} | " + " | ".join(valeurs) + " |")
    lignes += [
        "",
        f"## 6. Exemples catégorisés (graine 42, {args.exemples} par catégorie et par langue au plus)",
        "",
        "| # | Catégorie | Langue | Source | Passage | Gold | Prédit |",
        "|---|---|---|---|---|---|---|",
    ]
    i = 0
    for c in CATEGORIES:
        for lang in LANGUES:
            for e in exemples([e for e in e42 if e["categorie"] == c and e["langue"] == lang], args.exemples):
                i += 1
                g, p = extrait(e["texte"], e["gold"]), extrait(e["texte"], e["pred"])
                lignes.append(f"| {i} | {c} | {lang} | {e['source']} | {e['passage_id']} | {g} | {p} |")

    erreurs42 = [e for e in e42 if e["categorie"] != "correcte"]
    coupes = [e for e in erreurs42 if coupe_un_mot(e["texte"], e["pred"])]
    ponctuation = [
        e
        for e in erreurs42
        if e["categorie"] == "bornes"
        and e["texte"][e["pred"][0] : e["pred"][1]].strip(" .,;:،؛") == e["texte"][e["gold"][0] : e["gold"][1]]
    ]
    par_cat = Counter(e["categorie"] for e in erreurs42)
    par_label = Counter((e["label"], e["categorie"]) for e in erreurs42)
    bornes = sorted(LABELS, key=lambda lab: -par_label[(lab, "bornes")])[:2]
    trop = sorted(LABELS, key=lambda lab: -par_label[(lab, TROP)])[:3]
    lignes += [
        "",
        "## 7. Lecture",
        "",
        f"- Les {len(erreurs42)} erreurs de la graine 42 : "
        + ", ".join(f"{c} {par_cat[c]}" for c in CATEGORIES)
        + ". Les **bornes** dominent : l'entité est trouvée mais découpée autrement que la référence, surtout pour "
        f"{bornes[0]} ({par_label[(bornes[0], 'bornes')]}) et {bornes[1]} ({par_label[(bornes[1], 'bornes')]}), "
        "entités longues dont le guide fixe des bornes larges (indicateur avec sa valeur, donnée sensible complète). "
        f"Parmi elles, **{len(ponctuation)} ne diffèrent que par la ponctuation** (point final ou virgule inclus par "
        "XLM-R, exclus par le guide) : un post-traitement qui retire la ponctuation aux bornes les corrigerait.",
        "- Les prédictions **en trop** viennent surtout de "
        + ", ".join(f"{lab} ({par_label[(lab, TROP)]})" for lab in trop)
        + " : termes métier plausibles que la référence n'annote pas.",
        f"- **{len(coupes)} prédictions coupent un mot** (début ou fin au milieu d'un mot, par exemple « vacuum ba », "
        "« sphogypse ») : frontières de sous-mots du tokeniseur de XLM-R mal reconverties en caractères. Piste : "
        "étendre chaque prédiction aux limites du mot avant l'évaluation et l'anonymisation.",
        f"- Les confusions d'étiquette sont rares ({par_cat['étiquette']}) et dispersées ; les entités sensibles "
        f"manquées sont peu nombreuses ({len(sens)}), d'où l'intérêt de XLM-R pour l'anonymisation en union avec les "
        "règles (Lot B, B14).",
        "- Mêmes tendances sur les graines 13 et 2026 (section 5).",
    ]
    Path(args.out).write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"{nb} erreurs par graine ; {i} exemples ; {len(coupes)} mots coupés -> {args.out}")


if __name__ == "__main__":
    main()
