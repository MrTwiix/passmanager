"""
widgets.py — Composants réutilisables de l'interface PassManager.

Chaque widget encapsule un comportement précis et peut être utilisé
dans n'importe quel écran sans duplication de code.

Composants :
  - StrengthBar   : barre de force colorée (score 0-4)
  - PasswordEntry : champ mot de passe avec bouton œil
  - StatusBar     : barre de statut avec auto-effacement
"""

import customtkinter as ctk

from app.config import STRENGTH_COLORS, STRENGTH_LABELS


class StrengthBar(ctk.CTkFrame):
    """
    Barre de progression colorée indiquant la force d'un mot de passe.

    Utilisation :
        bar = StrengthBar(parent)
        bar.set_score(3)  # 0-4 → couleur et label mis à jour automatiquement
    """

    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._label = ctk.CTkLabel(self, text="Force :", font=("", 12), anchor="w")
        self._label.pack(side="left", padx=(0, 8))

        self._bar = ctk.CTkProgressBar(self, width=140, height=10)
        self._bar.set(0)
        self._bar.pack(side="left", padx=(0, 8))

        self._level_label = ctk.CTkLabel(self, text="—", font=("", 12, "bold"), width=70, anchor="w")
        self._level_label.pack(side="left")

        self.set_score(0)

    def set_score(self, score: int) -> None:
        """
        Met à jour la barre avec un score de 0 (très faible) à 4 (très fort).

        Args:
            score: Entier entre 0 et 4.
        """
        score = max(0, min(4, score))
        color = STRENGTH_COLORS[score]
        label = STRENGTH_LABELS[score]

        self._bar.set((score + 1) / 5)
        self._bar.configure(progress_color=color)
        self._level_label.configure(text=label, text_color=color)

    def set_from_password(self, password: str) -> None:
        """Raccourci : calcule le score et met à jour la barre."""
        from app.generator import password_strength
        score, _, _ = password_strength(password)
        self.set_score(score)


class PasswordEntry(ctk.CTkFrame):
    """
    Champ de saisie de mot de passe avec bouton œil pour basculer
    entre affichage masqué (•••) et texte visible.

    Interface similaire à CTkEntry :
        entry.get()          → valeur courante
        entry.set("valeur")  → définit la valeur
        entry.configure(...)  → passe les kwargs à l'entrée interne
    """

    def __init__(self, parent, placeholder: str = "Mot de passe", **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._visible = False

        # Layout : entrée + bouton côte à côte
        self.columnconfigure(0, weight=1)

        self._entry = ctk.CTkEntry(
            self,
            show="•",
            placeholder_text=placeholder,
            height=36,
        )
        self._entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self._toggle_btn = ctk.CTkButton(
            self,
            text="👁",
            width=36,
            height=36,
            command=self._toggle_visibility,
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            text_color=("gray40", "gray60"),
        )
        self._toggle_btn.grid(row=0, column=1)

    def _toggle_visibility(self) -> None:
        self._visible = not self._visible
        self._entry.configure(show="" if self._visible else "•")
        self._toggle_btn.configure(text="🔒" if self._visible else "👁")

    def get(self) -> str:
        return self._entry.get()

    def set(self, value: str) -> None:
        self._entry.delete(0, "end")
        self._entry.insert(0, value)

    def bind(self, sequence, func, add="+"):
        """Redirige les bindings vers l'entrée interne."""
        return self._entry.bind(sequence, func, add)

    def configure(self, **kwargs):
        """Redirige configure vers l'entrée interne si applicable."""
        entry_keys = {"state", "placeholder_text", "font", "width", "height"}
        entry_kwargs = {k: v for k, v in kwargs.items() if k in entry_keys}
        if entry_kwargs:
            self._entry.configure(**entry_kwargs)
        else:
            super().configure(**kwargs)


class StatusBar(ctk.CTkLabel):
    """
    Barre de statut en bas de l'écran principal.

    Affiche un message temporaire ou permanent.

    Utilisation :
        status = StatusBar(parent)
        status.set("Mot de passe copié !")          # permanent
        status.set("Copié !", duration_ms=3000)     # auto-effacement après 3s
    """

    def __init__(self, parent, **kwargs) -> None:
        super().__init__(
            parent,
            text="",
            anchor="w",
            font=("", 12),
            text_color=("gray40", "gray60"),
            **kwargs,
        )
        self._after_id = None

    def set(self, message: str, duration_ms: int = 0) -> None:
        """
        Affiche un message dans la barre de statut.

        Args:
            message:     Texte à afficher.
            duration_ms: Si > 0, efface le message après ce délai (en ms).
        """
        # Annule le timer précédent si actif
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

        self.configure(text=message)

        if duration_ms > 0:
            self._after_id = self.after(duration_ms, lambda: self.configure(text=""))

    def clear(self) -> None:
        """Efface immédiatement le message."""
        self.set("")
