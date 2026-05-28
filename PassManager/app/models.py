"""
models.py — Structures de données et exceptions métier de PassManager.

Utiliser une dataclass plutôt qu'un dict brut :
  - Autocomplétion dans l'IDE
  - Pas de fautes de frappe sur les clés
  - Documentation implicite de la structure
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now_utc() -> datetime:
    """Retourne l'heure actuelle en UTC (aware)."""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    """Génère un UUID v4 sous forme de string."""
    return str(uuid.uuid4())


# ─── Dataclass principale ──────────────────────────────────────────────────────

@dataclass
class Entry:
    """
    Représente une entrée du gestionnaire de mots de passe.

    Les champs obligatoires (title, username, password) doivent être fournis
    explicitement. Les autres ont des valeurs par défaut.
    """

    # Champs obligatoires
    title: str
    username: str
    password: str

    # Champs optionnels
    url: str = ""
    notes: str = ""

    # Méta-données gérées automatiquement
    id: str = field(default_factory=_new_uuid)
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    def to_dict(self) -> dict[str, Any]:
        """Sérialise l'entrée en dict JSON-sérialisable."""
        return {
            "id":         self.id,
            "title":      self.title,
            "username":   self.username,
            "password":   self.password,
            "url":        self.url,
            "notes":      self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entry":
        """Reconstruit une Entry depuis un dict (chargé depuis le vault)."""
        return cls(
            id=data["id"],
            title=data["title"],
            username=data["username"],
            password=data["password"],
            url=data.get("url", ""),
            notes=data.get("notes", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def touch(self) -> None:
        """Met à jour updated_at à l'heure actuelle (appelé lors d'une édition)."""
        self.updated_at = _now_utc()

    def matches(self, query: str) -> bool:
        """
        Retourne True si l'entrée correspond à la requête de recherche.
        Recherche insensible à la casse sur titre, username et URL.
        """
        q = query.lower().strip()
        if not q:
            return True
        return (
            q in self.title.lower()
            or q in self.username.lower()
            or q in self.url.lower()
        )

    def __repr__(self) -> str:
        return f"Entry(id={self.id[:8]}…, title={self.title!r})"


# ─── Exceptions métier ────────────────────────────────────────────────────────

class WrongPasswordError(Exception):
    """
    Levée quand le mot de passe maître fourni est incorrect.

    En pratique : AES-GCM lève une InvalidTag car le ciphertext ne peut pas
    être déchiffré avec une clé dérivée d'un mauvais mot de passe.
    """
    pass


class VaultNotFoundError(Exception):
    """
    Levée quand le fichier vault n'existe pas sur le disque.

    Attendu au premier lancement : l'UI doit proposer de créer un nouveau vault.
    """
    pass


class VaultCorruptedError(Exception):
    """
    Levée quand le fichier vault existe mais est illisible.

    Causes possibles : fichier tronqué, JSON invalide, modification manuelle.
    Le vault ne peut pas être récupéré automatiquement.
    """
    pass
