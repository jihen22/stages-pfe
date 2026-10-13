# Contribuer au projet — Plateforme de Gestion des Stages et PFE

Merci de contribuer 🙌 Ce document explique comment travailler sur le dépôt **sans casser la branche `main`**.

> ⚠️ **Règle d'or : on ne pousse JAMAIS directement sur `main`.**
> La branche `main` est protégée : toute modification doit passer par une **branche** puis une **Pull Request (PR)** approuvée par le mainteneur.

---

## 1. Prérequis

- **Python 3.10+** (testé avec 3.10.11)
- **Django 5.2** (voir `requirements.txt`)
- **Git**

## 2. Installation (une seule fois)

```bash
git clone https://github.com/jihen22/stages-pfe.git
cd stages-pfe

# (recommandé) environnement virtuel
python -m venv .venv
# Windows :
.venv\Scripts\activate
# macOS / Linux :
source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Préparer la base de données et les données de démo

```bash
python manage.py migrate
python manage.py create_demo_users    # 1 compte par rôle (mot de passe : demo1234)
python manage.py seed_demo            # offres, candidatures, profil, notifications
```

Comptes de démonstration (mot de passe `demo1234`) :

| Rôle | Identifiant |
|---|---|
| Étudiant | `etudiant` |
| Encadrant professionnel | `encadrant_pro` |
| Encadrant académique | `encadrant_acad` |
| Administration | `admin` |
| Jury | `jury` |

## 4. Lancer le serveur

```bash
python manage.py runserver
```

→ http://127.0.0.1:8000/

## 5. Travailler sur une modification (workflow)

```bash
# 1. Se mettre à jour
git checkout main
git pull origin main

# 2. Créer une branche (nom explicite)
git checkout -b feat/mon-profil-etudiant

# 3. Coder, puis lancer les tests
python manage.py test

# 4. Enregistrer et pousser SA branche (pas main !)
git add .
git commit -m "feat: ajout de la page profil étudiant"
git push origin feat/mon-profil-etudiant
```

5. Sur GitHub : clique **Compare & pull request** pour ta branche.
6. Le mainteneur **relit et approuve** → la PR est fusionnée.

> La branche `main` étant protégée, un `git push origin main` sera **refusé**. C'est normal.

## 6. Conventions

**Branches**
- `feat/...` : nouvelle fonctionnalité
- `fix/...` : correction de bug
- `docs/...` : documentation
- `refactor/...` : réorganisation sans changement de comportement

**Commits** — format court inspiré de *Conventional Commits* :
```
feat: ajout des notifications
fix: corrige le calcul de complétion du profil
docs: mise à jour du README
```

## 7. Tests

Tout changement doit **laisser la suite de tests verte** :

```bash
python manage.py test
```

Ajoute des tests pour toute nouvelle vue ou règle métier (permissions, transitions de statut, etc.).

## 8. Avant d'ouvrir la PR

- [ ] `python manage.py test` passe
- [ ] Le code respecte le style existant (apps par fonctionnalité : `forms.py`, `views.py`, `urls.py`)
- [ ] Les migrations sont incluses si tu as modifié un modèle (`python manage.py makemigrations`)
- [ ] Une PR claire et limitée à un seul sujet

Merci ! 🎓
