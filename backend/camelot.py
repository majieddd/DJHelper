"""Musical key <-> Camelot wheel mapping and harmonic-mixing compatibility.

The Camelot wheel is the standard DJ tool for harmonic mixing: tracks whose
Camelot codes are identical, one step apart on the wheel (+/-1 same letter), or
the relative major/minor (same number, switched letter) blend without clashing.
"""
from __future__ import annotations

from typing import Optional, Tuple

# Pitch classes: C=0, C#=1, D=2, ... B=11
PITCH_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Camelot code per pitch class for major (B side) and minor (A side).
_MAJOR_CAMELOT = {
    0: "8B", 1: "3B", 2: "10B", 3: "5B", 4: "12B", 5: "7B",
    6: "2B", 7: "9B", 8: "4B", 9: "11B", 10: "6B", 11: "1B",
}
_MINOR_CAMELOT = {
    0: "5A", 1: "12A", 2: "7A", 3: "2A", 4: "9A", 5: "4A",
    6: "11A", 7: "6A", 8: "1A", 9: "8A", 10: "3A", 11: "10A",
}


def to_camelot(pitch_class: int, is_major: bool) -> str:
    """pitch_class 0-11, is_major bool -> Camelot code like '8A'."""
    table = _MAJOR_CAMELOT if is_major else _MINOR_CAMELOT
    return table[pitch_class % 12]


def key_name(pitch_class: int, is_major: bool) -> str:
    return f"{PITCH_NAMES[pitch_class % 12]} {'maj' if is_major else 'min'}"


def parse_camelot(code: str) -> Optional[Tuple[int, str]]:
    """'8A' -> (8, 'A'). Returns None if unparseable."""
    if not code:
        return None
    code = code.strip().upper()
    letter = code[-1]
    if letter not in ("A", "B"):
        return None
    try:
        number = int(code[:-1])
    except ValueError:
        return None
    if not 1 <= number <= 12:
        return None
    return number, letter


def compatibility(code_a: str, code_b: str) -> float:
    """Harmonic compatibility score in [0, 1] between two Camelot codes.

    1.00 = same key (perfect blend / energy-neutral)
    0.90 = +/-1 on the wheel, same letter (classic smooth transition)
    0.85 = relative major/minor (same number, switched letter)
    0.55 = +/-2 ("energy boost" mix, slightly more adventurous)
    0.10 = otherwise (dissonant, avoid unless intentional)
    """
    a = parse_camelot(code_a)
    b = parse_camelot(code_b)
    if a is None or b is None:
        return 0.3  # unknown key -> neutral-ish so it isn't strongly penalised
    na, la = a
    nb, lb = b
    if na == nb and la == lb:
        return 1.0
    # circular distance on the 12-hour wheel
    diff = min((na - nb) % 12, (nb - na) % 12)
    if la == lb and diff == 1:
        return 0.90
    if la != lb and na == nb:
        return 0.85
    if la == lb and diff == 2:
        return 0.55
    return 0.10
