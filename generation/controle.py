"""LOT D (Gold) : contrôle automatique des ajouts et des omissions d'une fiche générée.

Exigence du palier Gold (sujet P7, p. 18) : « contrôle automatique des ajouts et omissions ». Le contrôle compare une
fiche au document source, sans modèle ni GPU :

  - AJOUT : élément tiré de la source (rubriques contexte, objectifs, donnees, contraintes ; les éléments « gabarit »
    — consignes, livrables, critères — sont exclus) qui
      * contient un nombre absent de tout le document (« nombre_absent », le cas le plus dangereux : « six mois »,
        « 40 000 DT » inventés), ou
      * n'est porté par aucun passage : moins de SEUIL_AJOUT de ses mots dans le meilleur passage (« non_ancre »).
    Les pseudonymes ([ENTREPRISE_A]…) et les formulations du gabarit (« Analyser les causes… : ») ne comptent pas
    comme des mots de contenu.
  - OMISSION : fait clé du document qu'aucun élément ne reprend. Faits clés : les entités CONTRAINTE (toute contrainte
    doit être respectée par les étudiants) et INDICATEUR (les chiffres du problème et des données). Un fait est
    couvert si un élément en reprend au moins SEUIL_COUVERTURE des mots, nombres compris.

Validation par injection (graine 2027, dev seulement) : sur chaque fiche de référence du dev, on injecte un ajout
(élément d'un autre document de même langue), un nombre modifié et une omission (élément retiré), puis on mesure le
rappel et la précision du contrôle sur ces erreurs connues. La validation contre une annotation humaine (40 fiches)
viendra ensuite.

    python generation/controle.py --out reports/lot_d_gold_controle.md
    python generation/controle.py --gen generation/sorties/llm_e3_dev_s42.jsonl --out ...

Le test gelé n'est jamais lu : documents et fiches du dev seulement.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RACINE / "generation"), str(RACINE)]
import gabarit  # noqa: E402
from llm import HISTORIQUE, normaliser  # noqa: E402

RUBRIQUES_SOURCE = ["contexte", "objectifs", "donnees", "contraintes"]
FAITS_CLES = ("CONTRAINTE", "INDICATEUR")
SEUIL_AJOUT = 0.5
SEUIL_COUVERTURE = 0.6
GRAINE = 2027

PSEUDONYME = re.compile(r"\[[A-Z_]+(?:_[A-Z0-9]+)?\]")
CHIFFRES_ARABES = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")
MILLIERS = re.compile(r"(?<=\d)[   ](?=\d{3}\b)")
NOMBRE = re.compile(r"\d+(?:[.,]\d+)?")
# Nombres écrits en lettres (2 à 12), par langue : « six mois » compte comme le nombre 6. Les mots ambigus sont
# exclus (« neuf » = nouveau ; en français, « four » est un équipement, pas le nombre 4).
NOMBRES_LETTRES = {
    "fr": {
        "deux": "2",
        "trois": "3",
        "quatre": "4",
        "cinq": "5",
        "six": "6",
        "sept": "7",
        "huit": "8",
        "dix": "10",
        "douze": "12",
    },
    "en": {
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "twelve": "12",
    },
    "ar": {
        "اثنان": "2",
        "اثنين": "2",
        "ثلاثة": "3",
        "اربعة": "4",
        "خمسة": "5",
        "ستة": "6",
        "سبعة": "7",
        "ثمانية": "8",
        "تسعة": "9",
        "عشرة": "10",
    },
}
SIX_ANGLAIS = re.compile(r"\bsix-month\b", re.IGNORECASE)


def _vocabulaire_gabarit() -> set[str]:
    """Mots des formulations du gabarit (gabarit.PHRASES, llm.HISTORIQUE) : ils ne viennent pas du document."""
    modeles = [m for phrases in gabarit.PHRASES.values() for m in phrases.values()] + list(HISTORIQUE.values())
    return {w for m in modeles for w in re.findall(r"\w+", normaliser(m.replace("{}", " ")))}


MOTS_GABARIT = _vocabulaire_gabarit()


def liste(valeur: object) -> list[dict]:
    """Rubrique d'une fiche sous forme de liste d'éléments (le contexte est un élément seul)."""
    if not valeur:
        return []
    return valeur if isinstance(valeur, list) else [valeur]  # type: ignore[list-item]


def nettoyer(texte: str) -> str:
    """Texte comparable : sans pseudonymes, chiffres arabes ramenés aux chiffres latins, milliers recollés."""
    return MILLIERS.sub("", PSEUDONYME.sub(" ", texte).translate(CHIFFRES_ARABES))


def nombres(texte: str, lang: str | None = None) -> set[str]:
    """Nombres d'un texte, virgule décimale ramenée au point (« 6,1 » = « 6.1 ») ; avec ``lang``, nombres en lettres
    de cette langue compris (« six mois » -> 6)."""
    propre = nettoyer(texte)
    chiffres = {n.replace(",", ".") for n in NOMBRE.findall(propre)}
    table = NOMBRES_LETTRES.get(lang or "", {})
    lettres = {table[w] for w in re.findall(r"\w+", normaliser(propre)) if w in table}
    if lang == "en" and SIX_ANGLAIS.search(propre):
        lettres.add("6")
    return chiffres | lettres


def mots_contenu(texte: str) -> list[str]:
    """Mots de contenu normalisés (bruit OCR arabe compris), sans les mots des formulations du gabarit."""
    return [m for m in re.findall(r"\w+", normaliser(nettoyer(texte))) if m not in MOTS_GABARIT]


def part_reprise(texte: str, source: str) -> float:
    """Part des mots de contenu de ``texte`` présents dans ``source`` (1,0 si aucun mot de contenu)."""
    m = mots_contenu(texte)
    if not m:
        return 1.0
    vus = set(mots_contenu(source))
    return sum(1 for w in m if w in vus) / len(m)


def textes_document(doc: dict) -> dict[str, str]:
    """Texte de chaque passage, original et anonymisé (la fiche peut reprendre l'un ou l'autre)."""
    return {p["passage_id"]: f"{p['text']}\n{p.get('text_anonymise') or ''}" for p in doc["passages"]}


def elements_source(fiche: dict) -> list[tuple[str, dict]]:
    """Éléments de la fiche tirés du document (origine autre que « gabarit »), avec leur rubrique."""
    return [
        (rub, e)
        for rub in RUBRIQUES_SOURCE
        for e in liste(fiche.get(rub))
        if e.get("origine") != "gabarit" and e.get("texte")
    ]


def ajouts(fiche: dict, doc: dict) -> list[dict]:
    """Éléments de la fiche qu'aucun passage ne porte : nombre absent du document, ou contenu non ancré."""
    textes = textes_document(doc)
    nombres_doc = set().union(*(nombres(t, doc.get("lang")) for t in textes.values())) if textes else set()
    sortie = []
    for rub, e in elements_source(fiche):
        absents = nombres(e["texte"], doc.get("lang")) - nombres_doc
        if absents:
            sortie.append({"rubrique": rub, "texte": e["texte"], "motif": "nombre_absent", "detail": sorted(absents)})
            continue
        meilleur = max((part_reprise(e["texte"], t) for t in textes.values()), default=0.0)
        if meilleur < SEUIL_AJOUT:
            sortie.append({"rubrique": rub, "texte": e["texte"], "motif": "non_ancre", "detail": round(meilleur, 2)})
    return sortie


def faits_cles(doc: dict) -> list[dict]:
    """Entités CONTRAINTE et INDICATEUR du document, sans doublon de texte."""
    vus, faits = set(), []
    for p in doc["passages"]:
        for ent in p["entities"]:
            cle = normaliser(ent["text"]).strip()
            if ent["label"] in FAITS_CLES and cle not in vus:
                vus.add(cle)
                faits.append({"label": ent["label"], "texte": ent["text"], "passage_id": p["passage_id"]})
    return faits


def couvert(fait: str, elements: list[str]) -> bool:
    """Un élément reprend-il le fait (mots de contenu et nombres) ?"""
    nb = nombres(fait)
    for texte in elements:
        if nb and not nb <= nombres(texte):
            continue
        if part_reprise(fait, texte) >= SEUIL_COUVERTURE:
            return True
    return False


def omissions(fiche: dict, doc: dict, faits: list[dict] | None = None) -> list[dict]:
    """Faits clés du document qu'aucun élément de la fiche ne reprend."""
    elements = [e["texte"] for _, e in elements_source(fiche)]
    return [f for f in (faits if faits is not None else faits_cles(doc)) if not couvert(f["texte"], elements)]


def controler(fiche: dict, doc: dict) -> dict:
    """Contrôle complet d'une fiche : ajouts et omissions, à afficher à l'enseignant avant validation."""
    return {"doc_id": fiche["doc_id"], "ajouts": ajouts(fiche, doc), "omissions": omissions(fiche, doc)}


# ---------- Validation par injection d'erreurs connues ----------


def changer_nombre(texte: str, rng: random.Random) -> str | None:
    """Remplace le premier nombre du texte par une valeur absente du texte (ex. 6 -> 13)."""
    m = NOMBRE.search(texte)
    if not m:
        return None
    nouveau = str(int(float(m.group().replace(",", "."))) + rng.randint(7, 40))
    return texte[: m.start()] + nouveau + texte[m.end() :]


def injecter(refs: list[dict], docs: dict[str, dict], graine: int = GRAINE) -> list[dict]:
    """Pour chaque fiche de référence : un ajout étranger, un nombre modifié, une omission (si possible)."""
    rng = random.Random(graine)
    cas = []
    for ref in refs:
        doc = docs[ref["doc_id"]]
        nombres_doc = set().union(*(nombres(t, doc.get("lang")) for t in textes_document(doc).values()))
        autres = [
            (r, e)
            for r in refs
            if r["doc_id"] != ref["doc_id"] and r["lang"] == ref["lang"]
            for _, e in elements_source(r)
        ]
        etrangers = [e for _, e in autres if part_reprise(e["texte"], "\n".join(textes_document(doc).values())) < 0.3]
        if etrangers:
            f = json.loads(json.dumps(ref))
            e = dict(rng.choice(etrangers), origine="source")
            f["donnees"] = liste(f.get("donnees")) + [e]
            cas.append({"type": "ajout_etranger", "doc_id": ref["doc_id"], "fiche": f, "attendu": e["texte"]})
        chiffres = [
            (rub, k, e)
            for rub in ("donnees", "contraintes", "objectifs")
            for k, e in enumerate(liste(ref.get(rub)))
            if e.get("origine") != "gabarit" and nombres(e["texte"])
        ]
        if chiffres:
            rub, k, e = rng.choice(chiffres)
            nouveau = changer_nombre(e["texte"], rng)
            if (
                nouveau
                and not (nombres(nouveau, doc.get("lang")) - nombres(e["texte"], doc.get("lang"))) <= nombres_doc
            ):
                f = json.loads(json.dumps(ref))
                f[rub] = liste(f.get(rub))
                f[rub][k] = dict(e, texte=nouveau)
                cas.append({"type": "nombre_modifie", "doc_id": ref["doc_id"], "fiche": f, "attendu": nouveau})
        faits = faits_cles(doc)
        avant = {f["texte"] for f in omissions(ref, doc, faits)}
        retirables = []
        for rub in ("donnees", "contraintes"):
            for k, e in enumerate(liste(ref.get(rub))):
                if e.get("origine") == "gabarit":
                    continue
                f = json.loads(json.dumps(ref))
                f[rub] = [x for j, x in enumerate(liste(f.get(rub))) if j != k]
                perdus = {o["texte"] for o in omissions(f, doc, faits)} - avant
                if perdus:
                    retirables.append((f, perdus, e["texte"]))
        if retirables:
            f, perdus, texte = rng.choice(retirables)
            cas.append(
                {"type": "omission", "doc_id": ref["doc_id"], "fiche": f, "attendu": texte, "perdus": sorted(perdus)}
            )
    return cas


def valider(refs: list[dict], docs: dict[str, dict]) -> dict:
    """Rappel du contrôle sur les erreurs injectées et fausses alertes sur les fiches de référence intactes."""
    res: dict = {"fausses_alertes_ajout": [], "omissions_reference": [], "cas": defaultdict(lambda: [0, 0])}
    for ref in refs:
        doc = docs[ref["doc_id"]]
        res["fausses_alertes_ajout"] += [dict(a, doc_id=ref["doc_id"]) for a in ajouts(ref, doc)]
        res["omissions_reference"] += [dict(o, doc_id=ref["doc_id"]) for o in omissions(ref, doc)]
    for c in injecter(refs, docs):
        doc = docs[c["doc_id"]]
        if c["type"] == "omission":
            detecte = bool(c["perdus"])  # par construction : le retrait fait apparaître au moins un fait non couvert
        else:
            detecte = any(a["texte"] == c["attendu"] for a in ajouts(c["fiche"], doc))
        res["cas"][c["type"]][0] += int(detecte)
        res["cas"][c["type"]][1] += 1
    return res


# ---------- Rapport ----------


def charger(chemin: Path) -> list[dict]:
    return [json.loads(ligne) for ligne in chemin.open(encoding="utf-8") if ligne.strip()]


def resume_fiches(fiches: list[dict], docs: dict[str, dict]) -> tuple[dict, list[dict]]:
    """Compteurs par groupe (global, langue, source) : fiches, éléments contrôlés, ajouts, omissions, faits clés."""
    groupes: dict[str, Counter] = defaultdict(Counter)
    details = []
    for f in fiches:
        doc = docs[f["doc_id"]]
        c = controler(f, doc)
        details.append(c)
        for g in ("global", f"langue={doc['lang']}", f"source={f['doc_id'][:4]}"):
            groupes[g].update(
                {
                    "fiches": 1,
                    "elements": len(elements_source(f)),
                    "ajouts": len(c["ajouts"]),
                    "omissions": len(c["omissions"]),
                    "faits": len(faits_cles(doc)),
                    "nombre_absent": sum(a["motif"] == "nombre_absent" for a in c["ajouts"]),
                }
            )
    return groupes, details


def ecrire_rapport(chemin: Path, val: dict, resumes: dict[str, tuple[dict, list[dict]]]) -> str:
    lignes = [
        "# Lot D · Gold : contrôle automatique des ajouts et des omissions (dev)",
        "",
        "Produit par `python generation/controle.py`. Documents et fiches du **dev** seulement ; test gelé non lu.",
        f"Seuils : ajout si < {SEUIL_AJOUT:.0%} des mots de contenu dans le meilleur passage, ou nombre absent du "
        f"document ; fait couvert si ≥ {SEUIL_COUVERTURE:.0%} de ses mots (nombres compris) dans un élément. "
        f"Injection : graine {GRAINE}.",
        "",
        "## 1. Validation par injection (fiches de référence du dev)",
        "",
        "| Erreur injectée | Détectées | Cas | Rappel |",
        "|---|---|---|---|",
    ]
    for typ, (ok, n) in sorted(val["cas"].items()):
        lignes.append(f"| {typ} | {ok} | {n} | {ok / n:.2f} |" if n else f"| {typ} | 0 | 0 | - |")
    lignes += [
        "",
        f"Alertes d'ajout sur les 21 fiches de référence intactes : **{len(val['fausses_alertes_ajout'])}** "
        "(à vérifier à la main : une alerte sur la référence est une fausse alerte, ou un défaut de la "
        "référence).",
        f"Faits clés non repris par les fiches de référence : **{len(val['omissions_reference'])}** "
        "(la référence choisit ses faits ; ces cas sont à juger par les relecteurs, pas des erreurs prouvées).",
        "",
    ]
    for a in val["fausses_alertes_ajout"]:
        lignes.append(f"- alerte d'ajout `{a['doc_id']}` ({a['rubrique']}, {a['motif']} {a['detail']}) : {a['texte']}")
    lignes += [
        "",
        "## 2. Fiches générées",
        "",
        "| Fiches | Groupe | Fiches | Éléments | Ajouts | dont nombre absent | Omissions | Faits clés | Faits omis |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for nom, (groupes, _) in resumes.items():
        for g, c in groupes.items():
            taux = c["omissions"] / c["faits"] if c["faits"] else 0.0
            lignes.append(
                f"| `{nom}` | {g} | {c['fiches']} | {c['elements']} | {c['ajouts']} | {c['nombre_absent']} | "
                f"{c['omissions']} | {c['faits']} | {taux:.0%} |"
            )
    lignes += ["", "## 3. Ajouts signalés dans les fiches générées", ""]
    for nom, (_, details) in resumes.items():
        signales = [(d["doc_id"], a) for d in details for a in d["ajouts"]]
        lignes.append(f"### `{nom}` ({len(signales)})")
        lignes += [f"- `{doc}` ({a['rubrique']}, {a['motif']} {a['detail']}) : {a['texte']}" for doc, a in signales]
        lignes.append("")
    lignes += [
        "## Limites",
        "",
        "- Validation par injection seulement : elle mesure le rappel sur des erreurs construites. La précision "
        "réelle sera mesurée contre l'annotation humaine des 40 fiches (ajouts, omissions) du plan Gold.",
        "- Comparaison lexicale : une paraphrase fidèle peut être signalée comme ajout, une omission reformulée "
        "peut passer ; les seuils sont fixés avant la mesure et non réglés sur le dev.",
        "- Le test des nombres se fait à l'échelle du document : un nombre inventé qui existe ailleurs dans le "
        "document (« six mois » quand le texte cite « 6 % ») passe inaperçu.",
        "- Faits clés = entités CONTRAINTE et INDICATEUR de référence ; dans le pipeline, ce seront les entités "
        "prédites par le lot B.",
    ]
    texte = "\n".join(lignes) + "\n"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(texte, encoding="utf-8")
    return texte


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ref", type=Path, default=RACINE / "data/final/fiches_dev.jsonl")
    ap.add_argument("--docs", type=Path, default=RACINE / "data/final/documents_dev.jsonl")
    ap.add_argument(
        "--gen",
        type=Path,
        nargs="*",
        default=[
            RACINE / "generation/sorties/gabarit_v2_dev.jsonl",
            RACINE / "generation/sorties/llm_champs_dev_s42.jsonl",
        ],
    )
    ap.add_argument("--out", type=Path, default=RACINE / "reports/lot_d_gold_controle.md")
    args = ap.parse_args()
    for chemin in (args.ref, args.docs):
        if "test" in chemin.name:
            raise SystemExit("Le contrôle se règle sur le dev : le test gelé n'est jamais lu ici.")
    docs = {d["doc_id"]: d for d in charger(args.docs)}
    refs = charger(args.ref)
    val = valider(refs, docs)
    resumes = {g.name: resume_fiches(charger(g), docs) for g in args.gen if g.exists()}
    print(ecrire_rapport(args.out, val, resumes))


if __name__ == "__main__":
    main()
