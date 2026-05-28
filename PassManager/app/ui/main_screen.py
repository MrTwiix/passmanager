"""
main_screen.py — Écran principal de PassManager.

Contient :
  - Barre du haut : logo, recherche, bouton +Ajouter, Générateur, Verrou
  - Zone centrale : liste défilante des cartes EntryCard
  - Barre de statut en bas
"""

import threading
import time
from typing import Callable

import customtkinter as ctk

from app.config import CLIPBOARD_TIMEOUT
from app.models import Entry
from app.ui.entry_card import EntryCard
from app.ui.entry_dialog import EntryDialog
from app.ui.generator_dialog import GeneratorDialog
from app.ui.widgets import StatusBar
from app.vault import VaultManager


class MainScreen(ctk.CTkFrame):
    """
    Écran principal affiché après authentification.

    Args:
        parent:        Widget parent.
        vault_manager: Instance partagée de VaultManager.
        on_lock:       Callback appelé quand l'utilisateur demande le verrouillage.
    """

    def __init__(
        self,
        parent,
        vault_manager: VaultManager,
        on_lock: Callable,
        **kwargs,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._vm = vault_manager
        self._on_lock = on_lock
        self._clipboard_timer_id = None

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self._build_topbar()
        self._build_list_area()
        self._build_statusbar()
        self.refresh_entries()

    # ─── Barre du haut ────────────────────────────────────────────────────────

    def _build_topbar(self) -> None:
        topbar = ctk.CTkFrame(self, corner_radius=0, height=56)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.columnconfigure(1, weight=1)
        topbar.grid_propagate(False)

        # Logo
        ctk.CTkLabel(
            topbar,
            text="🔐  PassManager",
            font=("", 18, "bold"),
        ).grid(row=0, column=0, padx=20, pady=8, sticky="w")

        # Champ de recherche centré
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._on_search_change())
        search_entry = ctk.CTkEntry(
            topbar,
            placeholder_text="🔍  Rechercher…",
            textvariable=self._search_var,
            height=34,
            width=280,
        )
        search_entry.grid(row=0, column=1, pady=8)

        # Boutons d'action à droite
        btn_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=12, pady=8, sticky="e")

        ctk.CTkButton(
            btn_frame,
            text="➕  Nouveau",
            height=34,
            font=("", 13),
            command=self._add_entry,
        ).grid(row=0, column=0, padx=4)

        ctk.CTkButton(
            btn_frame,
            text="🎲  Générateur",
            height=34,
            font=("", 13),
            fg_color="transparent",
            border_width=1,
            command=self._open_generator,
        ).grid(row=0, column=1, padx=4)

        ctk.CTkButton(
            btn_frame,
            text="🔒",
            height=34,
            width=40,
            font=("", 16),
            fg_color="transparent",
            border_width=1,
            command=self._on_lock,
        ).grid(row=0, column=2, padx=4)

    # ─── Zone de liste ────────────────────────────────────────────────────────

    def _build_list_area(self) -> None:
        # Conteneur avec scroll
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            label_text="",
        )
        self._scroll_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 4))
        self._scroll_frame.columnconfigure(0, weight=1)

        # Message vide affiché si aucune entrée
        self._empty_label = ctk.CTkLabel(
            self._scroll_frame,
            text="Aucune entrée.\nCliquez sur ➕ Ajouter pour commencer.",
            font=("", 14),
            text_color=("gray50", "gray55"),
            justify="center",
        )

    # ─── Barre de statut ──────────────────────────────────────────────────────

    def _build_statusbar(self) -> None:
        bar_frame = ctk.CTkFrame(self, height=28, corner_radius=0)
        bar_frame.grid(row=2, column=0, sticky="ew")
        bar_frame.columnconfigure(0, weight=1)
        bar_frame.grid_propagate(False)

        self._status_bar = StatusBar(bar_frame)
        self._status_bar.grid(row=0, column=0, sticky="ew", padx=16)

    # ─── Affichage des entrées ────────────────────────────────────────────────

    def refresh_entries(self, query: str = "") -> None:
        """Recharge et affiche les entrées (avec filtre éventuel)."""
        # Suppression des cartes précédentes
        for widget in self._scroll_frame.winfo_children():
            if isinstance(widget, EntryCard):
                widget.destroy()
        self._empty_label.grid_remove()

        entries = self._vm.get_entries(query)

        if not entries:
            self._empty_label.grid(row=0, column=0, pady=60)
            count_text = "Aucune entrée" if not query else f"Aucun résultat pour « {query} »"
        else:
            for i, entry in enumerate(entries):
                card = EntryCard(
                    self._scroll_frame,
                    entry=entry,
                    on_copy=self._copy_password,
                    on_edit=self._edit_entry,
                    on_delete=self._confirm_delete,
                )
                card.grid(row=i, column=0, sticky="ew", pady=(0, 6))
            total = len(self._vm.get_entries())
            if query:
                count_text = f"{len(entries)} résultat(s) sur {total} entrée(s)"
            else:
                count_text = f"{total} entrée(s)"

        self._status_bar.set(count_text)

    # ─── Actions ──────────────────────────────────────────────────────────────

    def _on_search_change(self) -> None:
        """Appelé à chaque frappe dans le champ de recherche."""
        self.refresh_entries(self._search_var.get())

    def _add_entry(self) -> None:
        """Ouvre le formulaire de création d'une nouvelle entrée."""
        def on_save(entry: Entry) -> None:
            self._vm.add_entry(entry)
            self.refresh_entries(self._search_var.get())
            self._status_bar.set(f"✅  Entrée « {entry.title} » ajoutée.", duration_ms=4000)

        EntryDialog(self, vault_manager=self._vm, on_save=on_save)

    def _edit_entry(self, entry_id: str) -> None:
        """Ouvre le formulaire d'édition pour l'entrée donnée."""
        entry = self._vm.get_entry_by_id(entry_id)
        if not entry:
            return

        def on_save(updated: Entry) -> None:
            self._vm.update_entry(updated)
            self.refresh_entries(self._search_var.get())
            self._status_bar.set(f"✅  Entrée « {updated.title} » mise à jour.", duration_ms=4000)

        EntryDialog(self, vault_manager=self._vm, on_save=on_save, entry=entry)

    def _confirm_delete(self, entry_id: str) -> None:
        """Affiche une boîte de dialogue de confirmation avant suppression."""
        entry = self._vm.get_entry_by_id(entry_id)
        if not entry:
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirmer la suppression")
        dialog.geometry("380x180")
        dialog.resizable(False, False)
        dialog.after(100, dialog.grab_set)

        ctk.CTkLabel(
            dialog,
            text=f"Supprimer « {entry.title} » ?",
            font=("", 15, "bold"),
        ).pack(pady=(28, 8))

        ctk.CTkLabel(
            dialog,
            text="Cette action est irréversible.",
            font=("", 12),
            text_color=("gray50", "gray55"),
        ).pack()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(
            btn_frame,
            text="Annuler",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=dialog.destroy,
        ).grid(row=0, column=0, padx=8)

        def do_delete():
            self._vm.delete_entry(entry_id)
            self.refresh_entries(self._search_var.get())
            self._status_bar.set(f"🗑️  Entrée « {entry.title} » supprimée.", duration_ms=4000)
            dialog.destroy()

        ctk.CTkButton(
            btn_frame,
            text="Supprimer",
            width=110,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            text_color="white",
            command=do_delete,
        ).grid(row=0, column=1, padx=8)

    def _copy_password(self, entry_id: str) -> None:
        """Copie le mot de passe dans le presse-papier avec effacement auto."""
        entry = self._vm.get_entry_by_id(entry_id)
        if not entry:
            return

        # Annule le timer précédent
        if self._clipboard_timer_id is not None:
            self.after_cancel(self._clipboard_timer_id)

        try:
            import pyperclip
            pyperclip.copy(entry.password)
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(entry.password)

        # Compte à rebours dans la barre de statut
        self._start_clipboard_countdown(entry.title)

    def _start_clipboard_countdown(self, entry_title: str) -> None:
        """Lance le compte à rebours d'effacement du presse-papier."""
        remaining = [CLIPBOARD_TIMEOUT]

        def tick():
            if remaining[0] <= 0:
                try:
                    import pyperclip
                    pyperclip.copy("")
                except Exception:
                    pass
                self._status_bar.set("✅  Presse-papier effacé.")
                self._clipboard_timer_id = None
                return
            self._status_bar.set(
                f"📋  Mot de passe de « {entry_title} » copié — effacement dans {remaining[0]}s"
            )
            remaining[0] -= 1
            self._clipboard_timer_id = self.after(1000, tick)

        tick()

    def _open_generator(self) -> None:
        """Ouvre le générateur (sans injection, mode standalone)."""
        GeneratorDialog(self, on_use=None)
