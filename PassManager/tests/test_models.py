"""
test_models.py — Tests unitaires des modèles de données.

Couvre :
  - Sérialisation / désérialisation d'Entry
  - Génération automatique de l'ID
  - Remplissage automatique de created_at et updated_at
  - Méthode touch() met à jour updated_at uniquement
  - Méthode matches() pour la recherche
"""

import time
from datetime import datetime, timezone

import pytest

from app.models import Entry, VaultCorruptedError, VaultNotFoundError, WrongPasswordError


# ─── Tests Entry ──────────────────────────────────────────────────────────────

def test_entry_serialization_roundtrip():
    """Entry → dict → Entry : résultat identique."""
    original = Entry(title="GitHub", username="tom", password="secret123", url="https://github.com")
    restored = Entry.from_dict(original.to_dict())
    assert restored.id       == original.id
    assert restored.title    == original.title
    assert restored.username == original.username
    assert restored.password == original.password
    assert restored.url      == original.url
    assert restored.notes    == original.notes


def test_entry_auto_id():
    """L'ID est généré automatiquement si non fourni."""
    e1 = Entry(title="A", username="u", password="p")
    e2 = Entry(title="B", username="u", password="p")
    assert e1.id != e2.id
    assert len(e1.id) == 36  # UUID4 = 36 chars avec tirets


def test_entry_auto_timestamps():
    """created_at et updated_at sont remplis automatiquement à la création."""
    entry = Entry(title="Test", username="u", password="p")
    assert isinstance(entry.created_at, datetime)
    assert isinstance(entry.updated_at, datetime)
    assert entry.created_at.tzinfo is not None  # UTC aware


def test_entry_touch_updates_only_updated_at():
    """touch() met à jour updated_at mais pas created_at."""
    entry = Entry(title="Test", username="u", password="p")
    original_created = entry.created_at
    original_updated = entry.updated_at

    time.sleep(0.01)  # Garantit un timestamp différent
    entry.touch()

    assert entry.created_at == original_created, "created_at ne doit pas changer"
    assert entry.updated_at >= original_updated, "updated_at doit être mis à jour"


def test_entry_optional_fields_default_empty():
    """Les champs optionnels (url, notes) sont vides par défaut."""
    entry = Entry(title="X", username="y", password="z")
    assert entry.url   == ""
    assert entry.notes == ""


def test_entry_matches_title():
    """matches() retourne True si la requête est dans le titre."""
    entry = Entry(title="GitHub", username="tom", password="p")
    assert entry.matches("git")
    assert entry.matches("GitHub")
    assert entry.matches("GIT")  # insensible à la casse
    assert not entry.matches("gitlab")


def test_entry_matches_username():
    """matches() retourne True si la requête est dans le username."""
    entry = Entry(title="X", username="tom@example.com", password="p")
    assert entry.matches("tom")
    assert entry.matches("example")


def test_entry_matches_url():
    """matches() retourne True si la requête est dans l'URL."""
    entry = Entry(title="X", username="u", password="p", url="https://github.com")
    assert entry.matches("github")
    assert entry.matches("https")


def test_entry_matches_empty_query():
    """matches() avec query vide retourne toujours True."""
    entry = Entry(title="X", username="u", password="p")
    assert entry.matches("")
    assert entry.matches("   ")


# ─── Tests des exceptions ─────────────────────────────────────────────────────

def test_wrong_password_error_is_exception():
    with pytest.raises(WrongPasswordError):
        raise WrongPasswordError("test")


def test_vault_not_found_error_is_exception():
    with pytest.raises(VaultNotFoundError):
        raise VaultNotFoundError("test")


def test_vault_corrupted_error_is_exception():
    with pytest.raises(VaultCorruptedError):
        raise VaultCorruptedError("test")
