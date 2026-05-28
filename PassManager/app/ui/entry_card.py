"""
entry_card.py — Widget carte pour une entrée du gestionnaire.

Affiche :
  - Avatar circulaire (initiale du titre)
  - Titre en gras
  - Sous-titre (URL ou username)
  - Boutons : Copier / Éditer / Supprimer
"""

from typing import Callable

import customtkinter as ctk

from app.models import Entry


class EntryCard(ctk.CTkFrame):
    """
    Carte d'affichage d'une entrée dans la liste principale.

    Args:
        parent:      Widget parent.
        entry:       Entrée à afficher.
        on_copy:     Callback(entry_id: str) → copier le mot de passe.
        on_edit:     Callback(entry_id: str) → ouvrir le formulaire d'édition.
        on_delete:   Callback(entry_id: str) → demander confirmation et supprimer.
    """

    def __init__(
        self,
        parent,
        entry: Entry,
        on_copy:   Callable[[str], None],
        on_edit:   Callable[[str], None],
        on_delete: Callable[[str], None],
        **kwargs,
    ) -> None:
        super().__init__(parent, corner_radius=10, border_width=1, **kwargs)
        self._entry    = entry
        self._on_copy  = on_copy
        self._on_edit  = on_edit
        self._on_delete = on_delete

        self.columnconfigure(1, weight=1)
        self._build_ui()

    # ─── Construction ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Avatar circulaire ─────────────────────────────────────────────────
        initial = (self._entry.title[0].upper() if self._entry.title else "?")
        avatar = ctk.CTkLabel(
            self,
            text=initial,
            font=("", 18, "bold"),
            width=44,
            height=44,
            corner_radius=22,
            fg_color=self._avatar_color(initial),
            text_color="white",
        )
        avatar.grid(row=0, column=0, rowspan=2, padx=(12, 10), pady=12, sticky="ns")

        # ── Textes ────────────────────────────────────────────────────────────
        title_label = ctk.CTkLabel(
            self,
            text=self._entry.title,
            font=("", 14, "bold"),
            anchor="w",
        )
        title_label.grid(row=0, column=1, sticky="w", pady=(12, 0))

        subtitle = self._entry.url or self._entry.username or ""
        if len(subtitle) > 50:
            subtitle = subtitle[:47] + "…"
        subtitle_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=("", 12),
            text_color=("gray45", "gray60"),
            anchor="w",
        )
        subtitle_label.grid(row=1, column=1, sticky="w", pady=(0, 12))

        # ── Boutons d'action ──────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=2, padx=(0, 12), pady=12, sticky="ns")

        entry_id = self._entry.id

        ctk.CTkButton(
            btn_frame,
            text="📋",
            width=34,
            height=30,
            font=("", 14),
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            command=lambda: self._on_copy(entry_id),
        ).grid(row=0, column=0, padx=2)

        ctk.CTkButton(
            btn_frame,
            text="✏️",
            width=34,
            height=30,
            font=("", 14),
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            command=lambda: self._on_edit(entry_id),
        ).grid(row=0, column=1, padx=2)

        ctk.CTkButton(
            btn_frame,
            text="🗑️",
            width=34,
            height=30,
            font=("", 14),
            fg_color="transparent",
            hover_color=("#fde8e8", "#4a1e1e"),
            text_color=("#c0392b", "#e74c3c"),
            command=lambda: self._on_delete(entry_id),
        ).grid(row=0, column=2, padx=2)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _avatar_color(initial: str) -> str:
        """
        Retourne une couleur déterministe basée sur l'initiale.
        Donne une couleur différente à chaque lettre pour différencier visuellement les cartes.
        """
        colors = [
            "#3498db", "#9b59b6", "#e67e22", "#1abc9c",
            "#e74c3c", "#2ecc71", "#f39c12", "#16a085",
            "#8e44ad", "#27ae60", "#d35400", "#2980b9",
        ]
        idx = (ord(initial) % len(colors)) if initial.isalpha() else 0
        return colors[idx]
