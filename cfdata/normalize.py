"""Normaliseur FR / AR / EN pour les features, la recherche et les modèles classiques.

Les annotations (spans) restent sur le texte ORIGINAL : la normalisation sert à comparer des mots.
Règles (désactivables pour l'ablation) : unicode (NFKC, chiffres arabo-indiens), ponct (apostrophes,
guillemets, tirets), tatweel, diacr (harakat), alef (أ إ آ ٱ -> ا ; ى -> ي ; ة -> ه), casse, accents.
"""
from __future__ import annotations

import re
import unicodedata

DEFAUT = {"unicode": True, "ponct": True, "tatweel": True, "diacr": True, "alef": True, "casse": True, "accents": False}

_DIACR = re.compile(r"[\u064B-\u0652\u0670\u06D6-\u06ED]")
_PONCT = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "`": "'", "«": '"', "»": '"', "“": '"', "”": '"',
                        "–": "-", "—": "-", "‐": "-", "‑": "-", "\u00a0": " ", "\u202f": " "})
_ALEF = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"})
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize(text, regles=None):
    r = {**DEFAUT, **(regles or {})}
    if r["unicode"]:
        text = unicodedata.normalize("NFKC", text).translate(_ARABIC_DIGITS)
    if r["ponct"]:
        text = text.translate(_PONCT)
    if r["tatweel"]:
        text = text.replace("ـ", "")
    if r["diacr"]:
        text = _DIACR.sub("", text)
    if r["alef"]:
        text = text.translate(_ALEF)
    if r["casse"]:
        text = text.lower()
    if r["accents"]:
        text = "".join(c for c in unicodedata.normalize("NFD", text)
                       if unicodedata.category(c) != "Mn" or "\u0600" <= c <= "\u06FF")
    return re.sub(r"[ \t]+", " ", text)


def normalize_token(tok, regles=None):
    return normalize(tok, regles).strip() or tok


if __name__ == "__main__":
    for t in ["مجمع الاطلس للميكانيك الـدقيقة", "إدارة الجودة، مُسؤول الصيانة", "L’entreprise « STCB » — Sfax",
              "TRS de ٦٢ %", "Lc partcnaire impose"]:
        print(f"{t!r:45} -> {normalize(t)!r}")