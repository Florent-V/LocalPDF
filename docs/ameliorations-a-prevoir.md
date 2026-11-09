# Améliorations à prévoir

Points connus, volontairement laissés en l'état. Ce fichier est identique dans les dépôts ImageTools et pdf-tools : toute évolution se reporte dans les deux.

## IP cliente et `FORWARDED_ALLOW_IPS`

**État actuel**
- `docker-compose.yml` : `FORWARDED_ALLOW_IPS: "*"` sur le service `api`. Uvicorn fait confiance aux en-têtes `X-Forwarded-*` de n'importe quel appelant.
- En prod, c'est acceptable : `api` ne publie aucun port, seul le conteneur `web` (Caddy) l'atteint.
- En dev, `api` est en `network_mode: host` : n'importe quel client local peut forger ces en-têtes (sans conséquence sur une machine de dev).
- `frontend/Caddyfile` n'a pas de `trusted_proxies`. Le Caddy du conteneur `web` remplace donc le `X-Forwarded-For` reçu du Caddy de l'hôte par l'IP de ce dernier : l'API voit l'IP du proxy, pas celle du client (comportement par défaut de Caddy, à confirmer dans les journaux de prod).

**Ce que fait (et ne fait pas) ce paramètre**
- Deux conteneurs du même réseau Compose se parlent toujours (`web` joint `api` par `api:8000`) : `FORWARDED_ALLOW_IPS` n'y change rien.
- Il décide seulement si uvicorn croit les en-têtes `X-Forwarded-For` et `X-Forwarded-Proto` envoyés par l'appelant. Par défaut, uvicorn ne les croit que pour `127.0.0.1`. Derrière Caddy (une IP `172.x`), il les ignorerait : l'API croirait recevoir du `http`, depuis l'IP de Caddy.
- `"*"` ne veut donc pas dire « tout le monde peut appeler l'API » : le filtrage des appelants est fait par le réseau Compose (pas de `ports:` sur `api`). En prod, « tout le monde » revient en pratique à « seulement `web` ».
- On ne met pas l'IP ou le nom de `web` directement : son IP est attribuée dynamiquement (elle change à la recréation du conteneur), et la variable n'accepte que des IP ou des sous-réseaux, pas des noms de service. D'où l'idée du sous-réseau fixe.
- Le sous-réseau fixe restreint la confiance au réseau du projet. Un conteneur compromis dans ce même réseau pourrait encore forger ces en-têtes : c'est une défense en plus, au gain limité.

**Historique**
- Ancien pdf-tools : le mode prod avait `--proxy-headers --forwarded-allow-ips=*` en ligne de commande ; le mode dev n'avait rien (pas de proxy devant `api`, cookie sans `Secure`, donc sans conséquence). Un dev sans ce réglage ne reflétait pas la prod : il ne l'aurait pas testée.
- Ancien ImageTools : déjà `FORWARDED_ALLOW_IPS: "*"` dans le compose de base.
- Aujourd'hui, les deux projets ont la même commande et la même variable en dev et en prod, pour ne plus avoir de différence cachée jusqu'à la mise en production.

**Impact**
Faible. Le rate limit de pdf-tools (`app/core/limiter.py`) utilise `user:{sub}` pour les utilisateurs connectés. L'IP n'est qu'un repli, et le middleware d'auth renvoie déjà 401 aux anonymes sous `/api`. ImageTools n'a pas de limiteur par IP. L'IP n'apparaît que dans les journaux d'accès.

**À faire plus tard**
1. Fixer un sous-réseau par projet dans `docker-compose.yml` (un différent par projet, libre sur l'hôte), à trouver avec `docker network inspect <projet>_default` :
   ```yaml
   networks:
     default:
       ipam:
         config:
           - subnet: 172.30.10.0/24
   ```
2. Remplacer `FORWARDED_ALLOW_IPS: "*"` par ce sous-réseau, dans `docker-compose.prod.yml` seulement (laisser `"*"` en dev).
3. Pour récupérer la vraie IP client, ajouter dans les options globales de `frontend/Caddyfile` (identique dans les deux dépôts) :
   ```
   servers {
       trusted_proxies static private_ranges
   }
   ```
4. Vérifier en prod : l'IP vue par l'API (journaux uvicorn) est celle du client, et non celle du proxy.

À traiter aussi si le port de `api` est un jour publié ou placé derrière un autre proxy.
