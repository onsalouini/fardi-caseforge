"""LOT D : analyse des erreurs des fiches générées par gabarit (dev uniquement).

    python generation/analyser_erreurs.py

Deux configurations, générées puis comparées aux fiches de référence (data/final/fiches_dev.jsonl) :
  - « référence » : entités, types de passage et anonymisation de référence (erreurs propres au gabarit) ;
  - « bout en bout » : entités du Lot B (reports/predictions/lotb_dev_v2.jsonl) et anonymisation B6c union_seuil
    (results/lotb/b6c_anonymisation_dev_union_seuil.jsonl) : erreurs ajoutées par l'extraction et l'anonymisation.
Une erreur est un élément de référence sans correspondant (omission), un élément généré sans correspondant (ajout)
ou un nom sensible présent dans la fiche (fuite). Correspondance : recouvrement de mots ≥ 50 % (Jaccard), comme
generation/evaluer.py.

Chaque erreur reçoit une cause par des règles explicites (fonction `cause`), écrites après lecture des erreurs ;
le classement est à relire par le Lot D avant d'être cité dans le rapport. Le rapport cite des textes du dev : ne pas
le lire pour concevoir des règles du Lot B (protocole « dev jamais lu »).
Sortie : reports/lot_d_erreurs.md.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluer import SENSIBLES, SEUIL, jaccard, liste  # noqa: E402
from gabarit import brancher_lot_b, charger, generer, textes_fixes  # noqa: E402

RUBRIQUES = ["contexte", "objectifs", "donnees", "contraintes"]
ENTITES_LOTB = "reports/predictions/lotb_dev_v2.jsonl"
ANONYM_LOTB = "results/lotb/b6c_anonymisation_dev_union_seuil.jsonl"
# éléments « données » fixes des fiches de référence, non tirés d'une entité (cf. cfdata/templates.py, autres_donnees)
DONNEES_FIXES = {"extractions de l'erp", "erp extracts", "مستخرجات من نظام التصرف المندمج", "fiches de non-conformité",
                 "non-conformity reports", "بطاقات عدم المطابقة"}
SUIVI = re.compile(r"\[PERSONNE_\d+\]")

CAUSES = {
    "fixe": "Donnée fixe de la référence (ERP, fiches de non-conformité) que le gabarit ne produit pas",
    "suivi": "Passage typé « objectif » recopié alors qu'il décrit le suivi du projet (responsable, démarche)",
    "libre": "Texte libre : la référence reformule ou découpe autrement que le gabarit (indicateurs du problème en données)",
    "contexte": "Choix du passage de contexte : la référence prend l'en-tête du formulaire, le gabarit le premier passage « contexte »",
    "partiel": "Recouvrement partiel ou bruit OCR (tatweel arabe) qui casse les mots",
    "extraction": "Erreur d'extraction du Lot B propagée à la fiche (entité manquée, mal bornée ou en trop)",
    "fuite": "Fuite : nom sensible non détecté par l'anonymisation, recopié dans la fiche",
    "autre": "Autre",
}


def generer_tout(entites=None, anonym=None, version=1):
    fixes = textes_fixes()
    docs = brancher_lot_b(charger("data/final/documents_dev.jsonl"), entites, anonym)
    return {d["doc_id"]: (d, generer(d, fixes, version)) for d in docs}


def erreurs(gen_par_doc, refs):
    out = []
    for doc_id, (doc, gen) in gen_par_doc.items():
        ref = refs[doc_id]
        for rub in RUBRIQUES:
            g, r = liste(gen.get(rub)), liste(ref.get(rub))
            for e in r:
                best = max([jaccard(e["texte"], x["texte"]) for x in g] or [0.0])
                if best < SEUIL:
                    out.append({"doc_id": doc_id, "lang": doc["lang"], "rubrique": rub, "type": "omission",
                                "texte": e["texte"], "recouvrement": round(best, 2)})
            for x in g:
                best = max([jaccard(e["texte"], x["texte"]) for e in r] or [0.0])
                if best < SEUIL:
                    out.append({"doc_id": doc_id, "lang": doc["lang"], "rubrique": rub, "type": "ajout",
                                "texte": x["texte"], "recouvrement": round(best, 2)})
        noms = {e["text"] for p in doc["passages"] for e in p["entities"] if e["label"] in SENSIBLES}
        texte = json.dumps(gen, ensure_ascii=False)
        for n in sorted(n for n in noms if n and n in texte):
            out.append({"doc_id": doc_id, "lang": doc["lang"], "rubrique": "fiche", "type": "fuite", "texte": n,
                        "recouvrement": None})
    return out


def cause(err, dans_reference):
    if err["type"] == "fuite":
        return "fuite"
    if not dans_reference:
        return "extraction"
    t = err["texte"].strip().lower()
    if err["type"] == "omission" and t in DONNEES_FIXES:
        return "fixe"
    if err["type"] == "ajout" and err["rubrique"] == "objectifs" and SUIVI.search(err["texte"]):
        return "suivi"
    if err["doc_id"].startswith("lib_"):
        return "libre"
    if err["rubrique"] == "contexte":
        return "contexte"
    if "ـ" in err["texte"] or (err["recouvrement"] is not None and err["recouvrement"] >= 0.3):
        return "partiel"
    return "autre"


def analyser(refs, noms_ref, version):
    ref_conf = erreurs(generer_tout(version=version), refs)
    cles_ref = {(e["doc_id"], e["rubrique"], e["type"], e["texte"]) for e in ref_conf}
    be = generer_tout(ENTITES_LOTB, ANONYM_LOTB, version)
    be_conf = erreurs(be, refs)
    for doc_id, (_, gen) in be.items():  # fuites des noms de référence non détectés par le Lot B
        texte = json.dumps(gen, ensure_ascii=False)
        for n in sorted(n for n in noms_ref[doc_id] if n and n in texte):
            e = {"doc_id": doc_id, "lang": be[doc_id][0]["lang"], "rubrique": "fiche", "type": "fuite", "texte": n,
                 "recouvrement": None}
            if e not in be_conf:
                be_conf.append(e)
    for e in ref_conf:
        e["config"], e["cause"] = "référence", cause(e, True)
    nouvelles = [e for e in be_conf if (e["doc_id"], e["rubrique"], e["type"], e["texte"]) not in cles_ref]
    for e in nouvelles:
        e["config"], e["cause"] = "bout en bout", cause(e, False)
    toutes = ref_conf + nouvelles

    return toutes, ref_conf, nouvelles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/lot_d_erreurs.md")
    a = ap.parse_args()
    refs = {f["doc_id"]: f for f in charger("data/final/fiches_dev.jsonl")}
    noms_ref = {d["doc_id"]: {e["text"] for p in d["passages"] for e in p["entities"] if e["label"] in SENSIBLES}
                for d in charger("data/final/documents_dev.jsonl")}

    toutes, ref_conf, nouvelles = analyser(refs, noms_ref, 1)
    v2_toutes, v2_ref, v2_nouv = analyser(refs, noms_ref, 2)
    c = Counter(e["cause"] for e in toutes)
    cr = Counter(e["cause"] for e in ref_conf)
    L = ["# LOT D : analyse des erreurs des fiches générées (dev)", "",
         "Analyse faite sur le gabarit d'origine (`generation/gabarit.py --version 1`) ; ses conclusions ont conduit au "
         "gabarit `--version 2` (section 4).", "",
         f"{len(toutes)} erreurs : {len(ref_conf)} avec les entrées de référence (erreurs du gabarit) et {len(nouvelles)} "
         "ajoutées en bout en bout (entités du Lot B, anonymisation B6c `union_seuil`). Correspondance : Jaccard ≥ 50 %.",
         "Causes attribuées par des règles explicites (`generation/analyser_erreurs.py`, fonction `cause`), à relire. "
         "**Ce rapport cite des textes du dev : ne pas le lire pour concevoir des règles du Lot B.** Le test n'est pas utilisé.",
         "", "## 1. Causes", "", "| Cause | Erreurs | Omissions | Ajouts | Fuites | Piste de correction |", "|---|---|---|---|---|---|"]
    pistes = {
        "fixe": "ajouter au gabarit les données fixes par langue (comme la référence)",
        "suivi": "ne pas recopier un passage « objectif » qui contient un responsable ([PERSONNE_n]) ; n'en garder que la démarche",
        "libre": "pour les textes libres, reprendre les indicateurs du passage « probleme » dans les données",
        "contexte": "pour les formulaires, prendre l'en-tête (passage « autre » avec [ENTREPRISE_A] et [SITE_1]) comme contexte",
        "partiel": "normaliser le texte (tatweel, OCR) avant la comparaison ; aligner les préfixes du gabarit sur la référence",
        "extraction": "améliorer le NER (XLM-R, Lot C Silver) ; utiliser le type de passage prédit (Lot C)",
        "fuite": "règles de rappel du Lot B ; contrôle final de la fiche contre les noms détectés dans tout le document",
        "autre": "à examiner",
    }
    for k, n in c.most_common():
        sous = [e for e in toutes if e["cause"] == k]
        cnt = Counter(e["type"] for e in sous)
        L.append(f"| {CAUSES[k]} | **{n}** | {cnt['omission']} | {cnt['ajout']} | {cnt['fuite']} | {pistes[k]} |")
    par = Counter((e["lang"], e["doc_id"][:3]) for e in toutes)
    L += ["", "Répartition par langue et origine : " + ", ".join(f"{lg}/{o} {n}" for (lg, o), n in sorted(par.items())) + ".",
          "", "## 2. Les erreurs, une par ligne", "",
          "| # | Configuration | Document | Rubrique | Type | Recouvrement | Texte (début) | Cause |", "|---|---|---|---|---|---|---|---|"]
    for i, e in enumerate(sorted(toutes, key=lambda e: (e["cause"], e["doc_id"], e["rubrique"])), 1):
        txt = e["texte"].replace("|", "/").replace("\n", " ")[:90]
        rec = "" if e["recouvrement"] is None else f"{e['recouvrement']:.2f}"
        L.append(f"| {i} | {e['config']} | {e['doc_id']} | {e['rubrique']} | {e['type']} | {rec} | {txt} | {e['cause']} |")
    L += ["", "## 3. Lecture", "",
          f"- Avec les entrées de référence, la première cause est **{CAUSES[cr.most_common(1)[0][0]][0].lower() + CAUSES[cr.most_common(1)[0][0]][1:]}** "
          f"({cr.most_common(1)[0][1]} erreurs sur {len(ref_conf)}) : elle vient de la conception du gabarit, pas des entrées, "
          "et se corrige sans modèle.",
          f"- En bout en bout, {len(nouvelles)} erreurs s'ajoutent : elles mesurent ce que coûtent l'extraction et "
          "l'anonymisation du Lot B (par rubrique : " + ", ".join(f"{r} {n}" for r, n in
          Counter(e["rubrique"] for e in nouvelles).most_common()) + "). Les fuites qui atteignent la fiche sont les plus "
          "graves (critère « anonymisation » de la grille).",
          "- Les textes libres (`lib_`) concentrent des erreurs pour un petit nombre de documents : le gabarit est calé sur "
          "les documents simulés."]
    c2 = Counter(e["cause"] for e in v2_toutes)
    L += ["", "## 4. Après correction du gabarit (version 2)", "",
          "Deux corrections tirées des causes « donnée fixe » et « suivi du projet » : (1) les données citées en toutes lettres "
          "dans un passage « donnee » (ERP, fiches de non-conformité) sont reprises avec le libellé de la référence, seulement "
          "si le passage les mentionne ; (2) un passage « objectif » qui nomme un responsable ([PERSONNE_n]) n'est plus "
          "recopié. Vérification sur le TRAIN (jamais vu par l'analyse) pour écarter un sur-ajustement au dev.", "",
          f"Erreurs restantes : **{len(v2_toutes)}** (contre {len(toutes)}), dont {len(v2_ref)} avec les entrées de référence "
          f"(contre {len(ref_conf)}) et {len(v2_nouv)} ajoutées en bout en bout.", "",
          "| Cause | Version 1 | Version 2 |", "|---|---|---|"]
    for k in CAUSES:
        if c.get(k) or c2.get(k):
            L.append(f"| {CAUSES[k]} | {c.get(k, 0)} | {c2.get(k, 0)} |")
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"v1 : {len(toutes)} erreurs ({len(ref_conf)} référence, {len(nouvelles)} bout en bout) ; v2 : {len(v2_toutes)} -> {a.out}")
    for k, n in c.most_common():
        print(f"  {n:3}  {CAUSES[k]}")


if __name__ == "__main__":
    main()
