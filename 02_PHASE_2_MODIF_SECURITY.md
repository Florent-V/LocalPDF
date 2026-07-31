# PHASE 2 : Modification et Sécurité

## Objectif
Ajouter les fonctionnalités de modification visuelle et de protection des documents.

## Tâches Backend & Frontend (Features)
- [ ] **Feature : Rotation** -> API & UI pour pivoter une ou toutes les pages d'un PDF (90°, 180°, 270°).
- [ ] **Feature : Filigrane (Watermark)** -> API & UI pour ajouter un texte ou une image en filigrane (choix de l'opacité, position).
- [ ] **Feature : Mot de passe** -> API & UI pour chiffrer/verrouiller un PDF avec un mot de passe.
- [ ] **Feature : Déverrouiller** -> API & UI pour retirer la protection d'un PDF (nécessite le mot de passe d'origine).
- [ ] **Feature : Censure (Redaction)** -> API & UI. Permettre à l'utilisateur de tracer des rectangles sur l'UI (ou de cibler du texte) pour noircir de manière irréversible des champs sensibles.
- [ ] **Feature : Remplissage de formulaire** -> Détecter les champs d'un formulaire PDF et générer une UI pour les remplir.

## Validation
- [ ] Ajouter les tests unitaires basiques côté backend pour ces manipulations.
- [ ] S'assurer que les fichiers temporaires ne fuient pas en cas d'erreur serveur.
