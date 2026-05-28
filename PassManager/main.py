"""
main.py — Point d'entrée unique de PassManager.

Instancie l'application et lance la boucle principale Tkinter.

Utilisation :
    python main.py
"""

from app.ui.app import App


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
