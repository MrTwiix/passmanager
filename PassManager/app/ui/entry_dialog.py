"""
entry_dialog.py — Formulaire d'ajout et d'édition d'une entrée.

Contient :
  - Champs : titre*, username/email*, mot de passe* (avec œil + générateur), URL, notes
  - Barre de force en temps réel sous le champ mot de passe
  - Bouton "Vérifier HIBP" (mode édition uniquement)
  - Boutons Enregistrer / Annuler
"""

import threading
from typing import Callable, Optional

import customtkinter as ctk

from app.models import Entry
from app.ui.generator_dialog import GeneratorDialog
from app.ui.widgets import PasswordEntry, StrengthBar
from app.vault import VaultManager


class EntryDialog(ctk.CTkToplevel):
    """
    Fenêtre modale pour créer ou éditer une entrée.

    Args:
        parent:        Widget parent.
        vault_manager: Instance de VaultManager.
        on_save:       Callback(entry: Entry) après enregistrement.
        entry:         Entrée à éditer (None = création).
    """

    def __init__(
        self,
        parent,
        vault_manager: VaultManager,
        on_save: Callable[[Entry], None],
        entry: Optional[Entry] = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._vm = vault_manager
        self._on_save = on_save
        self._entry = entry
        self._is_edit = entry is not None

        title_text = "Modifier le mot de passe" if self._is_edit else "Nouveau mot de passe"
        self.title(title_text)
        self.geometry("520x720" if self._is_edit else "520x640")
        self.resizable(False, False)
        self.after(100, self.grab_set)

        self._build_ui()
        if self._is_edit:
            self._populate_fields()

    # ─── Construction de l'UI ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)

        # Titre de la fenêtre
        title_text = "✏️  Modifier" if self._is_edit else "➕  Nouveau mot de passe"
        ctk.CTkLabel(self, text=title_text, font=("", 20, "bold")).grid(
            row=0, column=0, pady=(24, 16), padx=32, sticky="w"
        )

        # ── Formulaire ────────────────────────────────────────────────────────
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=32)
        form.columnconfigure(1, weight=1)

        row = 0

        # Titre
        ctk.CTkLabel(form, text="Titre *", font=("", 13)).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1
        self._title_entry = ctk.CTkEntry(form, placeholder_text="Ex : GitHub", height=36)
        self._title_entry.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        row += 1

        # Username / email
        ctk.CTkLabel(form, text="Identifiant / Email *", font=("", 13)).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1
        self._username_entry = ctk.CTkEntry(form, placeholder_text="Ex : votre@email.com", height=36)
        self._username_entry.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        row += 1

        # Mot de passe
        ctk.CTkLabel(form, text="Mot de passe *", font=("", 13)).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1
        pwd_row = ctk.CTkFrame(form, fg_color="transparent")
        pwd_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        pwd_row.columnconfigure(0, weight=1)

        self._pwd_entry = PasswordEntry(pwd_row, placeholder="Mot de passe")
        self._pwd_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self._pwd_entry.bind("<KeyRelease>", lambda _: self._update_strength())

        gen_btn = ctk.CTkButton(
            pwd_row,
            text="🎲",
            width=36,
            height=36,
            command=self._open_generator,
            fg_color="transparent",
            border_width=1,
            font=("", 16),
        )
        gen_btn.grid(row=0, column=1)
        row += 1

        # Barre de force
        self._strength_bar = StrengthBar(form)
        self._strength_bar.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 12))
        row += 1

        # URL
        ctk.CTkLabel(form, text="URL", font=("", 13)).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1
        self._url_entry = ctk.CTkEntry(form, placeholder_text="Ex : https://github.com", height=36)
        self._url_entry.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        row += 1

        # Notes
        ctk.CTkLabel(form, text="Notes", font=("", 13)).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1
        self._notes_text = ctk.CTkTextbox(form, height=80)
        self._notes_text.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        row += 1

        # Bouton HIBP (mode édition uniquement)
        if self._is_edit:
            self._hibp_btn = ctk.CTkButton(
                form,
                text="🔍  Vérifier Have I Been Pwned",
                fg_color="transparent",
                border_width=1,
                font=("", 12),
                command=self._check_hibp,
            )
            self._hibp_btn.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
            row += 1

            self._hibp_label = ctk.CTkLabel(form, text="", font=("", 12))
            self._hibp_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
            row += 1

        # Message d'erreur
        self._error_label = ctk.CTkLabel(form, text="", font=("", 12), text_color="#e74c3c", wraplength=420)
        self._error_label.grid(row=row, column=0, columnspan=2)
        row += 1

        # Boutons Enregistrer / Annuler
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=(8, 24), padx=32, sticky="e")

        ctk.CTkButton(
            btn_frame,
            text="Annuler",
            width=110,
            height=38,
            fg_color="transparent",
            border_width=1,
            command=self.destroy,
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_frame,
            text="✓  Enregistrer",
            width=140,
            height=38,
            font=("", 13, "bold"),
            command=self._on_save_click,
        ).grid(row=0, column=1)

    # ─── Pré-remplissage (mode édition) ───────────────────────────────────────

    def _populate_fields(self) -> None:
        """Pré-remplit les champs avec les données de l'entrée existante."""
        e = self._entry
        self._title_entry.insert(0, e.title)
        self._username_entry.insert(0, e.username)
        self._pwd_entry.set(e.password)
        self._url_entry.insert(0, e.url)
        self._notes_text.insert("1.0", e.notes)
        self._update_strength()

    # ─── Logique ──────────────────────────────────────────────────────────────

    def _update_strength(self) -> None:
        """Met à jour la barre de force selon le mot de passe saisi."""
        self._strength_bar.set_from_password(self._pwd_entry.get())

    def _open_generator(self) -> None:
        """Ouvre le générateur et injecte le résultat dans le champ mot de passe."""
        def on_use(password: str) -> None:
            self._pwd_entry.set(password)
            self._update_strength()

        GeneratorDialog(self, on_use=on_use)

    def _on_save_click(self) -> None:
        """Valide le formulaire et sauvegarde l'entrée."""
        title    = self._title_entry.get().strip()
        username = self._username_entry.get().strip()
        password = self._pwd_entry.get()
        url      = self._url_entry.get().strip()
        notes    = self._notes_text.get("1.0", "end-1c").strip()

        # Validation des champs obligatoires
        if not title:
            self._error_label.configure(text="Le titre est obligatoire.")
            return
        if not username:
            self._error_label.configure(text="L'identifiant est obligatoire.")
            return
        if not password:
            self._error_label.configure(text="Le mot de passe est obligatoire.")
            return

        self._error_label.configure(text="")

        if self._is_edit:
            # Mise à jour de l'entrée existante
            self._entry.title    = title
            self._entry.username = username
            self._entry.password = password
            self._entry.url      = url
            self._entry.notes    = notes
            entry = self._entry
        else:
            # Création d'une nouvelle entrée
            from app.models import Entry
            entry = Entry(
                title=title,
                username=username,
                password=password,
                url=url,
                notes=notes,
            )

        self._on_save(entry)
        self.destroy()

    def _check_hibp(self) -> None:
        """Vérifie le mot de passe actuel via Have I Been Pwned (thread de fond)."""
        password = self._pwd_entry.get()
        if not password:
            self._hibp_label.configure(text="Saisissez un mot de passe d'abord.", text_color="#e67e22")
            return

        self._hibp_btn.configure(state="disabled", text="Vérification…")
        self._hibp_label.configure(text="", text_color=("gray40", "gray60"))

        def run():
            try:
                count = self._vm.check_hibp(password)
                if count == 0:
                    msg   = "✅  Ce mot de passe n'a jamais été exposé dans une fuite connue."
                    color = "#2ecc71"
                else:
                    msg   = f"⚠️  Exposé {count:,} fois dans des fuites de données ! Changez-le."
                    color = "#e74c3c"
                self.after(0, lambda: self._hibp_label.configure(text=msg, text_color=color))
            except Exception as e:
                self.after(0, lambda: self._hibp_label.configure(
                    text=f"Erreur réseau : {e}", text_color="#e67e22"
                ))
            finally:
                self.after(0, lambda: self._hibp_btn.configure(
                    state="normal", text="🔍  Vérifier Have I Been Pwned"
                ))

        threading.Thread(target=run, daemon=True).start()
