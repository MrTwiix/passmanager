# 🔐 PassManager

Gestionnaire de mots de passe desktop **entièrement local**, développé en Python 3.12.

Projet personnel — Tom Jaffelin · EPITA Lyon · Cycle ingénieur (2e année)

---

## Fonctionnalités

- **Stockage chiffré** : AES-256-GCM + dérivation de clé Argon2id
- **Génération sécurisée** : module `secrets` (cryptographiquement sûr)
- **Audit de force** : entropie Shannon en temps réel
- **Vérification HIBP** : protocole k-anonymat (le mot de passe ne quitte jamais la machine)
- **Copie sécurisée** : effacement automatique du presse-papier après 30s
- **Verrouillage auto** : après N minutes d'inactivité
- **GUI moderne** : CustomTkinter, thème sombre/clair

---

## Installation

```bash
# Cloner le dépôt
git clone https://github.com/tom-jaffelin/passmanager.git
cd passmanager

# Créer et activer un environnement virtuel
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
python main.py
```

**Python 3.12 requis.** Testé sur Windows 11, macOS 14, Ubuntu 22.04.

---

## Lancer les tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
pytest tests/ --cov=app --cov-report=term-missing
```

---

## Architecture

```
PassManager/
├── main.py                  # Point d'entrée unique
├── app/
│   ├── config.py            # Constantes centralisées (Argon2, AES, timeouts…)
│   ├── models.py            # Dataclass Entry + exceptions métier
│   ├── crypto.py            # Argon2id + AES-256-GCM (module autonome)
│   ├── vault.py             # VaultManager : CRUD + persistance + HIBP
│   ├── generator.py         # Génération + analyse de force (module autonome)
│   └── ui/
│       ├── app.py           # Fenêtre racine, routage, verrouillage auto
│       ├── auth_screen.py   # Écran d'authentification (création / déverrouillage)
│       ├── main_screen.py   # Écran principal (liste, recherche, actions)
│       ├── entry_card.py    # Widget carte d'entrée
│       ├── entry_dialog.py  # Formulaire ajout/édition + HIBP
│       ├── generator_dialog.py  # Générateur de mots de passe
│       └── widgets.py       # Composants réutilisables (StrengthBar, PasswordEntry…)
├── tests/
│   ├── test_crypto.py
│   ├── test_vault.py
│   ├── test_generator.py
│   └── test_models.py
└── docs/
    └── architecture.md      # Diagrammes ASCII des flux de données
```

**Règle absolue** : `app/ui/` ne connaît pas `app/crypto.py`. L'UI passe exclusivement par `vault.py`.

---

## Choix cryptographiques

### Argon2id (dérivation de clé)

| Paramètre | Valeur | Pourquoi |
|-----------|--------|----------|
| Algorithme | Argon2id | Gagnant Password Hashing Competition 2015. Résistant GPU (mémoire) ET side-channel (mode hybrid). Recommandé OWASP 2024. |
| `time_cost` | 3 | ~1 seconde sur machine standard — ralentit le brute-force sans gêner l'utilisateur. |
| `memory_cost` | 64 MB | Rend les attaques GPU massivement parallèles impraticables économiquement. |
| `hash_len` | 32 bytes | Taille exacte d'une clé AES-256. Zéro troncature, zéro expansion. |
| `salt` | 16 bytes aléatoires | Généré via `os.urandom()`. Unique par vault. Stocké en clair (public). |

**Pourquoi pas bcrypt ?** bcrypt est limité à 72 caractères (troncature silencieuse) et ne paramètre pas la mémoire — vulnérable aux attaques GPU modernes.

### AES-256-GCM (chiffrement du vault)

| Paramètre | Valeur | Pourquoi |
|-----------|--------|----------|
| Mode | GCM (AEAD) | Chiffre ET authentifie en une passe. Toute modification du fichier vault invalide le tag. |
| Clé | 256 bits (directement d'Argon2id) | Jamais stockée sur disque. Existe en mémoire pendant la session uniquement. |
| Nonce | 12 bytes, regénéré à chaque sauvegarde | `os.urandom()` — jamais réutilisé. |
| Tag | 16 bytes | Vérification obligatoire au déchiffrement — garantit intégrité + authenticité. |

**Pourquoi pas AES-CBC ?** CBC chiffre mais n'authentifie pas — padding oracle attacks possibles. GCM est AEAD : toute modification du ciphertext est détectée immédiatement.

### Format du fichier vault

```json
{
  "salt":       "<base64 — 16 bytes, généré à la création>",
  "nonce":      "<base64 — 12 bytes, regénéré à chaque sauvegarde>",
  "ciphertext": "<base64 — JSON des entrées chiffré AES-256-GCM>"
}
```

### Vérification HIBP (k-anonymat)

1. SHA-1 local du mot de passe
2. Envoi des **5 premiers caractères hex** uniquement à l'API
3. L'API renvoie ~500 suffixes correspondants
4. Comparaison locale — ni le mot de passe ni son hash complet ne quittent la machine

---

## Licence

MIT — voir [LICENSE](LICENSE)
