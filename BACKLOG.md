# Backlog produit

Total: 168 jours-homme. AI items: 9, 24 to 34 (61 j). Non-AI items: 107 j.
The old item 10 (Docker / CI) was removed and items 11 to 40 were renumbered 10 to 39. The project keeps its current base (SQLite, no Docker).
Mixed items: 10 (AI suggestion), 26 (display), 35 (predictive indicators).

| ID | User story / Tâche | Priorité | Durée | Type |
|----|--------------------|----------|-------|------|
| 1 | En tant qu'utilisateur, je veux m'inscrire et m'authentifier selon mon rôle, pour accéder à mon espace. | Haute | 5 j | Web |
| 2 | En tant qu'utilisateur connecté, je veux consulter et modifier mon profil, pour garder mes informations à jour. | Moyenne | 2 j | Web |
| 3 | En tant qu'encadrant professionnel, je veux publier une offre de stage ou de PFE, pour recruter des étudiants. | Haute | 3 j | Web |
| 4 | En tant qu'encadrant académique, je veux valider une offre relevant de mon domaine avant sa publication, pour garantir sa pertinence académique. | Haute | 2 j | Web |
| 5 | En tant qu'étudiant, je veux rechercher et consulter les offres, pour trouver un stage ou un PFE. | Haute | 3 j | Web |
| 6 | En tant qu'étudiant, je veux postuler en ligne avec un CV et une lettre de motivation, pour candidater. | Haute | 4 j | Web |
| 7 | En tant qu'étudiant, je veux suivre l'état de ma candidature et être notifié à chaque changement de statut, pour réagir rapidement. | Haute | 4 j | Web |
| 8 | En tant qu'encadrant professionnel, je veux consulter les candidatures reçues, pour choisir un candidat. | Haute | 2 j | Web |
| 9 | Collecter et structurer de façon anonymisée les données du processus pour alimenter les modèles d'IA. | Haute | 3 j | IA |
| 10 | En tant qu'encadrant académique, je veux affecter un sujet de PFE à un étudiant selon mon domaine d'expertise, à partir d'une suggestion fondée sur le domaine et la charge, pour garantir un encadrement pertinent. | Haute | 6 j | Mixte |
| 11 | En tant qu'étudiant, je veux échanger avec mon encadrant dans un espace de suivi, pour être accompagné. | Haute | 4 j | Web |
| 12 | En tant qu'étudiant, je veux déposer mes livrables avec l'historique des versions, pour justifier mon avancement. | Haute | 4 j | Web |
| 13 | En tant qu'encadrant académique, je veux valider un livrable ou demander une correction, pour contrôler la qualité. | Haute | 3 j | Web |
| 14 | En tant que système, je veux gérer le cycle de vie d'un PFE par une machine à états, pour assurer la cohérence du suivi. | Haute | 6 j | Web |
| 15 | En tant qu'encadrant professionnel, je veux suivre l'avancement de l'étudiant et participer à l'évaluation du stage, pour l'accompagner. | Moyenne | 3 j | Web |
| 16 | En tant qu'encadrant académique, je veux consulter ma charge d'encadrement, pour planifier mon suivi. | Moyenne | 2 j | Web |
| 17 | En tant qu'administrateur, je veux générer les documents (convention, attestation, PV), pour gagner du temps. | Haute | 5 j | Web |
| 18 | En tant qu'encadrant professionnel, je veux valider la convention générée, pour officialiser le stage. | Haute | 2 j | Web |
| 19 | En tant qu'administrateur, je veux planifier les soutenances selon les jurys, les salles et les créneaux, pour organiser les sessions. | Haute | 6 j | Web |
| 20 | En tant qu'administrateur, je veux détecter et résoudre les conflits de planning, pour éviter les doubles réservations. | Haute | 5 j | Web |
| 21 | En tant que membre du jury, je veux consulter ma convocation, mon planning et les rapports, et saisir les notes, pour évaluer la soutenance. | Moyenne | 5 j | Web |
| 22 | En tant qu'étudiant, je veux consulter mon planning de soutenance et ma convocation, pour me préparer. | Moyenne | 2 j | Web |
| 23 | En tant qu'administrateur, je veux un journal des actions critiques, pour assurer la traçabilité. | Moyenne | 3 j | Web |
| 24 | Mettre en place un service de modèles d'IA indépendant, appelé de façon asynchrone par le backend. | Haute | 5 j | IA |
| 25 | Extraire les compétences des CV et calculer les vecteurs (embeddings) des CV et des offres. | Haute | 5 j | IA |
| 26 | Calculer le score de compatibilité CV-offre et l'afficher à l'étudiant. | Haute | 8 j | Mixte |
| 27 | Générer une justification et un score de confiance pour chaque résultat de modèle. | Haute | 4 j | IA |
| 28 | Classer les candidatures reçues par score de pertinence pour l'encadrant professionnel. | Moyenne | 3 j | IA |
| 29 | Recommander à l'étudiant des offres personnalisées selon son profil. | Moyenne | 4 j | IA |
| 30 | Calculer le score de similarité d'un rapport et repérer les passages proches, à l'attention de l'encadrant académique. | Haute | 8 j | IA |
| 31 | Calculer l'indicateur de risque de retard ou de difficulté et ses facteurs explicatifs, à l'attention de l'encadrant académique. | Haute | 8 j | IA |
| 32 | Détecter les candidatures anormales et alerter l'administrateur pour vérification. | Moyenne | 6 j | IA |
| 33 | Journaliser les versions de modèles utilisées pour chaque résultat. | Moyenne | 3 j | IA |
| 34 | Contrôler la qualité et la confidentialité des données utilisées par les modèles. | Moyenne | 4 j | IA |
| 35 | En tant qu'administrateur, je veux consulter des tableaux de bord analytiques, avec des indicateurs prédictifs, pour piloter la plateforme. | Moyenne | 6 j | Mixte |
| 36 | En tant qu'utilisateur, je veux une application rapide et stable (tests d'intégration, optimisation, correction des anomalies), pour travailler sans interruption. | Haute | 6 j | Web |
| 37 | En tant qu'utilisateur, je veux accéder à l'application via une URL stable sur l'environnement de production. | Haute | 5 j | Web |
| 38 | En tant qu'équipe, je veux rédiger une documentation technique et un manuel utilisateur, pour faciliter la maintenance et la prise en main. | Moyenne | 4 j | Web |
| 39 | En tant que client, je veux valider l'application lors d'une recette finale, pour confirmer sa conformité au cahier des charges. | Haute | 5 j | Web |
