"""
test_vault.py — Tests unitaires de VaultManager.

Utilise un fichier vault temporaire (tmp_path de pytest) pour
isoler chaque test sans toucher au vault réel de l'utilisateur.

Couvre :
  - Création du vault
  - Déverrouillage (bon et mauvais mot de passe)
  - Vault inexistant
  - CRUD complet (add, get, update, delete)
  - Persistance après rechargement
  - Filtrage par requête
  - Timestamps (updated_at vs created_at)
"""

import pytest

from app.models import Entry, VaultNotFoundError, WrongPasswordError
from app.vault import VaultManager

PASSWORD = "motdepasse_test_42"


# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def vm(tmp_path):
    """VaultManager pointant vers un fichier temporaire isolé."""
    vault_file = tmp_path / "test.vault"
    manager = VaultManager(vault_path=vault_file)
    manager.create(PASSWORD)
    return manager


@pytest.fixture
def sample_entry():
    return Entry(title="GitHub", username="tom@example.com", password="super-secret-42", url="https://github.com")


# ─── Tests cycle de vie ───────────────────────────────────────────────────────

def test_create_creates_file(tmp_path):
    """create() crée le fichier vault sur le disque."""
    vault_file = tmp_path / "new.vault"
    manager = VaultManager(vault_path=vault_file)
    assert not vault_file.exists()
    manager.create(PASSWORD)
    assert vault_file.exists()


def test_unlock_with_correct_password(tmp_path):
    """unlock() avec le bon mot de passe → vault déverrouillé."""
    vault_file = tmp_path / "test.vault"
    m1 = VaultManager(vault_path=vault_file)
    m1.create(PASSWORD)

    m2 = VaultManager(vault_path=vault_file)
    m2.unlock(PASSWORD)
    assert m2.is_unlocked


def test_unlock_wrong_password_raises(tmp_path):
    """unlock() avec mauvais mot de passe → WrongPasswordError."""
    vault_file = tmp_path / "test.vault"
    m = VaultManager(vault_path=vault_file)
    m.create(PASSWORD)

    m2 = VaultManager(vault_path=vault_file)
    with pytest.raises(WrongPasswordError):
        m2.unlock("mauvais_mot_de_passe")


def test_unlock_missing_file_raises(tmp_path):
    """unlock() sur un vault inexistant → VaultNotFoundError."""
    vault_file = tmp_path / "inexistant.vault"
    m = VaultManager(vault_path=vault_file)
    with pytest.raises(VaultNotFoundError):
        m.unlock(PASSWORD)


def test_lock_clears_memory(vm):
    """Après lock(), le vault est verrouillé et les entrées effacées."""
    vm.lock()
    assert not vm.is_unlocked


# ─── Tests CRUD ───────────────────────────────────────────────────────────────

def test_add_entry(vm, sample_entry):
    """add_entry() → l'entrée est présente dans get_entries()."""
    vm.add_entry(sample_entry)
    entries = vm.get_entries()
    assert any(e.id == sample_entry.id for e in entries)


def test_get_entries_empty(vm):
    """Vault vide → get_entries() retourne une liste vide."""
    assert vm.get_entries() == []


def test_update_entry(vm, sample_entry, tmp_path):
    """update_entry() → modifications persistées après rechargement."""
    vm.add_entry(sample_entry)

    sample_entry.title = "GitHub Pro"
    vm.update_entry(sample_entry)

    # Recharge depuis le disque
    vault_file = tmp_path / "test.vault"
    # Le vm de la fixture est déjà sur le bon chemin
    entries = vm.get_entries()
    updated = next(e for e in entries if e.id == sample_entry.id)
    assert updated.title == "GitHub Pro"


def test_delete_entry(vm, sample_entry):
    """delete_entry() → l'entrée absente après suppression."""
    vm.add_entry(sample_entry)
    vm.delete_entry(sample_entry.id)
    entries = vm.get_entries()
    assert not any(e.id == sample_entry.id for e in entries)


def test_delete_nonexistent_raises(vm):
    """delete_entry() sur un ID inexistant → KeyError."""
    with pytest.raises(KeyError):
        vm.delete_entry("id_qui_nexiste_pas")


def test_update_nonexistent_raises(vm):
    """update_entry() sur un ID inexistant → KeyError."""
    ghost = Entry(title="Ghost", username="u", password="p")
    with pytest.raises(KeyError):
        vm.update_entry(ghost)


# ─── Tests recherche ─────────────────────────────────────────────────────────

def test_get_entries_filter(vm):
    """get_entries(query) filtre correctement sur titre, username, URL."""
    vm.add_entry(Entry(title="GitHub", username="tom", password="p", url="https://github.com"))
    vm.add_entry(Entry(title="Gmail",  username="tom@gmail.com", password="p"))
    vm.add_entry(Entry(title="Notion", username="user", password="p"))

    results = vm.get_entries("git")
    assert len(results) == 1
    assert results[0].title == "GitHub"

    results = vm.get_entries("tom")
    assert len(results) == 2

    results = vm.get_entries("notion")
    assert len(results) == 1


def test_get_entries_empty_query_returns_all(vm):
    """get_entries('') retourne toutes les entrées."""
    vm.add_entry(Entry(title="A", username="u", password="p"))
    vm.add_entry(Entry(title="B", username="u", password="p"))
    assert len(vm.get_entries("")) == 2


# ─── Tests timestamps ─────────────────────────────────────────────────────────

def test_timestamps_on_update(vm, sample_entry):
    """updated_at change après update_entry(), created_at reste identique."""
    import time
    vm.add_entry(sample_entry)
    original_created = sample_entry.created_at
    original_updated = sample_entry.updated_at

    time.sleep(0.05)
    sample_entry.password = "nouveau_mot_de_passe"
    vm.update_entry(sample_entry)

    updated = vm.get_entry_by_id(sample_entry.id)
    assert updated.created_at == original_created, "created_at ne doit pas changer"
    assert updated.updated_at > original_updated,  "updated_at doit être mis à jour"


# ─── Tests persistance ────────────────────────────────────────────────────────

def test_persistence_after_reload(tmp_path):
    """Les données persistent après fermeture et réouverture du vault."""
    vault_file = tmp_path / "persist.vault"

    # Session 1 : création et ajout
    m1 = VaultManager(vault_path=vault_file)
    m1.create(PASSWORD)
    m1.add_entry(Entry(title="Persistent", username="u", password="p"))

    # Session 2 : rechargement
    m2 = VaultManager(vault_path=vault_file)
    m2.unlock(PASSWORD)
    entries = m2.get_entries()
    assert len(entries) == 1
    assert entries[0].title == "Persistent"
