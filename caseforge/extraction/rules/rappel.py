"""Règles de rappel (B6c) : familles de noms qui fuyaient jusqu'à la fiche (analyse de propagation du Lot D).

Règles générales, jamais de nom précis dans un lexique. Elles visent le rappel ; chacune a son ``rule_id`` et peut
être désactivée (``configs/rules.yaml`` pour le NER, ``configs/anonymization.yaml`` pour l'anonymisation).

- ``rappel.org_sigle`` : mot de 2 à 6 majuscules (chiffres ou « & » admis, au moins 2 lettres) absent de la liste
  d'exclusion des sigles techniques et normatifs (``sigles_techniques.txt`` et autres lexiques), qui n'est ni un mot
  courant en majuscules, ni un chiffre romain, ni un mot d'un titre en majuscules. Sans définition entre
  parenthèses ni ORG ailleurs dans le document (ce qu'exige ``matchers.org_sigle_document``).
- ``rappel.org_camelcase`` : ORG sans forme juridique, sous trois formes. (a) Un nom en CamelCase qui contient
  un élément de secteur (« -Plast », « -Tex »). (b) Une suite de mots capitalisés suivie d'un mot de secteur
  (« Compo », « Pharma », « Group »). (c) Un nom suivi d'un pays (inclus dans le span) ou d'une ville (laissée
  hors du span). Pour (c), le nom doit être en CamelCase ou contenir un mot qui n'est pas un mot courant.
  Lexique : ``secteurs_org.txt``.
- ``rappel.personne_prenom_ar`` : prénom arabe de ``prenoms_ar.txt`` suivi de 1 ou 2 mots arabes (arrêt sur
  mot-outil, verbe, fonction ou ponctuation), ou sa translittération latine suivie de 1 ou 2 mots capitalisés.
  Un prénom « ambigu » (aussi nom commun) n'est retenu qu'avec un indice : position de signature (« من: »,
  « إلى: », « الإمضاء », « في الختام »…), apposition de fonction (« ، مسؤول … », « مدير … » avant ou après), ou
  nom de famille en « ال ».
"""

from __future__ import annotations

import re
from functools import cache

from caseforge.extraction.rules.base import Candidat
from caseforge.extraction.rules.lexicons import charger, ensemble_normalise, normaliser, par_attribut, termes
from caseforge.extraction.rules.matchers import (
    _LIENS_PERSONNE,
    Mot,
    _arret_ar,
    _fonction,
    _mot_courant,
    _sigles_connus,
    _suite_arabe,
    _suite_latine,
)

REGLES_RAPPEL: tuple[str, ...] = ("rappel.org_sigle", "rappel.org_camelcase", "rappel.personne_prenom_ar")

_SIGLE = re.compile(r"(?<![\w&-])[A-Z][A-Z0-9&]{1,5}(?![\w&-])")
_ROMAIN = re.compile(r"M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})")
_CAMEL = re.compile(r"[A-ZÀ-Ý][a-zà-ÿ]+(?:[A-ZÀ-Ý][a-zà-ÿ]+)+")
_SEGMENTS = re.compile(r"[A-ZÀ-Ý][a-zà-ÿ]*")
_SIGNATURE_AR = ("من :", "من:", "إلى :", "إلى:", "الى:", "الإمضاء", "الامضاء", "في الختام", "مع تحياتي", "التوقيع")
_FENETRE_SIGNATURE = 25


# ---------- Lexiques ----------
@cache
def prenoms_ar() -> dict[str, tuple[str, tuple[str, ...]]]:
    """Prénom arabe normalisé -> (type ``courant`` / ``ambigu``, translittérations latines)."""
    out = {}
    for terme, attribut in charger("prenoms_ar"):
        typ, _, lat = attribut.partition("\t")
        out[normaliser(terme)] = (typ.strip(), tuple(x.strip() for x in lat.split("|") if x.strip()))
    return out


@cache
def _prenoms_latins() -> dict[str, str]:
    """Translittération latine (premier mot) -> type du prénom."""
    out: dict[str, str] = {}
    for typ, lats in prenoms_ar().values():
        for lat in lats:
            out.setdefault(lat.split()[0], typ)
    return out


@cache
def _secteurs() -> dict[str, frozenset[str]]:
    return {k: frozenset(v) for k, v in par_attribut("secteurs_org").items()}


@cache
def _villes() -> frozenset[str]:
    return frozenset(t for t in termes("sites_tunisie") if t[:1].isupper())


@cache
def _mots_non_noms() -> frozenset[str]:
    """Mots capitalisés qui ne font pas partie d'un nom d'entreprise (génériques, fonctions, déclencheurs de site)."""
    out = set()
    for lex in ("generiques", "fonctions", "sites_declencheurs", "civilites"):
        out |= {normaliser(m) for t in termes(lex) for m in t.split()}
    out |= {normaliser(t) for t in termes("mots_outils")}
    return frozenset(out)


# ---------- ORG : sigles non définis ----------
def org_sigles(text: str) -> list[Candidat]:
    """Sigles inconnus en majuscules, candidats ORG (rappel de l'anonymisation)."""
    out = []
    for m in _SIGLE.finditer(text):
        w = m.group()
        if sum(c.isalpha() for c in w) < 2 or _ROMAIN.fullmatch(w):
            continue
        avant, apres = text[max(0, m.start() - 2) : m.start()], text[m.end() : m.end() + 3]
        if re.search(r"[A-Z]\s?$", avant) or re.match(r"\s?[A-Z]{2}", apres):
            continue  # mot d'un titre en majuscules
        if w in _sigles_connus() or w.replace("&", "") in _sigles_connus() or _mot_courant(w):
            continue
        out.append(Candidat(m.start(), m.end(), "ORG", "rappel.org_sigle"))
    return out


# ---------- ORG : CamelCase, secteur, pays ----------
def _camel_secteur(mot: str) -> bool:
    """Nom en CamelCase dont un segment est un élément de secteur (« TuniPlast »)."""
    if not _CAMEL.fullmatch(mot):
        return False
    morphemes = {normaliser(x) for x in _secteurs().get("morpheme", ())}
    return any(normaliser(s) in morphemes for s in _SEGMENTS.findall(mot))


def _nom_gauche(ms: list[Mot], j: int, maxi: int = 3) -> int:
    """Début de la suite de mots capitalisés (hors génériques, fonctions, villes) qui finit juste avant ``j``."""
    i = j
    while i > 0 and j - i < maxi:
        m = ms[i - 1]
        if not m.latin_cap or normaliser(m.texte) in _mots_non_noms() or m.texte in _villes():
            break
        i -= 1
    return i


def org_camelcase(ms: list[Mot]) -> list[Candidat]:
    """ORG sans forme juridique : CamelCase de secteur, nom + mot de secteur, nom + pays ou ville."""
    sect = _secteurs()
    suffixes, pays = sect.get("suffixe", frozenset()), sect.get("pays", frozenset())
    out = []
    for j, m in enumerate(ms):
        if _camel_secteur(m.texte) and not (j > 0 and ms[j - 1].latin_cap):
            fin = j + 1
            if fin < len(ms) and ms[fin].texte in pays | suffixes:
                fin += 1
            out.append(Candidat(m.start, ms[fin - 1].end, "ORG", "rappel.org_camelcase"))
            continue
        if not m.latin_cap or j == 0:
            continue
        inclus = m.texte in suffixes or m.texte in pays
        if not inclus and m.texte not in _villes():
            continue
        i = _nom_gauche(ms, j)
        if i == j:
            continue
        nom = ms[i:j]
        if i == 0 or ms[i - 1].texte in {".", ":", "\n"}:
            nom_debut_phrase = True
        else:
            nom_debut_phrase = False
        if m.texte not in suffixes:  # pays ou ville : il faut un vrai nom (CamelCase ou mot non courant)
            if not any(_CAMEL.fullmatch(x.texte) or not _mot_courant(x.texte) for x in nom):
                continue
            if nom_debut_phrase and len(nom) == 1 and not _CAMEL.fullmatch(nom[0].texte):
                continue
        fin = ms[j].end if inclus else ms[j - 1].end
        out.append(Candidat(nom[0].start, fin, "ORG", "rappel.org_camelcase"))
    return out


# ---------- PERSONNE : prénom arabe sans civilité ----------
def _indice_signature(text: str, debut: int) -> bool:
    """Le mot qui commence en ``debut`` suit de près un libellé de signature ou d'adresse."""
    avant = text[max(0, debut - _FENETRE_SIGNATURE) : debut]
    return any(s in avant for s in _SIGNATURE_AR)


def _indice_fonction(ms: list[Mot], i: int, j: int) -> bool:
    """Apposition de fonction juste avant le prénom ou juste après le nom (« مدير الإنتاج X », « X، مسؤولة … »)."""
    if i > 0 and _fonction(ms[i - 1]):
        return True
    k = j
    while k < len(ms) and ms[k].texte in {"،", ",", "-", "–"}:
        k += 1
    return k < len(ms) and _fonction(ms[k])


def personnes_prenom_ar(text: str, ms: list[Mot], verbes: set[int]) -> list[Candidat]:
    """PERSONNE : prénom arabe (ou translittéré) + 1 ou 2 mots, indice exigé pour un prénom ambigu."""
    pr = prenoms_ar()
    composes = {k: v for k, v in pr.items() if " " in k}
    lat = _prenoms_latins()
    generiques = ensemble_normalise("generiques")
    out = []
    for i, m in enumerate(ms):
        typ = None
        n_prenom = 1
        if m.arabe:
            n = normaliser(m.texte)
            if i + 1 < len(ms) and f"{n} {normaliser(ms[i + 1].texte)}" in composes:
                typ, n_prenom = composes[f"{n} {normaliser(ms[i + 1].texte)}"][0], 2
            elif n in pr and not _arret_ar(m):
                typ = pr[n][0]
            if typ is None:
                continue
            k = i + n_prenom
            if k >= len(ms) or not ms[k].arabe or _arret_ar(ms[k]) or ms[k].start in verbes or _fonction(ms[k]):
                continue
            if normaliser(ms[k].texte) in generiques:
                continue
            j = _suite_arabe(ms, k, verbes, 1)
            if j < len(ms) and ms[j].arabe and normaliser(ms[j].texte).startswith("ال") and not _arret_ar(ms[j]):
                if ms[j].start not in verbes and not _fonction(ms[j]):
                    j += 1  # second mot du nom (nisba : « … التونسي »)
            famille_al = any(normaliser(x.texte).startswith("ال") for x in ms[k:j])
        elif m.texte in lat and not m.arabe:
            typ = lat[m.texte]
            j = _suite_latine(ms, i + 1, _LIENS_PERSONNE, maxi=2)
            if j == i + 1 or any(_fonction(x) for x in ms[i + 1 : j]):
                continue
            famille_al = False
        else:
            continue
        indice = famille_al or _indice_signature(text, m.start) or _indice_fonction(ms, i, j)
        if typ == "ambigu" and not indice:
            continue
        out.append(Candidat(m.start, ms[j - 1].end, "PERSONNE", "rappel.personne_prenom_ar"))
    return out


def rappel_candidates(text: str, ms: list[Mot], verbes: set[int]) -> list[Candidat]:
    """Candidats des trois règles de rappel (filtrés ensuite par ``regles_desactivees``)."""
    return org_sigles(text) + org_camelcase(ms) + personnes_prenom_ar(text, ms, verbes)
