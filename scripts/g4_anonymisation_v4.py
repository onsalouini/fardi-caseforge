"""Lot B Gold · G4 : anonymisation remesurée avec les prédictions XLM-R v4 du Lot C, contre le gel Silver (dev).

    python -m scripts.g4_anonymisation_v4

Système mesuré : ``union_fichier`` avec les options du gel Silver (``fusion_fichier: bornes_ds``, coréférence,
balayage renforcé, ``generaliser: false`` ; options fixées ici explicitement, pour que la mesure ne dépende pas de la
valeur courante de ``fichier_predictions`` dans ``configs/anonymization.yaml``). Seul le fichier de prédictions change :

- Silver : les 3 graines officielles de B14 (``scripts.b14_xlmr.OFFICIELLES``, empreintes vérifiées) ;
- v4 : ``reports/predictions/xlmr_v4_dev_<graine>.jsonl`` (``origin/lot-c-gold``, commit 8a0581d ; empreintes de
  ``V4`` vérifiées), appariées à la graine Silver de même nom.

Contrôles : format, couverture du dev et bornes des fichiers v4 (``scripts.b14_xlmr.controler``) ; masques Silver
recalculés identiques à ceux du gel (``results/lotb_silver/b16/masques_bornes_regles_DS_<graine>.jsonl``).

Mesures (``scripts.b6d_cv.mesurer``) : fuite [IC 95 %, bootstrap par document], fuites totales / partielles,
sur-masquage, F1 stricte au caractère ; Δ apparié v4 − Silver par graine (``scripts.b14_xlmr.comparer``, bootstrap
apparié des documents, 10 000 tirages, graine 42). Ventilations CLAUDE.md §5 : étiquette, langue (``doc_lang``) avec
annexe des passages mixtes, source. Règle de décision ``REGLE`` écrite dans ``experiments.md`` avant la mesure,
appliquée par ``decision`` ; ce script ne modifie pas ``configs/``.

Sorties : ``results/lotb_gold/g4_anonymisation_v4.md`` et ``.json``, masques v4 par graine dans
``results/lotb_gold/g4/`` (offsets seulement). Le test gelé n'est pas lu ; le texte du dev n'est pas affiché.
"""

from __future__ import annotations

import statistics
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import chemin_predictions
from caseforge.anonymization.policy import Politique, charger_politique
from caseforge.eval.data import ecrire_json, ecrire_jsonl
from caseforge.eval.leak import ETIQUETTES_SENSIBLES
from caseforge.labels import LABELS, REPO_ROOT, SENSITIVE_LABELS
from scripts.b6d_cv import mesurer
from scripts.b14_xlmr import OFFICIELLES, comparer, controler, empreinte_ok, lire_lignes, sha256
from scripts.b16_ablations_silver import ecarts_masques
from scripts.eval_anonymization import charger_documents, lignes_gold, masques

PRED = REPO_ROOT / "reports" / "predictions"
B16 = REPO_ROOT / "results" / "lotb_silver" / "b16"
SORTIE = REPO_ROOT / "results" / "lotb_gold" / "g4"
RAPPORT = REPO_ROOT / "results" / "lotb_gold" / "g4_anonymisation_v4.md"
JSON = REPO_ROOT / "results" / "lotb_gold" / "g4_anonymisation_v4.json"
LOT_C_COMMIT = "8a0581d"
LOT_C_COMMIT_AJOUT = "0b47a2e"
HAUSSE_SUR_MASQUAGE_MAX = 0.02
TOLERANCE = 1e-12
REGLE = (
    "v4 remplace le Silver dans `fichier_predictions` si la fuite moyenne (3 graines) ne monte pas (Δ moyen v4 − "
    "Silver ≤ 0) et si le sur-masquage moyen ne monte pas de plus de 2 points (Δ moyen ≤ +2,0 pt) ; sinon, on garde "
    "le Silver. `fusion_fichier`, `coreference`, `balayage` et `generaliser` ne sont pas réajustés."
)
"""Règle de décision, écrite dans ``experiments.md`` avant la mesure (entrée « G4 (pré-enregistrement) »)."""
OPTIONS_GEL_SILVER: dict[str, Any] = {
    "fusion_fichier": "bornes_ds",
    "coreference": True,
    "balayage": True,
    "balayage_renforce": True,
    "generaliser": False,
}
"""Options du gel Silver (``configs/anonymization.yaml`` du 14/11/2026), imposées à la politique."""


@dataclass(frozen=True)
class FichierV4:
    """Un fichier de prédictions XLM-R v4 du Lot C."""

    nom: str
    chemin: Path
    sha256_lf: str
    """Empreinte sha256 du contenu aux fins de ligne LF (blob Git du commit 8a0581d)."""


V4: tuple[FichierV4, ...] = (
    FichierV4(
        "s13", PRED / "xlmr_v4_dev_s13.jsonl", "8e352fe022b1ef6234c85ccd2b35e4c754b554805b3a57cf41f43c949deda689"
    ),
    FichierV4(
        "s42", PRED / "xlmr_v4_dev_s42.jsonl", "ca3e31bd282dee05fa0c03d0e681640749a2dba75f8b748cf3a16acc8054273d"
    ),
    FichierV4(
        "s2026", PRED / "xlmr_v4_dev_s2026.jsonl", "c2595014f4cf849cae8e8c57024be68395664184b603a0ca0903f31856a59dec"
    ),
)
SILVER: dict[str, Path] = {v.nom: v.chemin for v in OFFICIELLES}
SYSTEMES = ("silver", "v4")


# ---------- Décision ----------
def decision(fuite: dict[str, float], sur_masquage: dict[str, float]) -> dict[str, Any]:
    """Applique ``REGLE`` aux moyennes sur les graines : ``{"silver": x, "v4": y}`` pour chaque mesure."""
    d_fuite = fuite["v4"] - fuite["silver"]
    d_sm = sur_masquage["v4"] - sur_masquage["silver"]
    fuite_ok = d_fuite <= TOLERANCE
    sm_ok = d_sm <= HAUSSE_SUR_MASQUAGE_MAX + TOLERANCE
    return {
        "regle": REGLE,
        "delta_fuite": d_fuite,
        "delta_sur_masquage": d_sm,
        "fuite_ne_monte_pas": fuite_ok,
        "sur_masquage_ok": sm_ok,
        "v4_retenu": fuite_ok and sm_ok,
    }


# ---------- Mesures ----------
def politique_gel_silver() -> Politique:
    """Politique de ``configs/anonymization.yaml`` avec les options du gel Silver imposées."""
    return charger_politique(**OPTIONS_GEL_SILVER)


def anonymiser(docs: list[dict], fichier: Path, pol: Politique) -> list[dict]:
    """``union_fichier`` sur chaque document, avec le fichier de prédictions donné."""
    return [anonymize_document(d, "union_fichier", politique=pol, fichier_predictions=fichier) for d in docs]


def chiffres(r: dict[str, Any], m: dict[str, list[int]], gold: list[dict]) -> dict[str, float]:
    """Chiffres scalaires d'une exécution (global et tranches §5), pour les moyennes entre graines."""
    f, sm, f1 = r["fuite"], r["fuite"]["sur_masquage"], r["f1_caractere"]
    out: dict[str, float] = {
        "fuite": f["global"]["taux"],
        "fuites": f["global"]["fuites"],
        "totales": f["global"]["totales"],
        "partielles": f["global"]["partielles"],
        "sur_masquage": sm["global"]["taux"],
        "f1": f1["global"]["f1"],
        "precision": f1["global"]["p"],
        "rappel": f1["global"]["r"],
        "mixtes:n": f["mixtes"]["n"],
        "mixtes:fuites": f["mixtes"]["fuites"],
    }
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k, x in f[axe].items():
            out[f"fuite:{k}"] = x["taux"]
            out[f"fuites:{k}"] = x["fuites"]
            out[f"n:{k}"] = x["n"]
        for k, x in f1[axe].items():
            out[f"f1:{k}"] = x["f1"]
    for axe in ("par_langue", "par_source"):
        for k, x in sm[axe].items():
            out[f"sur_masquage:{k}"] = x["taux"]
    for lab, n in r["sur_masquage_par_etiquette_gold"].items():
        out[f"sm_car:{lab}"] = n
    return out


def moyennes(execs: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Moyenne et écart-type de population (ddof = 0, convention de B14 et B16) de chaque chiffre."""
    cles = sorted({k for e in execs.values() for k in e})
    out = {}
    for k in cles:
        xs = [e.get(k, 0.0) for e in execs.values()]
        out[k] = {"moyenne": statistics.fmean(xs), "ecart_type": statistics.pstdev(xs), "n": len(xs)}
    return out


def controles_fichiers(docs: list[dict]) -> dict[str, Any]:
    """Format, couverture du dev, bornes et empreintes des fichiers v4 (erreur si un contrôle échoue)."""
    textes = {p["passage_id"]: p["text"] for d in docs for p in d["passages"]}
    ids_dev = [r["passage_id"] for r in lire_lignes(SILVER["s42"])]
    out: dict[str, Any] = {}
    for v in V4:
        c = controler(v.chemin, textes, ids_dev)
        c["sha256_lf"] = sha256(v.chemin, lf=True)
        c["empreinte_ok"] = c["sha256_lf"] == v.sha256_lf
        c["hors_documents_dev"] = sorted({r["passage_id"] for r in lire_lignes(v.chemin)} - set(textes))
        c["passages_documents_dev_absents"] = len(set(textes) - {r["passage_id"] for r in lire_lignes(v.chemin)})
        erreurs = [
            nom
            for nom, ok in (
                ("empreinte", c["empreinte_ok"]),
                ("format", c["cles_ligne"] == {"entities/passage_id": c["n_lignes"]}),
                ("entités", set(c["cles_entite"]) <= {"end/label/start"}),
                ("passage_id uniques", c["n_passage_id_uniques"] == c["n_lignes"]),
                ("couverture du dev", c["memes_passage_id_que_crf"]),
                ("hors dev", not c["hors_documents_dev"]),
                ("bornes", c["hors_texte"] == c["vides"] == c["bornes_non_entieres"] == 0),
                ("étiquettes", c["etiquette_inconnue"] == 0),
            )
            if not ok
        ]
        if erreurs:
            raise RuntimeError(f"{v.chemin.name} : contrôle(s) en échec : {', '.join(erreurs)}")
        out[v.nom] = c
    return out


def controle_gel(docs: list[dict]) -> dict[str, Any]:
    """Gel Gold : si ``fichier_predictions`` pointe vers v4 s42, ``anonymize_document(doc)`` sans argument doit
    redonner les masques v4 s42 mesurés ici (``results/lotb_gold/g4/masques_v4_s42.jsonl``).

    G5 a activé la généralisation, G5 bis l'a remise à false (``generaliser_sauf`` inactif) : le contrôle compare les
    autres options et anonymise avec ``generaliser=False``, ce qui redonne le système gelé par G4."""
    defaut = chemin_predictions()
    attendu = next(v.chemin for v in V4 if v.nom == "s42")
    out: dict[str, Any] = {"fichier_predictions": defaut.relative_to(REPO_ROOT).as_posix()}
    if defaut != attendu:
        return {**out, "fait": False}
    opts = charger_politique().options
    diff = {k: opts[k] for k, x in OPTIONS_GEL_SILVER.items() if k != "generaliser" and opts[k] != x}
    if opts["backend"] != "union_fichier" or diff:
        raise RuntimeError(f"configuration gelée différente des options du gel Silver : {diff or opts['backend']}")
    ref = SORTIE / "masques_v4_s42.jsonl"
    n = ecarts_masques(masques([anonymize_document(d, generaliser=False) for d in docs]), ref)
    if n:
        raise RuntimeError(f"système par défaut différent de v4 s42 ({n} passages)")
    return {**out, "fait": True, "reference": ref.relative_to(REPO_ROOT).as_posix(), "passages_differents": n}


# ---------- Rapport ----------
def _f(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _pc(x: float) -> str:
    return _f(100 * x, 1)


def _pts(x: float) -> str:
    return f"{100 * x:+.1f}".replace(".", ",")


def _sg(x: float) -> str:
    return f"{x:+.3f}".replace(".", ",")


def _nb(x: float) -> str:
    return _f(x, 1) if x != int(x) else str(int(x))


def _me(m: dict[str, dict[str, float]], k: str, fmt: Callable[[float], str], suffixe: str = "") -> str:
    x = m[k]
    return f"{fmt(x['moyenne'])} ± {fmt(x['ecart_type'])}{suffixe}"


def _ic(r: dict[str, Any]) -> str:
    lo, hi = r["fuite"]["global"]["ic95"]
    return f"[{_pc(lo)} ; {_pc(hi)}]"


def _p(b: dict[str, Any]) -> str:
    return "p < 0,001" if b["p_bilaterale"] < 0.001 else f"p = {_f(b['p_bilaterale'])}"


def lecture(deltas: dict[str, dict[str, Any]], quoi: str) -> str:
    """Démontré si l'IC 95 % du Δ apparié exclut 0 pour les 3 graines."""
    ics = [d[quoi]["ic95"] for d in deltas.values()]
    n = len(ics)
    if all(lo > 0 for lo, _ in ics):
        return f"hausse démontrée ({n}/{n} graines)"
    if all(hi < 0 for _, hi in ics):
        return f"baisse démontrée ({n}/{n} graines)"
    h, b = sum(lo > 0 for lo, _ in ics), sum(hi < 0 for _, hi in ics)
    return "non démontré" + (f" (hausse {h}/{n}, baisse {b}/{n})" if h or b else "")


def _ordre(k: str) -> tuple[bool, str]:
    return (k == "lib", k)


def _tranches(res: dict[str, Any], axe: str) -> list[str]:
    ex = res["executions"]["silver"]["s13"]["fuite"][axe]
    return list(ETIQUETTES_SENSIBLES) if axe == "par_etiquette" else sorted(ex, key=_ordre)


def markdown(res: dict[str, Any]) -> str:
    """Rapport G4."""
    M, dec = res["moyennes"], res["decision"]
    S, V = M["silver"], M["v4"]
    n_occ = sum(S[f"n:{lab}"]["moyenne"] for lab in ETIQUETTES_SENSIBLES)
    L = [
        "# Lot B Gold · G4 : anonymisation avec XLM-R v4 du Lot C, contre le gel Silver",
        "",
        "**Règle de décision, écrite dans `experiments.md` AVANT la mesure** (entrée « G4 (pré-enregistrement) ») : "
        + REGLE,
        "",
        "**Split : dev** (`documents_dev.jsonl`, 21 documents, 171 passages, "
        f"{_nb(n_occ)} occurrences sensibles). Test gelé non lu ; texte du dev non affiché. Commande : "
        "`python -m scripts.g4_anonymisation_v4` ; chiffres complets dans "
        "`results/lotb_gold/g4_anonymisation_v4.json`, masques v4 dans `results/lotb_gold/g4/`.",
        "",
        "**Système** : `union_fichier`, options du gel Silver (`fusion_fichier: bornes_ds`, coréférence, balayage "
        "renforcé, extension des montants, plafonds, `generaliser: false`). Seul le fichier de prédictions change. "
        "**Silver** = 3 graines officielles de B14 (s13 `results/lotb_silver/b14/lotc_9096adf/xlmr_dev_s13.jsonl`, "
        "s42 `reports/predictions/xlmr_dev_s42.jsonl`, s2026 `results/lotb_silver/b14/lotc_9096adf/"
        "xlmr_dev_s2026.jsonl`). **v4** = `reports/predictions/xlmr_v4_dev_<graine>.jsonl`, récupérés seuls de "
        f"`origin/lot-c-gold` (commit {LOT_C_COMMIT}, fichiers ajoutés en {LOT_C_COMMIT_AJOUT}), sans les fichiers "
        "`_brut`. Appariement par nom de graine. Moyenne ± écart-type de population sur les 3 graines.",
        "",
        "Mesures : fuite = occurrence sensible gold dont un caractère non blanc reste visible (masque), IC 95 % par "
        "bootstrap des documents (1 000 tirages, par graine) ; totale = aucun caractère masqué ; sur-masquage = "
        "caractères masqués hors entités sensibles gold / caractères masqués ; F1 stricte au caractère sur les entités "
        "sensibles. Δ apparié = v4 − Silver de même graine, bootstrap apparié des documents (10 000 tirages, graine "
        "42) ; « démontré » = IC 95 % du Δ qui exclut 0 pour chacune des 3 graines. Limites : 21 documents ; points "
        "de contrôle XLM-R choisis sur le dev par le Lot C (optimiste pour les deux systèmes).",
        "",
        "## Contrôles",
        "",
    ]
    for g, c in res["controles_fichiers"].items():
        L.append(
            f"- v4 {g} : sha256 (LF) `{c['sha256_lf']}` conforme au blob de {LOT_C_COMMIT} ; {c['n_lignes']} lignes "
            f"`{{passage_id, entities: [{{start, end, label}}]}}`, {c['n_passage_id_uniques']} identifiants uniques = "
            f"les {c['n_lignes']} passages de `dev.jsonl` ; 0 hors dev ; bornes dans le texte ; {c['n_entites']} "
            f"entités dont {c['n_sensibles']} sensibles ; {c['passages_documents_dev_absents']} passages dédoublonnés "
            "de `documents_dev.jsonl` absents, comme au Silver (sans prédiction du fichier : règles seules)."
        )
    for nom, c in res["controles_masques"].items():
        L.append(f"- {nom} : {c['passages_differents']} / 171 passage(s) différent(s) de `{c['reference']}`.")
    g = res["controle_gel_gold"]
    L.append(
        f"- Gel Gold : système par défaut (`anonymize_document(doc)`, "
        f"`fichier_predictions: {g['fichier_predictions']}`) : {g['passages_differents']} / 171 passage(s) "
        f"différent(s) de `{g['reference']}`."
        if g["fait"]
        else f"- Gel Gold : non contrôlé (`fichier_predictions` = `{g['fichier_predictions']}`, pas v4 s42)."
    )
    L += [
        "",
        "## Résultat global",
        "",
        "| Système | Fuite | IC 95 % (s13 / s42 / s2026) | Totales / partielles | Sur-masquage | F1 car. "
        "| Précision / rappel car. |",
        "|---|---|---|---|---|---|---|",
    ]
    for s, nom in (("silver", "Silver (gel du 14/11)"), ("v4", "**v4**")):
        m, ex = M[s], res["executions"][s]
        L.append(
            f"| {nom} | **{_me(m, 'fuite', _pc, ' %')}** | {' / '.join(_ic(ex[g]) for g in ex)} "
            f"| {_me(m, 'totales', _nb)} / {_me(m, 'partielles', _nb)} | {_me(m, 'sur_masquage', _pc, ' %')} "
            f"| {_me(m, 'f1', _f)} | {_f(m['precision']['moyenne'])} / {_f(m['rappel']['moyenne'])} |"
        )
    L += [
        "",
        "## Par graine et Δ apparié v4 − Silver",
        "",
        "| Graine | Fuite Silver → v4 | Δ fuite [IC 95 %], p | Sur-masquage Silver → v4 "
        "| Δ sur-masquage [IC 95 %], p | F1 car. Silver → v4 (Δ) |",
        "|---|---|---|---|---|---|",
    ]
    for g, d in res["deltas"].items():
        cs, cv = res["chiffres"]["silver"][g], res["chiffres"]["v4"][g]
        cells = []
        for quoi in ("fuite", "sur_masquage"):
            b = d[quoi]
            lo, hi = b["ic95"]
            cells.append(f"{_pts(b['difference'])} pt [{_pts(lo)} ; {_pts(hi)}], {_p(b)}")
        L.append(
            f"| {g} | {_pc(cs['fuite'])} → {_pc(cv['fuite'])} % ({_nb(cs['fuites'])} → {_nb(cv['fuites'])} fuites) "
            f"| {cells[0]} | {_pc(cs['sur_masquage'])} → {_pc(cv['sur_masquage'])} % | {cells[1]} "
            f"| {_f(cs['f1'])} → {_f(cv['f1'])} ({_sg(cv['f1'] - cs['f1'])}) |"
        )
    L.append(
        f"| **moyenne** | {_pc(S['fuite']['moyenne'])} → {_pc(V['fuite']['moyenne'])} % | **{_pts(dec['delta_fuite'])} "
        f"pt**, {lecture(res['deltas'], 'fuite')} | {_pc(S['sur_masquage']['moyenne'])} → "
        f"{_pc(V['sur_masquage']['moyenne'])} % | **{_pts(dec['delta_sur_masquage'])} pt**, "
        f"{lecture(res['deltas'], 'sur_masquage')} | {_f(S['f1']['moyenne'])} → {_f(V['f1']['moyenne'])} "
        f"({_sg(V['f1']['moyenne'] - S['f1']['moyenne'])}) |"
    )
    L += [
        "",
        "## Décision",
        "",
        f"- Règle : {REGLE}",
        f"- Δ fuite moyenne : {_pts(dec['delta_fuite'])} pt → "
        + ("ne monte pas." if dec["fuite_ne_monte_pas"] else "**monte**."),
        f"- Δ sur-masquage moyen : {_pts(dec['delta_sur_masquage'])} pt → "
        + ("≤ +2,0 pt." if dec["sur_masquage_ok"] else "**> +2,0 pt**."),
        "- **"
        + (
            "v4 retenu** : `fichier_predictions` passe à `reports/predictions/xlmr_v4_dev_s42.jsonl` (graine s42, "
            "comme au Silver)."
            if dec["v4_retenu"]
            else "v4 non retenu** : `fichier_predictions` reste sur le Silver "
            "(`reports/predictions/xlmr_dev_s42.jsonl`)."
        ),
        "",
        "## Ventilations (§5)",
        "",
        "Moyenne ± écart-type sur les 3 graines. `lib` : 3 documents, tendance seulement. Les effectifs (n occ.) sont "
        "ceux du gold, identiques pour les deux systèmes.",
        "",
        "### Fuite, % (nombre de fuites)",
        "",
        "| Tranche (n occ.) | Silver | v4 | Δ moyen |",
        "|---|---|---|---|",
    ]
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k in _tranches(res, axe):
            d = V[f"fuite:{k}"]["moyenne"] - S[f"fuite:{k}"]["moyenne"]
            L.append(
                f"| {k} ({_nb(S[f'n:{k}']['moyenne'])}) | {_me(S, f'fuite:{k}', _pc, ' %')} "
                f"({_nb(S[f'fuites:{k}']['moyenne'])}) | {_me(V, f'fuite:{k}', _pc, ' %')} "
                f"({_nb(V[f'fuites:{k}']['moyenne'])}) | {_pts(d)} pt |"
            )
    L += ["", "### F1 stricte au caractère", "", "| Tranche | Silver | v4 | Δ moyen |", "|---|---|---|---|"]
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k in _tranches(res, axe):
            d = V[f"f1:{k}"]["moyenne"] - S[f"f1:{k}"]["moyenne"]
            L.append(f"| {k} | {_me(S, f'f1:{k}', _f)} | {_me(V, f'f1:{k}', _f)} | {_sg(d)} |")
    L += ["", "### Sur-masquage", "", "| Tranche | Silver | v4 | Δ moyen |", "|---|---|---|---|"]
    for axe in ("par_langue", "par_source"):
        for k in _tranches(res, axe):
            d = V[f"sur_masquage:{k}"]["moyenne"] - S[f"sur_masquage:{k}"]["moyenne"]
            L.append(
                f"| {k} | {_me(S, f'sur_masquage:{k}', _pc, ' %')} | {_me(V, f'sur_masquage:{k}', _pc, ' %')} "
                f"| {_pts(d)} pt |"
            )
    L += [
        "",
        "Sur-masquage par étiquette : caractères non blancs masqués hors entités sensibles, selon l'étiquette gold "
        "qu'ils recouvrent (`O` = aucune entité ; les étiquettes sensibles n'en ont pas par définition).",
        "",
        "| Étiquette gold recouverte | Silver (car.) | v4 (car.) |",
        "|---|---|---|",
    ]
    for lab in (*[x for x in LABELS if x not in SENSITIVE_LABELS], "O"):
        k = f"sm_car:{lab}"
        zero = {"moyenne": 0.0, "ecart_type": 0.0}
        s, v = S.get(k, zero), V.get(k, zero)
        L.append(
            f"| {lab} | {_f(s['moyenne'], 1)} ± {_f(s['ecart_type'], 1)} "
            f"| {_f(v['moyenne'], 1)} ± {_f(v['ecart_type'], 1)} |"
        )
    L += [
        "",
        "### Passages mixtes (annexe, n < 30 : pas de conclusion)",
        "",
        f"{_nb(S['mixtes:n']['moyenne'])} occurrences sensibles dans des passages `mixte` (champ `lang`) ; fuites : "
        f"Silver {_me(S, 'mixtes:fuites', _nb)}, v4 {_me(V, 'mixtes:fuites', _nb)}.",
    ]
    return "\n".join(L) + "\n"


# ---------- Programme ----------
def main() -> None:
    """Contrôles, mesures Silver et v4 sur le dev, Δ appariés, décision et rapport."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", message=r"passage .* absent de ")  # 9 passages dédoublonnés (B14)
    for v in OFFICIELLES:
        if not empreinte_ok(v):
            raise RuntimeError(f"empreinte inattendue pour {v.chemin}")
    docs = charger_documents("dev")
    gold = lignes_gold(docs)
    pol = politique_gel_silver()
    res: dict[str, Any] = {
        "split": "dev (documents_dev.jsonl)",
        "regle": REGLE,
        "options": OPTIONS_GEL_SILVER,
        "lot_c": {"branche": "origin/lot-c-gold", "commit": LOT_C_COMMIT, "commit_ajout": LOT_C_COMMIT_AJOUT},
        "fichiers": {
            "silver": {g: p.relative_to(REPO_ROOT).as_posix() for g, p in SILVER.items()},
            "v4": {v.nom: v.chemin.relative_to(REPO_ROOT).as_posix() for v in V4},
        },
        "controles_fichiers": controles_fichiers(docs),
        "controles_masques": {},
        "executions": {"silver": {}, "v4": {}},
        "chiffres": {"silver": {}, "v4": {}},
        "deltas": {},
    }
    SORTIE.mkdir(parents=True, exist_ok=True)
    for v in V4:
        g = v.nom
        m_par = {}
        for s, f in (("silver", SILVER[g]), ("v4", v.chemin)):
            sorties = anonymiser(docs, f, pol)
            m = masques(sorties)
            r = mesurer(docs, gold, sorties)
            res["executions"][s][g] = {k: r[k] for k in ("fuite", "f1_caractere", "sur_masquage_par_etiquette_gold")}
            res["chiffres"][s][g] = chiffres(r, m, gold)
            m_par[s] = m
            c = res["chiffres"][s][g]
            print(
                f"[{s} · {g}] fuite {100 * c['fuite']:.1f} % · sur-masquage {100 * c['sur_masquage']:.1f} % · "
                f"F1 {c['f1']:.3f}"
            )
        ref = B16 / f"masques_bornes_regles_DS_{g}.jsonl"
        n = ecarts_masques(m_par["silver"], ref)
        res["controles_masques"][f"Silver {g} recalculé"] = {
            "reference": ref.relative_to(REPO_ROOT).as_posix(),
            "passages_differents": n,
        }
        if n:
            raise RuntimeError(f"masques Silver {g} différents du gel ({n} passages)")
        ecrire_jsonl(
            SORTIE / f"masques_v4_{g}.jsonl",
            [{"passage_id": p, "masque_offsets": sorted(o)} for p, o in m_par["v4"].items()],
        )
        res["deltas"][g] = comparer(gold, m_par["silver"], m_par["v4"])
    res["controle_gel_gold"] = controle_gel(docs)
    res["moyennes"] = {s: moyennes(res["chiffres"][s]) for s in SYSTEMES}
    M = res["moyennes"]
    res["decision"] = decision(
        {s: M[s]["fuite"]["moyenne"] for s in SYSTEMES}, {s: M[s]["sur_masquage"]["moyenne"] for s in SYSTEMES}
    )
    ecrire_json(JSON, res)
    RAPPORT.write_text(markdown(res), encoding="utf-8")
    d = res["decision"]
    print(
        f"delta fuite {100 * d['delta_fuite']:+.2f} pt · delta sur-masquage {100 * d['delta_sur_masquage']:+.2f} pt · "
        f"v4 retenu : {d['v4_retenu']}"
    )


if __name__ == "__main__":
    main()
