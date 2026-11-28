# Plateforme de gestion des stages et PFE (Tek-Up)

## Contexte
Projet d'équipe (3 étudiants), module Développement de Projet, cycle ingénieur Tek-Up.
Cahier des charges v2.0. Backlog complet dans BACKLOG.md. Avancement dans PROGRESS.md.

## Stack
- Django (backend + templates)
- Bootstrap 5.3 (interface responsive)
- SQLite (base actuelle, à garder)
- App Django `ia` pour les fonctionnalités d'IA (service appelé de façon asynchrone)
- Garder la base du projet telle quelle : pas de Docker, pas de changement de base de données.

## Rôles
Étudiant, encadrant académique, encadrant professionnel, administrateur, membre du jury.

## Décisions fixées (ne pas modifier)
- C'est l'encadrant académique qui affecte les sujets de PFE, pas l'administration.
- L'administration gère uniquement les documents (convention, attestation, PV) et la planification des soutenances.
- Les tâches IA (IDs 9, 24 à 34) sont développées après les fonctionnalités web. Pour les items mixtes (10, 26, 35), construire d'abord la partie web avec un point d'extension vide pour l'IA.

## Définition de « done » pour une user story
Un item est DONE seulement si tout est vrai :
1. Modèle(s) et migration(s) présents
2. Vue(s), URL(s) et template(s) fonctionnels
3. Accès restreint au(x) bon(s) rôle(s)
4. Interface responsive (Bootstrap)
5. Au moins un test automatisé couvre le cas principal

Si une partie manque, l'item est PARTIAL. Sans preuve dans le code, l'item est NOT STARTED.

## Règles de travail
- Implémenter un seul item du backlog à la fois.
- Avant de coder, lire PROGRESS.md et proposer un plan court.
- Après chaque item : lancer les tests, puis mettre à jour PROGRESS.md (statut, fichiers modifiés, ce qui reste).
- Ne pas modifier les migrations déjà appliquées ; en créer de nouvelles.
