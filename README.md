# Plateforme de Gestion des Stages et PFE

Application Django de gestion des stages et des projets de fin d'études (PFE) :
offres et candidatures, projets PFE et livrables, encadrement académique,
planification des soutenances et saisie des notes.

## Prérequis

- Python 3.10+ (testé avec 3.10.11)
- Django 5.2 (voir `requirements.txt`)
- Git

## Installation

```bash
git clone https://github.com/jihen22/stages-pfe.git
cd stages-pfe

# Environnement virtuel (recommandé)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Base de données et données de démonstration

```bash
python manage.py migrate
python manage.py create_demo_users   # un compte par rôle
python manage.py seed_demo          # offres, candidatures, profil, notifications
python manage.py seed_showcase      # projets PFE, livrables, soutenances, notes
```

`seed_showcase` est **idempotente** : vous pouvez la relancer sans créer de
doublons. Elle ajoute notamment :

- 5 projets PFE (dont 2 en attente d'un encadrant académique)
- 8 livrables avec un fichier PDF téléchargeable
- 3 soutenances (une déjà notée 16,75/20) et le planning des deux autres
- 1 étudiant sans projet, disponible dans le formulaire « Créer un projet »

Les fichiers des livrables proviennent de `rapportpfe.pdf` à la racine du projet
s'il existe (fichier personnel, non versionné), sinon du PDF neutre
`fixtures/demo_report.pdf` fourni avec le dépôt. Pour utiliser un autre fichier :

```bash
python manage.py seed_showcase --report chemin/vers/mon-rapport.pdf
```

## Comptes de démonstration

Mot de passe : `demo1234`

| Rôle | Identifiants |
|---|---|
| Étudiants | `etudiant` (Sami), `etudiant2` (Ines), `etudiant3` (Yassine), `etudiant4` (Nour), `etudiant5` (Mehdi) |
| Encadrants académiques | `encadrant_acad` (Leila), `encadrant_acad2` (Ridha) |
| Encadrant professionnel | `encadrant_pro` (Karim) |
| Administration | `admin` |
| Jury | `jury`, `jury2` |

Le compte personnel `jihenmess22`, s'il existe dans la base, conserve son propre
mot de passe ; la commande lui ajoute simplement un projet encadré.

## Lancer le serveur

```bash
python manage.py runserver
```

Puis ouvrir http://127.0.0.1:8000/ — ou double-cliquer `start.bat` sous Windows.

## Tests

```bash
python manage.py test
```

## Données locales

`db.sqlite3` et `media/` sont ignorés par Git : ne les poussez jamais. Le fichier
`rapportpfe.pdf` est également destiné à rester local (rapport personnel). Pour
partager un jeu de données, utilisez `python manage.py seed_showcase` plutôt
que la base de données elle-même.

## Contribuer

Le workflow (branches, pull requests, conventions de commits) est décrit dans
[CONTRIBUTING.md](CONTRIBUTING.md).
