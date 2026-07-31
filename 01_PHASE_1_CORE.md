# PHASE 1 : Initialisation & Organisation PDF

## Objectif
Mettre en place l'architecture Docker/Makefile, le socle Nuxt 3 / FastAPI, et les premières fonctionnalités de manipulation de base (Organisation).

## Tâches Infrastructures
- [ ] Créer le `docker-compose.yml` (Service `frontend` Nuxt, Service `backend` FastAPI).
- [ ] Créer les `Dockerfile` respectifs pour le développement.
- [ ] Créer le `Makefile` avec les commandes de base (`install`, `up`, `down`, `logs`, `clean`).
- [ ] Configurer la communication CORS entre le front et le back.

## Tâches Frontend (Nuxt 3)
- [ ] Initialiser le projet Nuxt 3 avec Nuxt UI.
- [ ] Créer un layout principal (Header, Sidebar/Menu, Footer).
- [ ] Créer un composant générique "Upload de fichier" (Drag & Drop) qui sera réutilisé.
- [ ] Créer la page d'accueil listant les outils disponibles.

## Tâches Backend (FastAPI) & Features PDF
- [ ] Mettre en place un système de gestion de fichiers temporaires (upload, traitement, renvoi à l'utilisateur, suppression automatique).
- [ ] **Feature : Fusionner** -> API pour recevoir `N` fichiers PDF et renvoyer un PDF unique fusionné. Créer l'UI correspondante.
- [ ] **Feature : Diviser** -> API pour extraire toutes les pages ou une plage de pages d'un PDF. Créer l'UI correspondante.
- [ ] **Feature : Organiser** -> API pour changer l'ordre des pages ou supprimer des pages spécifiques. UI permettant de visualiser les miniatures et de les drag & drop.

## Validation
- [ ] Mettre à jour la documentation (README).
