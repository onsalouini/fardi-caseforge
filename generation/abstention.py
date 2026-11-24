"""LOT D (Gold) : abstention de la fiche quand le document ne contient pas l'information.

Exigence de la règle commune du Gold (sujet, §3) : « abstention ». Une fiche ne doit jamais combler un vide par une
invention : si le document ne donne ni contrainte ni donnée, la rubrique dit « Non précisé dans le document » au lieu
de rester vide (ambigu pour l'enseignant) ou d'être remplie par une valeur inventée.

1. ``abstenir(fiche)`` : toute rubrique objectifs / donnees / contraintes vide reçoit un élément d'origine
   « abstention » (texte fixe par langue, aucune source).
2. Jeu d'évaluation (dev seulement) : pour chaque document du dev, une variante sans ses contraintes (passages qui
   portent une entité CONTRAINTE ou de type « contrainte » retirés) et une variante sans ses données (passages de type
   « donnee » retirés). Une variante n'est gardée que si plus aucune entité du fait retiré ne reste dans le document :
   l'abstention est alors la seule bonne réponse pour cette rubrique.
3. Mesure, par rubrique retirée : abstention correcte (seulement l'élément d'abstention), rubrique remplie depuis un
   autre passage (éléments ancrés : pas une invention), invention (élément signalé par ``controle.ajouts``) ; et
   fausses abstentions sur les documents d'origine (rubrique abstenue alors que la référence la remplit).

    python generation/abstention.py --jeu                       # écrit generation/jeux/abstention_dev.jsonl
    python generation/abstention.py --out reports/lot_d_gold_abstention.md
    python generation/abstention.py --gen <fiches LLM générées sur le jeu> --out ...

Le test gelé n'est jamais lu.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RACINE / "generation"), str(RACINE)]
import controle  # noqa: E402
import gabarit  # noqa: E402

RUBRIQUES = ["objectifs", "donnees", "contraintes"]
MESSAGE = {
    "fr": "Non précisé dans le document.",
    "en": "Not specified in the document.",
    "ar": "غير محدد في الوثيقة.",
}
ORIGINE = "abstention"
# Rubrique retirée -> (types de passage retirés, étiquette dont aucune entité ne doit rester)
RETRAITS = {"contraintes": ({"contrainte"}, "CONTRAINTE"), "donnees": ({"donnee"}, None)}
JEU = RACINE / "generation/jeux/abstention_dev.jsonl"


def element_abstention(lang: str) -> dict:
    """Élément « non précisé » dans la langue de la fiche (français par défaut)."""
    return {"texte": MESSAGE.get(lang, MESSAGE["fr"]), "origine": ORIGINE, "sources": []}


def abstenir(fiche: dict) -> dict:
    """Remplace chaque rubrique vide par l'élément d'abstention (modifie et renvoie la fiche)."""
    for rub in RUBRIQUES:
        if not fiche.get(rub):
            fiche[rub] = [element_abstention(fiche.get("lang", "fr"))]
    return fiche


def est_abstenue(elements: list[dict]) -> bool:
    return bool(elements) and all(e.get("origine") == ORIGINE for e in elements)


def variante(doc: dict, rubrique: str) -> dict | None:
    """Document sans les passages de la rubrique ; None si le fait retiré reste présent ailleurs."""
    types, label = RETRAITS[rubrique]
    garder = [
        p
        for p in doc["passages"]
        if p.get("ptype") not in types and not (label and any(e["label"] == label for e in p["entities"]))
    ]
    if len(garder) == len(doc["passages"]) or not garder:
        return None
    if label and any(e["label"] == label for p in garder for e in p["entities"]):
        return None
    return {
        **doc,
        "doc_id": f"{doc['doc_id']}_sans_{rubrique}",
        "doc_origine": doc["doc_id"],
        "champ_retire": rubrique,
        "passages": garder,
    }


def construire_jeu(docs: list[dict]) -> list[dict]:
    return [v for d in docs for rub in RETRAITS if (v := variante(d, rub))]


def mesurer(fiches: list[dict], jeu: dict[str, dict]) -> dict[str, Counter]:
    """Compteurs par groupe (global, rubrique, langue, source) sur les variantes du jeu."""
    groupes: dict[str, Counter] = defaultdict(Counter)
    for f in fiches:
        doc = jeu.get(f["doc_id"])
        if doc is None:
            continue
        rub = doc["champ_retire"]
        elements = f.get(rub) or []
        signales = {
            a["texte"] for a in controle.ajouts({**f, **{r: [] for r in controle.RUBRIQUES_SOURCE if r != rub}}, doc)
        }
        if est_abstenue(elements):
            issue = "abstention_correcte"
        elif any(e["texte"] in signales for e in elements):
            issue = "invention"
        elif not elements:
            issue = "rubrique_vide"
        else:
            issue = "remplie_depuis_un_autre_passage"
        for g in ("global", f"rubrique={rub}", f"langue={doc['lang']}", f"source={doc['doc_origine'][:4]}"):
            groupes[g].update({"variantes": 1, issue: 1})
    return groupes


def fausses_abstentions(fiches: list[dict], refs: dict[str, dict]) -> list[tuple[str, str]]:
    """Rubriques abstenues alors que la fiche de référence du même document les remplit."""
    sortie = []
    for f in fiches:
        ref = refs.get(f["doc_id"])
        for rub in RUBRIQUES if ref else []:
            if est_abstenue(f.get(rub) or []) and controle.liste(ref.get(rub)):
                sortie.append((f["doc_id"], rub))
    return sortie


def ecrire_rapport(chemin: Path, mesures: dict[str, dict[str, Counter]], fausses: dict[str, list]) -> str:
    issues = ["abstention_correcte", "remplie_depuis_un_autre_passage", "invention", "rubrique_vide"]
    lignes = [
        "# Lot D · Gold : abstention (dev)",
        "",
        "Produit par `python generation/abstention.py`. Jeu : `generation/jeux/abstention_dev.jsonl`, variantes des "
        "documents du **dev** sans leurs contraintes ou sans leurs données ; test gelé non lu.",
        "",
        "Bonne réponse : l'élément « Non précisé dans le document ». Une rubrique remplie depuis un autre passage "
        "n'est pas une invention (éléments ancrés) ; une invention est un élément signalé par `controle.ajouts`.",
        "",
        "## 1. Variantes à champ retiré",
        "",
        "| Fiches | Groupe | Variantes | Abstention correcte | Remplie (ancrée) | Invention | Vide | Taux |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for nom, groupes in mesures.items():
        for g, c in sorted(groupes.items(), key=lambda kv: (kv[0] != "global", kv[0])):
            taux = c["abstention_correcte"] / c["variantes"] if c["variantes"] else 0.0
            lignes.append(
                f"| `{nom}` | {g} | {c['variantes']} | " + " | ".join(str(c[i]) for i in issues) + f" | {taux:.0%} |"
            )
    lignes += ["", "## 2. Fausses abstentions sur les documents d'origine", ""]
    for nom, liste in fausses.items():
        lignes.append(
            f"- `{nom}` : **{len(liste)}**" + (" (" + ", ".join(f"{d} {r}" for d, r in liste) + ")" if liste else "")
        )
    lignes += [
        "",
        "## Limites",
        "",
        "- Le jeu retire des passages entiers : un document réel peut laisser une contrainte implicite ; la cible Gold "
        "(≥ 80 % d'abstentions correctes, aucune invention) se lit sur les fiches du LLM, le gabarit s'abstenant par "
        "construction.",
        "- Les objectifs ne sont pas retirés : le gabarit et le LLM les dérivent aussi de l'indicateur du problème.",
        "- Une rubrique « remplie (ancrée) » n'est pas forcément juste : le contrôle est lexical. Sur le LLM à champs, "
        "les données des variantes sans données sont presque toujours « Relevés de l'équipement X », composées depuis "
        "le passage du problème : les mots sont dans le document, mais rien ne dit que des relevés sont fournis.",
    ]
    texte = "\n".join(lignes) + "\n"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(texte, encoding="utf-8")
    return texte


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]  # console Windows (cp1252)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--docs", type=Path, default=RACINE / "data/final/documents_dev.jsonl")
    ap.add_argument("--ref", type=Path, default=RACINE / "data/final/fiches_dev.jsonl")
    ap.add_argument("--jeu", action="store_true", help="écrit le jeu de variantes puis s'arrête")
    ap.add_argument("--gen", type=Path, nargs="*", default=[], help="fiches générées sur le jeu (en plus du gabarit)")
    ap.add_argument("--orig", type=Path, nargs="*", default=[], help="fiches générées sur le dev d'origine")
    ap.add_argument("--out", type=Path, default=RACINE / "reports/lot_d_gold_abstention.md")
    args = ap.parse_args()
    if "test" in args.docs.name or "test" in args.ref.name:
        raise SystemExit("L'abstention se mesure sur le dev : le test gelé n'est jamais lu ici.")
    docs = controle.charger(args.docs)
    jeu = construire_jeu(docs)
    JEU.parent.mkdir(parents=True, exist_ok=True)
    with JEU.open("w", encoding="utf-8") as f:
        f.writelines(json.dumps(v, ensure_ascii=False) + "\n" for v in jeu)
    print(f"{len(jeu)} variantes -> {JEU} ({Counter(v['champ_retire'] for v in jeu)})")
    if args.jeu:
        return
    fixes = gabarit.textes_fixes()
    index = {v["doc_id"]: v for v in jeu}
    mesures = {"gabarit v2 + abstention": mesurer([abstenir(gabarit.generer(v, fixes)) for v in jeu], index)}
    for chemin in args.gen:
        mesures[chemin.name] = mesurer([abstenir(f) for f in controle.charger(chemin)], index)
    refs = {f["doc_id"]: f for f in controle.charger(args.ref)}
    fausses = {
        "gabarit v2 + abstention": fausses_abstentions([abstenir(gabarit.generer(d, fixes)) for d in docs], refs)
    }
    for chemin in args.orig:
        fausses[chemin.name] = fausses_abstentions([abstenir(f) for f in controle.charger(chemin)], refs)
    print(ecrire_rapport(args.out, mesures, fausses))


if __name__ == "__main__":
    main()
