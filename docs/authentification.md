# Authentification des applications Python (pdf-tools, ImageTools) : client OAuth par découverte, sans paquet partagé

> **Destinataires :** les agents des dépôts **pdf-tools** et **ImageTools**. Ce document est identique dans les deux dépôts (`docs/authentification.md`).
> **Remplace :** `AUTH-ARCHITECTURE.md` et l'ADR 0001 (Authelia, voir l'annexe). L'architecture reste la même ; les différences sont la configuration par découverte et l'absence de paquet partagé.
> **Prérequis :** le serveur OAuth publie `/.well-known/oauth-authorization-server` (voir `01-SERVEUR-OAUTH-DISCOVERY.md`). Vérifier avec `curl <issuer>/.well-known/oauth-authorization-server` avant de commencer.

---

# Partie 1 : architecture

## 1.1 Décision
**Le backend FastAPI est le client OAuth (BFF). Le front Nuxt est une SPA statique servie par Caddy. Pas de Node en production. La session est stockée côté serveur, dans SQLite.**

```
Navigateur ──cookie __Host-session (opaque)──▶ Caddy ─┬─ /*        → fichiers statiques (nuxt generate, ssr:false)
                                                      ├─ /auth/*   → FastAPI
                                                      └─ /api/*    → FastAPI (session vérifiée avant lecture du corps)
FastAPI ──découverte, code + PKCE, refresh, révocation──▶ Serveur OAuth2
Serveur OAuth2 ──logout_token (back-channel)──▶ FastAPI /auth/backchannel-logout
```

Les raisons, sur les critères du projet :
- **Bonnes pratiques :** pattern BFF (*OAuth 2.0 for Browser-Based Apps*), PKCE S256 et état à usage unique (RFC 9700).
- **Sécurité :** aucun jeton dans le navigateur, une seule frontière de confiance, révocation immédiate par suppression de la session.
- **Fiabilité :** URL et clés lues depuis le serveur, jamais recopiées.
- **Performances :** un seul runtime (Python) ; le statique est servi par Caddy ; les uploads ne passent pas par un relais.
- **Maintenabilité :** un module d'auth au **même emplacement et avec la même structure** dans chaque app (voir le §1.3).

## 1.2 Ce que la découverte apporte
- **Configuration réduite** à `OAUTH_ISSUER`, `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` et `PUBLIC_ORIGIN`.
- **Plus d'URL d'endpoints en dur** : elles sont lues dans les métadonnées.
- **Vérification du logout token par `jwks_uri`** avec `PyJWKClient`, qui met les clés en cache et suit leur rotation par `kid`. Plus de clé recopiée.
- **Vérifications au démarrage** : l'issuer correspond, S256 est supporté, les endpoints requis sont présents. L'app échoue immédiatement si le serveur n'est pas conforme.

## 1.3 Pas de paquet partagé : la règle de cohérence
On renonce au paquet séparé. Le risque connu est que les copies divergent, comme avec les bugs d'uid et de nom de cookie. On le maîtrise ainsi :
1. **Structure identique** dans les deux dépôts : `app/auth/` (arborescence au §2.1), mêmes noms de fichiers, de fonctions et de variables d'environnement.
2. **Rien de spécifique à l'app dans `app/auth/`.** Ce qui dépend de l'app (préfixes protégés, chemins publics) se passe en paramètre depuis `main.py`.
3. **Constante de version** `AUTH_MODULE_VERSION = "2.2.0"` dans `app/auth/__init__.py`. Toute modification du module dans un dépôt doit être reportée dans l'autre, avec le même incrément de version.
4. **Mêmes tests** d'auth, avec une suite identique dans les deux dépôts (`backend/app/tests/auth/` dans pdf-tools, `backend/tests/auth/` dans ImageTools ; seuls les chemins d'import diffèrent).
5. **Vérification de dérive :** `diff -r -x __pycache__ pdf-tools/backend/app/auth ImageTools/backend/app/auth` doit être vide. À exécuter avant chaque merge touchant à l'auth.

**L'implémentation de référence est celle de pdf-tools.** ImageTools en est une copie conforme.

---

# Partie 2 : spécification (identique pour les deux apps)

## 2.1 Arborescence
```
app/auth/
  __init__.py        # AUTH_MODULE_VERSION, setup_auth(app, settings, protected_prefixes, public_paths)
  config.py          # AuthSettings (pydantic-settings)
  discovery.py       # lecture, validation et cache des métadonnées
  client.py          # wrapper Authlib AsyncOAuth2Client (échange, refresh, révocation)
  store.py           # SessionStore SQLite (sessions, login_attempts, jti vus)
  middleware.py      # AuthMiddleware ASGI pur
  routes.py          # /auth/login, /auth/callback, /auth/logout, /auth/backchannel-logout, /api/me
  logout_token.py    # vérification du logout token (PyJWKClient)
  csrf.py            # vérification Origin / Sec-Fetch-Site
  deps.py            # current_user (lit request.state.user)
tests/auth/
```
Dépendances : `authlib`, `httpx`, `pyjwt[crypto]`, `pydantic-settings`. **Supprimer** toute dépendance devenue inutile (vérification JWT Bearer de l'ancien relais Nitro, `python-jose`…).

## 2.2 Configuration
```
OAUTH_ISSUER              (obligatoire, valeur EXACTE de l'issuer, ex : https://auth.example.com)
OAUTH_CLIENT_ID           (obligatoire)
OAUTH_CLIENT_SECRET       (obligatoire)
OAUTH_SCOPES              (défaut : celui en usage aujourd'hui)
PUBLIC_ORIGIN             (obligatoire, ex : https://pdf.example.com ; le redirect_uri en est déduit : {PUBLIC_ORIGIN}/auth/callback)
SESSION_DB_PATH           (défaut : /data/sessions.db)
SESSION_IDLE_TTL          (défaut : 8h)
SESSION_ABSOLUTE_TTL      (défaut : 7j)
SESSION_REVALIDATE_INTERVAL (défaut : 15min)
SESSION_COOKIE_NAME       (défaut : session ; nom du cookie hors prod. Distinct par app, car en dev les apps partagent `localhost` et les navigateurs partagent les cookies entre ports)
COOKIE_SECURE             (défaut : true ; false autorisé uniquement si APP_ENV=dev)
APP_ENV                   (prod | dev)
OAUTH_LOGOUT_TOKEN_SECRET (UNIQUEMENT si le serveur signe en HS256 et ne publie pas de jwks_uri)
```
L'app **refuse de démarrer** si une variable obligatoire manque, ou si `COOKIE_SECURE=false` alors que `APP_ENV=prod`.

## 2.3 Découverte (`discovery.py`)
- Au démarrage (lifespan FastAPI) : `GET {OAUTH_ISSUER}/.well-known/oauth-authorization-server`, avec repli sur `/.well-known/openid-configuration` si la première renvoie 404.
- **Validations bloquantes** (RFC 8414 §3.3 et RFC 9700) :
  - `metadata["issuer"] == OAUTH_ISSUER`, en **égalité stricte de chaînes** ;
  - `"S256" in code_challenge_methods_supported` ;
  - `authorization_endpoint` et `token_endpoint` présents et en `https` (sauf si `APP_ENV=dev`) ;
  - pour le back-channel : `jwks_uri` présent, sinon `OAUTH_LOGOUT_TOKEN_SECRET` doit être défini.
- Échec de validation : l'app ne démarre pas, avec un message explicite. Serveur injoignable : réessayer avec un backoff (5 tentatives) ; si ça échoue toujours, ne pas démarrer, ou rester en état *not ready* (healthcheck en 503).
- Cache en mémoire, rafraîchi en arrière-plan toutes les heures. Un échec de rafraîchissement **conserve** les métadonnées précédentes et journalise un avertissement.
- Les endpoints facultatifs (`revocation_endpoint`, `end_session_endpoint`, `userinfo_endpoint`) sont utilisés s'ils sont présents. Leur absence n'est pas une erreur ; on dégrade proprement.

## 2.4 Client OAuth (`client.py`)
- `authlib.integrations.httpx_client.AsyncOAuth2Client`, avec `client_id`, `client_secret`, `redirect_uri` et `code_challenge_method="S256"`. Méthode d'authentification client : la première de `token_endpoint_auth_methods_supported` parmi `client_secret_basic` et `client_secret_post`.
- **Ne pas utiliser** `authlib.integrations.starlette_client` : elle stocke son état dans le `SessionMiddleware` de Starlette, c'est-à-dire un cookie signé, ce qui n'est pas révocable.
- Un seul `httpx.AsyncClient` partagé, ouvert dans le lifespan, avec des timeouts explicites (connexion 5 s, lecture 10 s).

## 2.5 Cookie et stockage
- Cookie : `__Host-session` en prod (`SESSION_COOKIE_NAME`, par défaut `session`, en dev), valeur `secrets.token_urlsafe(32)`, avec `HttpOnly; Secure; SameSite=Lax; Path=/`. **Aucun jeton ni aucune donnée dans le cookie.**
- SQLite en mode WAL, `busy_timeout` à 5 s. Tables :
  - `sessions(id_hash PK, sub, oauth_sid, user_claims JSON, access_token, refresh_token, access_expires_at, created_at, last_seen_at, last_revalidated_at, absolute_expires_at)`, avec un index sur `sub` et un sur `oauth_sid`. On stocke **le SHA-256 de l'identifiant**, jamais l'identifiant lui-même.
  - `login_attempts(state PK, code_verifier, nonce, return_to, expires_at)`, avec un TTL de 10 min et un usage unique.
  - `seen_jti(jti PK, expires_at)`, pour empêcher le rejeu des logout tokens.
- Une tâche périodique (toutes les 10 min) purge les lignes expirées des trois tables.

## 2.6 Endpoints (`routes.py`)

**`GET /auth/login?return_to=…`**
1. `return_to` : accepté seulement s'il commence par `/` mais pas par `//` ni par `/\`. Sinon, `/`.
2. Générer `state`, `code_verifier` et `nonce` (si le scope `openid` est utilisé), puis les insérer dans `login_attempts`.
3. Redirection 302 vers `authorization_endpoint` (lu depuis les métadonnées).

**`GET /auth/callback`**
1. Si le paramètre `error` est présent : redirection vers `/?auth_error=<code>`, sans boucle.
2. Si le serveur annonce `authorization_response_iss_parameter_supported: true`, vérifier que `iss` est égal à `OAUTH_ISSUER` (RFC 9207).
3. `DELETE … RETURNING` sur `login_attempts` par `state` : usage unique et atomique. Si la ligne est absente ou expirée, renvoyer 400.
4. Échange du code avec le `code_verifier`.
5. Identité : si un `id_token` est reçu, le vérifier via le JWKS (`iss`, `aud`, `exp`, `nonce`). Sinon, appeler `userinfo_endpoint`. Sinon, utiliser les claims de l'access token, uniquement s'il est un JWT vérifiable via le JWKS.
6. Créer une **nouvelle** session (identifiant neuf, contre la fixation de session), poser le cookie, rediriger vers `return_to`.

**`POST /auth/logout`** (protégé par la vérification CSRF)
1. Supprimer la session et effacer le cookie.
2. Si `revocation_endpoint` est présent, révoquer le refresh token au mieux : un échec est journalisé mais ne bloque pas la déconnexion.
3. Réponse JSON : `{"redirect": …}`, avec `end_session_endpoint` s'il est publié. Sinon repli sur la convention du serveur OAuth maison : `{OAUTH_ISSUER}/logout?redirect_uri={PUBLIC_ORIGIN}/`, qui ferme aussi la session SSO du serveur et ne redirige que vers l'origine d'une application enregistrée.

**`POST /auth/backchannel-logout`** (pas de session, pas de vérification CSRF, joignable par le serveur OAuth)
Vérification dans `logout_token.py` :
- signature : `PyJWKClient(jwks_uri, cache_keys=True, lifespan=3600)`, puis `get_signing_key_from_jwt()`, appelé via `run_in_threadpool` car le client est synchrone. Algorithmes autorisés : ceux des métadonnées (`id_token_signing_alg_values_supported`) ou une liste fixe, **jamais `none`**. Repli en HS256 avec `OAUTH_LOGOUT_TOKEN_SECRET` seulement si le serveur n'a pas de JWKS ;
- `iss == OAUTH_ISSUER`, `aud` contient `OAUTH_CLIENT_ID`, `iat` récent (marge de 5 min), `exp` vérifié s'il est présent ;
- `events` contient la clé `http://schemas.openid.net/event/backchannel-logout` ; `nonce` est **absent** ; `sub` ou `sid` est présent ;
- `jti` absent de `seen_jti`, puis inséré.

Action : supprimer les sessions par `oauth_sid` si `sid` est présent, sinon par `sub`. Réponse 200 avec `Cache-Control: no-store`, ou 400.

**`GET /api/me`** : 200 avec `{sub, name, email, roles}`, ou 401. `Cache-Control: no-store`.

## 2.7 Middleware (`middleware.py`)
**ASGI pur, pas de `BaseHTTPMiddleware`.** FastAPI parse le corps multipart *avant* d'exécuter les dépendances. Le contrôle d'auth doit donc se faire dans le middleware, **avant toute lecture du corps**, faute de quoi un upload de 200 Mo non authentifié serait entièrement reçu avant le 401.

Pour les chemins sous `protected_prefixes` qui ne figurent pas dans `public_paths` :
1. Lire le cookie et charger la session par `sha256(id)`. Si elle n'existe pas, renvoyer 401 avec un JSON `{"error":"unauthenticated"}`.
2. Si le délai d'inactivité ou la durée absolue est dépassé, supprimer la session et renvoyer 401.
3. Mettre à jour `last_seen_at` au plus une fois par minute.
4. Si `last_revalidated_at` est plus ancien que `SESSION_REVALIDATE_INTERVAL`, lancer la **revalidation** :
   - `BEGIN IMMEDIATE`, relire la ligne et vérifier que la revalidation est toujours nécessaire. Si ce n'est plus le cas, un autre worker l'a déjà faite : on s'arrête là. Ce verrou en base fonctionne avec N workers uvicorn ;
   - refresh auprès de `token_endpoint`, puis stockage des nouveaux jetons (rotation) et mise à jour de `last_revalidated_at` ;
   - en cas d'`invalid_grant`, supprimer la session et renvoyer 401. En cas d'erreur réseau ou de 5xx, **garder** la session et réessayer à la requête suivante.
5. Placer l'utilisateur dans `scope["state"]["user"]`.

C'est ce refresh périodique qui sert de filet de sécurité si un back-channel logout se perd : une session révoquée sur le serveur tombe au plus tard après `SESSION_REVALIDATE_INTERVAL`.

`deps.current_user` se contente de lire `request.state.user`.

## 2.8 CSRF (`csrf.py`)
Pour POST, PUT, PATCH et DELETE sous `/api/*` et sur `/auth/logout` : exiger `Origin == PUBLIC_ORIGIN`, ou `Sec-Fetch-Site == same-origin` si `Origin` est absent. Sinon, 403. Exception : `/auth/backchannel-logout`. Aucune configuration CORS.

## 2.9 Ce qu'il faut supprimer
- La vérification JWT Bearer héritée du relais Nitro, et ses clés et variables d'environnement.
- Toute URL d'endpoint OAuth en dur ou en variable d'environnement.
- Tout l'ancien code d'auth en dehors de `app/auth/`.

## 2.10 Code métier
Les jobs privés et le rate limit par utilisateur utilisent `request.state.user.sub`. Les tests existants doivent rester verts.

---

# Partie 3 : frontend Nuxt (identique dans les deux apps)
- `ssr: false`, build avec `nuxt generate`.
- **Supprimer** `server/`, `nuxt-auth-utils`, tout relais `/api/**` et tout secret OAuth.
- `composables/useUser.ts` : `GET /api/me` une seule fois, puis cache dans `useState`. Expose `user`, `loading`, `refresh()` et `logout()`.
- Middleware de route global : s'il n'y a pas d'utilisateur, `window.location.href = '/auth/login?return_to=' + encodeURIComponent(to.fullPath)`. C'est une navigation complète, pas un `navigateTo`.
- Wrapper `$fetch` : sur 401, même redirection. Aucune logique de jeton côté front.
- `logout()` : `POST /auth/logout`, puis `window.location.href = res.redirect`.
- Dev : `nitro.devProxy` vers FastAPI pour `/api` et `/auth`, afin de rester sur une seule origine.

---

# Partie 4 : déploiement
- **Image `api`** : multi-stage avec Python slim et `uv`, utilisateur non root, volume `/data` (sessions et fichiers de travail). Le traitement lourd reste hors de la boucle d'événements. Healthcheck sur `/api/health`, qui renvoie 503 tant que la découverte n'a pas réussi.
- **Image `web`** : un stage Node pour `nuxt generate`, puis un stage final `caddy:alpine` qui ne contient que les fichiers statiques. Pas de Node en runtime.
- Caddyfile :
  ```
  app.example.com {
      encode zstd gzip
      handle /auth/* { reverse_proxy api:8000 }
      handle /api/*  { request_body { max_size 210MB }  reverse_proxy api:8000 { flush_interval -1 } }
      handle { root * /srv; try_files {path} /index.html; file_server }
      header { -Server  X-Content-Type-Options nosniff  Referrer-Policy strict-origin-when-cross-origin  Content-Security-Policy "default-src 'self'; frame-ancestors 'none'" }
  }
  ```
- Uvicorn : `--proxy-headers --forwarded-allow-ips=<ip de caddy>`. Le service `api` **ne publie aucun port** : il n'est joignable que via Caddy et le serveur OAuth (pour le back-channel).
- Côté serveur OAuth, déclarer pour chaque app : le redirect URI `{PUBLIC_ORIGIN}/auth/callback` et le back-channel URI `{PUBLIC_ORIGIN}/auth/backchannel-logout`.

---

# Partie 5 : tests obligatoires (`tests/auth/`, avec un serveur OAuth simulé qui expose `.well-known` et un JWKS)
1. **Découverte :** un issuer différent d'un caractère (slash final compris) bloque le démarrage ; l'absence de S256 bloque le démarrage ; repli sur `openid-configuration` ; un échec de rafraîchissement conserve le cache.
2. **Login :** S256 présent dans l'URL ; `return_to` malveillants rejetés (`//evil.com`, `https://evil.com`, `/\evil`).
3. **Callback :** `state` inconnu, expiré ou rejoué → 400 ; `error` géré ; `iss` RFC 9207 vérifié s'il est annoncé ; l'identifiant de session change à chaque login.
4. **Cookie :** attributs exacts ; aucun jeton dedans ; seul le hash est en base.
5. **Middleware :** un upload volumineux non authentifié reçoit 401 **sans consommation du corps** ; inactivité et durée absolue respectées.
6. **Revalidation :** succès avec rotation des jetons ; `invalid_grant` → 401 et suppression ; erreur réseau → session conservée ; **N requêtes concurrentes, un seul refresh**.
7. **Back-channel :** un jeton valide supprime les sessions par `sid`, puis par `sub`. Tous ces cas sont rejetés : mauvaise signature, `alg=none`, `kid` inconnu, mauvais `aud` ou `iss`, `nonce` présent, `events` absent, `jti` rejoué. Une rotation de clé (nouveau `kid` dans le JWKS) est acceptée sans redémarrage.
8. **CSRF :** `Origin` étranger → 403 ; `Sec-Fetch-Site: same-origin` → OK ; le back-channel est exempté.
9. **Logout :** session supprimée, cookie effacé, révocation tentée, succès même si la révocation échoue.
10. **Métier :** les tests existants (jobs privés, rate limit) restent verts.

# Partie 6 : critères d'acceptation
- Seules les variables `OAUTH_ISSUER`, `OAUTH_CLIENT_ID` et `OAUTH_CLIENT_SECRET` décrivent le serveur OAuth : aucune URL d'endpoint dans la configuration ni dans le code.
- `diff -r` des dossiers `app/auth` des deux dépôts est vide, et celui des tests d'auth aussi.
- Aucun process Node dans les conteneurs de production ; plus aucune trace de `nuxt-auth-utils` ni de `server/` dans le front.
- Aucun jeton visible dans le navigateur.
- Une déconnexion faite côté serveur OAuth rend la session invalide en moins d'une seconde (back-channel), ou au plus tard après `SESSION_REVALIDATE_INTERVAL` si le back-channel échoue.
- Un upload de 200 Mo non authentifié est rejeté avant transfert.

# Ordre d'exécution
1. **pdf-tools** : implémenter `app/auth/` et `tests/auth/`, migrer le front et le déploiement, puis faire un test de bout en bout avec le vrai serveur.
2. **ImageTools** : copier `app/auth/` et `tests/auth/` **à l'identique**, brancher dans `main.py` avec ses propres `protected_prefixes`, migrer le front et le déploiement, puis faire un test de bout en bout.
3. Vérifier le `diff -r` des deux dépôts.

---

# Annexe : historique de la décision (ex-ADR 0001, 2026-08-13)

**Statut : remplacé.** L'ADR 0001 retenait Authelia devant Caddy (`forward_auth`) pour protéger des petites apps sans base de données. Il a été remplacé par le serveur OAuth maison (`OAuth-serveur`) et l'architecture BFF décrite ci-dessus.

**Contexte de l'époque.** Les petites apps (ImageConverter, pdf-tools…) sont des outils personnels sans état ni comptes : le besoin était « une porte fermée devant plusieurs apps », sans base de données par app. Elles sont exposées en sous-domaines d'un même domaine, derrière un Caddy global qui route vers chaque conteneur.

**Critères.** Gratuit et open-source (obligatoire) ; aucune modification du code des apps (haute) ; intégration au Caddy existant (haute) ; SSO entre apps (moyenne) ; faible coût opérationnel, sans base lourde (haute) ; aucun impact sur les apps à auth intégrée (obligatoire).

| Option | Avantages | Inconvénients |
|---|---|---|
| A. `basic_auth` Caddy par app | aucun service ajouté | pas de session partagée, pas de logout ni de 2FA, édition manuelle du Caddyfile à chaque app |
| **B. Authelia + `forward_auth` (retenue à l'époque)** | léger, utilisateurs en YAML, SQLite embarqué, vrai SSO par cookie de domaine parent, aucune modif des apps | exige des sous-domaines d'un même domaine ; pas d'envoi d'email sans SMTP |
| C. oauth2-proxy + OIDC | fonctionne sur des domaines hétérogènes | un sidecar par app et un IdP OIDC à fournir |
| D. Authentik | IdP complet (OIDC, SAML) | PostgreSQL et Redis requis, surdimensionné |

**Pourquoi remplacé.** Le serveur OAuth maison fournit déjà les comptes, le 2FA, le SSO et le back-channel logout. Les apps l'utilisent comme clients OAuth (BFF) : cela évite d'ajouter Authelia et de maintenir un `users_database.yml` et un bloc `forward_auth` par app, et la session et la révocation sont gérées côté applicatif.
