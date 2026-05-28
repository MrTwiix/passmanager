"""
generator_dialog.py — Fenêtre de génération de mots de passe.

Slider longueur, cases options (majuscules, chiffres, symboles),
bouton régénérer, barre de force, boutons Copier et Utiliser.

Le bouton "Utiliser" injecte le mot de passe directement dans le champ
du formulaire parent (callback on_use).
"""

from typing import Callable, Optional

import customtkinter as ctk

from app.config import DEFAULT_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from app.generator import generate_password
from app.ui.widgets import StrengthBar


class GeneratorDialog(ctk.CTkToplevel):
    """
    Fenêtre modale de génération de mots de passe.

    Args:
        parent:   Widget parent.
        on_use:   Callback(password: str) appelé quand l'utilisateur clique "Utiliser".
                  Si None, le bouton "Utiliser" est masqué.
    """

    def __init__(self, parent, on_use: Optional[Callable[[str], None]] = None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self._on_use = on_use
        self._generated_password = ""

        self.title("Générateur de mots de passe")
        self.geometry("460x420")
        self.resizable(False, False)
        self.after(100, self.grab_set)

        self._build_ui()
        self._regenerate()  # Génère un mot de passe dès l'ouverture

    # ─── Construction de l'UI ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)

        # Titre
        ctk.CTkLabel(
            self, text="Générateur", font=("", 20, "bold")
        ).grid(row=0, column=0, pady=(24, 4))

        ctk.CTkLabel(
            self,
            text="Génération cryptographiquement sécurisée (module secrets)",
            font=("", 11),
            text_color=("gray45", "gray60"),
        ).grid(row=1, column=0, pady=(0, 16))

        # Zone d'affichage du mot de passe généré
        pwd_frame = ctk.CTkFrame(self, corner_radius=10)
        pwd_frame.grid(row=2, column=0, sticky="ew", padx=24)
        pwd_frame.columnconfigure(0, weight=1)

        self._pwd_label = ctk.CTkLabel(
            pwd_frame,
            text="",
            font=("Courier New", 16, "bold"),
            wraplength=360,
            justify="center",
        )
        self._pwd_label.grid(row=0, column=0, padx=16, pady=16)

        # Barre de force
        self._strength_bar = StrengthBar(self)
        self._strength_bar.grid(row=3, column=0, pady=(8, 4))

        # Slider de longueur
        slider_frame = ctk.CTkFrame(self, fg_color="transparent")
        slider_frame.grid(row=4, column=0, sticky="ew", padx=24, pady=(8, 0))
        slider_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(slider_frame, text="Longueur :", font=("", 13)).grid(row=0, column=0, padx=(0, 8))

        self._length_var = ctk.IntVar(value=DEFAULT_PASSWORD_LENGTH)
        self._length_label = ctk.CTkLabel(slider_frame, text=str(DEFAULT_PASSWORD_LENGTH), width=30, font=("", 13, "bold"))
        self._length_label.grid(row=0, column=2, padx=(8, 0))

        self._slider = ctk.CTkSlider(
            slider_frame,
            from_=MIN_PASSWORD_LENGTH,
            to=MAX_PASSWORD_LENGTH,
            variable=self._length_var,
            command=self._on_slider_change,
            number_of_steps=MAX_PASSWORD_LENGTH - MIN_PASSWORD_LENGTH,
        )
        self._slider.grid(row=0, column=1, sticky="ew")

        # Cases à cocher pour les options
        options_frame = ctk.CTkFrame(self, fg_color="transparent")
        options_frame.grid(row=5, column=0, pady=(12, 0))

        self._upper_var   = ctk.BooleanVar(value=True)
        self._digits_var  = ctk.BooleanVar(value=True)
        self._symbols_var = ctk.BooleanVar(value=True)

        for col, (text, var) in enumerate([
            ("Majuscules", self._upper_var),
            ("Chiffres",   self._digits_var),
            ("Symboles",   self._symbols_var),
        ]):
            cb = ctk.CTkCheckBox(
                options_frame,
                text=text,
                variable=var,
                command=self._regenerate,
                font=("", 13),
            )
            cb.grid(row=0, column=col, padx=12)

        # Bouton régénérer
        ctk.CTkButton(
            self,
            text="↻  Régénérer",
            height=36,
            font=("", 13),
            fg_color="transparent",
            border_width=1,
            command=self._regenerate,
        ).grid(row=6, column=0, pady=(16, 0))

        # Boutons d'action
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=7, column=0, pady=(12, 24))

        ctk.CTkButton(
            btn_frame,
            text="📋  Copier",
            width=140,
            height=40,
            font=("", 13, "bold"),
            command=self._copy,
        ).grid(row=0, column=0, padx=8)

        if self._on_use is not None:
            ctk.CTkButton(
                btn_frame,
                text="✓  Utiliser",
                width=140,
                height=40,
                font=("", 13, "bold"),
                fg_color="#2ecc71",
                hover_color="#27ae60",
                text_color="white",
                command=self._use,
            ).grid(row=0, column=1, padx=8)

    # ─── Logique ──────────────────────────────────────────────────────────────

    def _on_slider_change(self, value) -> None:
        """Appelé à chaque déplacement du slider."""
        length = int(value)
        self._length_label.configure(text=str(length))
        self._regenerate()

    def _regenerate(self) -> None:
        """Génère un nouveau mot de passe et met à jour l'affichage."""
        length  = int(self._length_var.get())
        upper   = self._upper_var.get()
        digits  = self._digits_var.get()
        symbols = self._symbols_var.get()

        pwd = generate_password(
            length=length,
            use_upper=upper,
            use_digits=digits,
            use_symbols=symbols,
        )
        self._generated_password = pwd
        self._pwd_label.configure(text=pwd)
        self._strength_bar.set_from_password(pwd)

    def _copy(self) -> None:
        """Copie le mot de passe dans le presse-papier."""
        try:
            import pyperclip
            pyperclip.copy(self._generated_password)
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(self._generated_password)

    def _use(self) -> None:
        """Injecte le mot de passe dans le formulaire parent et ferme la fenêtre."""
        if self._on_use:
            self._on_use(self._generated_password)
        self.destroy()
