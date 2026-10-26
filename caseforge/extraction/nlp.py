"""Pipeline linguistique multilingue du Lot B : spaCy (fr, en), stanza via spacy-stanza (ar), « mixte » par phrase.

- fr : ``fr_core_news_md`` ; en : ``en_core_web_md`` ;
- ar : modèle stanza ``ar`` (UD PADT) chargé par ``spacy_stanza`` ; si stanza ou son modèle est indisponible,
  repli explicite sur ``spacy.blank("ar")`` avec un avertissement (tokenisation seule, sans proclitiques séparés) ;
- mixte : le texte est découpé en phrases contiguës, la langue de chaque phrase est détectée avec
  ``cfdata.common.detect_lang`` et chaque phrase est analysée par le pipeline de sa langue.

Les pipelines sont chargés une seule fois (cache). ``parse`` vérifie que le texte du ``Doc`` et les offsets de
chaque token correspondent exactement au texte d'origine.
"""

from __future__ import annotations

import re
import warnings
from functools import cache
from typing import Any

import spacy
from spacy.language import Language
from spacy.tokens import Doc, Token

from cfdata.common import detect_lang

MODELES_SPACY: dict[str, str] = {"fr": "fr_core_news_md", "en": "en_core_web_md"}
PROCESSEURS_STANZA = "tokenize,mwt,pos,lemma,depparse"
LANGUES = ("fr", "en", "ar", "mixte")

# Phrases contiguës : jusqu'à une ponctuation finale suivie d'un blanc (« 4.5 » n'est pas coupé) ou un saut de
# ligne ; les blancs qui suivent restent dans la phrase, et les segments recouvrent exactement le texte.
_PHRASE = re.compile(r"[^\n]*?(?:[.!?؟]+(?:[ \t]+|\n+|$)|\n+|$)")
_ARABE = re.compile(r"[؀-ۿݐ-ݿ]")
_LATIN = re.compile(r"[A-Za-zÀ-ÿ]")

if not Token.has_extension("lang"):
    Token.set_extension("lang", default=None)


@cache
def pipeline(lang: str) -> Language:
    """Renvoie le pipeline spaCy d'une langue (``fr``, ``en`` ou ``ar``), chargé une seule fois."""
    if lang in MODELES_SPACY:
        return spacy.load(MODELES_SPACY[lang])
    if lang == "ar":
        try:
            import spacy_stanza

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)  # torch.load(weights_only=False) dans stanza 1.6
                return spacy_stanza.load_pipeline(
                    "ar", processors=PROCESSEURS_STANZA, verbose=False, download_method=None
                )
        except Exception as exc:  # stanza absent, modèle non téléchargé, incompatibilité torch…
            warnings.warn(
                f"stanza (ar) indisponible ({type(exc).__name__}: {exc}) : repli sur spacy.blank('ar')",
                RuntimeWarning,
                stacklevel=2,
            )
            return spacy.blank("ar")
    raise ValueError(f"langue sans pipeline : {lang!r} (attendu : fr, en, ar)")


def est_repli(lang: str) -> bool:
    """Indique si le pipeline de ``lang`` est le repli ``spacy.blank`` (aucun composant entraîné)."""
    nlp = pipeline(lang)
    return not nlp.pipe_names and type(nlp.tokenizer).__module__.startswith("spacy.")


def langue_segment(segment: str) -> str:
    """Langue d'une phrase pour le choix du pipeline : ``detect_lang`` ; si « mixte », l'écriture majoritaire."""
    lang = detect_lang(segment)
    if lang != "mixte":
        return lang
    return "ar" if len(_ARABE.findall(segment)) >= len(_LATIN.findall(segment)) else "fr"


def segments(text: str) -> list[str]:
    """Découpe un texte en phrases contiguës dont la concaténation redonne exactement le texte."""
    out = [m.group() for m in _PHRASE.finditer(text) if m.group()]
    assert "".join(out) == text
    return out


def verifier_offsets(doc: Doc, text: str) -> None:
    """Lève ``ValueError`` si le ``Doc`` ne reproduit pas le texte ou si un token est mal placé."""
    if doc.text != text:
        raise ValueError("le texte du Doc diffère du texte d'origine")
    for t in doc:
        if text[t.idx : t.idx + len(t.text)] != t.text:
            raise ValueError(f"offset faux pour le token {t.i} ({t.idx})")


def doc_depuis_stanza(nlp: Language, text: str) -> Doc:
    """Construit le ``Doc`` arabe à partir de la sortie stanza, avec des offsets fidèles au texte.

    ``spacy-stanza`` 1.0.4 écrit dans le ``Doc`` les mots d'un token composé même quand ils ne sont pas des
    sous-chaînes du texte (« للشركة » -> « ل » + « الشركة ») : le texte du ``Doc`` diffère alors de l'original.
    Ici, les mots d'un token composé deviennent des tokens séparés seulement s'ils recouvrent exactement le token
    (« بالمنطقة » -> « ب » + « المنطقة ») ; sinon le token reste entier et porte l'analyse de son mot principal
    (celui dont la tête est hors du token). Les blancs du texte sont reproduits tels quels.
    """
    sdoc = nlp.tokenizer.snlp(text)  # type: ignore[attr-defined]
    words: list[str] = []
    spaces: list[bool] = []
    a: dict[str, list[str]] = {"pos": [], "tags": [], "lemmas": [], "morphs": [], "deps": []}
    heads: list[int] = []
    sent_starts: list[bool] = []
    curseur = 0

    def ajouter(mot: str, pos: str, tag: str, lemme: str, morph: str, dep: str, head: int | None) -> None:
        words.append(mot)
        spaces.append(False)
        for k, v in zip(("pos", "tags", "lemmas", "morphs", "deps"), (pos, tag, lemme, morph, dep), strict=True):
            a[k].append(v)
        heads.append(len(words) - 1 if head is None else head)
        sent_starts.append(False)

    def blancs(jusqua: int) -> None:
        nonlocal curseur
        trou = text[curseur:jusqua]
        if trou.startswith(" ") and words and not spaces[-1]:
            spaces[-1] = True
            trou = trou[1:]
        if trou:  # autres blancs : token d'espacement, rattaché au token précédent
            ajouter(trou, "SPACE", "_SP", trou, "", "dep", len(words) - 1 if words else None)
        curseur = jusqua

    for sent in sdoc.sentences:
        groupes: list[tuple[int, str, list]] = []
        for tok in sent.tokens:
            ws = tok.words
            if len(ws) > 1 and "".join(w.text for w in ws) == tok.text:
                pos = tok.start_char
                for w in ws:
                    groupes.append((pos, w.text, [w]))
                    pos += len(w.text)
            else:
                groupes.append((tok.start_char, tok.text, list(ws)))
        # index des tokens spaCy de la phrase (en tenant compte des tokens d'espacement insérés avant chacun)
        debut_phrase = True
        mot_vers_tok: dict[int, int] = {}
        en_attente: list[tuple[int, Any]] = []
        for s, surface, ws in groupes:
            blancs(s)
            ids = {w.id for w in ws}
            rep = next((w for w in ws if w.head not in ids), ws[-1])
            for w in ws:
                mot_vers_tok[w.id] = len(words)
            en_attente.append((len(words), rep))
            ajouter(
                surface,
                rep.upos or "X",
                rep.xpos or "",
                rep.lemma or surface,
                rep.feats or "",
                rep.deprel or "dep",
                None,
            )
            if debut_phrase:
                sent_starts[-1] = True
                debut_phrase = False
            curseur = s + len(surface)
        for i, rep in en_attente:
            heads[i] = i if rep.head == 0 else mot_vers_tok.get(rep.head, i)
            if rep.head == 0:
                a["deps"][i] = "ROOT"
    blancs(len(text))
    try:
        doc = Doc(nlp.vocab, words=words, spaces=spaces, heads=heads, **a)
        _ = list(doc.sents)  # vérifie que l'arbre est exploitable
    except Exception:  # arbre incohérent après fusion : on garde l'analyse sans dépendances
        a.pop("deps")
        doc = Doc(nlp.vocab, words=words, spaces=spaces, sent_starts=sent_starts, **a)
    return doc


def _analyser(lang: str, text: str) -> Doc:
    """Analyse un texte d'une seule langue avec son pipeline."""
    nlp = pipeline(lang)
    if lang == "ar" and hasattr(nlp.tokenizer, "snlp"):
        return doc_depuis_stanza(nlp, text)
    return nlp(text)


def _parse_mixte(text: str) -> Doc:
    """Analyse chaque phrase avec le pipeline de sa langue et réunit les résultats dans un seul ``Doc``."""
    words: list[str] = []
    spaces: list[bool] = []
    attrs: dict[str, list[str]] = {"pos": [], "tags": [], "lemmas": [], "morphs": []}
    langs: list[str] = []
    sent_starts: list[bool] = []
    for seg in segments(text):
        lang = langue_segment(seg)
        sub = _analyser(lang, seg)
        verifier_offsets(sub, seg)
        for i, t in enumerate(sub):
            words.append(t.text)
            spaces.append(bool(t.whitespace_))
            attrs["pos"].append(t.pos_ or "X")
            attrs["tags"].append(t.tag_)
            attrs["lemmas"].append(t.lemma_ or t.text)
            attrs["morphs"].append(str(t.morph))
            langs.append(lang)
            sent_starts.append(i == 0)
    doc = Doc(spacy.blank("xx").vocab, words=words, spaces=spaces, sent_starts=sent_starts, **attrs)
    for t, lang in zip(doc, langs, strict=True):
        t._.lang = lang
    return doc


def parse(text: str, lang: str) -> Doc:
    """Analyse un texte avec le pipeline de sa langue (``fr``, ``en``, ``ar`` ou ``mixte``).

    Les offsets caractère des tokens (``token.idx``) correspondent au texte d'origine ; ``token._.lang`` donne la
    langue du pipeline utilisé (utile pour les passages mixtes).
    """
    if lang not in LANGUES:
        raise ValueError(f"langue inconnue : {lang!r} (attendu : {', '.join(LANGUES)})")
    if lang == "mixte":
        doc = _parse_mixte(text)
    else:
        doc = _analyser(lang, text)
        for t in doc:
            t._.lang = lang
    verifier_offsets(doc, text)
    return doc


def offsets(doc: Doc) -> list[tuple[int, int]]:
    """Offsets ``(début, fin)`` des tokens non blancs d'un ``Doc``."""
    return [(t.idx, t.idx + len(t.text)) for t in doc if not t.is_space]


# ---------- Proclitiques arabes (guide v2, cas 10) ----------
PROCLITIQUES = "وفبلك"
# Noms génériques qui ouvrent une ORG ou un SITE (exemples du guide v2 et termes usuels) : « لشركة » -> « شركة ».
TETES_GENERIQUES = frozenset({"شركة", "مؤسسة", "مجمع", "مصنع", "مدينة", "ولاية", "منطقة"})
_MOT = re.compile(r"[^\s،؛.,:;()«»\"']+")


def _detachable(mot: str) -> bool:
    """Vrai si ``mot`` commence par un proclitique qu'on peut retirer sans casser le mot."""
    # « للشركة » = ل + الشركة contracté (alef élidé) : aucun décalage ne redonne « الشركة », on n'y touche pas
    if len(mot) < 3 or mot[0] not in PROCLITIQUES or mot.startswith("لل"):
        return False
    reste = mot[1:]
    # « بالمنطقة » -> « المنطقة » ; on exige au moins 3 lettres après « ال » (« والي » reste entier)
    if reste.startswith("ال") and len(reste) >= 5:
        return True
    # « وبالمنطقة » : و est détachable si le reste l'est lui-même
    return reste in TETES_GENERIQUES or _detachable(reste)


def strip_arabic_proclitics(text: str, start: int, end: int) -> tuple[int, int]:
    """Retire les proclitiques و ف ب ل ك collés en tête du span (au plus deux : « وبالمنطقة »), « ال » conservé.

    Guide v2, cas 10 : « لشركة النسيج » -> « شركة النسيج », « بالمنطقة الصناعية » -> « المنطقة الصناعية ».
    Un proclitique n'est retiré que si le reste du mot commence par « ال » ou est un nom générique
    (``TETES_GENERIQUES``) : « ولاية », « وحدة » ou « بنزرت » commencent par و / ب sans proclitique et restent
    entiers. La règle du mot générique de SITE (« بمدينة صفاقس » -> « صفاقس ») est une autre règle, non appliquée ici.
    """
    s = start
    for _ in range(2):
        m = _MOT.match(text, s, end)
        if not m or not _detachable(m.group()):
            break
        s += 1
    return s, end
