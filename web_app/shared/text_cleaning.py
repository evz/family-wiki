# text_cleaning.py
"""
Dutch genealogy text cleaning utilities for Family Wiki Tools

Based on cleaning.py - quick‑and‑dirty helpers for Dutch genealogy RAG projects:

  • clean_text(raw)          -> normalised text, ready for chunking + embedding
  • canonicalise_surname(s)  -> (prefix, core, canonical, sort_key)

Dependencies
------------
stdlib           : unicodedata, re, itertools
pypi             : ftfy, rapidfuzz, wordfreq
"""
from __future__ import annotations

import re
import unicodedata as ud

from rapidfuzz.distance import Levenshtein
from wordfreq import top_n_list


# ---------------------------------------------------------------------------
# 1. OCR clean‑up
# ---------------------------------------------------------------------------

# Dutch‑specific tweaks
_IJ_FIX_RE   = re.compile(r'\b[yÿ]\b')            # y/ÿ misread for ij
_HYPHEN_RE   = re.compile(r'-\s*\n\s*')           # split‑word line breaks
_LONG_S_RE   = re.compile(r'ſ')                   # long‑s to normal s
_LIGATURES   = {
    'ﬂ': 'fl', 'ﬁ': 'fi', 'ﬃ': 'ffi', 'ﬄ': 'ffl',
    'ﬅ': 'st', 'ﬆ': 'st',
}

def _strip_diacritics(s: str) -> str:
    """NFKD normalise then drop combining marks."""
    nfkd = ud.normalize("NFKD", s)
    return "".join(c for c in nfkd if not ud.combining(c))

def _replace_ligatures(s: str) -> str:
    return "".join(_LIGATURES.get(c, c) for c in s)

def _ocr_spellfix(tokens: list[str]) -> list[str]:
    """
    Lightweight spelling fix:
      * uses wordfreq 40k Dutch word list
      * Levenshtein <=1
    Much faster than a transformer but works fine for common OCR slips.
    """
    vocab = set(top_n_list("nl", 40000))
    fixed = []
    for tok in tokens:
        if tok in vocab or not tok.isalpha():
            fixed.append(tok)
            continue
        # pick the best candidate within dist 1
        cands = [w for w in vocab if abs(len(w) - len(tok)) <= 1]
        scores = [(Levenshtein.distance(tok, w), w) for w in cands]
        best = min(scores, default=(5, tok))[1]
        fixed.append(best if best in vocab and len(best) else tok)
    return fixed

def clean_text(raw: str, *, spellfix: bool = True) -> str:
    """Pipe‑line all normalisations & light spell‑fix."""
    txt = _HYPHEN_RE.sub("", raw)               # de‑hyphenate line breaks
    txt = _LONG_S_RE.sub("s", txt)              # ſ → s
    txt = _replace_ligatures(txt)
    txt = _IJ_FIX_RE.sub("ij", txt)
    txt = _strip_diacritics(txt)                # drop accents
    txt = ud.normalize("NFC", txt)              # collapse to composed

    # optional token‑level edit distance pass
    if spellfix:
        toks = re.findall(r"\w+|\W+", txt)      # keep punctuation
        words, seps = toks[::2], toks[1::2]
        if len(words) == 0:                     # nothing to fix
            return txt
        fixed_words = _ocr_spellfix(words)
        txt = "".join(w + (seps[i] if i < len(seps) else "")
                      for i, w in enumerate(fixed_words))
    return txt


# ---------------------------------------------------------------------------
# 2. Surname canonicalisation
# ---------------------------------------------------------------------------

PREFIXES = {
    "van", "van de", "van der", "van den", "van het",
    "de", "den", "der", "het",
    "ter", "ten", "te", "'t", "op", "in", "aan", "uit", "over"
}

# Pre‑build concatenation patterns: e.g. r'^(van)([A-Z])' → split
_CONCAT_RES = [re.compile(rf"^({p.replace(' ', '')})([A-Z].+)") for p in PREFIXES]

def _split_prefix(name: str) -> tuple[str | None, str]:
    """
    Return (prefix, core).  prefix=None if none detected.
    Handles spaced and concatenated variants.
    """
    tokens = name.lower().split()
    # spaced prefix?
    if len(tokens) > 1:
        first, second = tokens[0], " ".join(tokens[:2])
        if second in PREFIXES:
            return second, " ".join(tokens[2:])
        if first in PREFIXES:
            return first, " ".join(tokens[1:])

    # concatenated 'VanDerBerg' → van der berg
    for rex in _CONCAT_RES:
        m = rex.match(name)
        if m:
            pref, core = m.group(1), m.group(2)
            # try to un‑squash 'vander' → 'van der' where possible
            spaced = " ".join(list(pref))
            best   = pref if pref in PREFIXES else spaced.rstrip()
            return best, core.lower()

    return None, name.lower()


def canonicalise_surname(raw: str) -> dict[str, str | None]:
    """
    Return dict with:
      prefix      – tussenvoegsel or None
      core        – surname without prefix
      canonical   – 'prefix core' lower‑case (prefix may be '')
      sort_key    – core (for alphabetical sort)
    Keeps ASCII‑-only, no accents → better match keys.
    """
    raw_no_acc   = _strip_diacritics(raw)
    prefix, core = _split_prefix(raw_no_acc)
    canonical    = f"{prefix} {core}".strip() if prefix else core
    return {
        "prefix": prefix,
        "core": core,
        "canonical": canonical,
        "sort_key": core,
    }


# ---------------------------------------------------------------------------
# 3. Additional corpus cleaning for RAG
# ---------------------------------------------------------------------------

def clean_corpus_text(raw: str, *, spellfix: bool = True, remove_headers: bool = True) -> str:
    """
    Enhanced text cleaning specifically for corpus preprocessing

    Args:
        raw: Raw text content
        spellfix: Whether to apply OCR spell correction
        remove_headers: Whether to remove common headers/footers

    Returns:
        Cleaned text ready for chunking and embedding
    """
    # First apply the standard cleaning
    cleaned = clean_text(raw, spellfix=spellfix)

    # Additional corpus-specific cleaning
    if remove_headers:
        # Remove page numbers and common headers
        cleaned = re.sub(r'\n\s*\d+\s*\n', '\n', cleaned)  # standalone page numbers
        cleaned = re.sub(r'\n\s*Pagina \d+.*?\n', '\n', cleaned, flags=re.IGNORECASE)  # "Pagina X"
        cleaned = re.sub(r'\n\s*Bladzijde \d+.*?\n', '\n', cleaned, flags=re.IGNORECASE)  # "Bladzijde X"

    # Clean up excessive whitespace
    cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)  # reduce multiple blank lines
    cleaned = re.sub(r' +', ' ', cleaned)  # reduce multiple spaces
    cleaned = cleaned.strip()

    return cleaned
