"""LOT D (Gold) : 40 textes libres neufs (SRC-LIBRE v4), rédigés avec un LLM ouvert puis vérifiés par un humain.

Décision d'équipe (22/11/2026) : rédaction aidée par Qwen2.5-7B-Instruct (4 bits, Kaggle), usage déclaré dans la carte
de données ; annotations pré-remplies automatiquement puis **vérifiées par un humain** (aucune annotation de modèle
présentée comme humaine). But : renforcer le point faible du Silver, les textes libres (`lib_`), surtout en arabe.

Quatre étapes :

  plan        40 documents (16 ar, 12 fr, 12 en), 6 formats libres, secteurs et valeurs fictives tirés des lexiques v4
              du lot A (``caseforge.gold.generer_v4.choisir_valeurs`` : lexiques disjoints du v3, donc du test gelé) ;
              graine 2027 ; identifiants ``lib_<langue>_500`` et suivants -> ``data/gold/libres_v4/plan.jsonl``.
  rediger     (GPU) le LLM rédige chaque document en plaçant MOT POUR MOT les valeurs du plan ; une valeur absente
              est signalée -> ``data/gold/libres_v4/brut/<doc_id>.txt`` et ``redaction.jsonl``.
  preannoter  découpe en passages (lignes vides), entités pré-annotées = occurrences exactes des valeurs du plan, type
              de passage déduit des valeurs qu'il contient -> ``a_verifier/passages_preannotes.jsonl`` et la page
              ``a_verifier/verifier.html`` (page d'annotation du lot A, pré-remplie : on corrige au lieu d'annoter).
  integrer    lit le fichier JSON exporté par la page (annotations vérifiées) -> ``passages.jsonl``,
              ``documents.jsonl`` et ``metadonnees.csv`` au format de ``data/gold/synth_v4/`` ; ``python -m
              caseforge.gold.train_v4`` les ajoute ensuite au train (lot A).

    python generation/textes_libres.py plan
    python generation/textes_libres.py rediger                     # Kaggle T4, ~40 min
    python generation/textes_libres.py preannoter
    python generation/textes_libres.py integrer annotations_<prénom>.json

Rien ici ne lit le dev ni le test gelé.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections.abc import Callable
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RACINE / "generation"), str(RACINE)]

from caseforge.gold import generer_v4 as G  # noqa: E402
from caseforge.gold import lexiques_v4 as L  # noqa: E402
from caseforge.labels import LABELS  # noqa: E402

GRAINE = 2027
DOSSIER = RACINE / "data/gold/libres_v4"
LANGUES = ["ar"] * 16 + ["fr"] * 12 + ["en"] * 12
FORMATS = ["courriel", "compte_rendu", "fiche_nc", "message_technicien", "demande_projet", "note_interne"]
NOM_FORMAT = {
    "fr": {
        "courriel": "un courriel d'un responsable de l'entreprise à l'école d'ingénieurs",
        "compte_rendu": "le compte rendu d'une réunion de production",
        "fiche_nc": "une fiche de non-conformité remplie à la main",
        "message_technicien": "un message court et familier d'un technicien à son chef",
        "demande_projet": "une demande de projet de fin d'études adressée à l'école",
        "note_interne": "une note interne de la direction technique",
    },
    "en": {
        "courriel": "an email from a company manager to the engineering school",
        "compte_rendu": "the minutes of a production meeting",
        "fiche_nc": "a hand-filled non-conformity report",
        "message_technicien": "a short informal message from a technician to the supervisor",
        "demande_projet": "a final-year project request sent to the school",
        "note_interne": "an internal memo from the technical department",
    },
    "ar": {
        "courriel": "رسالة إلكترونية من مسؤول في الشركة إلى مدرسة المهندسين",
        "compte_rendu": "محضر اجتماع حول الإنتاج",
        "fiche_nc": "بطاقة عدم مطابقة معبأة يدويا",
        "message_technicien": "رسالة قصيرة وغير رسمية من تقني إلى رئيسه",
        "demande_projet": "طلب مشروع ختم دروس موجه إلى المدرسة",
        "note_interne": "مذكرة داخلية من الإدارة الفنية",
    },
}
# Emplacements placés dans le texte (valeurs de choisir_valeurs) ; SITEC (la ville seule) suit le guide v2 (site sans
# le mot générique).
EMPLACEMENTS = [
    "ORG",
    "SITEC",
    "PROD",
    "EQUIP",
    "IND",
    "IND2",
    "PROC",
    "CTR",
    "CTR2",
    "PER",
    "ROLE",
    "DS_COUT",
    "DS_LOT",
    "DS_MAIL",
    "DS_TEL",
]
# Type de passage déduit des valeurs qu'il contient, par priorité (à vérifier avec les entités).
PRIORITE_PTYPE = [
    ("contrainte", {"CTR", "CTR2"}),
    ("objectif", {"PROC"}),
    ("donnee", {"IND2", "DS_LOT", "DS_COUT"}),
    ("probleme", {"IND", "EQUIP"}),
    ("contexte", {"ORG", "SITEC", "PROD"}),
]

CONSIGNE = """Tu écris un document industriel FICTIF, réaliste, pour un jeu de données d'école d'ingénieurs.
Langue du document : {langue}. Type de document : {format}.
Écris 5 à 7 paragraphes courts séparés par une ligne vide, dans cet ordre : présentation de l'entreprise et du site,
problème constaté, données disponibles, travail demandé aux étudiants, contraintes, coordonnées de la personne à
contacter. Style naturel du type de document (formules, abréviations ou fautes légères permises).

Tu DOIS recopier MOT POUR MOT chacune de ces valeurs, sans les traduire ni les modifier :
{valeurs}

N'ajoute aucun autre nom réel d'entreprise, de personne, de ville ni de marque. Réponds seulement par le texte du
document, sans titre ajouté ni commentaire."""

Moteur = Callable[[list[dict], int], str]


# ---------------------------------------------------------------- plan


def planifier(graine: int = GRAINE) -> list[dict]:
    """40 documents : langue, format, secteur, valeurs fictives des emplacements."""
    rng = random.Random(graine)
    langues = LANGUES[:]
    rng.shuffle(langues)
    compte: dict[str, int] = {}
    plan = []
    for i, langue in enumerate(langues):
        secteur = L.SECTEURS[i % len(L.SECTEURS)]
        valeurs, _ = G.choisir_valeurs(langue, secteur, rng, code_switch=False)
        n = 500 + compte.get(langue, 0)
        compte[langue] = compte.get(langue, 0) + 1
        plan.append(
            {
                "doc_id": f"lib_{langue}_{n}",
                "lang": langue,
                "secteur": secteur,
                "format": FORMATS[i % len(FORMATS)],
                "graine": graine * 1000 + i,
                "valeurs": {k: valeurs[k] for k in EMPLACEMENTS},
            }
        )
    return plan


# ---------------------------------------------------------------- rédaction


def messages_redaction(doc: dict) -> list[dict]:
    langue = {"fr": "français", "en": "anglais", "ar": "arabe"}[doc["lang"]]
    valeurs = "\n".join(f"- {v}" for v in doc["valeurs"].values())
    texte = CONSIGNE.format(langue=langue, format=NOM_FORMAT[doc["lang"]][doc["format"]], valeurs=valeurs)
    return [{"role": "user", "content": texte}]


def nettoyer_reponse(reponse: str) -> str:
    """Retire les clôtures de code et les espaces superflus ; paragraphes séparés par une seule ligne vide."""
    texte = re.sub(r"^```\w*\s*|\s*```$", "", reponse.strip())
    paragraphes = [p.strip() for p in re.split(r"\n\s*\n", texte) if p.strip()]
    return "\n\n".join(paragraphes)


def valeurs_absentes(doc: dict, texte: str) -> list[str]:
    """Emplacements dont la valeur n'apparaît pas mot pour mot (le rôle n'est pas une entité : ignoré)."""
    return [k for k, v in doc["valeurs"].items() if k != "ROLE" and v not in texte]


REVISIONS = 3
CONSIGNE_REVISION = """Voici un document industriel FICTIF. Il lui manque des valeurs qui doivent y figurer
MOT POUR MOT. Réécris le document en gardant sa langue, son style, ses paragraphes et tout son contenu, et insère
chacune de ces valeurs exactement telle qu'elle est écrite ici (même orthographe, mêmes chiffres, sans traduction) :
{manquantes}

Ces valeurs sont déjà présentes : garde-les exactement telles quelles.
{presentes}

DOCUMENT À CORRIGER :
{texte}

Réponds seulement par le document corrigé, paragraphes séparés par une ligne vide."""


def messages_revision(doc: dict, texte: str, absentes: list[str]) -> list[dict]:
    """Deuxième tour : insérer mot pour mot les valeurs absentes, sans perdre les autres."""
    manquantes = "\n".join(f"* {doc['valeurs'][k]}" for k in absentes)
    presentes = "\n".join(f"* {v}" for k, v in doc["valeurs"].items() if k not in absentes and k != "ROLE")
    contenu = CONSIGNE_REVISION.format(manquantes=manquantes, presentes=presentes, texte=texte)
    return [{"role": "user", "content": contenu}]


def moteur_fictif(messages: list[dict], graine: int) -> str:
    """Moteur de test : recopie les valeurs dans des paragraphes fixes (aucun GPU) ; en révision, ajoute les valeurs
    manquantes à la fin du document."""
    contenu = messages[0]["content"]
    if "DOCUMENT À CORRIGER :" in contenu:
        texte = contenu.split("DOCUMENT À CORRIGER :\n", 1)[1].split("\n\nRéponds seulement", 1)[0]
        manquantes = re.findall(r"^\* (.*)$", contenu.split("Ces valeurs sont déjà présentes", 1)[0], re.MULTILINE)
        return texte + "\n\n" + " ; ".join(manquantes)
    vals = re.findall(r"^- (.*)$", contenu, re.MULTILINE)
    return "\n\n".join(
        [
            " ".join(vals[0:3]),
            " ".join(vals[3:5]),
            vals[5] + " " + " ".join(vals[11:13]),
            vals[6],
            vals[7] + " ; " + vals[8],
            " ".join(vals[9:11]) + " " + " ".join(vals[13:]),
        ]
    )


def rediger(plan: list[dict], moteur: Moteur, dossier: Path = DOSSIER, reprendre: bool = True) -> list[dict]:
    brut = dossier / "brut"
    brut.mkdir(parents=True, exist_ok=True)
    journal = []
    for doc in plan:
        chemin = brut / f"{doc['doc_id']}.txt"
        if reprendre and chemin.exists():
            texte = chemin.read_text(encoding="utf-8")
        else:
            texte = nettoyer_reponse(moteur(messages_redaction(doc), doc["graine"]))
        absentes = valeurs_absentes(doc, texte)
        depart, revisions = len(absentes), 0
        # Révision : jusqu'à REVISIONS tours pour insérer les valeurs absentes ; on garde la meilleure version.
        while absentes and revisions < REVISIONS:
            revisions += 1
            candidat = nettoyer_reponse(moteur(messages_revision(doc, texte, absentes), doc["graine"] + revisions))
            if len(valeurs_absentes(doc, candidat)) < len(absentes):
                texte, absentes = candidat, valeurs_absentes(doc, candidat)
        chemin.write_text(texte, encoding="utf-8")
        journal.append(
            {
                "doc_id": doc["doc_id"],
                "valeurs_absentes": absentes,
                "absentes_avant_revision": depart,
                "revisions": revisions,
                "caracteres": len(texte),
            }
        )
        print(f"{doc['doc_id']} : {len(texte)} caractères, absentes {depart} -> {len(absentes)} {absentes}", flush=True)
    ecrire_jsonl(dossier / "redaction.jsonl", journal)
    return journal


# ---------------------------------------------------------------- pré-annotation


def occurrences(texte: str, valeurs: dict[str, str]) -> list[dict]:
    """Entités = occurrences exactes des valeurs (les plus longues d'abord, sans chevauchement)."""
    candidats = sorted(((v, k) for k, v in valeurs.items() if k in G.ETIQUETTE and v), key=lambda x: -len(x[0]))
    pris: list[tuple[int, int]] = []
    entites = []
    for valeur, cle in candidats:
        for m in re.finditer(re.escape(valeur), texte):
            if any(m.start() < f and d < m.end() for d, f in pris):
                continue
            pris.append((m.start(), m.end()))
            entites.append(
                {"start": m.start(), "end": m.end(), "label": G.ETIQUETTE[cle], "text": valeur, "ref": G.REFERENCE[cle]}
            )
    return sorted(entites, key=lambda e: e["start"])


def type_passage(texte: str, valeurs: dict[str, str]) -> str:
    presentes = {k for k, v in valeurs.items() if v and v in texte}
    return next((ptype for ptype, cles in PRIORITE_PTYPE if presentes & cles), "autre")


def preannoter(plan: list[dict], dossier: Path = DOSSIER) -> list[dict]:
    passages = []
    for doc in plan:
        chemin = dossier / "brut" / f"{doc['doc_id']}.txt"
        if not chemin.exists():
            continue
        for i, texte in enumerate(p for p in chemin.read_text(encoding="utf-8").split("\n\n") if p.strip()):
            passages.append(
                {
                    "doc_id": doc["doc_id"],
                    "passage_id": f"{doc['doc_id']}_p{i:03d}",
                    "lang": doc["lang"],
                    "text": texte,
                    "ptype": type_passage(texte, doc["valeurs"]),
                    "entities": occurrences(texte, doc["valeurs"]),
                }
            )
    return passages


def ecrire_page(passages: list[dict], chemin: Path) -> None:
    """Page d'annotation du lot A, pré-remplie avec la pré-annotation (mémoire du navigateur séparée)."""
    from cfdata.common import tokenize

    taches = [
        {
            "passage_id": p["passage_id"],
            "lang": p["lang"],
            "text": p["text"],
            "tokens": [[t, s, e] for t, s, e in tokenize(p["text"])],
        }
        for p in passages
    ]
    pre = {
        p["passage_id"]: [{k: e[k] for k in ("start", "end", "label", "text")} for e in p["entities"]] for p in passages
    }
    modele = (RACINE / "caseforge/gold/annoter_v4.html").read_text(encoding="utf-8")
    remplacements = [
        ("__TACHES__", json.dumps(taches, ensure_ascii=False)),
        ("__LABELS__", json.dumps(list(LABELS))),
        ('"cf_kappa_v4_"', '"cf_verif_libres_v4_"'),
        ('localStorage.getItem(cle())||"{}"', "localStorage.getItem(cle())||JSON.stringify(PRE)"),
    ]
    for ancien, nouveau in remplacements:
        if ancien not in modele:
            raise SystemExit(f"Modèle de page inattendu : « {ancien} » introuvable dans annoter_v4.html")
        modele = modele.replace(ancien, nouveau)
    modele = modele.replace("<script>", "<script>\nconst PRE=" + json.dumps(pre, ensure_ascii=False) + ";", 1)
    modele = re.sub(r"<title>.*?</title>", "<title>CaseForge · vérification des textes libres v4</title>", modele)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(modele.encode("utf-8"))


# ---------------------------------------------------------------- intégration


def integrer(plan: list[dict], passages: list[dict], export: dict, dossier: Path = DOSSIER) -> int:
    """Passages vérifiés -> passages.jsonl, documents.jsonl, metadonnees.csv (format de synth_v4)."""
    verifies = {a["passage_id"]: a["entities"] for a in export["annotations"]}
    manquants = [p["passage_id"] for p in passages if p["passage_id"] not in verifies]
    if manquants:
        raise SystemExit(f"{len(manquants)} passages non vérifiés dans l'export (ex. {manquants[:3]})")
    infos = {d["doc_id"]: d for d in plan}
    lignes, documents = [], {}
    for p in passages:
        doc = infos[p["doc_id"]]
        refs = {(e["label"], e["text"]): e.get("ref") for e in p["entities"]}
        entites = [
            {
                **{k: e[k] for k in ("start", "end", "label", "text")},
                "ref": refs.get((e["label"], e["text"])) or f"{e['label'].lower()}_{i}",
            }
            for i, e in enumerate(sorted(verifies[p["passage_id"]], key=lambda e: e["start"]))
        ]
        lignes.append(
            {
                "doc_id": p["doc_id"],
                "passage_id": p["passage_id"],
                "text": p["text"],
                "entities": entites,
                "lang": doc["lang"],
                "doc_lang": doc["lang"],
                "sensitivity": G.sensibilite(entites),
                "ptype": p["ptype"],
                "secteur": doc["secteur"],
                "format": doc["format"],
                "bruit": "libre",
                "famille": "L",
                "source_id": "SRC-LIBRE",
                "source_type": "simule_redaction_libre",
                "licence": "CC-BY-4.0 (équipe)",
                "annotation_method": "redaction_llm_preannotation_verifiee",
                "verifie_humain": True,
                "n_annotateurs": 1,
                "n_annotateurs_aveugles": 0,
                "labels_couverts": list(LABELS),
                "version": "v4",
                "annotateur": export["annotateur"],
                "generation": {"modele": "Qwen/Qwen2.5-7B-Instruct (4 bits)", "graine": doc["graine"]},
            }
        )
        anonyme, remplacements = G.anonymiser(p["text"], entites)
        documents.setdefault(
            p["doc_id"],
            {
                "doc_id": p["doc_id"],
                "lang": doc["lang"],
                "secteur": doc["secteur"],
                "format": doc["format"],
                "source_id": "SRC-LIBRE",
                "version": "v4",
                "passages": [],
            },
        )
        documents[p["doc_id"]]["passages"].append(
            {
                "passage_id": p["passage_id"],
                "ptype": p["ptype"],
                "text": p["text"],
                "text_anonymise": anonyme,
                "entities": entites,
                "remplacements": remplacements,
            }
        )
    ecrire_jsonl(dossier / "passages.jsonl", lignes)
    ecrire_jsonl(dossier / "documents.jsonl", list(documents.values()))
    with open(dossier / "metadonnees.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["doc_id", "langue", "secteur", "format", "bruit", "version", "graine", "auteur"])
        for d in plan:
            if d["doc_id"] in documents:
                w.writerow(
                    [
                        d["doc_id"],
                        d["lang"],
                        d["secteur"],
                        d["format"],
                        "libre",
                        "v4",
                        d["graine"],
                        f"Qwen2.5-7B + {export['annotateur']}",
                    ]
                )
    return len(lignes)


# ---------------------------------------------------------------- utilitaires


def ecrire_jsonl(chemin: Path, lignes: list[dict]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in lignes)


def lire_jsonl(chemin: Path) -> list[dict]:
    return [json.loads(x) for x in chemin.read_text(encoding="utf-8").splitlines() if x.strip()]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]  # console Windows (cp1252)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = ap.add_subparsers(dest="etape", required=True)
    sous.add_parser("plan")
    r = sous.add_parser("rediger")
    r.add_argument("--moteur", choices=["transformers", "fictif"], default="transformers")
    r.add_argument("--modele", default="Qwen/Qwen2.5-7B-Instruct")
    r.add_argument("--limite", type=int)
    sous.add_parser("preannoter")
    i = sous.add_parser("integrer")
    i.add_argument("export", type=Path, help="fichier JSON téléchargé depuis la page de vérification")
    args = ap.parse_args()

    if args.etape == "plan":
        plan = planifier()
        ecrire_jsonl(DOSSIER / "plan.jsonl", plan)
        print(f"{len(plan)} documents -> {DOSSIER / 'plan.jsonl'}")
        return
    plan = lire_jsonl(DOSSIER / "plan.jsonl")
    if args.etape == "rediger":
        if args.moteur == "fictif":
            moteur: Moteur = moteur_fictif
        else:
            from llm import moteur_transformers

            moteur = moteur_transformers(args.modele, 0.5, 1500)
        journal = rediger(plan[: args.limite], moteur)
        print(f"{sum(not j['valeurs_absentes'] for j in journal)} / {len(journal)} documents avec toutes les valeurs")
    elif args.etape == "preannoter":
        passages = preannoter(plan)
        ecrire_jsonl(DOSSIER / "a_verifier/passages_preannotes.jsonl", passages)
        ecrire_page(passages, DOSSIER / "a_verifier/verifier.html")
        print(f"{len(passages)} passages pré-annotés -> {DOSSIER / 'a_verifier/verifier.html'}")
    else:
        passages = lire_jsonl(DOSSIER / "a_verifier/passages_preannotes.jsonl")
        export = json.loads(args.export.read_text(encoding="utf-8"))
        n = integrer(plan, passages, export)
        print(f"{n} passages vérifiés -> {DOSSIER / 'passages.jsonl'} ; ensuite : python -m caseforge.gold.train_v4")


if __name__ == "__main__":
    main()
