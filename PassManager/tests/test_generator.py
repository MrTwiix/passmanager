"""
test_generator.py — Tests unitaires du générateur de mots de passe.

Couvre :
  - Longueur exacte du mot de passe généré
  - Présence obligatoire des types de caractères activés
  - Absence des types de caractères désactivés
  - Calcul d'entropie (> 0 pour tout mot de passe non vide)
  - Évaluation de la force (score 0-4)
"""

import string

import pytest

from app.generator import (
    DIGITS,
    LOWERCASE,
    SYMBOLS,
    UPPERCASE,
    generate_password,
    password_entropy,
    password_strength,
)


# ─── Tests generate_password ──────────────────────────────────────────────────

def test_length_exact():
    """Le mot de passe généré a exactement la longueur demandée."""
    pwd = generate_password(length=20)
    assert len(pwd) == 20


def test_length_min_clamp():
    """Une longueur trop courte est clampée au minimum."""
    pwd = generate_password(length=1)
    assert len(pwd) >= 8


def test_length_max_clamp():
    """Une longueur trop grande est clampée au maximum."""
    pwd = generate_password(length=999)
    assert len(pwd) <= 40


def test_contains_symbols_when_enabled():
    """Avec symbols=True → au moins un symbole présent."""
    # Test sur 20 générations pour réduire la variance
    for _ in range(20):
        pwd = generate_password(length=20, use_symbols=True)
        if any(c in SYMBOLS for c in pwd):
            return
    pytest.fail("Aucun symbole trouvé en 20 générations")


def test_no_digits_when_disabled():
    """Avec digits=False → aucun chiffre dans le résultat."""
    for _ in range(10):
        pwd = generate_password(length=20, use_digits=False)
        assert not any(c in DIGITS for c in pwd), f"Chiffre trouvé dans : {pwd}"


def test_no_upper_when_disabled():
    """Avec upper=False → aucune majuscule dans le résultat."""
    for _ in range(10):
        pwd = generate_password(length=20, use_upper=False)
        assert not any(c in UPPERCASE for c in pwd), f"Majuscule trouvée dans : {pwd}"


def test_contains_lowercase_always():
    """Les minuscules sont toujours présentes (alphabet de base)."""
    for _ in range(10):
        pwd = generate_password(length=16, use_upper=False, use_digits=False, use_symbols=False)
        assert any(c in LOWERCASE for c in pwd)


def test_all_chars_in_alphabet():
    """Tous les caractères générés appartiennent à l'alphabet attendu."""
    alphabet = LOWERCASE + UPPERCASE + DIGITS + SYMBOLS
    pwd = generate_password(length=30, use_upper=True, use_digits=True, use_symbols=True)
    for c in pwd:
        assert c in alphabet, f"Caractère inattendu : {c!r}"


# ─── Tests password_entropy ───────────────────────────────────────────────────

def test_entropy_empty():
    """Entropie d'une chaîne vide = 0."""
    assert password_entropy("") == 0.0


def test_entropy_positive():
    """Entropie d'un mot de passe non vide > 0."""
    assert password_entropy("hello") > 0
    assert password_entropy("Tr0ub4dor&3") > 0


def test_entropy_increases_with_length():
    """Un mot de passe plus long avec variété a une entropie plus élevée."""
    short  = "aaa"
    longer = "aAbBcC123!!!"
    assert password_entropy(longer) > password_entropy(short)


# ─── Tests password_strength ──────────────────────────────────────────────────

def test_strength_empty():
    """Mot de passe vide → score 0."""
    score, label, color = password_strength("")
    assert score == 0


def test_strength_weak():
    """Mot de passe trivial → score faible."""
    score, _, _ = password_strength("abc")
    assert score <= 1


def test_strength_strong():
    """Mot de passe complexe → score élevé."""
    score, _, _ = password_strength("Tr0ub4dor&3!!XYZ")
    assert score >= 3


def test_strength_returns_tuple():
    """password_strength retourne un tuple (int, str, str)."""
    result = password_strength("TestPassword1!")
    assert isinstance(result, tuple)
    assert len(result) == 3
    score, label, color = result
    assert isinstance(score, int)
    assert isinstance(label, str)
    assert color.startswith("#")


def test_strength_score_range():
    """Le score est toujours entre 0 et 4."""
    test_passwords = ["", "a", "password", "Password1", "P@ssw0rd!!", "Tr0ub4dor&3!!XYZ99"]
    for pwd in test_passwords:
        score, _, _ = password_strength(pwd)
        assert 0 <= score <= 4, f"Score hors limites ({score}) pour : {pwd!r}"
