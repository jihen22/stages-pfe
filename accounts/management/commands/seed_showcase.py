"""Create the showcase dataset used for demos and presentations.

Run it after ``migrate``:

    python manage.py seed_showcase

The command is idempotent: running it again updates the same rows instead of
duplicating them. Demo accounts all use ``demo1234`` (the personal
``jihenmess22`` account, when it exists, keeps its own password).

Deliverable files come from ``rapportpfe.pdf`` at the project root when it is
present (personal, never committed), otherwise from ``fixtures/demo_report.pdf``
(the neutral placeholder committed with the repository).
"""
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files.base import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import ProfilEtudiant, User
from offres.models import Offre
from pfe.models import Livrable, ProjetPFE
from soutenances.models import NoteSoutenance, Soutenance

PASSWORD = "demo1234"
PFE_OFFER_TITLE = "PFE — Plateforme de gestion des stages et PFE (Django)"
LOCAL_REPORT = Path(settings.BASE_DIR) / "rapportpfe.pdf"
FALLBACK_REPORT = Path(settings.BASE_DIR) / "fixtures" / "demo_report.pdf"

OFFER_CONTENT = {
    "Stage Développement Web Django": (
        "Participation au développement d'une application web de gestion interne : écrans de "
        "suivi, formulaires et API REST. L'étudiant travaille avec l'équipe produit sur des "
        "tickets réels et livre des fonctionnalités en fin de sprint.",
        "Python, Django, HTML/CSS, SQL",
        "3 mois",
    ),
    "PFE Machine Learning appliqué": (
        "Conception et évaluation d'un modèle de prédiction pour anticiper les besoins en "
        "recrutement, du nettoyage des données jusqu'à la mise en production d'une API de "
        "scoring utilisée par l'équipe RH.",
        "Python, scikit-learn, pandas",
        "6 mois",
    ),
    "PFE Application mobile Flutter": (
        "Développement d'une application mobile de suivi de stage (candidatures, livrables, "
        "notifications) connectée à l'API de la plateforme.",
        "Dart, Flutter, REST",
        "6 mois",
    ),
    "Stage Data Analyst": (
        "Analyse des candidatures et production de tableaux de bord pour le suivi des offres "
        "et des stages. Missions : requêtes SQL, nettoyage des données et visualisation.",
        "SQL, Power BI, Excel",
        "4 mois",
    ),
    "PFE Sécurité des systèmes": (
        "Audit des contrôles d'accès de la plateforme et mise en place d'un plan de remédiation "
        "(authentification, permissions, journalisation).",
        "Linux, Réseaux, Pentest",
        "6 mois",
    ),
    "Stage DevOps / Cloud": (
        "Automatisation du déploiement de la plateforme : conteneurisation, intégration "
        "continue et supervision sur un environnement cloud.",
        "Docker, CI/CD, AWS",
        "3 mois",
    ),
}

LIVRABLES = (
    ("sami", "Rapport de cadrage", Livrable.Status.VALIDE,
     "Cadrage clair, périmètre validé.", "Cadrage du projet et analyse de l'existant."),
    ("sami", "Maquettes de l'interface", Livrable.Status.VALIDE,
     "Maquettes conformes au cahier des charges.", "Maquettes des écrans principaux."),
    ("sami", "Rapport d'avancement - v1", Livrable.Status.A_CORRIGER,
     "Détailler la partie tests et corriger les diagrammes.", "Point d'avancement à mi-parcours."),
    ("sami", "Documentation technique", Livrable.Status.DEPOSE,
     "", "Première version de la documentation technique."),
    ("ines", "Rapport de cadrage", Livrable.Status.DEPOSE,
     "", "Version préliminaire en attente d'un encadrant."),
    ("yassine", "Rapport final", Livrable.Status.VALIDE,
     "Rapport complet, soutenance autorisée.", "Rapport final du projet."),
    ("yassine", "Présentation de soutenance", Livrable.Status.VALIDE,
     "Support clair et bien structuré.", "Support de présentation pour la soutenance."),
    ("jihen", "Rapport de cadrage", Livrable.Status.DEPOSE,
     "", "Cadrage du projet et objectifs du modèle."),
)


def resolve_report(explicit=None):
    """Return the PDF to attach: explicit path, personal report, or placeholder."""
    if explicit:
        return Path(explicit)
    if LOCAL_REPORT.exists():
        return LOCAL_REPORT
    return FALLBACK_REPORT


def ensure_user(username, role, first_name, last_name, email):
    user, _ = User.objects.get_or_create(username=username)
    user.role = role
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.set_password(PASSWORD)
    user.save()
    return user


def at(year, month, day, hour, minute=0):
    return timezone.make_aware(datetime(year, month, day, hour, minute))


class Command(BaseCommand):
    help = "Create the PFE/soutenances showcase dataset (projects, deliverables, defenses)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--report",
            type=Path,
            help="PDF file to attach to the demo deliverables "
                 "(default: ./rapportpfe.pdf, else fixtures/demo_report.pdf).",
        )

    def handle(self, *args, **options):
        say = self.stdout.write
        report = resolve_report(options.get("report"))

        # -- users ---------------------------------------------------------
        etudiant = ensure_user("etudiant", User.Role.ETUDIANT, "Sami", "Ben Ali",
                               "etudiant@example.com")
        etudiant2 = ensure_user("etudiant2", User.Role.ETUDIANT, "Ines", "Bouazizi",
                                "ines.bouazizi@example.com")
        etudiant3 = ensure_user("etudiant3", User.Role.ETUDIANT, "Yassine", "Ferchichi",
                                "yassine.ferchichi@example.com")
        etudiant4 = ensure_user("etudiant4", User.Role.ETUDIANT, "Nour", "Gharbi",
                                "nour.gharbi@example.com")
        etudiant5 = ensure_user("etudiant5", User.Role.ETUDIANT, "Mehdi", "Ayari",
                                "mehdi.ayari@example.com")

        encadrant_acad = ensure_user("encadrant_acad", User.Role.ENCADRANT_ACAD, "Leila",
                                     "Mansouri", "encadrant.acad@example.com")
        encadrant_acad2 = ensure_user("encadrant_acad2", User.Role.ENCADRANT_ACAD, "Ridha",
                                      "Ben Salah", "ridha.bensalah@example.com")
        encadrant_pro = ensure_user("encadrant_pro", User.Role.ENCADRANT_PRO, "Karim",
                                    "Trabelsi", "encadrant.pro@example.com")
        ensure_user("admin", User.Role.ADMIN, "Nadia", "Gharbi", "admin@example.com")
        jury = ensure_user("jury", User.Role.JURY, "Hatem", "Jaziri", "jury@example.com")
        jury2 = ensure_user("jury2", User.Role.JURY, "Sonia", "Khelifi",
                            "sonia.khelifi@example.com")

        for user, filiere, niveau, competences in (
            (etudiant2, "Développement mobile", "Master 2", "Dart, Flutter, Firebase"),
            (etudiant3, "Sécurité informatique", "Master 2", "Linux, Réseaux, Python"),
            (etudiant4, "Génie logiciel", "Master 2", "Python, Django, SQL"),
            (etudiant5, "Data science", "Master 2", "Python, pandas, scikit-learn"),
        ):
            ProfilEtudiant.objects.update_or_create(
                user=user,
                defaults={"filiere": filiere, "niveau": niveau, "competences": competences},
            )

        # -- offers --------------------------------------------------------
        for titre, (description, competences, duree) in OFFER_CONTENT.items():
            offre = Offre.objects.filter(titre=titre).first()
            if offre is None:
                continue
            offre.description = description
            offre.competences = competences
            offre.duree = duree
            offre.save(update_fields=["description", "competences", "duree"])

        offre_pfe = Offre.objects.filter(titre__in=("offre1", PFE_OFFER_TITLE)).first()
        if offre_pfe is None:
            offre_pfe = Offre(encadrant_pro=encadrant_pro)
        offre_pfe.encadrant_pro = encadrant_pro
        offre_pfe.titre = PFE_OFFER_TITLE
        offre_pfe.description = (
            "Refonte et extension de la plateforme de gestion des stages et PFE : parcours de "
            "candidature, suivi des projets, dépôt de livrables et planning des soutenances."
        )
        offre_pfe.competences = "Python, Django, Bootstrap, SQLite"
        offre_pfe.duree = "6 mois"
        offre_pfe.type = Offre.Type.PFE
        offre_pfe.status = Offre.Status.PUBLIEE
        if offre_pfe.date_publication is None:
            offre_pfe.date_publication = timezone.now()
        offre_pfe.save()

        # -- projects ------------------------------------------------------
        projets = {}
        for key, user, encadrant, offre, sujet, description, status in (
            (
                "sami", etudiant, encadrant_acad, offre_pfe,
                "Plateforme de gestion des stages et PFE (Django)",
                "Conception et développement de la plateforme : gestion des offres, "
                "candidatures, projets PFE, livrables et soutenances.",
                ProjetPFE.Status.EN_COURS,
            ),
            (
                "ines", etudiant2, None,
                Offre.objects.filter(titre="PFE Application mobile Flutter").first(),
                "PFE Application mobile Flutter",
                "Application mobile de suivi de stage connectée à l'API de la plateforme.",
                ProjetPFE.Status.EN_COURS,
            ),
            (
                "yassine", etudiant3, encadrant_acad, None,
                "Audit de sécurité de la plateforme de stages",
                "Audit des contrôles d'accès et des flux d'authentification, avec plan de "
                "remédiation.",
                ProjetPFE.Status.SOUTENU,
            ),
            (
                "nour", etudiant4, None, None,
                "Détection des doublons dans les candidatures",
                "Nettoyage et déduplication des candidatures reçues, avec un tableau de bord "
                "de suivi des doublons signalés.",
                ProjetPFE.Status.EN_COURS,
            ),
        ):
            projets[key], _ = ProjetPFE.objects.update_or_create(
                etudiant=user,
                defaults={
                    "encadrant_acad": encadrant,
                    "offre": offre,
                    "sujet": sujet,
                    "description": description,
                    "status": status,
                },
            )

        jihen = User.objects.filter(username="jihenmess22").first()
        if jihen is not None:
            projets["jihen"], _ = ProjetPFE.objects.update_or_create(
                etudiant=jihen,
                defaults={
                    "encadrant_acad": encadrant_acad2,
                    "offre": Offre.objects.filter(titre="PFE Machine Learning appliqué").first(),
                    "sujet": "PFE Machine Learning appliqué",
                    "description": "Mise en place d'un modèle de prédiction des besoins en "
                                   "recrutement et d'une API de scoring.",
                    "status": ProjetPFE.Status.EN_COURS,
                },
            )

        # -- deliverables --------------------------------------------------
        attached = 0
        if not report.exists():
            say(self.style.WARNING(
                f"PDF introuvable : {report} — les livrables resteront sans fichier."
            ))
        for key, titre, status, feedback, commentaire in LIVRABLES:
            projet = projets.get(key)
            if projet is None:
                continue
            livrable, _ = Livrable.objects.update_or_create(
                projet=projet,
                titre=titre,
                defaults={
                    "status": status,
                    "commentaire": commentaire,
                    "commentaire_encadrant": feedback,
                },
            )
            if livrable.fichier and livrable.fichier.storage.exists(livrable.fichier.name):
                continue
            if not report.exists():
                continue
            with open(report, "rb") as handle:
                livrable.fichier.save(
                    f"rapport_pfe_{livrable.pk}.pdf", File(handle), save=True)
            attached += 1

        # -- defenses ------------------------------------------------------
        soutenances = {}
        if "yassine" in projets:
            soutenances["yassine"], _ = Soutenance.objects.update_or_create(
                projet=projets["yassine"],
                defaults={
                    "date": at(2026, 10, 20, 10),
                    "salle": "Amphi C",
                    "remarques": "Bon niveau technique, présentation claire.",
                },
            )
            soutenances["yassine"].jury.set([jury, jury2])
            for member, note, remarque in (
                (jury, "16.50", "Travail solide et bien documenté."),
                (jury2, "17.00", "Excellente maîtrise du sujet."),
            ):
                NoteSoutenance.objects.update_or_create(
                    soutenance=soutenances["yassine"],
                    jury_member=member,
                    defaults={"note": note, "remarque": remarque},
                )

        if "sami" in projets:
            soutenances["sami"], _ = Soutenance.objects.update_or_create(
                projet=projets["sami"],
                defaults={"date": at(2026, 11, 1, 9), "salle": "Amphi A", "remarques": ""},
            )
            soutenances["sami"].jury.set([jury, jury2])

        if "jihen" in projets:
            soutenances["jihen"], _ = Soutenance.objects.update_or_create(
                projet=projets["jihen"],
                defaults={"date": at(2026, 11, 4, 14), "salle": "Salle B12", "remarques": ""},
            )
            soutenances["jihen"].jury.set([jury2])

        # -- summary -------------------------------------------------------
        say("\nShowcase data ready\n")
        say("Offers")
        for offre in Offre.objects.order_by("pk"):
            say(f"  #{offre.pk:<3} {offre.get_type_display():<6} "
                f"{offre.get_status_display():<24} {offre.titre}")

        say("\nProjects")
        for projet in ProjetPFE.objects.select_related("etudiant", "encadrant_acad").order_by("pk"):
            superviseur = projet.encadrant_acad.username if projet.encadrant_acad else "à affecter"
            say(f"  #{projet.pk:<3} {projet.etudiant.username:<12} "
                f"{projet.get_status_display():<10} encadrant={superviseur:<16} "
                f"livrables={projet.livrables.count()}  {projet.sujet}")

        say("\nDefenses")
        for soutenance in Soutenance.objects.order_by("date"):
            moyenne = soutenance.moyenne
            moyenne = f"{moyenne:.2f}" if moyenne is not None else "-"
            moment = timezone.localtime(soutenance.date)
            say(f"  #{soutenance.pk:<3} {moment:%d/%m/%Y %H:%M} {soutenance.salle:<10} "
                f"moyenne={moyenne}  {soutenance.projet.sujet[:45]}")

        say(f"\nPDF source: {report}")
        say(f"PDF attached to {attached} deliverable(s)")

        say("\nStudents without a project (available in the create form)")
        for user in User.objects.filter(
            role=User.Role.ETUDIANT, projets_pfe__isnull=True
        ).order_by("username"):
            say(f"  {user.username:<12} {user.get_full_name() or user.username}")

        say("\nLogins (password demo1234):")
        say("  etudiant, etudiant2, etudiant3, etudiant4, etudiant5, encadrant_pro,")
        say("  encadrant_acad, encadrant_acad2, admin, jury, jury2")
        say("  (jihenmess22 keeps its own password)")
