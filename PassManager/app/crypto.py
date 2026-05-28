"""
crypto.py — Couche cryptographique de PassManager.

Ce module est AUTONOME : pas d'import depuis le reste de l'application.
Il peut être testé et raisonné indépendamment.

Primitives utilisées :
  - Dérivation de clé : Argon2id (argon2-cffi)
  - Chiffrement       : AES-256-GCM (cryptography — pyca)

Fonctions pures (zero état interne) : entrée → sortie, sans effets de bord.
"""

import json
import os
from base64 import b64decode, b64encode
from typing import Any

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import (
    AES_NONCE_LEN,
    ARGON2_HASH_LEN,
    ARGON2_MEMORY_COST,
    ARGON2_PARALLELISM,
    ARGON2_SALT_LEN,
    ARGON2_TIME_COST,
)


# ─── Dérivation de clé — Argon2id ─────────────────────────────────────────────

def derive_key(password: str, salt: bytes) -> bytes:
    """
    Dérive une clé AES-256 (32 bytes) depuis un mot de passe maître.

    Argon2id — mode hybride :
      - Résistant aux attaques GPU   → paramètre mémoire (64 MB)
      - Résistant aux side-channels  → mode "id" (hybride i+d)

    Args:
        password: Mot de passe maître en clair (str).
        salt:     16 bytes aléatoires propres à ce vault (public, stocké dans le fichier).

    Returns:
        32 bytes utilisables directement comme clé AES-256.
    """
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LEN,
        type=Type.ID,       # Argon2id = hybride Argon2i + Argon2d
    )


# ─── Chiffrement du vault — AES-256-GCM ───────────────────────────────────────

def encrypt_vault(data: dict[str, Any], password: str) -> bytes:
    """
    Sérialise et chiffre le contenu du vault.

    Flux :
      1. Génère un sel aléatoire (16 bytes) → pour Argon2id
      2. Dérive la clé depuis password + sel
      3. Génère un nonce aléatoire (12 bytes) → pour AES-GCM
      4. Chiffre le JSON des données
      5. Retourne le tout encodé en JSON (sel, nonce, ciphertext en base64)

    Le sel et le nonce sont des valeurs PUBLIQUES : les exposer ne compromet
    pas la sécurité (ils servent d'entrée à la dérivation / au chiffrement,
    pas de secret eux-mêmes).

    Args:
        data:     Dict Python à chiffrer (liste des entrées).
        password: Mot de passe maître en clair.

    Returns:
        bytes JSON contenant {salt, nonce, ciphertext} encodés en base64.
    """
    # 1. Sel pour Argon2id (nouveau à chaque recréation de vault)
    salt = os.urandom(ARGON2_SALT_LEN)

    # 2. Dérivation de la clé
    key = derive_key(password, salt)

    # 3. Nonce pour AES-GCM (NOUVEAU à chaque sauvegarde → jamais réutilisé)
    nonce = os.urandom(AES_NONCE_LEN)

    # 4. Chiffrement AES-256-GCM
    #    - Chiffre ET authentifie en une passe (AEAD)
    #    - Le tag de 16 bytes est concaténé au ciphertext par la librairie
    aesgcm = AESGCM(key)
    plaintext = json.dumps(data, default=str).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)

    # 5. Sérialisation finale (valeurs binaires → base64 pour le JSON)
    vault_json = {
        "salt":       b64encode(salt).decode("ascii"),
        "nonce":      b64encode(nonce).decode("ascii"),
        "ciphertext": b64encode(ciphertext).decode("ascii"),
    }
    return json.dumps(vault_json, indent=2).encode("utf-8")


def decrypt_vault(raw: bytes, password: str) -> dict[str, Any]:
    """
    Déchiffre et désérialise le contenu du vault.

    Flux inverse d'encrypt_vault :
      1. Parse le JSON externe (sel, nonce, ciphertext)
      2. Redeploie le sel → redérive la clé via Argon2id (~1s intentionnel)
      3. Déchiffre et vérifie l'authenticité (AES-GCM)
      4. Parse le JSON interne (les entrées)

    Args:
        raw:      Contenu brut du fichier vault (bytes).
        password: Mot de passe maître à tester.

    Returns:
        Dict Python avec les entrées déchiffrées.

    Raises:
        WrongPasswordError:  Si le mot de passe est incorrect (InvalidTag AES-GCM).
        VaultCorruptedError: Si le fichier est illisible (JSON invalide, données manquantes).
    """
    # Import ici pour éviter la dépendance circulaire (crypto ← models ← ?)
    # crypto.py est censé être autonome ; on importe les exceptions localement.
    from app.models import VaultCorruptedError, WrongPasswordError

    # 1. Parse du JSON externe
    try:
        vault_json = json.loads(raw.decode("utf-8"))
        salt       = b64decode(vault_json["salt"])
        nonce      = b64decode(vault_json["nonce"])
        ciphertext = b64decode(vault_json["ciphertext"])
    except (json.JSONDecodeError, KeyError, Exception) as e:
        raise VaultCorruptedError(f"Fichier vault illisible : {e}") from e

    # 2. Redérivation de la clé (même sel = même clé si même password)
    key = derive_key(password, salt)

    # 3. Déchiffrement AES-GCM + vérification du tag d'authenticité
    #    Si le mot de passe est faux → clé différente → tag invalide → InvalidTag
    try:
        from cryptography.exceptions import InvalidTag
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    except InvalidTag:
        raise WrongPasswordError("Mot de passe maître incorrect.")
    except Exception as e:
        raise VaultCorruptedError(f"Impossible de déchiffrer le vault : {e}") from e

    # 4. Parse du JSON interne (les entrées)
    try:
        return json.loads(plaintext.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise VaultCorruptedError(f"Données internes corrompues : {e}") from e
