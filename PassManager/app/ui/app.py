"""
app.py — Classe racine de l'application PassManager.

Responsabilités :
  - Initialisation de CustomTkinter et de la fenêtre principale
  - Routage entre les écrans (auth ↔ main)
  - Gestion du timeout de verrouillage automatique
  - Persistance du thème (sombre / clair)
"""

import json
from pathlib import Path

import customtkinter as ctk

from app.config import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_THEME,
    LOCK_TIMEOUT,
    PREFS_PATH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from app.vault import VaultManager


class App(ctk.CTk):
    """
    Fenêtre racine de PassManager.

    Cycle :
      1. Affiche AuthScreen (création ou déverrouillage)
      2. Après authentification → affiche MainScreen
      3. Sur verrouillage → détruit MainScreen, réaffiche AuthScreen
    """

    def __init__(self) -> None:
        # Chargement des préférences (thème) avant l'init CTk
        prefs = self._load_prefs()
        ctk.set_appearance_mode(prefs.get("theme", DEFAULT_THEME))
        ctk.set_default_color_theme("blue")

        super().__init__()

        self.title(f"{APP_NAME} {APP_VERSION}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.geometry(f"{WINDOW_MIN_WIDTH}x{WINDOW_MIN_HEIGHT}")

        # Centrage de la fenêtre au lancement
        self._center_window()

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Vault partagé entre tous les écrans
        self._vm = VaultManager()
        self._current_screen = None
        self._lock_after_id = None
        self._lock_timeout = LOCK_TIMEOUT
        self._prefs = prefs

        # Barre de menu (thème)
        self._build_menu()

        # Affichage initial
        self._show_auth()

    # ─── Routage ──────────────────────────────────────────────────────────────

    def _show_auth(self) -> None:
        """Affiche l'écran d'authentification."""
        self._cancel_lock_timer()
        self._destroy_current_screen()

        from app.ui.auth_screen import AuthScreen
        self._current_screen = AuthScreen(
            self,
            vault_manager=self._vm,
            on_success=self._show_main,
        )
        self._current_screen.grid(row=0, column=0, sticky="nsew")

    def _show_main(self) -> None:
        """Affiche l'écran principal après authentification."""
        self._destroy_current_screen()

        from app.ui.main_screen import MainScreen
        self._current_screen = MainScreen(
            self,
            vault_manager=self._vm,
            on_lock=self._lock,
        )
        self._current_screen.grid(row=0, column=0, sticky="nsew")

        # Lance le timer de verrouillage automatique
        self._reset_lock_timer()

        # Réinitialise le timer sur toute interaction utilisateur
        self.bind_all("<Motion>",  lambda _: self._reset_lock_timer(), add="+")
        self.bind_all("<Key>",     lambda _: self._reset_lock_timer(), add="+")
        self.bind_all("<Button>",  lambda _: self._reset_lock_timer(), add="+")

    def _lock(self) -> None:
        """Verrouille le vault et retourne à l'écran d'authentification."""
        self._vm.lock()
        self._show_auth()

    # ─── Verrouillage automatique ─────────────────────────────────────────────

    def _reset_lock_timer(self) -> None:
        """Remet le compteur d'inactivité à zéro."""
        self._cancel_lock_timer()
        if self._lock_timeout is not None:
            self._lock_after_id = self.after(
                self._lock_timeout * 1000,
                self._auto_lock,
            )

    def _cancel_lock_timer(self) -> None:
        if self._lock_after_id is not None:
            self.after_cancel(self._lock_after_id)
            self._lock_after_id = None

    def _auto_lock(self) -> None:
        """Déclenché après timeout d'inactivité."""
        if self._vm.is_unlocked:
            self._lock()

    # ─── Menu (thème) ─────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        """Ajoute un bouton de bascule thème en haut à droite via un frame overlay."""
        # On ne peut pas utiliser tk.Menu facilement avec CTk → bouton flottant
        # Le menu thème est dans la barre de titre de MainScreen
        pass

    def toggle_theme(self) -> None:
        """Bascule entre thème sombre et clair, et persiste le choix."""
        current = ctk.get_appearance_mode().lower()
        new_theme = "light" if current == "dark" else "dark"
        ctk.set_appearance_mode(new_theme)
        self._prefs["theme"] = new_theme
        self._save_prefs()

    # ─── Préférences ──────────────────────────────────────────────────────────

    def _load_prefs(self) -> dict:
        try:
            return json.loads(PREFS_PATH.read_text())
        except Exception:
            return {"theme": DEFAULT_THEME}

    def _save_prefs(self) -> None:
        try:
            PREFS_PATH.write_text(json.dumps(self._prefs, indent=2))
        except Exception:
            pass

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _center_window(self) -> None:
        """Centre la fenêtre sur l'écran au lancement."""
        self.update_idletasks()
        w = WINDOW_MIN_WIDTH
        h = WINDOW_MIN_HEIGHT
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _destroy_current_screen(self) -> None:
        if self._current_screen is not None:
            self._current_screen.destroy()
            self._current_screen = None
