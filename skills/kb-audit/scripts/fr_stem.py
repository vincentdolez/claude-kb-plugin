"""
Lightweight French stemmer — suffix-stripping approach.
Stdlib only, Python 3.9+. ~80% accuracy, optimised for vocabulary grouping.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

# Accent normalisation map for internal comparison
_ACCENT_MAP = str.maketrans(
    {"à": "a", "â": "a", "ä": "a", "é": "e", "è": "e", "ê": "e", "ë": "e",
     "ï": "i", "î": "i", "ô": "o", "ù": "u", "û": "u", "ü": "u",
     "ÿ": "y", "ç": "c", "œ": "oe", "æ": "ae"},
)


def _normalize(word: str) -> str:
    """Lowercase + strip non-alpha, keep accents intact."""
    return re.sub(r"[^a-zàâäéèêëïîôùûüÿçœæ]", "", word.lower())


# Ordered from longest to shortest so greedy match works.
# Each entry: (suffix, min_stem_len)
_SUFFIXES: list[tuple[str, int]] = [
    # 9+
    ("isations", 3),
    ("issement", 3),
    # 8
    ("isation", 3),
    # 7
    ("isions", 3),
    ("utions", 3),
    ("ations", 3),
    ("ements", 3),
    # 6
    ("ières", 3),
    ("antes", 3),
    ("ables", 3),
    ("ibles", 3),
    ("elles", 3),
    ("euses", 3),
    ("istes", 3),
    ("iques", 3),
    ("ments", 3),
    ("aises", 3),
    ("oises", 3),
    ("sions", 3),
    ("tions", 3),
    # 5
    ("ation", 3),
    ("ition", 3),
    ("ution", 3),
    ("ision", 3),
    ("ement", 3),
    ("ière", 3),
    ("aise", 3),
    ("oise", 3),
    ("ales", 3),
    ("ante", 3),
    ("ives", 3),
    ("eurs", 3),
    ("ités", 3),
    ("ants", 3),
    # 4
    ("tion", 3),
    ("sion", 3),
    ("ment", 3),
    ("ique", 3),
    ("iste", 3),
    ("euse", 3),
    ("able", 3),
    ("ible", 3),
    ("elle", 3),
    ("ance", 3),
    ("ence", 3),
    # 3
    ("ant", 3),
    ("eur", 3),
    ("ité", 3),
    ("ifs", 3),
    ("ive", 3),
    ("eux", 3),
    ("aux", 3),
    ("els", 3),
    ("ais", 3),
    ("ois", 3),
    ("ées", 3),
    ("ère", 3),
    ("ier", 3),
    ("ale", 3),
    # 2
    ("if", 3),
    ("el", 3),
    ("al", 3),
    ("er", 3),
    ("és", 3),
    ("ée", 3),
    ("é", 2),
]

# Final pass: strip plural markers
_PLURAL_SUFFIXES: list[tuple[str, int]] = [
    ("eaux", 3),  # gâteaux -> gât (handled before -x)
    ("aux", 3),   # already in main list but acts as plural of -al
    ("s", 2),
    ("x", 2),
]


def stem(word: str) -> str:
    """Return the stemmed form of a French word."""
    w = _normalize(word)
    if len(w) <= 3:
        return w

    # Step 1: strip longest matching suffix
    stripped = False
    for suffix, min_len in _SUFFIXES:
        if w.endswith(suffix) and len(w) - len(suffix) >= min_len:
            w = w[: -len(suffix)]
            stripped = True
            break

    # Step 2: strip residual plural marker only if no suffix was stripped
    if not stripped:
        for suffix, min_len in _PLURAL_SUFFIXES:
            if w.endswith(suffix) and len(w) - len(suffix) >= min_len:
                w = w[: -len(suffix)]
                break

    return w


def stem_set(words: set[str]) -> dict[str, list[str]]:
    """Group words by their stem. Returns {stem: [original_words]}."""
    groups: dict[str, list[str]] = defaultdict(list)
    for w in words:
        groups[stem(w)].append(w)
    # Sort variants for stable output
    return {k: sorted(v) for k, v in sorted(groups.items())}


# ── Quick self-test ─────────────────────────────────────────────
if __name__ == "__main__":
    tests: list[tuple[str, str]] = [
        # (input, expected_stem) — what matters is that variants share a stem
        ("automatisation", "automat"),
        ("automatisations", "automat"),
        ("stratégique", "stratég"),
        ("stratégiques", "stratég"),
        ("accélération", "accélér"),
        ("opérationnel", "opérationn"),
        ("opérationnelle", "opérationn"),
        ("opérationnels", "opérationn"),
        ("opérationnelles", "opérationn"),
        ("utilisateur", "utilisat"),
        ("utilisateurs", "utilisat"),
        ("utilisable", "utilis"),
        ("utilisables", "utilis"),
        ("modernisation", "modern"),
        ("décision", "déc"),
        ("décisions", "déc"),
        ("spécialiste", "spécial"),
        ("spécialistes", "spécial"),
        ("créativité", "créativ"),
        ("créativités", "créativ"),
        ("actif", "act"),
        ("active", "act"),
        ("actifs", "act"),
        ("actives", "act"),
        ("structurel", "structur"),
        ("structurelle", "structur"),
        ("structurels", "structur"),
        ("structurelles", "structur"),
        ("français", "franç"),
        ("française", "franç"),
        ("vannetais", "vannet"),
        ("important", "import"),
        ("importante", "import"),
        ("importants", "import"),
        ("importantes", "import"),
        ("accéléré", "accélér"),
        ("accélérée", "accélér"),
        ("accélérés", "accélér"),
        ("accélérées", "accélér"),
        ("premier", "prem"),
        ("première", "prem"),
        ("premières", "prem"),
        ("financier", "financ"),
        ("financière", "financ"),
        ("dangereux", "danger"),
        ("dangereuse", "danger"),
        ("dangereuses", "danger"),
        ("national", "nation"),
        ("nationale", "nation"),
        ("nationaux", "nation"),
        ("nationales", "nation"),
    ]

    passed = 0
    failed = 0
    for word, expected in tests:
        result = stem(word)
        ok = result == expected
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL  stem({word!r}) = {result!r}, expected {expected!r}")

    print(f"\n{passed}/{passed + failed} tests passed.")

    # Demo stem_set
    demo_words = {
        "automatisation", "automatisations", "stratégique", "stratégiques",
        "actif", "active", "actifs", "actives",
        "structurel", "structurelle", "structurels", "structurelles",
    }
    print("\nstem_set demo:")
    for s, variants in stem_set(demo_words).items():
        print(f"  {s}: {variants}")
