# Déploiement et authentification

LocalPDF est protégé par le serveur OAuth (dépôt `OAuth-serveur`) : sans compte autorisé sur l'application, rien
n'est accessible. Ce document couvre l'architecture, le test en local avec le serveur OAuth de dev, le premier
déploiement et les mises à jour. La spécification suivie est `docs/authentification.md`.
La procédure complète de mise en production et le déploiement continu sont dans
[mise-en-production.md](mise-en-production.md).

## Architecture

```
Navigateur ──cookie __Host-session (opaque)──▶ Caddy ─┬─ /*      → fichiers statiques (nuxt generate, ssr: false)
                                                      ├─ /auth/* → FastAPI
                                                      └─ /api/*  → FastAPI (session vérifiée avant lecture du corps)
FastAPI ──découverte, code + PKCE, refresh, révocation──▶ Serveur OAuth
Serveur OAuth ──logout_token (back-channel)──▶ FastAPI /auth/backchannel-logout
```

- **Le backend FastAPI est le client OAuth (BFF).** Le front est une application statique : pas de Node en production,
  pas de secret ni de jeton dans le navigateur.
- La session est stockée côté serveur (SQLite, volume `api-data`, fichier `/data/sessions.db`). Le cookie ne contient
  qu'un identifiant aléatoire ; la base ne garde que son SHA-256.
- La configuration se réduit à `OAUTH_ISSUER`, `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` et `PUBLIC_ORIGIN`. Les
  endpoints et les clés de signature sont lus dans `/.well-known/oauth-authorization-server`. Au démarrage,
  l'issuer doit être **identique caractère pour caractère** à celui que publie le serveur, et S256 doit être supporté,
  sinon l'API refuse de démarrer.
- Le contrôle d'accès est fait par un middleware ASGI **avant la lecture du corps** : un upload non authentifié reçoit
  un 401 sans être reçu en entier.
- Toutes les `AUTH_*` sont dans `backend/app/auth/` (`AUTH_MODULE_VERSION`). Ce dossier et `backend/app/tests/auth/`
  doivent rester identiques à ceux d'ImageTools (`diff -r`).
- Les jobs (fichiers temporaires multi-étapes) et le rate limit sont par utilisateur (`request.state.user.sub`).
- Une session est revalidée auprès du serveur (refresh) toutes les `SESSION_REVALIDATE_INTERVAL` (15 min) : si un
  back-channel logout se perd, l'accès tombe au plus tard à ce moment-là.

## Test en local avec le serveur OAuth de dev

### Ports utilisés en dev

| Port | Service | Publié sur l'hôte |
|---|---|---|
| **3010** (`FRONTEND_PORT`) | Application (Nuxt dev, proxy `/api` et `/auth` vers l'API) | oui |
| 8010 (`BACKEND_PORT`) | API FastAPI, en réseau `host` | oui (sur l'hôte) |
| 8080 | Serveur OAuth (dépôt `OAuth-serveur`, `make start`) | oui |
| 8025 | Mailpit du serveur OAuth (codes de connexion par e-mail) | oui |

L'API tourne en `network_mode: host` en dev : l'issuer du serveur de dev est `http://localhost:8080` et doit être
joignable sous ce nom exact depuis l'API (la découverte compare l'issuer strictement). `BACKEND_PORT` ne doit pas
entrer en conflit avec une autre application de l'hôte (8000 est pris par ImageTools).

### 1. Démarrer le serveur OAuth

```bash
cd ../OAuth-serveur && make start          # http://localhost:8080
make admin email=moi@example.com           # premier utilisateur (code reçu sur http://localhost:8025)
```

### 2. Déclarer l'application de dev sur le serveur OAuth

```bash
cd ../OAuth-serveur
make console c='app:application:create "LocalPDF dev" --id=localpdf-dev \
    --home-url=http://localhost:3010/ \
    --redirect-uri=http://localhost:3010/auth/callback \
    --backchannel-logout-uri=http://host.docker.internal:3010/auth/backchannel-logout'
#   → notez le client secret (affiché une seule fois)
make grant email=moi@example.com app=localpdf-dev
```

L'URL de back-channel utilise `host.docker.internal` car c'est le **conteneur** du serveur OAuth qui appelle
l'application publiée sur l'hôte ; Nuxt la transmet à l'API.

### 3. Configurer `.env` (dans ce dépôt)

```dotenv
BACKEND_PORT=8010
FRONTEND_PORT=3010
OAUTH_ISSUER=http://localhost:8080
OAUTH_CLIENT_ID=localpdf-dev
OAUTH_CLIENT_SECRET=<secret noté à l'étape 2>
```

Modèle : `.env.example`. En dev, `APP_ENV=dev` et `COOKIE_SECURE=false` sont fixés par `docker-compose.override.yml` (avec `PUBLIC_ORIGIN`, déduit de `FRONTEND_PORT`, et un cookie `localpdf-session` : les navigateurs ne séparent pas les cookies par port)
(cookie `session` au lieu de `__Host-session`, endpoints `http` acceptés).

### 4. Lancer

```bash
make dev          # premier plan (Ctrl+C pour arrêter), reconstruit les images
make up           # en arrière-plan
make logs          # suivre les journaux
make urls          # rappelle l'URL et les paramètres OAuth de dev
```

Ouvrir <http://localhost:3010> : redirection vers le serveur OAuth, connexion, retour sur l'application.

### Vérifications en local

| Test | Attendu |
|---|---|
| Ouvrir une page sans être connecté | Redirection vers `localhost:8080`, puis retour sur la page demandée |
| Utilisateur sans accès à l'application | Page « Vous n'avez pas accès » du serveur OAuth |
| `make console c="app:application:test-backchannel-logout localpdf-dev moi@example.com"` (dans `OAuth-serveur`) | « HTTP 200 », session fermée aussitôt |
| `make revoke email=…` (dans `OAuth-serveur`) | Session fermée au plus tard après `SESSION_REVALIDATE_INTERVAL` |
| `POST` d'un gros fichier sans session | 401 immédiat |
| Bouton de déconnexion (en-tête) | Déconnexion globale : session de l'app et session SSO fermées (`{OAUTH_ISSUER}/logout?redirect_uri=…`), retour sur l'écran de connexion du serveur OAuth |

## Premier déploiement (production)

Prérequis : un serveur avec Docker + Compose, Caddy sur l'hôte (HTTPS), un nom de domaine (ex. `pdf.mydomain.com`)
pointant sur le serveur, et le serveur OAuth déjà en production (`oauth.mydomain.com`, en HTTPS : l'API refuse des
endpoints `http` en production).

### 1. Déclarer l'application sur le serveur OAuth de production

Depuis le dépôt `OAuth-serveur` sur le serveur :

```bash
make prod-app name="LocalPDF" id=localpdf url=https://pdf.mydomain.com
#   → notez le client secret (affiché une seule fois)
make prod-grant email=moi@mydomain.com app=localpdf    # pour chaque utilisateur autorisé
```

L'application doit avoir pour redirect URI `https://pdf.mydomain.com/auth/callback` et pour back-channel URI
`https://pdf.mydomain.com/auth/backchannel-logout`.

### 2. Récupérer le code et configurer

```bash
git clone <url-du-depot> /opt/localpdf && cd /opt/localpdf
cp .env.example .env && chmod 600 .env
$EDITOR .env       # PUBLIC_ORIGIN, OAUTH_ISSUER, OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET
```

`OAUTH_ISSUER` = valeur exacte du champ `issuer` de `https://oauth.mydomain.com/.well-known/oauth-authorization-server`
(`curl` pour la lire). Le redirect URI est déduit de `PUBLIC_ORIGIN`.

### 3. Démarrer

```bash
make prod-build     # construit les images (nuxt generate, API avec LibreOffice : plusieurs minutes)
make prod-up        # démarre et attend les healthchecks
make prod-ps
make prod-health    # app : HTTP 302 attendu (redirection vers la connexion), api /api/health : 200
```

Le conteneur `web` (Caddy) écoute sur `127.0.0.1:${REMOTE_FRONTEND_PORT}` (3010 par défaut) uniquement. Le conteneur `api`
ne publie aucun port. `/api/health` répond 503 tant que le serveur OAuth n'a pas pu être lu ; `web` attend que `api`
soit sain.

### 4. Caddy de l'hôte

`/etc/caddy/sites/pdf.caddy` (voir `OAuth-serveur/docs/caddy-plusieurs-sites.md` pour les snippets `securite` et
`journal`) :

```caddy
pdf.mydomain.com {
	import securite
	import journal pdf

	# Première barrière sur tout le domaine, au-dessus de MAX_UPLOAD_MB et du 210MB du conteneur web
	request_body {
		max_size 250MB
	}
	reverse_proxy 127.0.0.1:3010
}
```

Pas de `response_header_timeout` : Caddy n'en a pas par défaut, une conversion longue passe. Le détail des limites de
taille est dans [mise-en-production.md](mise-en-production.md), étape 5.

```bash
sudo -u caddy caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
```

`/auth/backchannel-logout` doit rester joignable depuis le serveur OAuth (c'est le cas via l'URL publique).

### 5. Vérifier

Mêmes tests qu'en local (tableau ci-dessus), avec `make prod-…` côté serveur OAuth. Test du back-channel :

```bash
cd ../OAuth-serveur && make prod-console c="app:application:test-backchannel-logout localpdf moi@mydomain.com"
```

## Mise à jour

```bash
cd /opt/localpdf
make prod-deploy    # git pull --ff-only, build, redémarrage, état des conteneurs, nettoyage des images orphelines
make prod-health
```

Les jobs en cours (fichiers temporaires, TTL 30 min) sont perdus au redémarrage ; les sessions utilisateurs (volume
`api-data`) sont conservées. À conserver lors d'une sauvegarde : `.env` et le volume `api-data`.

## Commandes `make`

| Commande | Rôle |
|---|---|
| `make dev` / `make up` | Dev : démarre (avec reconstruction), au premier plan / en arrière-plan ; `up` affiche les URL |
| `make down`, `make logs`, `make urls` | Dev : arrêt, journaux, URL et paramètres OAuth |
| `make test`, `make lint` | Tests et linters (backend + frontend) |
| `make prod-build` | Construit les images de production |
| `make prod-up` | Démarre / met à jour la production |
| `make prod-deploy` | **Mise à jour** : pull, build, up, état |
| `make prod-down` / `make prod-restart` | Arrêt / redémarrage |
| `make prod-logs` / `make prod-ps` | Journaux / état |
| `make prod-health` | Vérifie que l'application et l'API répondent |

## Dépannage

| Symptôme | Cause probable |
|---|---|
| L'API ne démarre pas : `issuer mismatch` | `OAUTH_ISSUER` n'est pas identique à l'`issuer` publié (slash final, `http` vs `https`, `localhost` vs `127.0.0.1`) |
| `/api/health` en 503 | Serveur OAuth injoignable depuis l'API, ou découverte en échec (voir `make prod-logs`) |
| `redirect_uri` refusée par le serveur OAuth | `PUBLIC_ORIGIN` différent de l'origine déclarée sur le serveur OAuth |
| `Address already in use` en dev | `BACKEND_PORT` déjà pris sur l'hôte (l'API est en réseau `host`) |
| `COOKIE_SECURE=false is only allowed with APP_ENV=dev` | Configuration de dev dans un environnement `prod` |
| `403 forbidden_origin` sur un `POST` | Le navigateur envoie une `Origin` différente de `PUBLIC_ORIGIN` |
| Back-channel logout en échec | URL joignable depuis le serveur OAuth ? Voir `make prod-logs` (« Logout token refused ») |
