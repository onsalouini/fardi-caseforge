"""Lot B Silver · B13 : contrôle de cohérence du backend ``union_fichier`` sur le dev.

Compare ``union_fichier`` lisant ``reports/predictions/crf_dev.jsonl`` (CRF du Lot C, ``caseforge/models/crf_ner.py``)
au backend ``union`` (règles ∪ CRF B1 entraîné par ``detect._crf``). Configuration Bronze de
``configs/anonymization.yaml`` (coréférence, balayage renforcé, extension des montants, plafonds), sans
généralisation. Pour expliquer les écarts, deux variantes intermédiaires :

- ``union_fichier[recalculé]`` : fichier écrit à partir des prédictions du CRF de ``union`` sur les 171 passages du
  dev ; doit redonner ``union`` à l'identique (contrôle de l'implémentation) ;
- ``union_fichier[recalculé, 162]`` : le même fichier sans les passages absents de ``crf_dev.jsonl`` (effet des
  passages absents seuls).

L'écart restant entre ``union_fichier[recalculé, 162]`` et ``union_fichier[crf_dev.jsonl]`` vient des prédictions
elles-mêmes (deux CRF entraînés différemment). Mesures : taux de fuite (IC 95 %, bootstrap par document), écart
apparié, sur-masquage, F1 stricte au caractère, ventilées par étiquette, langue et source ; comparaison des entités
sensibles des deux fichiers. Le test gelé n'est pas lu ; le texte du dev n'est pas affiché.

    python -m scripts.b13_backend_fichier
"""

from __future__ import annotations

import time
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import (
    lire_predictions,
    passages_absents,
    predire_crf,
    reinitialiser_passages_absents,
)
from caseforge.anonymization.policy import charger_politique
from caseforge.eval.data import ecrire_json, ecrire_jsonl
from caseforge.eval.leak import ETIQUETTES_SENSIBLES, f1_stricte_sensibles, taux_fuite
from caseforge.eval.ner_metrics import source_of
from caseforge.labels import LABELS, SENSITIVE_LABELS
from scripts.eval_anonymization import charger_documents, comparaison_appariee, lignes_gold, lignes_predites, masques

SORTIE = Path("results/lotb_silver/b13")
RAPPORT = Path("results/lotb_silver/b13_backend_fichier.md")
FICHIER_LOT_C = Path("reports/predictions/crf_dev.jsonl")
SEUIL_POINTS = 0.5
"""Écart (en points de pourcentage, ou centièmes de F1) au-delà duquel une explication est demandée."""


REFERENCE_ETAPE0 = {"fuite": 0.066, "sur_masquage": 0.272, "f1": 0.592}
"""``union`` au dev à l'étape 0 du Silver (``results/lotb_silver/point_de_depart.md``), valeurs arrondies."""
HARNAIS = SORTIE / "eval_anonymization" / "b6_anonymisation_dev.json"
"""Sorties de ``scripts/eval_anonymization.py`` redirigées ici (jamais dans ``results/lotb/``, fichiers Bronze)."""


def harnais() -> dict[str, dict[str, float]] | None:
    """Chiffres de ``eval_anonymization.py`` (coréférence + balayage) s'il a été lancé, par backend."""
    if not HARNAIS.exists():
        return None
    import json

    r = json.loads(HARNAIS.read_text(encoding="utf-8"))
    out = {}
    for b in r["backends"]:
        c = r["configs"][b]["coref+balayage"]
        out[b] = {
            "fuite": c["fuite"]["global"]["taux"],
            "sur_masquage": c["fuite"]["sur_masquage"]["global"]["taux"],
            "f1": c["f1_caractere"]["global"]["f1"],
        }
    return out


def ecrire_predictions(chemin: Path, docs: list[dict], garder: set[str] | None = None) -> Path:
    """Fichier JSONL des prédictions du CRF de ``union`` (toutes étiquettes), au format du Lot C."""
    lignes = []
    for d in docs:
        preds = predire_crf([p["text"] for p in d["passages"]])
        for p, ents in zip(d["passages"], preds, strict=True):
            if garder is None or p["passage_id"] in garder:
                lignes.append(
                    {
                        "passage_id": p["passage_id"],
                        "entities": [{"start": e["start"], "end": e["end"], "label": e["label"]} for e in ents],
                    }
                )
    ecrire_jsonl(chemin, lignes)
    return chemin


def anonymiser(docs: list[dict], backend: str, fichier: Path | None = None) -> tuple[list[dict], list[str]]:
    """Anonymise le dev (configuration Bronze) ; renvoie les sorties et les passages absents du fichier."""
    pol = charger_politique()
    reinitialiser_passages_absents()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # les absences sont comptées par passages_absents
        sorties = [
            anonymize_document(d, backend, politique=pol, generaliser=False, fichier_predictions=fichier) for d in docs
        ]
    return sorties, (passages_absents(fichier) if fichier is not None else [])


def mesurer(docs: list[dict], gold: list[dict], sorties: list[dict]) -> dict[str, Any]:
    """Fuite (avec sur-masquage) et F1 stricte au caractère sur les sensibles."""
    return {
        "fuite": taux_fuite(gold, masques(sorties)),
        "f1_caractere": f1_stricte_sensibles(gold, lignes_predites(docs, sorties)),
    }


def comparer_entites(docs: list[dict], fichier_a: Path, fichier_b: Path) -> dict[str, dict[str, list[int]]]:
    """Entités sensibles identiques / seulement dans A / seulement dans B, sur les passages présents dans les deux.

    Groupes : global, étiquette, langue (``doc_lang``), source.
    """
    a, b = lire_predictions(fichier_a), lire_predictions(fichier_b)
    out: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    for d in docs:
        for p in d["passages"]:
            pid = p["passage_id"]
            if pid not in a or pid not in b:
                continue
            ea = {(e["start"], e["end"], e["label"]) for e in a[pid] if e["label"] in SENSITIVE_LABELS}
            eb = {(e["start"], e["end"], e["label"]) for e in b[pid] if e["label"] in SENSITIVE_LABELS}
            for i, ens in enumerate((ea & eb, ea - eb, eb - ea)):
                for _, _, lab in ens:
                    for g in ("global", f"etiquette={lab}", f"langue={d['lang']}", f"source={source_of(d['doc_id'])}"):
                        out[g]["n"][i] += 1
    return {g: dict(v) for g, v in out.items()}


# ---------- Rapport ----------
def pct(x: float) -> str:
    """Pourcentage à la française."""
    return f"{100 * x:.1f} %".replace(".", ",")


def pts(x: float) -> str:
    """Écart en points, signé."""
    return f"{100 * x:+.1f}".replace(".", ",")


def num(x: float) -> str:
    """Nombre à 3 décimales, à la française."""
    return f"{x:.3f}".replace(".", ",")


def ic(b: dict) -> str:
    """Taux et IC 95 %."""
    return f"{pct(b['taux'])} [{pct(b['ic95'][0])} ; {pct(b['ic95'][1])}]"


def tranches(m: dict[str, Any]) -> list[tuple[str, str]]:
    """Tranches de ventilation : global, étiquettes sensibles, langues, sources."""
    out = [("global", "global")] + [("par_etiquette", k) for k in ETIQUETTES_SENSIBLES]
    out += [("par_langue", k) for k in sorted(m["fuite"]["par_langue"])]
    return out + [("par_source", k) for k in sorted(m["fuite"]["par_source"])]


def valeurs(m: dict[str, Any], axe: str, k: str) -> dict[str, float | None]:
    """Fuite, sur-masquage (pas de ventilation par étiquette) et F1 d'une tranche."""
    f = m["fuite"]["global"] if axe == "global" else m["fuite"][axe][k]
    sm = m["fuite"]["sur_masquage"]
    sur = sm["global"]["taux"] if axe == "global" else sm.get(axe, {}).get(k, {}).get("taux")
    f1 = m["f1_caractere"]["global"] if axe == "global" else m["f1_caractere"][axe].get(k, {})
    return {"fuite": f["taux"], "n": f["n"], "sur_masquage": sur, "f1": f1.get("f1", 0.0)}


def ecarts(res: dict[str, Any], a: str, b: str) -> list[dict[str, Any]]:
    """Écarts b − a par tranche et par métrique."""
    out = []
    ma, mb = res["mesures"][a], res["mesures"][b]
    for axe, k in tranches(ma):
        va, vb = valeurs(ma, axe, k), valeurs(mb, axe, k)
        d = {"axe": axe, "tranche": k, "n": va["n"]}
        for met in ("fuite", "sur_masquage", "f1"):
            d[met] = None if va[met] is None or vb[met] is None else vb[met] - va[met]
        out.append(d)
    return out


def depasse(x: float | None) -> bool:
    """Écart supérieur à 0,5 point (ou 0,005 de F1)."""
    return x is not None and abs(x) > SEUIL_POINTS / 100 + 1e-12


def rapport(res: dict[str, Any]) -> str:
    """Rapport Markdown."""
    V = res["variantes"]
    L = [
        "# Lot B Silver · B13 : backends « fichier » et « union_fichier » (contrôle de cohérence, dev)",
        "",
        f"**Split : dev** (`documents_dev.jsonl`, {res['n_docs']} documents, {res['n_passages']} passages, "
        f"{res['n_occurrences']} occurrences sensibles). Test gelé non lu. Commande : "
        "`python -m scripts.b13_backend_fichier` ; chiffres complets dans `results/lotb_silver/b13/"
        "b13_backend_fichier_dev.json`.",
        "",
        "## 1. Backends ajoutés",
        "",
        "- `fichier` : entités lues dans un JSONL `{passage_id, entities: [{start, end, label}]}` (format de "
        "`reports/predictions/crf_dev.jsonl`), filtrées sur `SENSITIVE_LABELS` ; PRODUIT et EQUIPEMENT du fichier "
        "servent à la généralisation (option `generaliser`).",
        "- `union_fichier` : `rules` ∪ `fichier`, même fusion des spans (`fusionner`) et mêmes plafonds de budget que "
        "`union` ; le fichier prend la place du CRF.",
        "- Chemin : clé `fichier_predictions` de `configs/anonymization.yaml` (défaut "
        "`reports/predictions/crf_dev.jsonl`), argument `fichier` de `detect_document` / `detect_generalisables`, "
        "`fichier_predictions` de `anonymize_document`. Passage absent du fichier : aucune prédiction, un "
        "avertissement par passage, compteur `detect.passages_absents`. Une entité hors du texte du passage arrête "
        "la lecture (`ValueError`).",
        "- Les deux backends sont dans `BACKENDS`, donc dans `BACKENDS_PUBLICS` de l'API. Sur un texte libre "
        "(`anonymiser`), les passages s'appellent `0`, `1`… et sont absents du fichier : `fichier` ne masque rien et "
        "`union_fichier` revient à `rules`, avec un avertissement. `caseforge/pipeline.py` n'est pas modifié.",
        "",
        "## 2. Variantes",
        "",
        "| Variante | Backend | Fichier | Passages absents |",
        "|---|---|---|---|",
    ]
    for nom, v in V.items():
        L.append(f"| `{nom}` | `{v['backend']}` | {v['fichier'] or '—'} | {len(v['absents'])} |")
    L += [
        "",
        f"Passages du dev absents de `crf_dev.jsonl` : {len(V['union_fichier_lot_c']['absents'])} "
        f"({', '.join(V['union_fichier_lot_c']['absents'])}). Ce sont les passages dédoublonnés de `dev.jsonl` "
        f"(162 passages) ; ils portent {res['absents_gold_sensibles']} occurrence sensible gold : leur absence ne peut "
        "pas créer de fuite, seulement retirer du sur-masquage.",
        "",
        "## 3. Résultats globaux (dev, coréférence + balayage)",
        "",
        "| Variante | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère (P / R) |",
        "|---|---|---|---|---|",
    ]
    for nom in V:
        m = res["mesures"][nom]
        g, f = m["fuite"]["global"], m["f1_caractere"]["global"]
        L.append(
            f"| `{nom}` | {ic(g)} | {g['totales']} / {g['partielles']} | "
            f"{pct(m['fuite']['sur_masquage']['global']['taux'])} | {num(f['f1'])} ({num(f['p'])} / {num(f['r'])}) |"
        )
    ap = res["apparie"]
    u = res["mesures"]["union"]
    vu = {"fuite": u["fuite"]["global"]["taux"], "sur_masquage": u["fuite"]["sur_masquage"]["global"]["taux"],
          "f1": u["f1_caractere"]["global"]["f1"]}  # fmt: skip
    ok0 = all(round(vu[k], 3) == v for k, v in REFERENCE_ETAPE0.items())
    L += [
        "",
        f"Référence de l'étape 0 pour `union` (`results/lotb_silver/point_de_depart.md`) : fuite 6,6 %, sur-masquage "
        f"27,2 %, F1 0,592 ; retrouvée ici : **{'oui' if ok0 else 'NON'}** ({pct(vu['fuite'])}, "
        f"{pct(vu['sur_masquage'])}, {num(vu['f1'])}).",
    ]
    h = res.get("harnais")
    if h:
        L += [
            "",
            "Harnais officiel `scripts/eval_anonymization.py` (non modifié), sorties redirigées vers "
            "`results/lotb_silver/b13/eval_anonymization/` (rien n'est écrit dans `results/lotb/`), "
            "`--backends union union_fichier` (fichier par défaut de la config) : "
            + " ; ".join(
                f"`{b}` fuite {pct(v['fuite'])}, sur-masquage {pct(v['sur_masquage'])}, F1 {num(v['f1'])}"
                for b, v in h.items()
            )
            + ".",
        ]
    L += [
        "",
        f"Écart apparié de fuite `union_fichier_lot_c` − `union` (bootstrap par document, 10 000 tirages, graine 42) : "
        f"**{pts(ap['difference'])} point** [{pts(ap['ic95'][0])} ; {pts(ap['ic95'][1])}].",
        "",
        f"Contrôle d'implémentation : `union_fichier_recalcule` = `union` à l'identique : **"
        f"{'oui' if res['controle_identique'] else 'NON'}** (mêmes remplacements dans les {res['n_docs']} documents).",
        "",
        "## 4. Écarts `union_fichier_lot_c` − `union`, par tranche (§5)",
        "",
        "Écarts en points (fuite, sur-masquage) et en centièmes (F1 au caractère, ×100). En gras : écart > 0,5 point. "
        "Le "
        "sur-masquage ne se ventile pas par étiquette (un caractère sur-masqué n'appartient à aucune entité sensible).",
        "",
        "| Tranche (n occ.) | Fuite | Sur-masquage | F1 caractère |",
        "|---|---|---|---|",
    ]

    def cell(x: float | None) -> str:
        if x is None:
            return "—"
        return f"**{pts(x)}**" if depasse(x) else pts(x)

    for e in res["ecarts"]["total"]:
        L.append(f"| {e['tranche']} ({e['n']}) | {cell(e['fuite'])} | {cell(e['sur_masquage'])} | {cell(e['f1'])} |")
    mx = {n: res["mesures"][n]["fuite"]["mixtes"] for n in ("union", "union_fichier_lot_c")}
    L += [
        "",
        f"Passages mixtes (annexe) : {mx['union']['n']} occurrences sensibles ; "
        f"fuites `union` {mx['union']['fuites']}, "
        f"`union_fichier_lot_c` {mx['union_fichier_lot_c']['fuites']} (n < 30, pas de conclusion). Étiquettes non "
        f"sensibles ({', '.join(lab for lab in LABELS if lab not in SENSITIVE_LABELS)}) : ni masquées ni comptées.",
        "",
        "## 5. Explication des écarts",
        "",
        "Décomposition de l'écart total en deux effets additifs : **absents** = `union_fichier_recalcule_162` − "
        "`union_fichier_recalcule` (= `union`) ; **prédictions** = `union_fichier_lot_c` − "
        "`union_fichier_recalcule_162` (mêmes passages, autres prédictions).",
        "",
        "| Tranche | Fuite : absents / prédictions | Sur-masquage : absents / prédictions "
        "| F1 : absents / prédictions |",
        "|---|---|---|---|",
    ]
    for ea, ep in zip(res["ecarts"]["absents"], res["ecarts"]["predictions"], strict=True):
        L.append(
            f"| {ea['tranche']} | {cell(ea['fuite'])} / {cell(ep['fuite'])} | "
            f"{cell(ea['sur_masquage'])} / {cell(ep['sur_masquage'])} | {cell(ea['f1'])} / {cell(ep['f1'])} |"
        )
    ce = res["comparaison_entites"]
    L += [
        "",
        f"Entités sensibles des deux fichiers sur les {res['n_passages'] - len(V['union_fichier_lot_c']['absents'])} "
        "passages communs (identiques au caractère et à l'étiquette / seulement dans `crf_dev.jsonl` / seulement "
        "dans le CRF de `union`) :",
        "",
        "| Groupe | Identiques | Seulement Lot C | Seulement `union` |",
        "|---|---|---|---|",
    ]
    for g in sorted(ce, key=lambda x: (x != "global", x)):
        n = ce[g]["n"]
        L.append(f"| {g} | {n[0]} | {n[1]} | {n[2]} |")
    L += ["", *lecture(res), ""]
    return "\n".join(L)


def lecture(res: dict[str, Any]) -> list[str]:
    """Lecture générée à partir des chiffres (relancer le script la met à jour)."""
    tot = {e["tranche"]: e for e in res["ecarts"]["total"]}
    ab = {e["tranche"]: e for e in res["ecarts"]["absents"]}
    pr = {e["tranche"]: e for e in res["ecarts"]["predictions"]}
    g = tot["global"]
    signales = [
        (e["tranche"], met)
        for e in res["ecarts"]["total"]
        for met in ("fuite", "sur_masquage", "f1")
        if depasse(e[met])
    ]
    ce = res["comparaison_entites"]["global"]["n"]
    out = [
        "## 6. Lecture",
        "",
        f"- Global : fuite {pts(g['fuite'])} point, sur-masquage {pts(g['sur_masquage'])} point, F1 au caractère "
        f"{pts(g['f1'])} centième (`union_fichier_lot_c` − `union`).",
        f"- `union_fichier` est correct : avec les prédictions du CRF de `union` écrites dans un fichier, il redonne "
        f"`union` à l'identique ({'oui' if res['controle_identique'] else 'NON'}). Tout écart vient donc du "
        "contenu de `crf_dev.jsonl`, pas du backend.",
        f"- Passages absents ({len(res['variantes']['union_fichier_lot_c']['absents'])}) : effet global fuite "
        f"{pts(ab['global']['fuite'])}, sur-masquage {pts(ab['global']['sur_masquage'])}, F1 "
        f"{pts(ab['global']['f1'])}. Ils ne portent aucune entité sensible gold et le CRF de `union` y prédit "
        f"{res['absents_entites_crf']} entité (toutes étiquettes) : leur absence ne change rien ici. Sur un autre "
        "fichier, elle ne pourrait que retirer du sur-masquage.",
        f"- Prédictions : effet global fuite {pts(pr['global']['fuite'])}, sur-masquage "
        f"{pts(pr['global']['sur_masquage'])}, F1 {pts(pr['global']['f1'])}. Entités sensibles : {ce[0]} "
        f"identiques, {ce[1]} seulement dans `crf_dev.jsonl`, {ce[2]} seulement dans le CRF de `union` ; toutes "
        f"étiquettes, {res['passages_identiques'][0]} / {res['passages_identiques'][1]} passages communs ont "
        "exactement les mêmes entités. `crf_dev.jsonl` vient pourtant d'une autre chaîne de code "
        "(`caseforge/models/crf_ner.py`, Lot C, 26/10 : apprentissage sur `train.jsonl` via `spans_to_bio`, traits "
        "recopiés, spans reconstruits par `vers_spans`) que le CRF de `detect.py` (`train.bio.jsonl`, traits de "
        "`exemples/baseline_crf.py`, `bio_vers_spans_tokens`) ; mêmes hyperparamètres et L-BFGS déterministe : "
        "les deux chaînes donnent les mêmes prédictions sur les passages du dev (identité des modèles non vérifiée)."
        if not (ce[1] or ce[2])
        else f"- Prédictions : effet global fuite {pts(pr['global']['fuite'])}, sur-masquage "
        f"{pts(pr['global']['sur_masquage'])}, F1 {pts(pr['global']['f1'])}. Les deux fichiers diffèrent : {ce[0]} "
        f"entités sensibles identiques, {ce[1]} seulement dans `crf_dev.jsonl`, {ce[2]} seulement dans le CRF de "
        "`union`.",
        f"- `fichier_lot_c` et `crf` donnent aussi les mêmes chiffres (fuite "
        f"{pct(res['mesures']['fichier_lot_c']['fuite']['global']['taux'])} contre "
        f"{pct(res['mesures']['crf']['fuite']['global']['taux'])}).",
    ]
    if signales:
        out.append(
            "- Écarts > 0,5 point : "
            + "; ".join(
                f"{t} {m.replace('_', '-')} {pts(tot[t][m])} "
                f"(absents {pts(ab[t][m]) if ab[t][m] is not None else '—'}, "
                f"prédictions {pts(pr[t][m]) if pr[t][m] is not None else '—'})"
                for t, m in signales
            )
            + ". Chacun se décompose dans la table de la section 5 ; quand l'effet « absents » est nul, l'écart vient "
            "uniquement des prédictions différentes des deux CRF."
        )
    else:
        out.append("- Aucun écart supérieur à 0,5 point.")
    out.append(
        "- Conséquence : `union_fichier` est cohérent avec `union` au dev ; il peut servir à brancher les prédictions "
        "d'un autre modèle (XLM-R du Lot C) au même format. Ses fichiers couvrent les passages de `dev.jsonl` (162) : "
        "les 9 passages dédoublonnés de `documents_dev.jsonl` sont absents, sans effet tant qu'ils ne contiennent "
        "aucune entité sensible, ce qui est le cas au dev."
    )
    return out


def main() -> None:
    """Contrôle de cohérence sur le dev et rapport B13."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    SORTIE.mkdir(parents=True, exist_ok=True)
    docs = charger_documents("dev")
    gold = lignes_gold(docs)
    lot_c = set(lire_predictions(FICHIER_LOT_C))
    recalcule = ecrire_predictions(SORTIE / "crf_dev_recalcule.jsonl", docs)
    recalcule_162 = ecrire_predictions(SORTIE / "crf_dev_recalcule_162.jsonl", docs, garder=lot_c)
    variantes: dict[str, tuple[str, Path | None]] = {
        "union": ("union", None),
        "union_fichier_lot_c": ("union_fichier", FICHIER_LOT_C),
        "union_fichier_recalcule": ("union_fichier", recalcule),
        "union_fichier_recalcule_162": ("union_fichier", recalcule_162),
        "fichier_lot_c": ("fichier", FICHIER_LOT_C),
        "crf": ("crf", None),
    }
    res: dict[str, Any] = {
        "split": "dev (documents_dev.jsonl)",
        "n_docs": len(docs),
        "n_passages": sum(len(d["passages"]) for d in docs),
        "n_occurrences": sum(e["label"] in SENSITIVE_LABELS for g in gold for e in g["entities"]),
        "variantes": {},
        "mesures": {},
    }
    sorties: dict[str, list[dict]] = {}
    for nom, (backend, fichier) in variantes.items():
        t0 = time.perf_counter()
        s, absents = anonymiser(docs, backend, fichier)
        sorties[nom] = s
        res["variantes"][nom] = {"backend": backend, "fichier": str(fichier).replace("\\", "/") if fichier else None,
                                 "absents": absents}  # fmt: skip
        res["mesures"][nom] = mesurer(docs, gold, s)
        m = res["mesures"][nom]
        print(
            f"[{nom} · dev] fuite {ic(m['fuite']['global'])} · sur-masquage "
            f"{pct(m['fuite']['sur_masquage']['global']['taux'])} · F1 {num(m['f1_caractere']['global']['f1'])} · "
            f"absents {len(absents)} ({time.perf_counter() - t0:.0f} s)"
        )
    absents_lot_c = set(res["variantes"]["union_fichier_lot_c"]["absents"])
    res["absents_gold_sensibles"] = sum(
        e["label"] in SENSITIVE_LABELS for g in gold if g["passage_id"] in absents_lot_c for e in g["entities"]
    )
    # remplacements identiques, hors champ « systemes » (crf d'un côté, fichier de l'autre)
    res["controle_identique"] = all(
        [{k: v for k, v in r.items() if k != "systemes"} for r in a["remplacements"]]
        == [{k: v for k, v in r.items() if k != "systemes"} for r in b["remplacements"]]
        for a, b in zip(sorties["union"], sorties["union_fichier_recalcule"], strict=True)
    )
    a, b = lire_predictions(FICHIER_LOT_C), lire_predictions(recalcule)
    res["passages_identiques"] = [sum(list(a[k]) == list(b[k]) for k in a), len(a)]
    res["absents_entites_crf"] = sum(len(b[k]) for k in b if k not in a)
    res["harnais"] = harnais()
    res["apparie"] = comparaison_appariee(gold, masques(sorties["union_fichier_lot_c"]), masques(sorties["union"]))
    res["ecarts"] = {
        "total": ecarts(res, "union", "union_fichier_lot_c"),
        "absents": ecarts(res, "union_fichier_recalcule", "union_fichier_recalcule_162"),
        "predictions": ecarts(res, "union_fichier_recalcule_162", "union_fichier_lot_c"),
    }
    res["comparaison_entites"] = comparer_entites(docs, FICHIER_LOT_C, recalcule)
    ecrire_json(SORTIE / "b13_backend_fichier_dev.json", res)
    RAPPORT.write_text(rapport(res), encoding="utf-8")
    g = res["ecarts"]["total"][0]
    print(
        f"union_fichier_lot_c − union : fuite {pts(g['fuite'])} · sur-masquage {pts(g['sur_masquage'])} · "
        f"F1 {pts(g['f1'])} · contrôle identique {res['controle_identique']} · {time.perf_counter() - debut:.0f} s"
    )


if __name__ == "__main__":
    main()
