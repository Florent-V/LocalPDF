# PHASE 4 : Intelligence Artificielle & Extraction

## Objectif
Intégrer des capacités LLM (Large Language Models) au projet, en gardant la promesse "Privacy-First" (local) tout en offrant l'option d'utiliser des API.

## Tâches Backend (Architecture IA)
- [ ] Mettre en place une architecture modulaire : "Local Provider" (Ollama) vs "API Provider" (OpenAI / Anthropic).
- [ ] Créer une page de configuration UI (stockée dans le `localStorage` du navigateur) pour configurer l'URL locale d'Ollama ou une clé API externe.

## Tâches Backend & Frontend (Features)
- [ ] **Feature : PDF vers Markdown** -> Extraire le texte de manière structurée (titres, listes, tableaux) en utilisant une librairie avancée (ex: `Marker` ou `PyMuPDF4LLM`) et renvoyer un `.md`.
- [ ] **Feature : Résumé par IA** -> Envoyer le texte extrait à l'IA pour générer un résumé synthétique (points clés).
- [ ] **Feature : Traduction** -> Traduire le contenu extrait dans une langue cible via le LLM.
- [ ] **Feature : Chat avec le PDF (Optionnel)** -> UI type chatbot pour poser des questions spécifiques sur le document (RAG très basique en mémoire).

## Validation
- [ ] Mettre à jour le README avec les instructions pour installer Ollama localement si l'utilisateur choisit cette voie.
