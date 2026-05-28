"""
auth_screen.py — Écran d'authentification de PassManager.

Deux modes selon l'état du vault :
  - Création  : premier lancement, saisie + confirmation du mot de passe maître
  - Déverrouillage : vault existant, saisie du mot de passe maître

La dérivation Argon2id (~1 seconde) s'exécute dans un thread de fond
pour ne pas figer l'interface graphique pendant le calcul.
"""

import threading
from typing import Callable

import customtkinter as ctk

from app.models import VaultNotFoundError, WrongPasswordError
from app.ui.widgets import PasswordEntry
from app.vault import VaultManager
from app.config import MIN_MASTER_PASSWORD_LEN, APP_NAME


class AuthScreen(ctk.CTkFrame):
    """
    Écran d'authentification (création ou déverrouillage du vault).

    Args:
        parent:        Widget parent.
        vault_manager: Instance partagée de VaultManager.
        on_success:    Callback appelé après une authentification réussie.
    """

    def __init__(
        self,
        parent,
        vault_manager: VaultManager,
        on_success: Callable,
        **kwargs,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._vm = vault_manager
        self._on_success = on_success
        self._is_creation_mode = not vault_manager.vault_exists

        self._build_ui()

    # ─── Construction de l'UI ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construit l'interface selon le mode (création / déverrouillage)."""
        # Centrage vertical
        self.rowconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        # Carte centrale
        card = ctk.CTkFrame(self, width=400, corner_radius=16)
        card.grid(row=1, column=0)
        card.columnconfigure(0, weight=1)

        # Logo / titre
        logo = ctk.CTkLabel(
            card,
            text="🔐",
            font=("", 48),
        )
        logo.grid(row=0, column=0, pady=(32, 4))

        title = ctk.CTkLabel(
            card,
            text=APP_NAME,
            font=("", 28, "bold"),
        )
        title.grid(row=1, column=0, pady=(0, 4))

        subtitle_text = (
            "Créez votre coffre-fort" if self._is_creation_mode
            else "Déverrouillez votre coffre-fort"
        )
        subtitle = ctk.CTkLabel(
            card,
            text=subtitle_text,
            font=("", 14),
            text_color=("gray40", "gray60"),
        )
        subtitle.grid(row=2, column=0, pady=(0, 24))

        # Champ mot de passe
        ctk.CTkLabel(card, text="Mot de passe", font=("", 13)).grid(
            row=3, column=0, sticky="w", padx=32
        )
        self._password_entry = PasswordEntry(card, placeholder="Entrez votre mot de passe")
        self._password_entry.grid(row=4, column=0, sticky="ew", padx=32, pady=(4, 0))
        self._password_entry.bind("<Return>", lambda _: self._on_submit())

        # Champ confirmation (mode création uniquement)
        if self._is_creation_mode:
            ctk.CTkLabel(card, text="Confirmation", font=("", 13)).grid(
                row=5, column=0, sticky="w", padx=32, pady=(12, 0)
            )
            self._confirm_entry = PasswordEntry(card, placeholder="Confirmez votre mot de passe")
            self._confirm_entry.grid(row=6, column=0, sticky="ew", padx=32, pady=(4, 0))
            self._confirm_entry.bind("<Return>", lambda _: self._on_submit())

            hint = ctk.CTkLabel(
                card,
                text=f"Minimum {MIN_MASTER_PASSWORD_LEN} caractères",
                font=("", 11),
                text_color=("gray50", "gray55"),
            )
            hint.grid(row=7, column=0, sticky="w", padx=32, pady=(4, 0))

        # Label d'erreur (vide par défaut, visible si erreur)
        self._error_label = ctk.CTkLabel(
            card,
            text="",
            font=("", 12),
            text_color="#e74c3c",
            wraplength=320,
        )
        self._error_label.grid(row=8, column=0, pady=(8, 0))

        # Bouton d'action
        btn_text = "Créer le vault" if self._is_creation_mode else "Déverrouiller"
        self._submit_btn = ctk.CTkButton(
            card,
            text=btn_text,
            height=40,
            font=("", 14, "bold"),
            command=self._on_submit,
        )
        self._submit_btn.grid(row=9, column=0, sticky="ew", padx=32, pady=(16, 32))

    # ─── Logique ──────────────────────────────────────────────────────────────

    def _on_submit(self) -> None:
        """Déclenché au clic sur le bouton ou à la pression de Entrée."""
        password = self._password_entry.get()
        self._error_label.configure(text="")

        # ── Validation locale (avant de lancer le thread) ──────────────────
        if self._is_creation_mode:
            confirm = self._confirm_entry.get()

            if len(password) < MIN_MASTER_PASSWORD_LEN:
                self._show_error(
                    f"Le mot de passe doit contenir au moins {MIN_MASTER_PASSWORD_LEN} caractères."
                )
                return

            if password != confirm:
                self._show_error("Les mots de passe ne correspondent pas.")
                return

        elif not password:
            self._show_error("Veuillez saisir votre mot de passe.")
            return

        # ── Dérivation Argon2id en thread de fond (~1s) ─────────────────────
        self._set_loading(True)
        thread = threading.Thread(
            target=self._auth_thread,
            args=(password,),
            daemon=True,
        )
        thread.start()

    def _auth_thread(self, password: str) -> None:
        """
        Exécuté dans un thread de fond pour ne pas bloquer l'UI.
        Appelle after() pour repasser dans le thread principal.
        """
        try:
            if self._is_creation_mode:
                self._vm.create(password)
            else:
                self._vm.unlock(password)
            # Succès → callback dans le thread principal
            self.after(0, self._on_success)

        except WrongPasswordError:
            self.after(0, lambda: self._show_error("Mot de passe incorrect. Réessayez."))
        except VaultNotFoundError:
            self.after(0, lambda: self._show_error("Vault introuvable. Redémarrez l'application."))
        except Exception as e:
            self.after(0, lambda: self._show_error(f"Erreur inattendue : {e}"))
        finally:
            self.after(0, lambda: self._set_loading(False))

    def _set_loading(self, loading: bool) -> None:
        """Active ou désactive l'indicateur de chargement."""
        if loading:
            self._submit_btn.configure(text="Chargement…", state="disabled")
        else:
            btn_text = "Créer le vault" if self._is_creation_mode else "Déverrouiller"
            self._submit_btn.configure(text=btn_text, state="normal")

    def _show_error(self, message: str) -> None:
        """Affiche un message d'erreur sous les champs."""
        self._error_label.configure(text=message)
