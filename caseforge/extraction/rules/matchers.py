"""Couche « matchers » : PERSONNE, ORG et SITE à partir de déclencheurs lexicaux et de la forme des noms propres.

Guide v2 : section 2, cas 1 (sigles), cas 2 (personne + fonction : on ne garde que le nom), cas 10 (proclitiques
arabes hors du span), section 6 (« Ksar Hellal site » -> « Ksar Hellal » ; noms en un seul span, titre compris).

- PERSONNE : civilité + nom (fr, en, ar), initiales (« K. Sassi », « K.B. »), prénom courant + nom, nom après un
  libellé de champ (« De : », « From: », « من: ») ou une formule de clôture (signature) ; l'apposition qui suit
  (« , responsable qualité ») n'est jamais incluse.
- ORG : forme juridique ou mot déclencheur avant ou après le nom (« Société X », « X SARL », « شركة X »), libellé de
  champ (« Raison sociale : »), sigle défini entre parenthèses après un nom d'ORG (« … (STCB) »), puis réutilisé
  dans le même document, ainsi que les noms d'ORG et de personnes déjà trouvés.
- SITE : délégations et villes de Tunisie (liste publique), zones industrielles (« ZI X », « المنطقة الصناعية
  ب… »), libellés de champ (« Ville : »). Le mot générique (« site », « usine », « مدينة ») reste hors du span.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cache

from spacy.tokens import Doc

from caseforge.extraction.rules.base import Candidat
from caseforge.extraction.rules.lexicons import (
    _DIACRITIQUES_AR,
    PROCLITIQUES,
    ensemble_normalise,
    est_arabe,
    motif_lexique,
    normaliser,
    par_attribut,
    sans_article,
    termes,
)

_MOT = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:['’&-][A-Za-zÀ-ÖØ-öø-ÿ0-9]+)*\.?|[ء-يـً-ْٰ]+|\S")
_ABREVIATIONS = {"Dr.", "Mr.", "Ms.", "Mrs.", "M.", "MM.", "Pr.", "Ing.", "Eng.", "Prof.", "St.", "Inc.", "Ltd.", "Co."}
_INITIALES = re.compile(r"(?<![\w.])[A-Z]\.[A-Z]\.(?![\w])")
_SIGLE = re.compile(r"\s*\(\s*([A-Z][A-Z0-9&]{1,9})\s*\)")
_LIENS_PERSONNE = {"Ben", "ben", "Bel", "El", "el", "Ould", "Abdel", "Ibn", "Ben-"}
_MAX_NOM = 4


@dataclass(frozen=True)
class Mot:
    """Mot d'un passage et ses offsets."""

    texte: str
    start: int
    end: int

    @property
    def latin_cap(self) -> bool:
        """Mot latin commençant par une majuscule (« Ennasr », « MécaPièces », « d'Ennasr »)."""
        t = self.texte
        if t[:2].lower() in {"d'", "l'"} and len(t) > 2:
            t = t[2:]
        return t[:1].isupper() and t[:1].isalpha() and not est_arabe(t)

    @property
    def initiale(self) -> bool:
        """Initiale suivie d'un point (« K. »)."""
        return bool(re.fullmatch(r"[A-Z]\.", self.texte))

    @property
    def arabe(self) -> bool:
        return est_arabe(self.texte)


@dataclass
class Memoire:
    """Noms trouvés dans un document, réutilisés dans ses autres passages (sigles, ORG, personnes)."""

    sigles: set[str] = field(default_factory=set)
    orgs: set[str] = field(default_factory=set)
    personnes: set[str] = field(default_factory=set)


def mots(text: str) -> list[Mot]:
    """Découpe en mots latins (point final gardé pour les abréviations et initiales), mots arabes et ponctuations."""
    out = []
    for m in _MOT.finditer(text):
        t, s, e = m.group(), m.start(), m.end()
        if t.endswith(".") and len(t) > 1 and t not in _ABREVIATIONS and not re.fullmatch(r"[A-Z]\.", t):
            out.append(Mot(t[:-1], s, e - 1))
            out.append(Mot(".", e - 1, e))
        else:
            out.append(Mot(t, s, e))
    return out


# ---------- Lexiques ----------
def _outils(attribut: str) -> set[str]:
    return set(termes("mots_outils", attribut))


def _norm_set(nom: str, attribut: str | None = None) -> frozenset[str]:
    return ensemble_normalise(nom, attribut)


def _arret_ar(m: Mot) -> bool:
    """Le mot arabe ``m`` termine un nom (mot-outil, fonction, verbe d'état)."""
    n = normaliser(m.texte)
    return n in _norm_set("mots_outils", "arret_ar") or sans_article(n) in {
        sans_article(f) for f in _norm_set("fonctions")
    }


def _fonction(m: Mot) -> bool:
    n = normaliser(m.texte).rstrip(".")
    return n in _norm_set("fonctions") or normaliser(m.texte) in _norm_set("fonctions")


def _verbes(doc: Doc | None) -> set[int]:
    """Offsets de début des verbes du ``Doc`` (pour arrêter un nom arabe avant un verbe)."""
    if doc is None:
        return set()
    return {t.idx for t in doc if t.pos_ in {"VERB", "AUX"}}


# ---------- Suites de noms propres ----------
def _suite_latine(ms: list[Mot], i: int, connecteurs: set[str], maxi: int = _MAX_NOM) -> int:
    """Indice (exclu) de la fin d'un nom propre latin qui commence en ``i`` ; ``i`` si aucun."""
    j, dernier = i, i
    while j < len(ms) and j - i < maxi + 2:
        m = ms[j]
        if m.latin_cap or m.initiale or (m.texte.isupper() and m.texte.isalpha() and len(m.texte) > 1):
            if _fonction(m) and j > i:
                break
            dernier = j + 1
        elif m.texte not in connecteurs:
            break
        j += 1
    return dernier


def _suite_arabe(ms: list[Mot], i: int, verbes: set[int], maxi: int, liens: bool = True) -> int:
    """Fin (exclue) d'une suite de mots arabes commencée en ``i`` (arrêt sur mot-outil, verbe, ponctuation)."""
    j = i
    liens_nom = _norm_set("mots_outils", "lien_nom_ar")
    n = 0
    while j < len(ms) and n < maxi:
        m = ms[j]
        if not m.arabe or _arret_ar(m) or m.start in verbes:
            break
        if liens and normaliser(m.texte) in liens_nom:
            maxi += 1
        j += 1
        n += 1
    return j


def _cand(ms: list[Mot], i: int, j: int, label: str, regle: str) -> Candidat | None:
    if j <= i:
        return None
    return Candidat(ms[i].start, ms[j - 1].end, label, regle)


def _champ(ms: list[Mot], libelles: set[str]) -> Iterable[int]:
    """Indices des mots qui suivent un libellé de champ et ses deux-points (« Interlocuteur : X »)."""
    norm = {normaliser(x) for x in libelles}
    for i in range(len(ms)):
        for k in (3, 2, 1):  # libellés de 1 à 3 mots
            if i + k >= len(ms):
                continue
            libelle = normaliser(" ".join(m.texte for m in ms[i : i + k]))
            if libelle in norm and ms[i + k].texte == ":":
                yield i + k + 1
                break


# ---------- PERSONNE ----------
def personnes(text: str, ms: list[Mot], verbes: set[int]) -> list[Candidat]:
    """Candidats PERSONNE d'un passage."""
    out: list[Candidat | None] = []
    civ = set(termes("civilites"))
    civ_ar = _norm_set("civilites")
    prenoms = set(termes("prenoms"))
    prenoms_ar = _norm_set("prenoms")
    salut = _outils("salutation")
    for i, m in enumerate(ms):
        suiv = i + 1
        if m.texte in civ and not m.arabe:
            j = _suite_latine(ms, suiv, _LIENS_PERSONNE)
            out.append(_cand(ms, i, j, "PERSONNE", "matchers.personne_civilite") if j > suiv else None)
        elif m.arabe and normaliser(m.texte) in civ_ar:
            j = _suite_arabe(ms, suiv, verbes, 2)
            out.append(_cand(ms, i, j, "PERSONNE", "matchers.personne_civilite") if j > suiv else None)
        elif m.initiale and suiv < len(ms) and ms[suiv].latin_cap and len(ms[suiv].texte) > 2:
            if i > 0 and ms[i - 1].texte in civ:
                continue
            j = _suite_latine(ms, suiv, _LIENS_PERSONNE, maxi=2)
            out.append(_cand(ms, i, j, "PERSONNE", "matchers.personne_initiale"))
        elif m.texte in prenoms:
            j = _suite_latine(ms, suiv, _LIENS_PERSONNE, maxi=3)
            if j > suiv:
                out.append(_cand(ms, i, j, "PERSONNE", "matchers.personne_prenom"))
            elif i > 0 and ms[i - 1].texte in salut:
                out.append(_cand(ms, i, suiv, "PERSONNE", "matchers.personne_salutation"))
        elif m.arabe and normaliser(m.texte) in prenoms_ar and not _arret_ar(m) and suiv < len(ms) and ms[suiv].arabe:
            n2 = re.sub(f"[{_DIACRITIQUES_AR}]", "", ms[suiv].texte)  # « آلة » ne commence pas par « ال »
            if (n2.startswith("ال") or normaliser(n2) in _norm_set("mots_outils", "lien_nom_ar")) and not _arret_ar(
                ms[suiv]
            ):
                j = _suite_arabe(ms, suiv, verbes, 1)
                out.append(_cand(ms, i, j, "PERSONNE", "matchers.personne_prenom"))
    for x in _INITIALES.finditer(text):
        if x.group() not in set(termes("formes_juridiques")) | set(termes("sites_declencheurs")) | {"N.B."}:
            out.append(Candidat(x.start(), x.end(), "PERSONNE", "matchers.personne_initiale"))
    for i in _champ(ms, _outils("champ_personne")):
        if i < len(ms) and ms[i].arabe:
            j = _suite_arabe(ms, i, verbes, 3)
            out.append(_cand(ms, i, j, "PERSONNE", "matchers.personne_champ") if j - i >= 2 else None)
        elif i < len(ms):
            j = _suite_latine(ms, i, _LIENS_PERSONNE)
            if j - i >= 2 or (j - i == 1 and ms[i].texte in prenoms):
                out.append(_cand(ms, i, j, "PERSONNE", "matchers.personne_champ"))
    clotures = "|".join(re.escape(c) for c in sorted(_outils("cloture"), key=len, reverse=True))
    for x in re.finditer(rf"(?:{clotures})\s*[,.!]?[ \t]*\n+[ \t]*", text):
        i = next((k for k, m in enumerate(ms) if m.start >= x.end()), len(ms))
        if i < len(ms) and ms[i].arabe:
            j = _suite_arabe(ms, i, verbes, 3)
        else:
            j = _suite_latine(ms, i, _LIENS_PERSONNE)
        if j - i >= 2:
            out.append(_cand(ms, i, j, "PERSONNE", "matchers.personne_signature"))
    return [c for c in out if c is not None]


# ---------- ORG ----------
def _gauche_org(ms: list[Mot], j: int, connecteurs: set[str]) -> int:
    """Début d'un nom d'ORG latin qui se termine juste avant ``j`` (suffixe « Industries », « SARL »…)."""
    debut = _outils("debut")
    i = j
    while i > 0 and j - i < _MAX_NOM + 1:
        m = ms[i - 1]
        if m.latin_cap or (m.texte.isupper() and m.texte.isalpha()):
            i -= 1
        elif m.texte in connecteurs and i - 1 > 0 and ms[i - 2].latin_cap:
            i -= 1
        else:
            break
    while i < j and (ms[i].texte in debut or ms[i].texte in connecteurs or _fonction(ms[i])):
        i += 1
    return i


def orgs(text: str, ms: list[Mot], verbes: set[int]) -> list[Candidat]:
    """Candidats ORG d'un passage (hors sigles et réutilisations, ajoutés par ``matcher_candidates``)."""
    out: list[Candidat | None] = []
    formes = par_attribut("formes_juridiques")
    avant_lat = {t for t in formes["avant"] if not est_arabe(t)}
    apres = formes["apres"]
    avant_ar = {normaliser(t) for t in formes["avant"] if est_arabe(t)}
    connecteurs = _outils("connecteur")
    sites = _norm_set("sites_tunisie") | _norm_set("sites_declencheurs")
    for i, m in enumerate(ms):
        if m.texte in avant_lat and m.latin_cap:
            j = _suite_latine(ms, i + 1, connecteurs, maxi=7)
            if j > i + 1:
                out.append(_cand(ms, i, j, "ORG", "matchers.org_forme"))
        if m.texte in apres and i > 0:
            g = _gauche_org(ms, i, connecteurs)
            if g < i:
                out.append(_cand(ms, g, i + 1, "ORG", "matchers.org_forme"))
        if m.arabe:
            n = normaliser(m.texte)
            debut = m.start
            if n not in avant_ar and n[:1] in PROCLITIQUES and n[1:] in avant_ar:
                n, debut = n[1:], m.start + 1
            if n not in avant_ar or i + 1 >= len(ms) or not ms[i + 1].arabe:
                continue
            suivant = normaliser(ms[i + 1].texte)
            if (n.startswith("ال") or n in {"مصنع", "مصانع"}) and not suivant.startswith("ال"):
                continue  # « الشركة » / « مصنع » + nom commun indéfini : générique (« تستغل الشركة محطة »)
            j = i + 1
            while j < len(ms) and j - i <= 5:
                w = ms[j]
                nw = normaliser(w.texte)
                if not w.arabe or _arret_ar(w) or w.start in verbes:
                    break
                if nw[:1] == "ب" and (
                    nw.startswith("بال")
                    or nw[1:] in sites
                    or sans_article(nw[1:]) in sites
                    or motif_lexique("sites_tunisie").match(text, w.start + 1)
                ):
                    break  # complément de lieu : « … بمدينة صفاقس », « … بمنزل بورقيبة »
                j += 1
            if j > i + 1:
                out.append(Candidat(debut, ms[j - 1].end, "ORG", "matchers.org_forme"))
    for i in _champ(ms, _outils("champ_org")):
        if i < len(ms) and ms[i].arabe:
            j = _suite_arabe(ms, i, verbes, 4)
        else:
            j = _suite_latine(ms, i, connecteurs, maxi=6)
        out.append(_cand(ms, i, j, "ORG", "matchers.org_champ"))
    return [c for c in out if c is not None]


def sigles_definis(text: str, cands: Iterable[Candidat]) -> list[Candidat]:
    """Sigle entre parenthèses juste après un nom d'ORG (« Groupe … (GACCA) ») ; jamais TRS, MTBF, AMDEC (cas 1)."""
    exclus = {normaliser(t) for t in (*termes("processus_tetes"), *termes("indicateur_grandeurs"))}
    out = []
    for c in cands:
        if c.label != "ORG":
            continue
        m = _SIGLE.match(text, c.end)
        if m and normaliser(m.group(1)) not in exclus:
            out.append(Candidat(m.start(1), m.end(1), "ORG", "matchers.org_sigle"))
    return out


_SIGLE_SEUL = re.compile(r"(?<![\w&-])[A-Z][A-Z&]{2,6}(?![\w&-])")


@cache
def _sigles_connus() -> frozenset[str]:
    """Sigles qui ne sont pas des noms d'entreprise : sigles techniques et termes des autres lexiques."""
    out = set(termes("sigles_techniques"))
    for lex in (
        "processus_tetes",
        "indicateur_grandeurs",
        "equipement_tetes",
        "formes_juridiques",
        "sites_declencheurs",
    ):
        out |= {t for t in termes(lex) if t.isupper()}
    out |= set(termes("donnees_sensibles"))
    return frozenset(x.upper() for x in out)


def _mot_courant(sigle: str) -> bool:
    """Vrai si le sigle est un mot courant écrit en majuscules (« MINUTES », « REPORT ») : vecteur fr ou en connu."""
    from caseforge.extraction.nlp import pipeline  # import paresseux : modèles déjà chargés par l'analyse

    return any(pipeline(lang).vocab.has_vector(sigle.lower()) for lang in ("fr", "en"))


def sigles_document(text: str) -> list[Candidat]:
    """Cas 1 : un sigle inconnu (ni technique, ni mot courant) dans un document qui nomme une ORG en est le sigle."""
    out = []
    for m in _SIGLE_SEUL.finditer(text):
        avant, apres = text[max(0, m.start() - 2) : m.start()], text[m.end() : m.end() + 2]
        if re.search(r"[A-Z]\s?$", avant) or re.match(r"\s?[A-Z]{2}", apres):
            continue  # titre en majuscules (« NON-CONFORMANCE REPORT »)
        if m.group() in _sigles_connus() or _mot_courant(m.group()):
            continue
        out.append(Candidat(m.start(), m.end(), "ORG", "matchers.org_sigle_document"))
    return out


def reutilisations(text: str, memoire: Memoire) -> list[Candidat]:
    """Occurrences des sigles, ORG et personnes déjà trouvés dans le document, et sigles inconnus (cas 1)."""
    out = sigles_document(text) if memoire.orgs or memoire.sigles else []
    for noms, label, regle in (
        (memoire.sigles, "ORG", "matchers.org_sigle_reutilise"),
        (memoire.orgs, "ORG", "matchers.org_nom_reutilise"),
        (memoire.personnes, "PERSONNE", "matchers.personne_reutilisee"),
    ):
        for nom in sorted(noms, key=len, reverse=True):
            for m in re.finditer(rf"(?<![\w-]){re.escape(nom)}(?![\w-])", text):
                out.append(Candidat(m.start(), m.end(), label, regle))
    return out


# ---------- SITE ----------
_ZONE_LAT = re.compile(
    r"(?<![\w])(?:ZI|Z\.I\.|[Zz]one [Ii]ndustrielle|[Ii]ndustrial [Zz]one|[Ii]ndustrial [Pp]ark|[Ff]ree [Zz]one|"
    r"[Tt]echnop[ôo]le|[Pp]arc d'activités)\s+(?:de\s+|d'|of\s+)?"
    r"(?P<nom>[A-ZÀ-Ý][\w'’-]*(?:\s+(?:El\s+|el\s+|Ben\s+)?[A-ZÀ-Ý][\w'’-]*){0,2})"
)
_ZONE_AR = re.compile(
    r"(?<![\w])(?:المنطقة الصناعية|ولاية|معتمدية)\s+(?:ب(?=[ء-ي]))?"
    r"(?P<nom>[ء-يـ]+(?:\s+[ء-يـ]+)?)"
)
_AVANT_SITE = re.compile(
    r"(?:(?<![\w])(?:ZI|Z\.I\.|[Zz]one [Ii]ndustrielle|[Ii]ndustrial [Zz]one|[Tt]echnop[ôo]le)"
    r"\s+(?:de\s+|d'|of\s+)?|(?:المنطقة الصناعية|منطقة|ولاية|معتمدية)\s+(?:ب)?)$"
)
_APRES_SITE = re.compile(r"\s+(?:Technopark|Technopôle|Technopole|[Ff]ree [Zz]one|[Ii]ndustrial [Zz]one)(?![\w])")


def sites(text: str, ms: list[Mot], verbes: set[int]) -> list[Candidat]:
    """Candidats SITE d'un passage."""
    out = []
    lat = motif_lexique("sites_tunisie", casse=True, ocr=True)
    ar = motif_lexique("sites_tunisie", proclitiques=True)
    vus = set()
    for motif in (lat, ar):
        for x in motif.finditer(text):
            s, e = x.start(), x.end()
            if (s, e) in vus or (motif is lat and est_arabe(x.group())):
                continue
            vus.add((s, e))
            avant = _AVANT_SITE.search(text[max(0, s - 30) : s])
            if avant:
                s = max(0, s - 30) + avant.start()
            apres = _APRES_SITE.match(text, e)
            if apres:
                e = apres.end()
            out.append(Candidat(s, e, "SITE", "matchers.site_lexique"))
    for motif in (_ZONE_LAT, _ZONE_AR):
        for x in motif.finditer(text):
            nom = x.group("nom").split()
            arret = next((k for k, w in enumerate(nom) if _arret_ar(Mot(w, 0, 0))), len(nom))
            fin = x.start("nom") + len(" ".join(nom[:arret])) if arret else x.start("nom")
            if fin > x.start("nom"):
                out.append(Candidat(x.start(), fin, "SITE", "matchers.site_zone"))
    for i in _champ(ms, _outils("champ_site")):
        if i < len(ms) and ms[i].arabe:
            j = _suite_arabe(ms, i, verbes, 3)
        else:
            j = _suite_latine(ms, i, _outils("connecteur"), maxi=4)
        c = _cand(ms, i, j, "SITE", "matchers.site_champ")
        if c is not None:
            apres = _APRES_SITE.match(text, c.end)
            out.append(c.bornes(c.start, apres.end()) if apres else c)
    return out


# ---------- Point d'entrée ----------
def matcher_candidates(text: str, doc: Doc | None = None, memoire: Memoire | None = None) -> list[Candidat]:
    """Candidats PERSONNE, ORG et SITE d'un passage ; ``memoire`` apporte les noms déjà vus dans le document."""
    ms = mots(text)
    verbes = _verbes(doc)
    out = personnes(text, ms, verbes) + orgs(text, ms, verbes) + sites(text, ms, verbes)
    out += sigles_definis(text, out)
    from caseforge.extraction.rules.rappel import rappel_candidates  # B6c ; import circulaire évité

    out += rappel_candidates(text, ms, verbes)
    if memoire is not None:
        out += reutilisations(text, memoire)
    return out


def enrichir_memoire(text: str, cands: Iterable[Candidat], memoire: Memoire) -> None:
    """Ajoute à ``memoire`` les sigles définis, les noms d'ORG et les noms de personnes (sans civilité) trouvés."""
    civ = set(termes("civilites"))
    generiques = _norm_set("generiques")
    for c in cands:
        surface = text[c.start : c.end]
        if normaliser(surface) in generiques:
            continue
        if c.rule_id == "matchers.org_sigle":
            memoire.sigles.add(surface)
        elif c.label == "ORG" and c.rule_id in {"matchers.org_forme", "matchers.org_champ"} and len(surface) > 3:
            memoire.orgs.add(surface)
        elif c.label == "PERSONNE":
            nom = surface.split(maxsplit=1)
            if len(nom) == 2 and (nom[0] in civ or normaliser(nom[0]) in _norm_set("civilites")):
                surface = nom[1]
            if len(surface.split()) >= 2 and not re.match(r"[A-Z]\.", surface):
                memoire.personnes.add(surface)
