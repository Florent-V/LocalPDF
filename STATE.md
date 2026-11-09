# STATE.md — État du projet LocalPDF

## But du projet

Alternative locale, open-source et "Privacy-First" à des outils comme iLovePDF.
L'utilisateur manipule, convertit et analyse des PDF en local, sans que ses
données ne quittent son ordinateur.

## Règles architecturales

1. **Frontend** : Nuxt 3 (Vue 3) + Nuxt UI + TailwindCSS.
2. **Backend** : Python 3.12+ / FastAPI.
3. **Persistance** : fichiers traités en mémoire ou en dossier temporaire (UUID par
   job), purge TTL 30 min. Seul état durable : les sessions OAuth (SQLite, `/data`).
4. **Déploiement** : 100% Docker via `docker-compose`.
5. **Commandes** : orchestration exclusive via `Makefile`.

## Avancement — Phases 1 à 4 : terminées

Toutes les fonctionnalités prévues sont implémentées et validées :

- **Phase 1 — Core** : Docker/Makefile, socle Nuxt 3/FastAPI, CORS, upload
  drag & drop, fusionner, diviser, organiser.
- **Phase 2 — Modification & Sécurité** : rotation, filigrane, mot de passe
  (protéger/déverrouiller), censure (redaction), remplissage de formulaire.
- **Phase 3 — Conversions** : images ↔ PDF, Office → PDF (LibreOffice
  headless), PDF → Word (pdf2docx).
- **Phase 4 — IA** : architecture provider modulaire (Ollama local / OpenAI /
  Anthropic), PDF → Markdown, résumé, traduction, chat PDF (RAG basique).
- **Post-Phase 4** : feature Markdown → PDF ajoutée (commit `a5d01a32` et
  historique associé), avec durcissement sécurité (SSRF/local-file-read
  bloqués via `link_callback`, cap taille fichier 20MB, tests dédiés).

## Authentification

Le backend FastAPI est le client OAuth (BFF), module `backend/app/auth/` (spec
`docs/authentification.md`, version `AUTH_MODULE_VERSION`). Front statique
(`nuxt generate`, `ssr: false`) servi par Caddy ; session côté serveur (SQLite),
cookie opaque. Voir `docs/deploiement.md`.

## Structure des dossiers

```
pdf-tools/
├── .env.example                     # template config ports/environnement
├── Makefile                         # dev (make dev/up), prod (make prod-*) : identique à ImageConverter
├── docker-compose.yml                # variables via .env, limite mémoire backend 2G
├── README.md
├── STATE.md
├── backend/
│   ├── Dockerfile                    # python:3.12-slim + LibreOffice + fontconfig
│   ├── pyproject.toml, uv.lock       # deps (uv)
│   └── app/
│       ├── main.py                   # routers organize/modify/security/forms/convert/ai
│       ├── core/{config,exceptions,tempfiles}.py
│       ├── routers/{organize,modify,security,forms,convert,ai}.py
│       ├── services/{organize,modify,security,forms,convert}.py + ai/(service.py + providers/)
│       ├── schemas/{organize,modify,security,forms,convert,ai}.py
│       └── tests/{test_main,test_organize,test_phase2,test_phase3,test_convert}.py
└── frontend/
    ├── Dockerfile
    ├── nuxt.config.ts
    └── app/
        ├── app.vue
        ├── components/
        │   ├── layout/{AppHeader,AppSidebar,AppFooter,AppMobileNav}.vue
        │   ├── pdf/                   # nouveau : remplace PdfThumbnailGrid.vue
        │   └── ToolCard.vue
        ├── composables/{useApi,useJobPolling,useAiConfig,usePdfRenderer}.ts
        └── pages/
            ├── index.vue
            ├── parametres.vue
            └── outils/
                ├── fusionner, diviser, organiser            (Phase 1)
                ├── pivoter, filigrane, proteger,
                │   deverrouiller, censurer, formulaire      (Phase 2)
                ├── images-vers-pdf, pdf-vers-images,
                │   office-vers-pdf, pdf-vers-word           (Phase 3)
                ├── pdf-vers-markdown, resume, traduction,
                │   markdown-vers-pdf, chat                  (Phase 4)
```

## Ports

- Backend : `8010` en dev (`BACKEND_PORT`, réseau `host`) ; `8000` dans le conteneur de prod, non publié
- Frontend : `3010` en dev (`FRONTEND_PORT`) ; en prod Caddy sur `127.0.0.1:${REMOTE_FRONTEND_PORT}`

## Conventions

- Endpoints API : `/api/v1/<catégorie>/<action>`, catégories : `organize`,
  `modify`, `security`, `forms`, `convert`, `ai`.
- Mono-étape : `POST` multipart → `FileResponse`/`StreamingResponse`,
  suppression via `BackgroundTasks`.
- Multi-étape : `POST /jobs/{id}` → `PATCH /jobs/{id}` →
  `GET /jobs/{id}/download` → `DELETE /jobs/{id}`.
- Configuration IA : stockée dans le `localStorage` du navigateur, transmise à
  chaque requête, jamais persistée côté serveur.
- Clés API jamais stockées côté serveur.

## État du backend

- FastAPI 0.115.0, Uvicorn 0.32.0.
- Librairies PDF : PyMuPDF 1.24.13, pypdf 5.1.0, pikepdf 9.4.0.
- Conversion : Pillow, pdf2docx 0.5.8, LibreOffice headless, xhtml2pdf
  (markdown→PDF, avec `link_callback` bloquant réseau/fichiers locaux).
- IA : pymupdf4llm, ollama, openai, anthropic ; architecture provider modulaire.
- Tests : 20 passés (dont 8 sur `convert.py`, incluant 2 tests sécurité/DoS
  markdown→PDF).

## État du frontend

- Nuxt 3.5.1, Nuxt UI 4.10.0, TailwindCSS 4.3.3.
- pnpm 11.17.0, Vitest + happy-dom (1 test passé).
- Toutes les pages des Phases 1 à 4 + markdown-vers-pdf créées.

## Validation (dernier commit sur `main`)

- Tests backend : 20 passés · Tests frontend : 1 passé.
- Lint backend (ruff) : OK · Lint frontend (eslint) : OK.
- Build frontend : OK · Docker build : OK.
- `docker compose up` : backend health OK (`/health`).

## Travail en cours (non commité sur `main`)

Deux chantiers ouverts en parallèle, visibles dans `git status` :

1. **Refonte UI/UX du frontend** : nouveaux composants (`AppMobileNav.vue`,
   dossier `components/pdf/`, composable `usePdfRenderer.ts`), suppression de
   `PdfThumbnailGrid.vue` (remplacé), retouches sur layout (header/sidebar/
   footer), `main.css`, `app.config.ts`, et quasi toutes les pages `outils/*`.
   → à finaliser, tester dans le navigateur (golden path + edge cases par
   page) et commiter.
2. **Refactor config env/Docker** : `.env.example` + `.env` créés,
   `docker-compose.yml` passé en substitution de variables, `Makefile` avec
   `up` (sans rebuild) / `up-build` (avec rebuild) séparés, correction du
   endpoint `organize.py` + test associé.
   → à valider avec `make up-build` puis `docker compose ps` et un curl sur
   `localhost:8000`/`localhost:3000`, puis commiter.

Point de vigilance connu : `make restart` utilise `docker compose restart`,
qui ne réattache pas les réseaux Docker (cause du bug port 8080 vs 8000
précédemment observé).

## Notes importantes

- Modèle Ollama par défaut : `llama3.1:8b`, modifiable dans `/parametres`.
- Les features IA nécessitent un provider configuré (Ollama local ou API
  tierce).
