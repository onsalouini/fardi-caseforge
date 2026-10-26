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
