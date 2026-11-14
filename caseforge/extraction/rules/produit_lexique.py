"""B15 : têtes de PRODUIT apprises sur le gold du train (``dependencies.produit_lexique``).

Apprentissage (``apprendre``) : pour chaque PRODUIT gold, le mot-tête de sa surface, avec la langue du span. Le
français et l'arabe placent la tête en premier (« tuyaux en cuivre », « الأنابيب البلاستيكية ») ; l'anglais en
dernier (« copper pipes »). Les mots trop courts, les mots génériques (``generiques.txt``) et les têtes partagées
avec les lexiques d'EQUIPEMENT ou de PROCESSUS (ambiguës, cas 6 et 8) sont écartés.

Extraction (``lexique_candidates``) : une tête connue, analysée comme nom, ouvre un PRODUIT. En français et en
arabe, la valeur est lue vers la droite comme pour les autres règles (``produit.valeurs``) ; en anglais, le groupe
nominal est lu vers la gauche (adjectifs, noms, nombres), et un mot suivi d'un autre nom n'est pas une tête
(« oil change »). Les candidats ne font que combler les trous (``combler``) : un candidat qui chevauche un candidat
déjà proposé, quelle que soit son étiquette, est écarté.

Validation croisée : le lexique est appris sur les plis d'entraînement et passé dans la configuration
(``cfg["lexique_produit"]``) ; sans cette clé, il est lu dans ``data/lexicons/produit_tetes_train.txt``, appris
sur tout le train (``scripts/b15_regles_train.py``).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from functools import cache
from pathlib import Path
from typing import Any

from spacy.tokens import Doc

from caseforge.extraction.rules.base import Candidat
from caseforge.extraction.rules.dependencies import _delim, _lang, _span, preparer
from caseforge.extraction.rules.lexicons import (
    LEXIQUES,
    ensemble_normalise,
    est_arabe,
    normaliser,
    sans_article,
    termes,
)
from caseforge.extraction.rules.produit import _DETERMINANTS, _PARTITIFS, DEFAUT, OptionsProduit, valeurs

REGLE = "dependencies.produit_lexique"
FICHIER = LEXIQUES / "produit_tetes_train.txt"
LONGUEUR_MIN = 3
MAX_GAUCHE = 6
_MOTS = re.compile(r"[^\W\d_]+")
_NOMS = {"NOUN", "PROPN"}

Tetes = frozenset[tuple[str, str]]


@cache
def _exclus() -> frozenset[str]:
    """Mots qui ne peuvent pas être une tête : génériques, têtes d'EQUIPEMENT et de PROCESSUS (un seul mot)."""
    out = set(ensemble_normalise("generiques", article=False))
    for nom in ("equipement_tetes", "processus_tetes"):
        out |= {sans_article(normaliser(t)) for t in termes(nom) if t and " " not in t}
    return frozenset(out)


def langue_span(surface: str, lang: str, doc_lang: str) -> str:
    """Langue d'un span gold : arabe d'après l'écriture, sinon celle du passage (ou du document), français par
    défaut (comme ``dependencies._lang`` pour un mot latin dans un passage arabe)."""
    if est_arabe(surface):
        return "ar"
    return next((x for x in (lang, doc_lang) if x in {"fr", "en"}), "fr")


def tete(surface: str, langue: str) -> str | None:
    """Mot-tête normalisé d'une surface de PRODUIT (premier mot en fr / ar, dernier en en), ou ``None``."""
    mots = [sans_article(normaliser(m)) if langue == "ar" else normaliser(m) for m in _MOTS.findall(surface)]
    mots = [m for m in mots if len(m) >= LONGUEUR_MIN and m not in _DETERMINANTS | _PARTITIFS]
    if not mots:
        return None
    t = mots[-1] if langue == "en" else mots[0]
    return None if t in _exclus() else t


def apprendre(rows: Iterable[Mapping[str, Any]], label: str = "PRODUIT") -> Tetes:
    """Têtes ``(langue, tête)`` des entités ``label`` du gold de ``rows`` (passages au format de ``train.jsonl``)."""
    out: set[tuple[str, str]] = set()
    for r in rows:
        for e in r["entities"]:
            if e["label"] != label:
                continue
            surface = r["text"][e["start"] : e["end"]]
            langue = langue_span(surface, r.get("lang", ""), r.get("doc_lang", ""))
            t = tete(surface, langue)
            if t is not None:
                out.add((langue, t))
    return frozenset(out)


def ecrire(tetes: Tetes, chemin: Path = FICHIER) -> int:
    """Écrit le lexique (``tête<TAB>langue``, trié) ; renvoie le nombre de lignes."""
    entete = (
        "# Têtes de PRODUIT apprises sur le gold du train (B15, caseforge.extraction.rules.produit_lexique).\n"
        "# Source : entités gold PRODUIT du TRAIN (data/final/train.jsonl) ; dev non lu.\n"
        "# Généré par python -m scripts.b15_regles_train ; ne pas éditer à la main. Format : tête<TAB>langue.\n"
    )
    lignes = [f"{t}\t{lang}" for lang, t in sorted(tetes, key=lambda x: (x[0], x[1]))]
    chemin.write_text(entete + "\n".join(lignes) + "\n", encoding="utf-8")
    return len(lignes)


@cache
def charger(chemin: Path = FICHIER) -> Tetes:
    """Lexique écrit par ``ecrire`` (vide si le fichier n'existe pas)."""
    if not chemin.exists():
        return frozenset()
    out = set()
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if ligne and not ligne.startswith("#"):
            t, lang = ligne.split("\t")
            out.add((lang, t))
    return frozenset(out)


def tetes_config(cfg: Mapping[str, Any]) -> Tetes:
    """Lexique de la configuration (``lexique_produit``, validation croisée), sinon celui du fichier."""
    lex = cfg.get("lexique_produit")
    return charger() if lex is None else frozenset(lex)


def lexique_candidates(doc: Doc, tetes: Tetes, o: OptionsProduit = DEFAUT) -> list[Candidat]:
    """Candidats ``dependencies.produit_lexique`` ouverts par une tête connue."""
    if not tetes:
        return []
    preparer(doc)
    out: list[Candidat] = []
    for t in doc:
        lang = _lang(t)
        cle = sans_article(t._.norme) if lang == "ar" else t._.norme
        if (lang, cle) not in tetes or t.pos_ not in _NOMS:
            continue
        if lang == "en":
            if t.i + 1 < len(doc) and doc[t.i + 1].pos_ in _NOMS and _lang(doc[t.i + 1]) == "en":
                continue  # modifieur d'un autre nom (« oil change »)
            k = t.i
            while (
                k > 0
                and t.i - k < MAX_GAUCHE
                and doc[k - 1].pos_ in {"ADJ", "NOUN", "PROPN", "NUM"}
                and not _delim(doc[k - 1])
                and doc[k - 1]._.norme not in _DETERMINANTS
            ):
                k -= 1
            c = _span(doc, k, t.i + 1, "PRODUIT", REGLE)
            out += [c] if c is not None else []
        else:
            if t.i > 0 and doc[t.i - 1]._.norme in {"a", "au", "aux"}:
                continue  # complément d'un nom de machine (« presse à biscuits »)
            out += valeurs(doc, t.i, REGLE, o=o)[:1]
    return out


def combler(cands: list[Candidat], nouveaux: Iterable[Candidat]) -> list[Candidat]:
    """Ajoute à ``cands`` les ``nouveaux`` qui ne chevauchent aucun candidat déjà présent (ni l'un l'autre)."""
    out = list(cands)
    for n in nouveaux:
        if not any(n.start < c.end and c.start < n.end for c in out):
            out.append(n)
    return out
