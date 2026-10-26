"""Conversion entre tags BIO (tokens de ``cfdata.common.tokenize``) et spans au caractère près."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from cfdata.common import tokenize


def bio_vers_spans_tokens(tags: Sequence[str]) -> list[tuple[int, int, str]]:
    """Décode des tags BIO en spans de tokens ``(début, fin exclue, étiquette)``.

    Même convention que ``exemples/baseline_crf.py`` : un ``I-X`` qui suit ``O`` ou une autre étiquette ouvre
    une nouvelle entité.
    """
    out: list[tuple[int, int, str]] = []
    cur: tuple[int, str] | None = None
    for i, t in enumerate([*tags, "O"]):
        continue_cur = cur is not None and t.startswith("I-") and t[2:] == cur[1]
        if not continue_cur:
            if cur is not None:
                out.append((cur[0], i, cur[1]))
            cur = (i, t[2:]) if t != "O" else None
    return out


def spans_tokens_vers_caracteres(text: str, tokens: Sequence[str], spans: Iterable[tuple[int, int, str]]) -> list[dict]:
    """Convertit des spans de tokens en spans de caractères ``{start, end, label}``.

    Les tokens doivent être ceux de ``cfdata.common.tokenize(text)`` (c'est le cas des fichiers ``*.bio.jsonl``) ;
    sinon ``ValueError``.
    """
    offs = tokenize(text)
    if [t for t, _, _ in offs] != list(tokens):
        raise ValueError("les tokens ne correspondent pas à cfdata.common.tokenize(text)")
    return [{"start": offs[i][1], "end": offs[j - 1][2], "label": lab} for i, j, lab in spans]


def aligner_sur_tokens(entities: Iterable[dict], offsets: Sequence[tuple[int, int]]) -> list[dict]:
    """Aligne des spans de caractères sur des tokens, comme le ferait un aller-retour par BIO.

    Même règle que ``cfdata.common.spans_to_bio`` : un token reçoit l'étiquette d'une entité dès qu'il la
    chevauche, les entités étant traitées par position croissante (la dernière l'emporte sur un token partagé).
    Les tags obtenus sont ensuite décodés en spans de tokens puis en spans de caractères.
    """
    tags = ["O"] * len(offsets)
    for e in sorted(entities, key=lambda e: e["start"]):
        premier = True
        for i, (s, t) in enumerate(offsets):
            if s < e["end"] and t > e["start"]:
                tags[i] = ("B-" if premier else "I-") + e["label"]
                premier = False
    return [
        {"start": offsets[i][0], "end": offsets[j - 1][1], "label": lab} for i, j, lab in bio_vers_spans_tokens(tags)
    ]
