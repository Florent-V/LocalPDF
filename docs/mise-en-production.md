# Mise en production

Guide pas à pas : premier déploiement, puis mises à jour. La mise à jour courante se fait à la main : on se
connecte au serveur et on lance `make prod-deploy`. Aucun secret n'est stocké chez GitHub. Un déploiement
automatique est décrit en fin de document, **facultatif**. Pour l'architecture, le test en local et le dépannage, voir [deploiement.md](deploiement.md).

Les opérations passent par le `Makefile` (`make help`-style : `make prod-…`). Valeurs d'exemple utilisées ici :
domaine `pdf.mydomain.com`, serveur OAuth `oauth.mydomain.com`, dépôt cloné dans `/opt/localpdf`, propriétaire
Unix `ubuntu` (membre du groupe `docker`). Adaptez-les.

## Vue d'ensemble

```
Internet ─HTTPS─▶ Caddy de l'hôte ─HTTP─▶ 127.0.0.1:3010 (conteneur web : Caddy + front statique)
                                                          ├─ /auth/*, /api/* ─▶ conteneur api (FastAPI, client OAuth)
                                                          └─ le reste         ─▶ fichiers statiques
Serveur OAuth ─back-channel logout─▶ https://pdf.mydomain.com/auth/backchannel-logout
```

Seul `web` est atteignable, sur `127.0.0.1`. `api` ne publie aucun port. L'état durable (sessions) est dans le
volume Docker `api-data`.

## Partie 1 : premier déploiement

### 0. Prérequis

| Élément | Détail |
|---|---|
| Serveur | Linux, Docker Engine + plugin Compose, `git`, `make`, `curl`, 4 Go de RAM conseillés (LibreOffice) |
| DNS | `pdf.mydomain.com` pointe sur le serveur (enregistrement A/AAAA) |
| HTTPS | Caddy installé **sur l'hôte** (il obtient le certificat). Ports 80 et 443 ouverts |
| Serveur OAuth | En production et en **HTTPS** (`https://oauth.mydomain.com`). L'API refuse des endpoints `http` en prod |
| Accès | L'utilisateur Unix qui déploie est dans le groupe `docker` et a accès au dépôt Git (clé de déploiement en lecture seule si le dépôt est privé) |

Vérifier d'abord que le serveur OAuth publie bien sa découverte (c'est la source de toute la configuration) :

```bash
curl -s https://oauth.mydomain.com/.well-known/oauth-authorization-server | python3 -m json.tool | head -20
```

Noter la valeur **exacte** du champ `issuer` (sans modifier ni slash final).

### 1. Déclarer l'application sur le serveur OAuth

Sur le serveur OAuth, dans le dépôt `OAuth-serveur` :

```bash
make prod-app name="LocalPDF" id=localpdf url=https://pdf.mydomain.com
#   → noter le client secret : il n'est affiché qu'une seule fois
make prod-grant email=moi@mydomain.com app=localpdf       # une fois par utilisateur autorisé
```

L'application doit avoir :
- redirect URI : `https://pdf.mydomain.com/auth/callback` ;
- back-channel logout URI : `https://pdf.mydomain.com/auth/backchannel-logout`.

`make prod-app` déclare les deux URL ; vérifiez-les dans l'administration du serveur OAuth si besoin.

### 2. Récupérer le code

```bash
sudo mkdir -p /opt/localpdf && sudo chown ubuntu: /opt/localpdf
git clone <url-du-depot> /opt/localpdf
cd /opt/localpdf
```

### 3. Configurer `.env`

```bash
cp .env.example .env && chmod 600 .env
$EDITOR .env
```

| Variable | Valeur |
|---|---|
| `PUBLIC_ORIGIN` | `https://pdf.mydomain.com` (origine seule, sans chemin) |
| `OAUTH_ISSUER` | la valeur exacte du champ `issuer` relevée à l'étape 0 |
| `OAUTH_CLIENT_ID` | `localpdf` |
| `OAUTH_CLIENT_SECRET` | le secret noté à l'étape 1 |
| `REMOTE_FRONTEND_PORT` | `3010` (port local lié à `127.0.0.1`) |
| `MAX_UPLOAD_MB` | `200` |

`.env` n'est jamais commité et ne quitte pas le serveur (la CI ne le voit pas).

### 4. Construire et démarrer

```bash
make prod-build     # nuxt generate + image api avec LibreOffice : plusieurs minutes
make prod-up        # démarre et attend les healthchecks (api, puis web)
make prod-health    # app /auth/login : HTTP 302 ; api /api/health : 200
make prod-ps
```

Si `prod-up` échoue, `make prod-logs`. L'erreur la plus fréquente est `issuer mismatch` (voir le dépannage de
[deploiement.md](deploiement.md)).

### 5. Caddy de l'hôte (HTTPS)

`/etc/caddy/sites/pdf.caddy` (les snippets `securite` et `journal` sont décrits dans
`OAuth-serveur/docs/caddy-plusieurs-sites.md`) :

```caddy
pdf.mydomain.com {
	import securite
	import journal pdf

	# Uploads de PDF (MAX_UPLOAD_MB) et conversions longues (LibreOffice)
	request_body {
		max_size 250MB
	}
	reverse_proxy 127.0.0.1:3010 {
		transport http {
			response_header_timeout 300s
		}
	}
}
```

```bash
sudo -u caddy caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
```

### 6. Recette de la production

| Test | Attendu |
|---|---|
| `curl -sI https://pdf.mydomain.com/` | `200`, en-têtes de sécurité présents |
| `curl -s https://pdf.mydomain.com/api/me` | `401 {"error":"unauthenticated"}` |
| Ouvrir `https://pdf.mydomain.com` dans un navigateur | Redirection vers `oauth.mydomain.com`, connexion, retour sur l'application |
| Fusionner deux PDF | Le fichier fusionné se télécharge |
| Cookie dans les outils de développement | `__Host-session`, `HttpOnly`, `Secure`, `SameSite=Lax` |
| Utilisateur sans accès à `localpdf` | Page « pas d'accès » du serveur OAuth |
| Back-channel (sur le serveur OAuth) : `make prod-console c="app:application:test-backchannel-logout localpdf moi@mydomain.com"` | « HTTP 200 » et session fermée aussitôt |

### 7. Sauvegardes

`make prod-backup` copie `.env` et la base des sessions dans `./backups` (variable `BACKUP_DIR`, 30 jours de
rétention). Il est lancé automatiquement par `make prod-deploy`. Pour une sauvegarde planifiée en plus :

```bash
# crontab -e (utilisateur ubuntu) : tous les jours à 3 h
0 3 * * * cd /opt/localpdf && make prod-backup BACKUP_DIR=/var/backups/localpdf >> /var/log/localpdf-backup.log 2>&1
```

Ce qui compte : `.env` (indispensable, contient le secret OAuth). La base des sessions est facultative : sans
elle, les utilisateurs doivent simplement se reconnecter. Les fichiers de travail (`/tmp/localpdf`) sont éphémères.

Restauration des sessions (optionnelle) :

```bash
make prod-down
docker run --rm -v localpdf_api-data:/data -v /var/backups/localpdf:/b alpine \
  cp /b/sessions-<horodatage>.db /data/sessions.db
make prod-up
```

(Le nom du volume est `<dossier-du-projet>_api-data` : `docker volume ls`.)

## Partie 2 : mises à jour manuelles

```bash
cd /opt/localpdf
make prod-deploy    # git pull --ff-only, sauvegarde, build, redémarrage, healthcheck (échec = code retour ≠ 0)
```

`prod-deploy` ne déploie que ce qui est sur la branche suivie (`--ff-only` : jamais de fusion automatique). Si la
production n'est pas saine à la fin, la commande échoue : voir `make prod-logs`. Les jobs en cours (TTL 30 min) sont
perdus au redémarrage ; les sessions sont conservées.

Autres commandes utiles : `make prod-ps`, `make prod-logs`, `make prod-restart`, `make prod-health`,
`make prod-down`.

### Retour arrière

Le plus sûr est de passer par Git, donc par le même chemin que la CI :

```bash
git revert <commit-fautif>        # sur votre poste
git push origin main              # la CI repasse, le déploiement continu redéploie
```

En urgence, sur le serveur, sans attendre la CI :

```bash
cd /opt/localpdf
git log --oneline -5                       # repérer le dernier bon commit
git checkout --detach <bon-commit>
make prod-build prod-up prod-health
# puis, une fois la correction poussée sur main :
git checkout main && make prod-deploy
```

## Partie 3 : déploiement automatique (facultatif)

Inutile si vous déployez à la main avec `make prod-deploy` : c'est le mode par défaut, et la CI
(`.github/workflows/ci.yml`) se contente alors de lancer les tests et le lint. Cette partie n'est utile que si vous
voulez que la production se mette à jour sans vous connecter. Il y a deux modèles.

### Modèle « pull » : aucun secret chez GitHub (recommandé si vous le voulez)

Le serveur vérifie lui-même `main` toutes les 5 minutes et lance `make prod-deploy` uniquement si le commit a changé
**et** que ses checks GitHub sont tous verts. GitHub ne connaît ni clé, ni mot de passe, ni `.env`.

Script root `/usr/local/sbin/pull-deploy-localpdf` (0755) :

```bash
#!/usr/bin/env bash
set -euo pipefail
GH_REPO=Florent-V/LocalPDF               # dépôt public ; dépôt privé : voir plus bas
exec 9>/run/lock/deploy-localpdf.lock
flock -n 9 || exit 0
cd /opt/localpdf
runuser -u ubuntu -- git fetch --quiet origin main
[ "$(runuser -u ubuntu -- git rev-parse HEAD)" = "$(runuser -u ubuntu -- git rev-parse origin/main)" ] && exit 0
remote_sha=$(runuser -u ubuntu -- git rev-parse origin/main)
bad=$(curl -fsS "https://api.github.com/repos/$GH_REPO/commits/$remote_sha/check-runs" \
  | jq '[.check_runs[] | select(.status != "completed" or (.conclusion | IN("success","skipped","neutral") | not))] | length')
[ "$bad" = "0" ] || { echo "CI non verte pour $remote_sha, déploiement reporté"; exit 0; }
exec runuser -u ubuntu -- make prod-deploy BACKUP_DIR=/var/backups/localpdf
```

Timer systemd :

```ini
# /etc/systemd/system/pull-deploy-localpdf.service
[Unit]
Description=Pull-deploy LocalPDF
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/pull-deploy-localpdf

# /etc/systemd/system/pull-deploy-localpdf.timer
[Unit]
Description=Vérifie main toutes les 5 min
[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now pull-deploy-localpdf.timer
journalctl -u pull-deploy-localpdf -f      # suivi
sudo systemctl disable --now pull-deploy-localpdf.timer   # pour revenir au déploiement manuel
```

Dépôt privé : `git fetch` avec une deploy key en lecture seule (Settings → Deploy keys), et l'appel à l'API avec un
fine-grained token « Checks: read » limité à ce dépôt, stocké en `0600` root sur le serveur (jamais chez GitHub).

### Modèle « push SSH » : GitHub se connecte au serveur

Moins recommandé pour vous : il faut stocker une clé SSH de déploiement dans les secrets GitHub. Elle peut être
limitée à une commande forcée (qui ne sait que lancer `make prod-deploy`), mais c'est tout de même un secret chez
GitHub. La mise en place (utilisateur dédié, `authorized_keys` à commande forcée, environment `production`, job
`deploy` dans le workflow) est décrite dans `deploy-setup.md`, §1 à §3, de la compétence `securing-ci-cd`. Rien de
cela n'est actif dans ce dépôt.

### Dans tous les cas

- Protégez `main` (pull request obligatoire, checks `backend` et `frontend` requis, pas de force-push) : ce qui est
  sur `main` est ce qui sera déployé.
- Les actions du workflow sont épinglées par SHA ; `.github/dependabot.yml` propose leurs mises à jour. Un
  `.github/CODEOWNERS` impose votre relecture pour toute modification de `.github/`.
- 2FA sur le compte GitHub, collaborateurs réduits au minimum.

## Aide-mémoire

| Besoin | Commande |
|---|---|
| Premier démarrage | `make prod-build` puis `make prod-up` |
| Mise à jour | Sur le serveur : `make prod-deploy` |
| Vérifier | `make prod-health`, `make prod-ps` |
| Journaux | `make prod-logs` |
| Sauvegarde | `make prod-backup` |
| Redémarrer / arrêter | `make prod-restart` / `make prod-down` |
