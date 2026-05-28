"""
vault.py — Couche données de PassManager (VaultManager).

Responsabilités :
  - CRUD des entrées (create, read, update, delete)
  - Chiffrement / déchiffrement via crypto.py
  - Persistance sur disque (sauvegarde automatique à chaque mutation)
  - Vérification HIBP (Have I Been Pwned) via k-anonymat

L'UI ne connaît que cette classe. Elle ne touche JAMAIS à crypto.py directement.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional

import requests

from app.config import VAULT_PATH
from app.crypto import decrypt_vault, encrypt_vault
from app.models import Entry, VaultNotFoundError, WrongPasswordError


class VaultManager:
    """
    Gestionnaire du coffre-fort de mots de passe.

    Cycle de vie typique :
      1. vm = VaultManager()
      2. vm.create(password)   ← premier lancement
         OU
         vm.unlock(password)   ← lancements suivants
      3. vm.add_entry(...)     ← mutations (sauvegarde auto)
      4. vm.lock()             ← efface la clé et les entrées de la mémoire

    Attributs publics :
      - is_unlocked : bool — True si le vault est déverrouillé
    """

    def __init__(self, vault_path: Path = VAULT_PATH) -> None:
        self._vault_path = vault_path
        self._password: Optional[str] = None    # Jamais persisté sur disque
        self._entries: list[Entry] = []
        self._is_unlocked: bool = False

    # ─── Propriétés ───────────────────────────────────────────────────────────

    @property
    def is_unlocked(self) -> bool:
        return self._is_unlocked

    @property
    def vault_exists(self) -> bool:
        return self._vault_path.exists()

    # ─── Cycle de vie ─────────────────────────────────────────────────────────

    def create(self, password: str) -> None:
        """
        Crée un nouveau vault chiffré vide.

        Appelé au premier lancement de l'application.
        Écrase le vault existant si présent.

        Args:
            password: Mot de passe maître choisi par l'utilisateur.
        """
        self._password = password
        self._entries = []
        self._is_unlocked = True
        self._save()

    def unlock(self, password: str) -> None:
        """
        Déverrouille le vault existant avec le mot de passe fourni.

        La dérivation Argon2id prend ~1 seconde intentionnellement
        (résistance brute-force). Appeler depuis un thread de fond dans l'UI.

        Args:
            password: Mot de passe maître à vérifier.

        Raises:
            VaultNotFoundError:  Si le fichier vault n'existe pas.
            WrongPasswordError:  Si le mot de passe est incorrect.
            VaultCorruptedError: Si le fichier est illisible.
        """
        if not self._vault_path.exists():
            raise VaultNotFoundError(f"Vault introuvable : {self._vault_path}")

        raw = self._vault_path.read_bytes()
        data = decrypt_vault(raw, password)  # Lève WrongPasswordError si mauvais MDP

        self._password = password
        self._entries = [Entry.from_dict(e) for e in data.get("entries", [])]
        self._is_unlocked = True

    def lock(self) -> None:
        """
        Verrouille le vault : efface les données sensibles de la mémoire.

        Après cette appel, is_unlocked == False et _entries est vide.
        """
        self._password = None
        self._entries = []
        self._is_unlocked = False

    # ─── Lecture ──────────────────────────────────────────────────────────────

    def get_entries(self, query: str = "") -> list[Entry]:
        """
        Retourne les entrées du vault, filtrées si query est fourni.

        Le filtrage est insensible à la casse et porte sur titre, username et URL.

        Args:
            query: Terme de recherche (str vide = toutes les entrées).

        Returns:
            Liste d'Entry triée par titre (insensible à la casse).
        """
        self._require_unlocked()
        filtered = [e for e in self._entries if e.matches(query)]
        return sorted(filtered, key=lambda e: e.title.lower())

    def get_entry_by_id(self, entry_id: str) -> Optional[Entry]:
        """Retourne l'entrée correspondant à l'ID, ou None si introuvable."""
        self._require_unlocked()
        return next((e for e in self._entries if e.id == entry_id), None)

    # ─── Mutations (sauvegarde automatique) ───────────────────────────────────

    def add_entry(self, entry: Entry) -> None:
        """
        Ajoute une nouvelle entrée et sauvegarde le vault chiffré.

        Args:
            entry: Entrée à ajouter (doit avoir un ID unique).
        """
        self._require_unlocked()
        self._entries.append(entry)
        self._save()

    def update_entry(self, entry: Entry) -> None:
        """
        Met à jour une entrée existante et sauvegarde le vault chiffré.

        updated_at est mis à jour automatiquement.

        Args:
            entry: Entrée modifiée (l'ID doit exister dans le vault).

        Raises:
            KeyError: Si l'ID n'est pas trouvé.
        """
        self._require_unlocked()
        for i, e in enumerate(self._entries):
            if e.id == entry.id:
                entry.touch()
                self._entries[i] = entry
                self._save()
                return
        raise KeyError(f"Entrée introuvable : {entry.id}")

    def delete_entry(self, entry_id: str) -> None:
        """
        Supprime une entrée par son ID et sauvegarde le vault chiffré.

        Args:
            entry_id: ID de l'entrée à supprimer.

        Raises:
            KeyError: Si l'ID n'est pas trouvé.
        """
        self._require_unlocked()
        for i, e in enumerate(self._entries):
            if e.id == entry_id:
                del self._entries[i]
                self._save()
                return
        raise KeyError(f"Entrée introuvable : {entry_id}")

    # ─── Vérification HIBP ────────────────────────────────────────────────────

    def check_hibp(self, password: str, timeout: int = 5) -> int:
        """
        Vérifie si un mot de passe a été exposé dans une fuite de données.

        Protocole k-anonymat (Have I Been Pwned) :
          1. SHA-1 local du mot de passe
          2. Envoi des 5 premiers chars hexadécimaux à l'API seulement
          3. L'API renvoie ~500 suffixes commençant par ces 5 chars
          4. Comparaison locale — ni le mot de passe ni son hash complet ne quittent la machine

        Args:
            password: Mot de passe à vérifier.
            timeout:  Timeout HTTP en secondes.

        Returns:
            Nombre de fois que le mot de passe a été trouvé dans des fuites (0 = sécurisé).

        Raises:
            requests.RequestException: En cas d'erreur réseau ou timeout.
        """
        # 1. Hash SHA-1 local (jamais envoyé en entier)
        sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]

        # 2. Envoi des 5 premiers chars uniquement
        response = requests.get(
            f"https://api.pwnedpasswords.com/range/{prefix}",
            headers={"User-Agent": "PassManager/1.0 (personal project)"},
            timeout=timeout,
        )
        response.raise_for_status()

        # 3. Recherche du suffixe dans la réponse
        for line in response.text.splitlines():
            parts = line.split(":")
            if len(parts) == 2 and parts[0] == suffix:
                return int(parts[1])

        # 4. Non trouvé = jamais exposé
        return 0

    # ─── Export / Import ──────────────────────────────────────────────────────

    def export_encrypted(self, dest_path: Path) -> None:
        """
        Exporte le vault actuel vers un fichier de backup chiffré.

        Utilise le même format que le vault principal.
        """
        self._require_unlocked()
        encrypted = encrypt_vault(self._to_dict(), self._password)
        dest_path.write_bytes(encrypted)

    def import_encrypted(self, src_path: Path, password: str) -> int:
        """
        Importe les entrées depuis un fichier de backup chiffré.

        Les entrées importées sont AJOUTÉES aux entrées existantes
        (pas de remplacement). Les doublons (même ID) sont ignorés.

        Returns:
            Nombre d'entrées importées.
        """
        self._require_unlocked()
        raw = src_path.read_bytes()
        data = decrypt_vault(raw, password)
        existing_ids = {e.id for e in self._entries}
        new_entries = [
            Entry.from_dict(e)
            for e in data.get("entries", [])
            if e["id"] not in existing_ids
        ]
        self._entries.extend(new_entries)
        if new_entries:
            self._save()
        return len(new_entries)

    # ─── Méthodes privées ─────────────────────────────────────────────────────

    def _require_unlocked(self) -> None:
        """Lève RuntimeError si le vault est verrouillé."""
        if not self._is_unlocked:
            raise RuntimeError("Le vault est verrouillé. Appelez unlock() d'abord.")

    def _to_dict(self) -> dict:
        """Sérialise les entrées en dict JSON-sérialisable."""
        return {"entries": [e.to_dict() for e in self._entries]}

    def _save(self) -> None:
        """Chiffre et sauvegarde le vault sur disque."""
        encrypted = encrypt_vault(self._to_dict(), self._password)
        self._vault_path.write_bytes(encrypted)
