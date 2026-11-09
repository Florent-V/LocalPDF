# LocalPDF

**L'alternative open-source et privacy-first aux outils PDF en ligne** (iLovePDF, SmallPDF, etc.).

Pas de compte, pas de cloud tiers, pas de base de données, pas de traçage. Le traitement a lieu sur un backend Python que **vous** faites tourner — en local sur votre machine, ou auto-hébergé sur votre propre serveur.

> 🇫🇷 Interface entièrement en français · 🔒 100% privé — 0% de données conservées · 🐳 Prêt en une commande

---

## Pourquoi LocalPDF ?

| | Outils en ligne classiques | LocalPDF |
|---|---|---|
| Vos fichiers | Uploadés sur un serveur tiers, souvent conservés | Traités par **votre** backend, jamais par un tiers |
| Confidentialité | Dépend des CGU du service | Aucune base de données, aucun fichier persistant (voir ci-dessous) |
| Coût | Freemium, limites, pub | Gratuit, open-source, illimité |
| Hors-ligne | Impossible | Oui en local (hors fonctions IA distantes) |
| IA | Rarement proposée | Ollama local, ou clé API perso (OpenAI/Anthropic) |

### ⚠️ Ce que "privacy-first" veut dire exactement

LocalPDF n'a **pas** de frontend qui traite les PDF dans le navigateur — le traitement (fusion, rotation, filigrane, censure…) se fait côté backend Python (FastAPI + PyMuPDF/pypdf/pikepdf). Ce qui est garanti, et ce qui ne l'est pas, dépend de qui héberge ce backend :

- **Vous faites tourner le projet en local** (`make up` sur votre poste) → traitement **100% local** : le fichier ne sort jamais de votre machine, il transite juste entre le conteneur frontend et le conteneur backend, tous deux chez vous.
- **Vous déployez LocalPDF sur votre propre serveur** (pour vous ou pour des tiers) → ce n'est plus "local" au sens strict : les fichiers transitent par votre infrastructure. Mais c'est toujours **100% privé** dans le sens où :
  - aucune base de données ne stocke quoi que ce soit ;
  - aucun fichier n'est écrit de façon permanente — traitement en mémoire ou fichier temporaire, supprimé immédiatement après réponse (ou après TTL de 30 min pour les jobs multi-étapes) ;
  - aucune donnée n'est partagée avec un tiers.
- **Fonctions IA avec OpenAI ou Anthropic** (résumé, traduction, chat) → le **contenu textuel extrait** du PDF est envoyé à l'API du provider choisi (pas le fichier PDF brut). Ce n'est ni local, ni "zéro tiers" — c'est un compromis explicite que vous activez vous-même dans `/parametres`. Choisissez **Ollama** pour rester 100% local même sur les fonctions IA.

En clair : si vous hébergez publiquement cette application, ne présentez pas ça comme "vos fichiers ne quittent jamais votre appareil" à vos utilisateurs — dites plutôt "vos fichiers ne sont jamais stockés ni partagés avec un tiers".

## Fonctionnalités

18 outils PDF, organisés en 4 familles :

### 📑 Organisation
- **Fusionner** plusieurs PDF en un seul
- **Diviser** un PDF (plage de pages ou une page par fichier)
- **Organiser** : réordonner, supprimer et faire pivoter des pages via un aperçu visuel

### ✏️ Modification & Sécurité
- **Filigrane** : texte ou image, positionnement haut/centre/bas ou diagonal
- **Protéger** : chiffrement par mot de passe utilisateur/propriétaire
- **Déverrouiller** : suppression de la protection par mot de passe
- **Censurer** : masquage irréversible de zones ou de texte
- **Formulaires** : détection et remplissage des champs d'un PDF interactif

### 🔄 Conversions
- **Images → PDF** (JPG/PNG/WEBP) et **PDF → Images**
- **Markdown → PDF** et **PDF → Markdown** (extraction structurée : titres, listes, tableaux)
- **Office → PDF** (DOCX/XLSX/PPTX, via LibreOffice headless)
- **PDF → Word** (DOCX)

### 🤖 Intelligence Artificielle (privacy-first)
- **Résumé** et **Traduction** du contenu d'un PDF
- **Chat avec le PDF** via un mini-RAG en mémoire
- Choix du provider dans `/parametres` : **Ollama** (100% local), **OpenAI** ou **Anthropic**
- Aucune clé API stockée côté serveur — elle reste dans votre navigateur

## Stack technique

```
Frontend   Nuxt 3 · Nuxt UI · Tailwind CSS · pnpm
Backend    FastAPI (Python 3.12+) · PyMuPDF · pypdf · pikepdf · pymupdf4llm
Stockage   Aucune base de données — traitement en mémoire ou fichiers temporaires auto-purgés
Infra      Docker + docker-compose · Makefile · GitHub Actions
```

Aucune persistance : les traitements simples créent un dossier temporaire jetable ; les flux multi-étapes (organiser, censurer) utilisent un job en mémoire avec TTL de 30 minutes.

## Démarrage rapide

### Avec Docker (recommandé)

```bash
make up
```

- Application → http://localhost:3010 (port `FRONTEND_PORT`) — connexion via le serveur OAuth, voir [docs/deploiement.md](docs/deploiement.md)
- L'API (client OAuth) écoute sur `BACKEND_PORT` (8010) ; en production elle n'est joignable que par Caddy

### Développement natif

**Backend**
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
pnpm install
pnpm dev
```

### Commandes Makefile

| Commande | Description |
|----------|-------------|
| `make up` | Démarre les services en arrière-plan |
| `make down` | Arrête les services |
| `make logs` | Logs des deux services |
| `make build` | Reconstruit les images Docker |
| `make test` | Tests backend + frontend |
| `make lint` | Linters backend + frontend |
| `make prod-deploy` | Mise à jour en production (voir [docs/deploiement.md](docs/deploiement.md)) |
| `make clean` | Arrête et nettoie volumes / caches |

## Utiliser Ollama en local (IA 100% offline)

1. Installez [Ollama](https://ollama.com/) sur la machine hôte.
2. Téléchargez un modèle :
   ```bash
   ollama pull llama3.1:8b
   ```
3. Assurez-vous qu'Ollama écoute sur `0.0.0.0:11434` (utile avec Docker).
4. Dans `/parametres`, choisissez *Ollama* comme provider (URL par défaut : `http://host.docker.internal:11434`).

## Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `MAX_UPLOAD_MB` | `200` | Taille maximale d'upload (Mo) |
| `TEMP_TTL_MINUTES` | `30` | TTL des jobs multi-étapes |
| `OAUTH_ISSUER`, `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, `PUBLIC_ORIGIN` | — | Authentification (client OAuth par découverte), voir `.env.example` et [docs/deploiement.md](docs/deploiement.md) |

## API

Documentation FastAPI (`/docs`) : non routée par Caddy en production ; toutes les routes `/api/*` exigent une session.

Principaux préfixes de routes :

| Préfixe | Domaine |
|---|---|
| `/api/v1/organize` | Fusion, division, réorganisation + rotation |
| `/api/v1/modify` | Rotation, filigrane |
| `/api/v1/security` | Protection, déverrouillage, censure |
| `/api/v1/forms` | Inspection et remplissage de formulaires |
| `/api/v1/convert` | Images, Office, Markdown, Word |
| `/api/v1/ai` | Markdown, résumé, traduction, chat |

## Qualité & CI

- **Tests** : `pytest` (backend), `vitest` (frontend)
- **Lint** : `ruff` (backend), `eslint` (frontend)
- **CI** : GitHub Actions (`.github/workflows/ci.yml`) — lint + tests backend, lint + tests + build frontend sur chaque push/PR

## Licence

MIT — à confirmer par l'auteur.
