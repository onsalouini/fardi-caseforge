"""Lot B Gold · G2 : jeu tunisien et code-switché (évaluation seulement, jamais d'entraînement).

Les passages sont rédigés et annotés par des humains de l'équipe dans des fichiers texte, un passage par ligne,
avec une annotation simple dans le texte : ``[Sonede](ORG)``. Ce module :

- lit ces fichiers (:func:`lire_fichier`) et les convertit au format JSONL de ``data/final/`` (:func:`convertir`) ;
- contrôle offsets, étiquettes, métadonnées et doublons avec le train, le dev et les autres passages tunisiens
  (:func:`controler`) ;
- prépare les fichiers vierges de la double annotation à l'aveugle (:func:`fichier_vierge`) ;
- calcule le kappa de Cohen au niveau des mots entre deux annotateurs, par étiquette et par écriture, et liste les
  désaccords à arbitrer (:func:`accord`).

Format d'un fichier (voir ``data/lotb/tunisien/MODELE.txt`` et ``docs/guide_tunisien.md``) :

- ligne vide ou commençant par ``#`` : ignorée ;
- ``@annotateur: <nom>`` : une fois par fichier, avant le premier passage ;
- ``@doc: tun_<identifiant>`` : ouvre un document ; ses passages sont numérotés ``<doc>_p000``, ``_p001``… ;
- ``@ecriture: arabe|arabizi|latin`` et ``@lang: ar|mixte`` : valent pour les passages qui suivent ;
- toute autre ligne est un passage ; ``[texte](ETIQUETTE)`` marque une entité ; ``\\[``, ``\\]`` et ``\\\\``
  écrivent un crochet ou une barre oblique inverse littéraux.

Les étiquettes viennent de :mod:`caseforge.labels` ; aucune liste n'est écrite en dur ici.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from caseforge.labels import LABELS, REPO_ROOT, SENSITIVE_LABELS
from cfdata.agreement import cohen_kappa, token_labels
from cfdata.common import tokenize, trim_span

DOSSIER = REPO_ROOT / "data" / "lotb" / "tunisien"
GOLD = DOSSIER / "gold"
DOUBLE = DOSSIER / "double"
TEXTES = DOSSIER / "textes"
SORTIE_JSONL = DOSSIER / "tunisien.jsonl"
PREFIXE_DOC = "tun_"
SOURCE_ID = "SRC-TUN"
ECRITURES = ("arabe", "arabizi", "latin")
LANGS = ("ar", "mixte")
CIBLE_KAPPA = 0.70
CIBLE_PASSAGES = 60

_DIRECTIVE = re.compile(r"^@(\w+)\s*:\s*(.*?)\s*$")
_FIN_ENTITE = re.compile(r"\]\(([^()\s]*)\)")
_ID_DOC = re.compile(rf"^{PREFIXE_DOC}[A-Za-z0-9_-]+$")
_AR = re.compile(r"[؀-ۿݐ-ݿ]")
_LATIN = re.compile(r"[A-Za-zÀ-ÿ]")
_TASHKIL = re.compile(r"[ً-ٰٟـ]")  # voyelles brèves, shadda, tatwil


class ErreurTunisien(ValueError):
    """Erreur de format ou de contrôle ; le message liste chaque problème avec son fichier et sa ligne."""

    def __init__(self, problemes: list[str]) -> None:
        self.problemes = problemes
        super().__init__(f"{len(problemes)} problème(s) :\n" + "\n".join(f"  - {p}" for p in problemes))


@dataclass
class Passage:
    """Un passage lu dans un fichier texte, avec son origine pour les messages d'erreur."""

    passage_id: str
    doc_id: str
    text: str
    entities: list[dict[str, Any]]
    ecriture: str
    lang: str
    annotateur: str
    origine: str  # « fichier:ligne »
    avertissements: list[str] = field(default_factory=list)

    def ligne_jsonl(self) -> dict[str, Any]:
        """Ligne au format de ``data/final/*.jsonl`` (champs utiles au harnais, plus ``ecriture`` et ``annotateur``)."""
        return {
            "doc_id": self.doc_id,
            "passage_id": self.passage_id,
            "text": self.text,
            "entities": [{**e, "text": self.text[e["start"] : e["end"]]} for e in self.entities],
            "lang": self.lang,
            "doc_lang": "ar",
            "ecriture": self.ecriture,
            "annotateur": self.annotateur,
            "source_id": SOURCE_ID,
            "source_type": "redaction_humaine_tunisien",
            "annotation_method": "humain",
            "verifie_humain": True,
            "usage": "evaluation_seulement",
            "labels_couverts": list(LABELS),
        }


# ----------------------------------------------------------------- lecture d'une ligne annotée
def analyser_ligne(ligne: str) -> tuple[str, list[dict[str, Any]]]:
    """Retire l'annotation en ligne ; renvoie le texte brut et les entités (start, end, label).

    Lève ``ValueError`` (message en français, avec la colonne) si un crochet n'est pas fermé, si une entité est
    imbriquée, vide ou sans étiquette, ou si l'étiquette est inconnue.
    """
    texte: list[str] = []
    entites: list[dict[str, Any]] = []
    ouverte: tuple[int, int] | None = None  # (position dans le texte brut, colonne dans la ligne)
    i = 0
    while i < len(ligne):
        c = ligne[i]
        if c == "\\" and i + 1 < len(ligne) and ligne[i + 1] in "[]\\":
            texte.append(ligne[i + 1])
            i += 2
            continue
        if c == "[":
            if ouverte is not None:
                raise ValueError(f"colonne {i + 1} : « [ » dans une entité déjà ouverte (pas d'imbrication)")
            ouverte = (len(texte), i + 1)
            i += 1
            continue
        if c == "]":
            m = _FIN_ENTITE.match(ligne, i)
            if ouverte is None:
                raise ValueError(f"colonne {i + 1} : « ] » sans « [ » (écrire \\] pour un crochet littéral)")
            if m is None:
                raise ValueError(f"colonne {i + 1} : « ] » doit être suivi de (ETIQUETTE), par exemple [Sonede](ORG)")
            label = m.group(1)
            if label not in LABELS:
                raise ValueError(f"colonne {i + 2} : étiquette inconnue « {label} » (attendues : {', '.join(LABELS)})")
            debut, col = ouverte
            if debut == len(texte):
                raise ValueError(f"colonne {col} : entité vide")
            entites.append({"start": debut, "end": len(texte), "label": label})
            ouverte = None
            i = m.end()
            continue
        texte.append(c)
        i += 1
    if ouverte is not None:
        raise ValueError(f"colonne {ouverte[1]} : « [ » jamais fermé")
    return "".join(texte), entites


def retirer_annotation(ligne: str) -> str:
    """Texte d'une ligne sans son annotation (les échappements sont résolus)."""
    return analyser_ligne(ligne)[0]


def problemes_entites(texte: str, entites: list[dict[str, Any]]) -> list[str]:
    """Contrôle des offsets : bornes, texte non vide, aucune espace ni ponctuation en bordure, aucun chevauchement."""
    out = []
    for e in entites:
        s, t, lab = e["start"], e["end"], e["label"]
        extrait = texte[s:t]
        if lab not in LABELS:
            out.append(f"étiquette inconnue « {lab} »")
        if not (0 <= s < t <= len(texte)):
            out.append(f"offsets invalides {s}-{t} (texte de {len(texte)} caractères)")
            continue
        if not extrait.strip():
            out.append(f"entité {lab} vide ou réduite à des espaces")
        elif extrait != extrait.strip():
            out.append(f"bordure de « {extrait} » ({lab}) : espace à l'intérieur du crochet")
        elif trim_span(texte, s, t)[0] >= trim_span(texte, s, t)[1]:
            out.append(f"entité {lab} « {extrait} » réduite à de la ponctuation")
    tries = sorted(entites, key=lambda e: e["start"])
    for a, b in zip(tries, tries[1:], strict=False):
        if b["start"] < a["end"]:
            out.append(f"chevauchement : « {texte[a['start'] : a['end']]} » et « {texte[b['start'] : b['end']]} »")
    return out


def rogner(texte: str, entites: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retire la ponctuation en bordure avec ``cfdata.common.trim_span``, comme le Lot A (« Si Karim B. » → « … B »)."""
    out = []
    for e in entites:
        s, t = trim_span(texte, e["start"], e["end"])
        out.append({**e, "start": s, "end": t})
    return out


def avertissements_ecriture(texte: str, ecriture: str) -> list[str]:
    """Signale une écriture déclarée qui ne correspond pas aux lettres du passage (simple avertissement)."""
    n_ar, n_lat = len(_AR.findall(texte)), len(_LATIN.findall(texte))
    if ecriture == "arabe" and n_ar <= n_lat:
        return [f"écriture « arabe » déclarée, mais {n_lat} lettres latines pour {n_ar} lettres arabes"]
    if ecriture in ("arabizi", "latin") and n_ar > n_lat:
        return [f"écriture « {ecriture} » déclarée, mais {n_ar} lettres arabes pour {n_lat} lettres latines"]
    return []


# ----------------------------------------------------------------- lecture d'un fichier
def lire_lignes(lignes: Iterable[str], nom: str = "<texte>", annotations: bool = True) -> list[Passage]:
    """Lit un fichier au format décrit en tête du module ; lève :class:`ErreurTunisien` avec tous les problèmes.

    Avec ``annotations=False`` (fichier de textes bruts à double annoter), tout crochet d'annotation est refusé.
    """
    problemes: list[str] = []
    passages: list[Passage] = []
    etat: dict[str, str | None] = {"annotateur": None, "doc": None, "ecriture": None, "lang": None}
    rang: Counter[str] = Counter()
    for n, brute in enumerate(lignes, start=1):
        ligne = brute.rstrip("\r\n").lstrip("﻿")
        ou = f"{nom}:{n}"
        if not ligne.strip() or ligne.lstrip().startswith("#"):
            continue
        m = _DIRECTIVE.match(ligne.strip())
        if m:
            cle, val = m.group(1).lower(), m.group(2)
            if cle not in etat:
                problemes.append(f"{ou} : directive inconnue @{cle} (attendues : @annotateur, @doc, @ecriture, @lang)")
            elif cle == "doc" and not _ID_DOC.match(val):
                problemes.append(f"{ou} : @doc « {val} » doit commencer par {PREFIXE_DOC} (lettres, chiffres, _ ou -)")
            elif cle == "ecriture" and val not in ECRITURES:
                problemes.append(f"{ou} : @ecriture « {val} » inconnue (attendues : {', '.join(ECRITURES)})")
            elif cle == "lang" and val not in LANGS:
                problemes.append(f"{ou} : @lang « {val} » inconnue (attendues : {', '.join(LANGS)})")
            elif cle == "annotateur" and (not val or etat["annotateur"] not in (None, val)):
                problemes.append(f"{ou} : @annotateur vide ou différent du premier (un fichier par annotateur)")
            else:
                etat[cle] = val
            continue
        manque = [f"@{k}" for k, v in etat.items() if v is None and (annotations or k != "annotateur")]
        if manque:
            problemes.append(f"{ou} : passage avant {', '.join(manque)}")
            continue
        try:
            texte, entites = analyser_ligne(ligne)
        except ValueError as exc:
            problemes.append(f"{ou} : {exc}")
            continue
        if not annotations and entites:
            problemes.append(f"{ou} : annotation trouvée dans un fichier de textes bruts (aucune pré-annotation)")
            continue
        if texte != texte.strip():
            problemes.append(f"{ou} : espace en début ou en fin de passage")
        avant = len(problemes)
        problemes += [f"{ou} : {p}" for p in problemes_entites(texte, entites)]
        if len(problemes) == avant:
            entites = rogner(texte, entites)
        doc = str(etat["doc"])
        passages.append(
            Passage(
                passage_id=f"{doc}_p{rang[doc]:03d}",
                doc_id=doc,
                text=texte,
                entities=entites,
                ecriture=str(etat["ecriture"]),
                lang=str(etat["lang"]),
                annotateur=str(etat["annotateur"] or ""),
                origine=ou,
                avertissements=avertissements_ecriture(texte, str(etat["ecriture"])),
            )
        )
        rang[doc] += 1
    if problemes:
        raise ErreurTunisien(problemes)
    return passages


def lire_fichier(chemin: Path, annotations: bool = True) -> list[Passage]:
    """Lit un fichier texte UTF-8 (voir :func:`lire_lignes`)."""
    nom = chemin.relative_to(REPO_ROOT).as_posix() if chemin.is_relative_to(REPO_ROOT) else str(chemin)
    with open(chemin, encoding="utf-8") as f:
        return lire_lignes(f, nom, annotations)


# ----------------------------------------------------------------- doublons
def normaliser(texte: str) -> str:
    """Clé de comparaison : NFKC, minuscules, sans voyelles arabes ni tatwil, sans ponctuation, espaces réduites."""
    t = _TASHKIL.sub("", unicodedata.normalize("NFKC", texte).casefold())
    t = "".join(c if c.isalnum() else " " for c in t)
    return " ".join(t.split())


def doublons(passages: list[Passage], references: dict[str, Iterable[dict]]) -> list[str]:
    """Doublons (texte normalisé) entre passages tunisiens, et avec chaque corpus de ``references`` (train, dev)."""
    out = []
    vus: dict[str, Passage] = {}
    ids: dict[str, Passage] = {}
    for p in passages:
        if p.passage_id in ids:
            out.append(f"{p.origine} : passage_id {p.passage_id} déjà utilisé en {ids[p.passage_id].origine}")
        ids.setdefault(p.passage_id, p)
        cle = normaliser(p.text)
        if cle in vus:
            out.append(f"{p.origine} : même texte que {vus[cle].passage_id} ({vus[cle].origine})")
        vus.setdefault(cle, p)
    for nom, rows in references.items():
        for r in rows:
            p = vus.get(normaliser(r["text"]))
            if p is not None:
                out.append(f"{p.origine} : même texte que {r['passage_id']} du {nom}")
            if str(r.get("doc_id", "")).startswith(PREFIXE_DOC):
                out.append(f"{nom} : le document {r['doc_id']} porte le préfixe {PREFIXE_DOC} (jeu d'évaluation)")
    return out


def controler(passages: list[Passage], references: dict[str, Iterable[dict]]) -> None:
    """Contrôles globaux (doublons et identifiants) ; lève :class:`ErreurTunisien` s'il y a un problème."""
    problemes = doublons(passages, references)
    if problemes:
        raise ErreurTunisien(problemes)


def convertir(fichiers: list[Path], references: dict[str, Iterable[dict]]) -> list[dict[str, Any]]:
    """Lit et contrôle tous les fichiers (problèmes regroupés), puis renvoie les lignes JSONL."""
    passages: list[Passage] = []
    problemes: list[str] = []
    for f in fichiers:
        try:
            passages += lire_fichier(f)
        except ErreurTunisien as exc:
            problemes += exc.problemes
    if problemes:
        raise ErreurTunisien(problemes)
    controler(passages, references)
    return [p.ligne_jsonl() for p in passages]


def repartition(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Effectifs par écriture, par langue et par étiquette, et part des passages en lettres arabes."""
    ecr = Counter(r["ecriture"] for r in rows)
    etiq = Counter(e["label"] for r in rows for e in r["entities"])
    return {
        "n_passages": len(rows),
        "n_documents": len({r["doc_id"] for r in rows}),
        "par_ecriture": {k: ecr[k] for k in ECRITURES},
        "par_lang": {k: sum(r["lang"] == k for r in rows) for k in LANGS},
        "par_etiquette": {lab: etiq[lab] for lab in LABELS},
        "passages_avec_sensible": {
            lab: sum(any(e["label"] == lab for e in r["entities"]) for r in rows) for lab in LABELS
        },
        "part_arabe": ecr["arabe"] / len(rows) if rows else 0.0,
    }


def ecarts_repartition(rep: dict[str, Any], minimum_par_sensible: int = 10) -> list[str]:
    """Écarts à la répartition visée (guide tunisien) : simples avertissements, jamais bloquants."""
    out = []
    n = rep["n_passages"]
    if n != CIBLE_PASSAGES:
        out.append(f"{n} passages pour {CIBLE_PASSAGES} visés")
    if n and abs(rep["part_arabe"] - 0.5) > 0.1:
        out.append(f"{100 * rep['part_arabe']:.0f} % de passages en lettres arabes (visé : environ 50 %)")
    for lab in LABELS:
        if lab in SENSITIVE_LABELS and rep["passages_avec_sensible"][lab] < minimum_par_sensible:
            out.append(
                f"{lab} présent dans {rep['passages_avec_sensible'][lab]} passages (visé : ≥ {minimum_par_sensible})"
            )
    return out


# ----------------------------------------------------------------- double annotation
def fichier_vierge(lignes: Iterable[str], annotateur: str) -> str:
    """Copie d'un fichier de textes bruts pour un annotateur : directives et passages, sans aucune annotation.

    Refuse un fichier qui contient déjà une annotation (garantie d'absence de pré-annotation) ou un
    ``@annotateur``.
    """
    lignes = list(lignes)
    lire_lignes(lignes, annotations=False)  # lève si une annotation ou une erreur de format est présente
    out = [
        f"# Double annotation à l'aveugle : annoter seul, sans voir le fichier de l'autre annotateur.\n"
        f"# Ne modifier que les crochets : le texte doit rester identique au caractère près.\n"
        f"@annotateur: {annotateur}\n"
    ]
    for brute in lignes:
        if _DIRECTIVE.match(brute.strip()) and brute.strip().lower().startswith("@annotateur"):
            raise ValueError("un fichier de textes bruts ne doit pas contenir @annotateur")
        out.append(brute.rstrip("\r\n") + "\n")
    return "".join(out)


def _kappa_ou_none(a: list[str], b: list[str]) -> float | None:
    """Kappa de Cohen ; ``None`` si aucun mot ou si les deux annotateurs n'emploient qu'une même valeur."""
    if not a or set(a) == set(b) and len(set(a)) == 1:
        return None
    return cohen_kappa(a, b)


def _binaire(seq: list[str], label: str) -> list[str]:
    return [label if x == label else "autre" for x in seq]


def _bloc(a: list[str], b: list[str], n_passages: int) -> dict[str, Any]:
    return {
        "n_passages": n_passages,
        "n_mots": len(a),
        "kappa": _kappa_ou_none(a, b),
        "accord_brut": sum(x == y for x, y in zip(a, b, strict=True)) / len(a) if a else None,
    }


def apparier(pa: list[Passage], pb: list[Passage]) -> list[tuple[Passage, Passage]]:
    """Associe les passages des deux annotateurs par ``passage_id`` et vérifie que les textes sont identiques."""
    ia, ib = {p.passage_id: p for p in pa}, {p.passage_id: p for p in pb}
    problemes = [f"{i} absent du fichier de {pb[0].annotateur if pb else 'B'}" for i in ia if i not in ib]
    problemes += [f"{i} absent du fichier de {pa[0].annotateur if pa else 'A'}" for i in ib if i not in ia]
    for i in ia.keys() & ib.keys():
        a, b = ia[i], ib[i]
        if a.text != b.text:
            problemes.append(f"{i} : texte différent entre {a.origine} et {b.origine} (seuls les crochets changent)")
        if (a.ecriture, a.lang) != (b.ecriture, b.lang):
            problemes.append(f"{i} : @ecriture / @lang différents entre {a.origine} et {b.origine}")
    if problemes:
        raise ErreurTunisien(sorted(problemes))
    return [(ia[i], ib[i]) for i in ia]


def accord(pa: list[Passage], pb: list[Passage]) -> dict[str, Any]:
    """Kappa au niveau des mots (``cfdata.agreement``) : global, par étiquette (une contre le reste), par écriture.

    Renvoie aussi la liste des désaccords à arbitrer : pour chaque passage, les entités propres à chaque annotateur.
    """
    paires = apparier(pa, pb)
    seq_a: list[str] = []
    seq_b: list[str] = []
    par_ecr: dict[str, tuple[list[str], list[str], list[str]]] = defaultdict(lambda: ([], [], []))
    desaccords = []
    for a, b in paires:
        la, lb = token_labels(a.text, a.entities), token_labels(b.text, b.entities)
        seq_a += la
        seq_b += lb
        ea, eb, ids = par_ecr[a.ecriture]
        ea += la
        eb += lb
        ids.append(a.passage_id)
        sa = {(e["start"], e["end"], e["label"]) for e in a.entities}
        sb = {(e["start"], e["end"], e["label"]) for e in b.entities}
        if sa != sb:
            mots = [(tok, x, y) for (tok, _, _), x, y in zip(tokenize(a.text), la, lb, strict=True) if x != y]
            desaccords.append(
                {
                    "passage_id": a.passage_id,
                    "ecriture": a.ecriture,
                    "text": a.text,
                    "seulement_a": [_ent(a.text, s) for s in sorted(sa - sb)],
                    "seulement_b": [_ent(a.text, s) for s in sorted(sb - sa)],
                    "mots_en_desaccord": len(mots),
                    "mots": [{"mot": t, "a": x, "b": y} for t, x, y in mots],
                }
            )
    par_etiquette = {}
    for lab in LABELS:
        ba, bb = _binaire(seq_a, lab), _binaire(seq_b, lab)
        par_etiquette[lab] = {
            "kappa": _kappa_ou_none(ba, bb),
            "mots_a": ba.count(lab),
            "mots_b": bb.count(lab),
        }
    return {
        "annotateur_a": pa[0].annotateur if pa else "",
        "annotateur_b": pb[0].annotateur if pb else "",
        "cible": CIBLE_KAPPA,
        "global": _bloc(seq_a, seq_b, len(paires)),
        "par_etiquette": par_etiquette,
        "par_ecriture": {k: _bloc(v[0], v[1], len(v[2])) for k, v in sorted(par_ecr.items())},
        "desaccords": desaccords,
    }


def _ent(texte: str, s: tuple[int, int, str]) -> dict[str, Any]:
    return {"start": s[0], "end": s[1], "label": s[2], "text": texte[s[0] : s[1]]}


def _k(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}".replace(".", ",")


def rapport_accord(res: dict[str, Any], titre: str) -> str:
    """Rapport Markdown de l'accord inter-annotateurs et des désaccords à arbitrer."""
    g = res["global"]
    atteinte = g["kappa"] is not None and g["kappa"] >= res["cible"]
    L = [
        f"# Accord inter-annotateurs, jeu tunisien : {titre}",
        "",
        f"Annotateurs : {res['annotateur_a']} (A) et {res['annotateur_b']} (B), à l'aveugle, sans pré-annotation. "
        "Kappa de Cohen au niveau des mots (`cfdata.agreement`, tokenisation cfdata), étiquette du mot ou `O`. "
        f"Cible : kappa ≥ {_k(res['cible'])}.",
        "",
        f"**Kappa global : {_k(g['kappa'])}** ({g['n_passages']} passages, {g['n_mots']} mots ; accord brut "
        f"{_k(g['accord_brut'])}) : cible {'atteinte' if atteinte else 'NON atteinte'}.",
        "",
        "## Par écriture",
        "",
        "| écriture | passages | mots | kappa | accord brut |",
        "|---|---|---|---|---|",
        *[
            f"| {k} | {v['n_passages']} | {v['n_mots']} | {_k(v['kappa'])} | {_k(v['accord_brut'])} |"
            for k, v in res["par_ecriture"].items()
        ],
        "",
        "## Par étiquette (l'étiquette contre tout le reste)",
        "",
        "| étiquette | mots A | mots B | kappa |",
        "|---|---|---|---|",
        *[f"| {lab} | {v['mots_a']} | {v['mots_b']} | {_k(v['kappa'])} |" for lab, v in res["par_etiquette"].items()],
        "",
        "n/a : étiquette employée par aucun des deux annotateurs.",
        "",
        f"## Désaccords à arbitrer ({len(res['desaccords'])} passages)",
        "",
    ]
    if not res["desaccords"]:
        L.append("Aucun.")
    for d in res["desaccords"]:
        L += [
            f"### {d['passage_id']} ({d['ecriture']}, {d['mots_en_desaccord']} mots en désaccord)",
            "",
            f"> {d['text']}",
            "",
            "- seulement A : " + (" ; ".join(f"« {e['text']} » {e['label']}" for e in d["seulement_a"]) or "—"),
            "- seulement B : " + (" ; ".join(f"« {e['text']} » {e['label']}" for e in d["seulement_b"]) or "—"),
            "- mots : " + (" ; ".join(f"{m['mot']} ({m['a']} / {m['b']})" for m in d["mots"]) or "bordures seules"),
            "- décision : ",
            "",
        ]
    return "\n".join(L) + "\n"
