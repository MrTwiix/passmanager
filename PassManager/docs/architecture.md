# Architecture de PassManager

## Vue d'ensemble des couches

```
┌─────────────────────────────────────────────────────────┐
│                    Interface graphique                    │
│   app/ui/app.py  auth_screen.py  main_screen.py  ...    │
│   Zéro logique métier. Passe UNIQUEMENT par vault.py.   │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                      app/vault.py                        │
│   VaultManager : CRUD, persistance, HIBP                │
│   Orchestre crypto.py et models.py                      │
└──────────────┬──────────────────────────┬───────────────┘
               │                          │
               ▼                          ▼
┌─────────────────────────┐  ┌───────────────────────────┐
│      app/crypto.py       │  │       app/models.py        │
│  Argon2id + AES-256-GCM  │  │  Dataclass Entry           │
│  Fonctions pures.        │  │  Exceptions métier         │
│  Zéro dépendance externe │  │                            │
└─────────────────────────┘  └───────────────────────────┘

app/generator.py — Module autonome, testé indépendamment
app/config.py    — Constantes centralisées, pas de magic numbers
```

## Règle absolue

> `app/ui/` ne connaît **pas** `app/crypto.py`.
>
> L'UI passe **exclusivement** par `app/vault.py`.

## Flux de chiffrement (sauvegarde)

```
Entrées en mémoire (list[Entry])
        │
        ▼
json.dumps() → bytes UTF-8
        │
        ▼
AES-256-GCM encrypt (clé en mémoire, nonce aléatoire)
        │
        ▼
{salt: b64, nonce: b64, ciphertext: b64}
        │
        ▼
~/.passmanager.vault (JSON sur disque)
```

## Flux de déchiffrement (ouverture)

```
~/.passmanager.vault
        │
        ▼
Lecture sel (16 bytes, public)
        │
        ▼
Argon2id(password, sel) → clé 256 bits  ← ~1 seconde intentionnel
        │
        ▼
AES-256-GCM decrypt + vérification tag GCM
  → InvalidTag si mauvais mot de passe
        │
        ▼
json.loads() → list[Entry] en mémoire
```

## Protocole HIBP (k-anonymat)

```
Mot de passe à vérifier
        │
        ▼
SHA-1 local → ex: 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8
        │
  5 chars   suffixe (ne quitte JAMAIS la machine)
  ┌─────┐   ┌─────────────────────────────────────────┐
  │5BAA6│   │1E4C9B93F3F0682250B6CF8331B7EE68FD8      │
  └──┬──┘   └─────────────────────────────────────────┘
     │
     ▼ HTTPS
api.pwnedpasswords.com/range/5BAA6
     │
     ▼
~500 suffixes renvoyés
     │
     ▼
Comparaison locale du suffixe → count de fuites
```
