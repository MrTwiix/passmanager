"""
test_crypto.py — Tests unitaires de la couche cryptographique.

Couvre :
  - Chiffrement / déchiffrement round-trip
  - Mauvais mot de passe → WrongPasswordError
  - Unicité des nonces (deux chiffrements ≠ ciphertexts)
  - Longueur de la clé dérivée (32 bytes = AES-256)
  - Unicité des sels entre deux vault différents
"""

import json
from base64 import b64decode

import pytest

from app.crypto import decrypt_vault, derive_key, encrypt_vault
from app.models import WrongPasswordError


# ─── Fixtures ─────────────────────────────────────────────────────────────────

SAMPLE_DATA = {
    "entries": [
        {
            "id": "abc123",
            "title": "GitHub",
            "username": "tom",
            "password": "super-secret",
            "url": "https://github.com",
            "notes": "",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    ]
}

PASSWORD = "motdepasse_securise"
WRONG_PASSWORD = "mauvais_mot_de_passe"


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_encrypt_decrypt_roundtrip():
    """Chiffrement puis déchiffrement → données identiques."""
    encrypted = encrypt_vault(SAMPLE_DATA, PASSWORD)
    decrypted = decrypt_vault(encrypted, PASSWORD)
    assert decrypted == SAMPLE_DATA


def test_wrong_password_raises():
    """Mauvais mot de passe → WrongPasswordError."""
    encrypted = encrypt_vault(SAMPLE_DATA, PASSWORD)
    with pytest.raises(WrongPasswordError):
        decrypt_vault(encrypted, WRONG_PASSWORD)


def test_two_encryptions_differ():
    """
    Deux chiffrements du même plaintext → ciphertexts différents.
    Garantit que le nonce est bien régénéré à chaque sauvegarde.
    """
    enc1 = encrypt_vault(SAMPLE_DATA, PASSWORD)
    enc2 = encrypt_vault(SAMPLE_DATA, PASSWORD)
    # Les nonces et ciphertexts doivent différer
    j1 = json.loads(enc1)
    j2 = json.loads(enc2)
    assert j1["nonce"]      != j2["nonce"],      "Le nonce doit être unique à chaque appel"
    assert j1["ciphertext"] != j2["ciphertext"], "Le ciphertext doit différer si le nonce diffère"


def test_derived_key_length():
    """La clé dérivée par Argon2id fait exactement 32 bytes (AES-256)."""
    import os
    salt = os.urandom(16)
    key = derive_key(PASSWORD, salt)
    assert len(key) == 32, f"Longueur attendue : 32 bytes, obtenu : {len(key)}"


def test_two_vaults_have_different_salts():
    """Deux vault créés indépendamment → sels différents."""
    enc1 = encrypt_vault(SAMPLE_DATA, PASSWORD)
    enc2 = encrypt_vault(SAMPLE_DATA, PASSWORD)
    salt1 = json.loads(enc1)["salt"]
    salt2 = json.loads(enc2)["salt"]
    assert salt1 != salt2, "Chaque vault doit avoir un sel unique"


def test_empty_vault_roundtrip():
    """Vault vide → round-trip correct."""
    empty = {"entries": []}
    encrypted = encrypt_vault(empty, PASSWORD)
    decrypted = decrypt_vault(encrypted, PASSWORD)
    assert decrypted == empty


def test_corrupted_vault_raises():
    """Fichier corrompu → VaultCorruptedError."""
    from app.models import VaultCorruptedError
    with pytest.raises(VaultCorruptedError):
        decrypt_vault(b"ceci_nest_pas_un_vault_valide", PASSWORD)
