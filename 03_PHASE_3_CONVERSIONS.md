# PHASE 3 : Conversions & Dépendances Lourdes

## Objectif
Ajouter la capacité de convertir divers formats en PDF et inversement.

## Tâches Infrastructure
- [ ] Mettre à jour le `Dockerfile` du backend pour installer `LibreOffice` (headless) et `ImageMagick` (ou `Poppler`).
- [ ] Ajuster le `docker-compose.yml` si besoin (augmentation des limites de RAM pour LibreOffice).

## Tâches Backend & Frontend (Features)
- [ ] **Feature : Images vers PDF** -> API & UI pour convertir et compiler JPG, PNG, WEBP en un fichier PDF.
- [ ] **Feature : PDF vers Images** -> API & UI pour extraire chaque page d'un PDF sous forme d'image (ZIP).
- [ ] **Feature : Office vers PDF** -> API & UI pour convertir DOCX, XLSX, PPTX en PDF (via un appel sous-process à LibreOffice headless).
- [ ] **Feature : PDF vers Word** -> API (si possible via une librairie Python existante type `pdf2docx`).

## Validation
- [ ] Tester les temps de réponse sur les grosses conversions.
- [ ] Mettre en place un système de "Loading state" côté UI pour faire patienter l'utilisateur.
