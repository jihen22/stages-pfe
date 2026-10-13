"""Create idempotent demo data for the student experience.

Usage:
    python manage.py seed_demo

Creates/updates:
    * 6 offers (various statuses) owned by the ``encadrant_pro`` demo account;
    * a filled student profile for the ``etudiant`` demo account;
    * 3 applications in different statuses;
    * 3 notifications for the student.

Safe to run multiple times: existing rows are reused/updated.
"""

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils import timezone

from accounts.models import ProfilEtudiant, User
from candidatures.models import Candidature
from notifications.models import Notification
from offres.models import Offre

# (titre, type, status, competences, duree)
OFFRES = [
    ('Stage Développement Web Django', Offre.Type.STAGE, Offre.Status.PUBLIEE,
     'Python, Django, HTML/CSS', '3 mois'),
    ('PFE Machine Learning appliqué', Offre.Type.PFE, Offre.Status.PUBLIEE,
     'Python, scikit-learn, pandas', '6 mois'),
    ('PFE Application mobile Flutter', Offre.Type.PFE, Offre.Status.PUBLIEE,
     'Dart, Flutter, REST', '6 mois'),
    ('Stage Data Analyst', Offre.Type.STAGE, Offre.Status.EN_VALIDATION,
     'SQL, Power BI, Excel', '4 mois'),
    ('PFE Sécurité des systèmes', Offre.Type.PFE, Offre.Status.BROUILLON,
     'Linux, Réseaux, Pentest', '6 mois'),
    ('Stage DevOps / Cloud', Offre.Type.STAGE, Offre.Status.REFUSEE,
     'Docker, CI/CD, AWS', '3 mois'),
]

CANDIDATURE_MOTIF = (
    'Bonjour,\n\nJe suis vivement intéressé(e) par cette offre et je pense que mes '
    'compétences correspondent à vos attentes. Je reste à votre disposition pour un entretien.\n\nCordialement.'
)


class Command(BaseCommand):
    help = 'Crée des données de démonstration (offres, candidatures, profil, notifications).'

    def handle(self, *args, **options):
        # Reuse the existing demo accounts without modifying that command.
        call_command('create_demo_users')

        encadrant = User.objects.get(username='encadrant_pro')
        etudiant = User.objects.get(username='etudiant')

        offres = self._seed_offres(encadrant)
        self._seed_profil(etudiant)
        self._seed_candidatures(etudiant, offres)
        self._seed_notifications(etudiant)

        self.stdout.write(self.style.SUCCESS('\nDonnées de démonstration prêtes.'))

    # -- Offers -------------------------------------------------------------
    def _seed_offres(self, encadrant):
        offres = []
        for titre, type_, status, competences, duree in OFFRES:
            offre, _ = Offre.objects.update_or_create(
                encadrant_pro=encadrant,
                titre=titre,
                defaults={
                    'description': f'Offre de démonstration : {titre}.',
                    'competences': competences,
                    'duree': duree,
                    'type': type_,
                    'status': status,
                    'date_publication': timezone.now() if status == Offre.Status.PUBLIEE else None,
                },
            )
            offres.append(offre)
            self.stdout.write(f'  [offre] {titre} ({offre.get_status_display()})')
        return offres

    # -- Student profile ----------------------------------------------------
    def _seed_profil(self, etudiant):
        profil, _ = ProfilEtudiant.objects.get_or_create(user=etudiant)
        profil.filiere = 'Génie logiciel'
        profil.niveau = 'Master 2'
        profil.competences = 'Python, Django, SQL, Git, Docker'
        profil.telephone = '+216 20 123 456'
        profil.bio = (
            'Étudiant en génie logiciel passionné par le développement web et les '
            'applications mobiles. À la recherche d\'un PFE stimulant.'
        )
        if not profil.cv_base:
            profil.cv_base.save('cv_demo.txt', ContentFile('CV de démonstration'), save=False)
        profil.save()
        self.stdout.write(f'  [profil] complétude : {profil.completion}%')

    # -- Applications -------------------------------------------------------
    def _seed_candidatures(self, etudiant, offres):
        publiees = [o for o in offres if o.status == Offre.Status.PUBLIEE]
        statuts = [
            Candidature.Status.EN_ATTENTE,
            Candidature.Status.ACCEPTEE,
            Candidature.Status.REFUSEE,
        ]
        for offre, status in zip(publiees, statuts):
            candidature, _ = Candidature.objects.get_or_create(
                etudiant=etudiant,
                offre=offre,
                defaults={'cv': 'cvs/demo_cv.txt', 'lettre_motivation': CANDIDATURE_MOTIF},
            )
            if candidature.status != status:
                candidature.status = status
                candidature.save(update_fields=['status'])
            self.stdout.write(f'  [candidature] {offre.titre} ({candidature.get_status_display()})')

    # -- Notifications ------------------------------------------------------
    def _seed_notifications(self, etudiant):
        messages = [
            (
                'Votre candidature à « PFE Machine Learning appliqué » a été acceptée.',
                reverse('candidatures:mes_candidatures'),
            ),
            (
                'Votre candidature à « Stage DevOps / Cloud » a été refusée.',
                reverse('candidatures:mes_candidatures'),
            ),
            (
                'Bienvenue ! Complétez votre profil étudiant pour augmenter vos chances.',
                reverse('accounts:profil_etudiant'),
            ),
        ]
        for message, link in messages:
            Notification.objects.get_or_create(user=etudiant, message=message, defaults={'link': link})
            self.stdout.write(f'  [notification] {message[:50]}…')
