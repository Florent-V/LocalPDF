# MASTER PROMPT & CONTEXTE DU PROJET : LocalPDF

## But du projet
Créer une alternative locale, open-source et "Privacy-First" à des outils comme iLovePDF. L'utilisateur doit pouvoir manipuler, convertir et analyser des PDF en local, sans que ses données ne quittent son ordinateur.

## Règles Architecturales & Techniques
1. **Frontend :** VueJS 3 / Nuxt 3 (dernière version). Interface moderne avec **Nuxt UI** et TailwindCSS.
2. **Backend :** Python 3.11+ avec **FastAPI**. Choisi pour sa rapidité et son écosystème PDF (PyMuPDF, pypdf, etc.).
3. **Persistance :** AUCUNE BASE DE DONNÉES. L'application est un service "stateless". Les fichiers sont traités en mémoire ou dans un dossier temporaire chiffré/nettoyé immédiatement après le téléchargement.
4. **Déploiement & Environnement :** 100% Dockerisé via `docker-compose`. 
5. **Commandes :** Utilisation exclusive d'un `Makefile` pour orchestrer le projet (`make up`, `make down`, `make dev-front`, `make dev-back`).
6. **Documentation :** Le code doit être documenté, et un `README.md` exhaustif doit être maintenu.

## Méthodologie de travail
Tu agis en tant que Développeur Full-Stack Senior et Expert DevOps. 
Le projet est divisé en plusieurs phases (fichiers markdown). Pour chaque phase que je te fournis :
- Analyse les tâches (les cases à cocher `[ ]`).
- Propose l'architecture technique pour cette phase.
- Écris le code étape par étape.
- Coche les cases (en remplaçant `[ ]` par `[x]`) au fur et à mesure de tes réponses pour me montrer l'avancement.
