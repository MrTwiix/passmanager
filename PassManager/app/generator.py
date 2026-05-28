"""
generator.py — Génération sécurisée et analyse de mots de passe.

Module AUTONOME : zéro dépendance vers le reste de l'application.
Testable indépendamment de la GUI et du vault.

Utilise le module `secrets` (Python stdlib) qui s'appuie sur os.urandom()
→ cryptographiquement sûr, adapté à la génération de mots de passe.
"""

import math
import secrets
import string
from app.config import (
    DEFAULT_PASSWORD_LENGTH,
    ENTROPY_THRESHOLDS,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    STRENGTH_COLORS,
    STRENGTH_LABELS,
)


# ─── Jeux de caractères ────────────────────────────────────────────────────────

LOWERCASE = string.ascii_lowercase          # a-z (26 chars)
UPPERCASE = string.ascii_uppercase          # A-Z (26 chars)
DIGITS    = string.digits                   # 0-9 (10 chars)
SYMBOLS   = "!@#$%^&*()-_=+[]{}|;:,.<>?"   # 24 symboles courants (évite les ambigus)


# ─── Génération ───────────────────────────────────────────────────────────────

def generate_password(
    length: int = DEFAULT_PASSWORD_LENGTH,
    use_upper: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """
    Génère un mot de passe cryptographiquement sécurisé.

    Garanties :
      - Au moins 1 caractère de chaque type activé (évite les mots de passe
        qui ne satisfont pas les contraintes de certains sites).
      - Le reste est tiré aléatoirement dans l'alphabet complet.
      - Ordre final mélangé via secrets.SystemRandom pour éviter les biais
        (premier char toujours du même type si on concatène naïvement).

    Args:
        length:      Longueur du mot de passe (clampée entre MIN et MAX).
        use_upper:   Inclure des majuscules.
        use_digits:  Inclure des chiffres.
        use_symbols: Inclure des symboles.

    Returns:
        Mot de passe sous forme de str.
    """
    # Clampage défensif de la longueur
    length = max(MIN_PASSWORD_LENGTH, min(MAX_PASSWORD_LENGTH, length))

    # Alphabet complet selon les options activées
    alphabet = LOWERCASE  # toujours présent
    if use_upper:
        alphabet += UPPERCASE
    if use_digits:
        alphabet += DIGITS
    if use_symbols:
        alphabet += SYMBOLS

    # Garantie d'au moins 1 char de chaque type activé
    required_chars: list[str] = [secrets.choice(LOWERCASE)]
    if use_upper:
        required_chars.append(secrets.choice(UPPERCASE))
    if use_digits:
        required_chars.append(secrets.choice(DIGITS))
    if use_symbols:
        required_chars.append(secrets.choice(SYMBOLS))

    # Compléter jusqu'à la longueur demandée
    remaining = [secrets.choice(alphabet) for _ in range(length - len(required_chars))]

    # Mélanger pour que les chars garantis ne soient pas toujours en premier
    all_chars = required_chars + remaining
    rng = secrets.SystemRandom()
    rng.shuffle(all_chars)

    return "".join(all_chars)


# ─── Analyse d'entropie ───────────────────────────────────────────────────────

def password_entropy(password: str) -> float:
    """
    Calcule l'entropie de Shannon du mot de passe en bits.

    Entropie = -Σ p(c) * log2(p(c)) pour chaque caractère unique c.

    Note : cette métrique mesure la distribution des caractères dans le mot
    de passe fourni (entropie empirique), pas l'entropie théorique maximale.
    Un mot de passe aléatoire de 20 chars sur 94 symboles a ~131 bits
    d'entropie théorique ; l'entropie de Shannon est une approximation rapide.

    Args:
        password: Mot de passe à analyser (str).

    Returns:
        Entropie en bits (float ≥ 0). Retourne 0.0 pour une chaîne vide.
    """
    if not password:
        return 0.0

    n = len(password)
    freq: dict[str, int] = {}
    for c in password:
        freq[c] = freq.get(c, 0) + 1

    entropy = 0.0
    for count in freq.values():
        p = count / n
        entropy -= p * math.log2(p)

    # Normalisation : entropie par caractère * longueur = entropie totale estimée
    return entropy * n


def password_strength(password: str) -> tuple[int, str, str]:
    """
    Évalue la force d'un mot de passe.

    Combine l'entropie avec des heuristiques sur la composition
    (longueur, variété de types de caractères).

    Args:
        password: Mot de passe à évaluer.

    Returns:
        Tuple (score, label, color) où :
          - score : int de 0 (très faible) à 4 (très fort)
          - label : str lisible (ex : "Fort")
          - color : str hex (ex : "#2ecc71")
    """
    if not password:
        return 0, STRENGTH_LABELS[0], STRENGTH_COLORS[0]

    entropy = password_entropy(password)

    # Score de base par entropie
    score = 0
    for i, threshold in enumerate(ENTROPY_THRESHOLDS):
        if entropy >= threshold:
            score = i

    # Malus si le mot de passe est trop court (< 8 chars) quelles que soient les stats
    if len(password) < 8:
        score = min(score, 1)

    # Bonus si composition variée ET longueur correcte
    if len(password) >= 12:
        has_lower   = any(c in LOWERCASE for c in password)
        has_upper   = any(c in UPPERCASE for c in password)
        has_digit   = any(c in DIGITS    for c in password)
        has_symbol  = any(c in SYMBOLS   for c in password)
        variety = sum([has_lower, has_upper, has_digit, has_symbol])
        if variety >= 3 and score < 4:
            score = min(score + 1, 4)

    score = max(0, min(4, score))  # Clampage défensif
    return score, STRENGTH_LABELS[score], STRENGTH_COLORS[score]
