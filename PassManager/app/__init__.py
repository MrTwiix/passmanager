"""
PassManager — Gestionnaire de mots de passe sécurisé.

Package principal. Exporte les symboles publics les plus utilisés.
"""

from app.models import Entry, VaultCorruptedError, VaultNotFoundError, WrongPasswordError
from app.vault import VaultManager

__all__ = [
    "Entry",
    "VaultManager",
    "WrongPasswordError",
    "VaultNotFoundError",
    "VaultCorruptedError",
]

__version__ = "1.0.0"
__author__  = "Tom Jaffelin"
