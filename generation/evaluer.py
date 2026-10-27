"""LOT D : compare les fiches générées aux fiches de référence (dev uniquement).

Mesures par rubrique (contexte, objectifs, donnees, contraintes) :
  - éléments : un élément généré « correspond » à un élément de référence si leurs mots se recouvrent
    à au moins 50 % (Jaccard) -> précision (1 - ajouts), rappel (1 - omissions), F1 ;
  - citations : passages cités par la fiche générée vs par la référence -> précision, rappel ;
  - complétude : part des rubriques non vides ;
  - fuite : noms sensibles du document retrouvés dans la fiche (doit valoir 0).
Résultats globaux, par langue et par origine (syn = gabarits, lib = texte libre).

    python generation/evaluer.py --gen generation/sorties/fiches_dev.jsonl --out reports/lot_d.md
"""
import argparse
import json
import re
from collections import defaultdict

RUBRIQUES = ["contexte", "objectifs", "donnees", "contraintes"]
SENSIBLES = {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"}
SEUIL = 0.5


def charger(chemin):
    return [json.loads(ligne) for ligne in open(chemin, encoding="utf-8")]


def liste(valeur):
    if valeur is None:
        return []
    return valeur if isinstance(valeur, list) else [valeur]


def mots(texte):
    return set(re.findall(r"\w+", texte.lower()))


def jaccard(a, b):
    a, b = mots(a), mots(b)
    return len(a & b) / len(a | b) if a | b else 0.0


def apparier(gen, ref):
    """Appariement glouton un à un : renvoie le nombre de paires dont le recouvrement dépasse le seuil."""
    paires = sorted(((jaccard(g["texte"], r["texte"]), i, j) for i, g in enumerate(gen) for j, r in enumerate(ref)),
                    reverse=True)
    pris_g, pris_r, n = set(), set(), 0
    for score, i, j in paires:
        if score < SEUIL:
            break
        if i not in pris_g and j not in pris_r:
            pris_g.add(i), pris_r.add(j)
            n += 1
    return n


def ratio(a, b):
    return a / b if b else 0.0


def f1(p, r):
    return 2 * p * r / (p + r) if p + r else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", default="generation/sorties/fiches_dev.jsonl")
    ap.add_argument("--ref", default="data/final/fiches_dev.jsonl")
    ap.add_argument("--docs", default="data/final/documents_dev.jsonl")
    ap.add_argument("--out", default="reports/lot_d.md")
    args = ap.parse_args()

    refs = {f["doc_id"]: f for f in charger(args.ref)}
    docs = {d["doc_id"]: d for d in charger(args.docs)}
    # compteurs : [elements apparies, elements generes, elements reference, citations communes, citees gen, citees ref,
    #              rubriques remplies, rubriques, fuites]
    groupes = defaultdict(lambda: [0] * 9)
    par_rubrique = defaultdict(lambda: [0] * 9)
    fuites = []

    for gen in charger(args.gen):
        ref, doc = refs[gen["doc_id"]], docs[gen["doc_id"]]
        cles = ["global", f"langue={doc['lang']}", f"origine={gen['doc_id'][:3]}"]
        noms = {e["text"] for p in doc["passages"] for e in p["entities"] if e["label"] in SENSIBLES}
        texte_fiche = json.dumps(gen, ensure_ascii=False)
        fuite = sorted(n for n in noms if n and n in texte_fiche)
        if fuite:
            fuites.append((gen["doc_id"], fuite))
        for rub in RUBRIQUES:
            g, r = liste(gen.get(rub)), liste(ref.get(rub))
            cg = {s for e in g for s in e.get("sources", [])}
            cr = {s for e in r for s in e.get("sources", [])}
            val = [apparier(g, r), len(g), len(r), len(cg & cr), len(cg), len(cr), int(bool(g)), 1, 0]
            for c in cles + [f"rubrique={rub}"]:
                cible = par_rubrique if c.startswith("rubrique") else groupes
                cible[c] = [x + y for x, y in zip(cible[c], val)]
        for c in cles:
            groupes[c][8] += len(fuite)

    lignes = ["# LOT D : évaluation des fiches générées par gabarit (dev)", "",
              f"Fiches générées : `{args.gen}` · référence : `{args.ref}`. Le test gelé n'est pas utilisé.",
              f"Un élément généré correspond à un élément de référence si leurs mots se recouvrent à ≥ {SEUIL:.0%} (Jaccard).",
              "", "| Groupe | Éléments P | Éléments R | Éléments F1 | Citations P | Citations R | Complétude | Fuites |",
              "|---|---|---|---|---|---|---|---|"]
    for nom, t in list(groupes.items()) + list(par_rubrique.items()):
        p, r = ratio(t[0], t[1]), ratio(t[0], t[2])
        cp, cr = ratio(t[3], t[4]), ratio(t[3], t[5])
        fu = str(t[8]) if not nom.startswith("rubrique") else "-"
        lignes.append(f"| {nom} | {p:.2f} | {r:.2f} | {f1(p, r):.2f} | {cp:.2f} | {cr:.2f} | {ratio(t[6], t[7]):.0%} | {fu} |")
    lignes += ["", "P = précision (1 - part d'ajouts), R = rappel (1 - part d'omissions).", "",
               "## Fuites", ""] + ([f"- {d} : {', '.join(n)}" for d, n in fuites] or ["Aucune fuite détectée."])
    open(args.out, "w", encoding="utf-8").write("\n".join(lignes) + "\n")
    print("\n".join(lignes))


if __name__ == "__main__":
    main()
