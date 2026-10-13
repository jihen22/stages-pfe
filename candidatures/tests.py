import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from offres.models import Offre

from .models import Candidature

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class WorkflowTests(TestCase):
    """Full pipeline: create offer -> validate -> apply -> decision."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT)
        cls.encadrant = User.objects.create_user(
            username='pro', password='demo1234', role=User.Role.ENCADRANT_PRO)
        cls.admin = User.objects.create_user(
            username='admin', password='demo1234', role=User.Role.ADMIN)

    def test_full_workflow(self):
        # 1. Company supervisor creates and submits an offer.
        self.client.force_login(self.encadrant)
        response = self.client.post(reverse('offres:offre_create'), {
            'titre': 'Stage Django',
            'description': 'Développement d\'une application Django.',
            'competences': 'Python, Django',
            'duree': '6 mois',
            'type': Offre.Type.STAGE,
            'action': 'soumettre',
        })
        self.assertEqual(response.status_code, 302)
        offre = Offre.objects.get()
        self.assertEqual(offre.status, Offre.Status.EN_VALIDATION)
        self.assertEqual(offre.encadrant_pro, self.encadrant)

        # 2. Administration validates the offer.
        self.client.force_login(self.admin)
        response = self.client.post(reverse('offres:offre_valider', args=[offre.pk]))
        self.assertEqual(response.status_code, 302)
        offre.refresh_from_db()
        self.assertEqual(offre.status, Offre.Status.PUBLIEE)
        self.assertIsNotNone(offre.date_publication)

        # 3. Student sees it and applies with a CV.
        self.client.force_login(self.etudiant)
        self.assertEqual(self.client.get(reverse('offres:offre_list')).status_code, 200)
        cv = SimpleUploadedFile('cv.txt', b'mon cv', content_type='text/plain')
        response = self.client.post(reverse('candidatures:postuler', args=[offre.pk]), {
            'cv': cv,
            'lettre_motivation': 'Je suis très motivé.',
        })
        self.assertEqual(response.status_code, 302)
        candidature = Candidature.objects.get()
        self.assertEqual(candidature.status, Candidature.Status.EN_ATTENTE)
        self.assertEqual(candidature.etudiant, self.etudiant)

        # 4. A second application to the same offer is refused.
        response = self.client.get(reverse('candidatures:postuler', args=[offre.pk]))
        self.assertRedirects(response, reverse('candidatures:mes_candidatures'))
        self.assertEqual(Candidature.objects.count(), 1)

        # 5. Supervisor accepts the application.
        self.client.force_login(self.encadrant)
        response = self.client.post(reverse('candidatures:accepter', args=[candidature.pk]))
        self.assertEqual(response.status_code, 302)
        candidature.refresh_from_db()
        self.assertEqual(candidature.status, Candidature.Status.ACCEPTEE)

    def test_apply_to_unpublished_offer_is_blocked(self):
        offre = Offre.objects.create(
            encadrant_pro=self.encadrant, titre='Brouillon',
            description='x', status=Offre.Status.BROUILLON,
        )
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('candidatures:postuler', args=[offre.pk]))
        self.assertEqual(response.status_code, 404)

    def test_duplicate_application_is_blocked(self):
        offre = Offre.objects.create(
            encadrant_pro=self.encadrant, titre='Stage', description='x',
            status=Offre.Status.PUBLIEE,
        )
        self.client.force_login(self.etudiant)
        cv = SimpleUploadedFile('cv.txt', b'mon cv', content_type='text/plain')
        self.client.post(reverse('candidatures:postuler', args=[offre.pk]), {
            'cv': cv,
            'lettre_motivation': 'Motivé.',
        })
        self.assertEqual(Candidature.objects.filter(offre=offre).count(), 1)

        # A second attempt (even by GET) is short-circuited.
        response = self.client.get(reverse('candidatures:postuler', args=[offre.pk]))
        self.assertRedirects(response, reverse('candidatures:mes_candidatures'))
        self.assertEqual(Candidature.objects.filter(offre=offre).count(), 1)
