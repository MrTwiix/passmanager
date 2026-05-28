"""
config.py — Constantes centralisées de PassManager.

Toutes les magic numbers de l'application sont ici.
Modifier ce fichier pour ajuster les paramètres sans toucher au code métier.
"""

from pathlib import Path

# ─── Chemins ───────────────────────────────────────────────────────────────────

VAULT_PATH: Path = Path.home() / ".passmanager.vault"
PREFS_PATH: Path = Path.home() / ".passmanager.prefs"

# ─── Cryptographie — Argon2id ──────────────────────────────────────────────────
# Recommandations OWASP 2024 pour un usage interactif (login).

ARGON2_TIME_COST: int = 3          # Nombre d'itérations sur la mémoire
ARGON2_MEMORY_COST: int = 65_536   # 64 MB par dérivation (résistance GPU)
ARGON2_PARALLELISM: int = 2        # Nombre de threads parallèles
ARGON2_HASH_LEN: int = 32          # 256 bits → taille exacte d'une clé AES-256
ARGON2_SALT_LEN: int = 16          # 128 bits de sel aléatoire

# ─── Cryptographie — AES-256-GCM ───────────────────────────────────────────────

AES_NONCE_LEN: int = 12            # 96 bits (recommandation NIST pour GCM)
AES_TAG_LEN: int = 16              # 128 bits — tag d'authenticité GCM

# ─── Sécurité comportementale ──────────────────────────────────────────────────

CLIPBOARD_TIMEOUT: int = 30        # Secondes avant effacement du presse-papier
LOCK_TIMEOUT: int = 15 * 60        # Secondes d'inactivité avant verrouillage auto (15 min)

# Options de timeout affichées dans les préférences (None = jamais)
LOCK_TIMEOUT_OPTIONS: dict[str, int | None] = {
    "5 min":  5 * 60,
    "15 min": 15 * 60,
    "30 min": 30 * 60,
    "Jamais": None,
}

# ─── Validation des mots de passe ─────────────────────────────────────────────

MIN_MASTER_PASSWORD_LEN: int = 8   # Longueur minimale du mot de passe maître
MIN_PASSWORD_LENGTH: int = 8       # Longueur minimale pour le générateur
MAX_PASSWORD_LENGTH: int = 40      # Longueur maximale pour le générateur
DEFAULT_PASSWORD_LENGTH: int = 20  # Longueur par défaut du générateur

# ─── Interface graphique ───────────────────────────────────────────────────────

APP_NAME: str = "PassManager"
APP_VERSION: str = "1.0.0"
WINDOW_MIN_WIDTH: int = 900
WINDOW_MIN_HEIGHT: int = 600
DEFAULT_THEME: str = "dark"        # "dark" ou "light"

# ─── Seuils de force de mot de passe ──────────────────────────────────────────
# Basés sur l'entropie Shannon en bits.

ENTROPY_THRESHOLDS: list[float] = [0, 25, 45, 60, 80]  # bits → scores 0-4
STRENGTH_LABELS: list[str] = ["Très faible", "Faible", "Moyen", "Fort", "Très fort"]
STRENGTH_COLORS: list[str] = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#1abc9c"]
