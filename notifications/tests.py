import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from candidatures.models import Candidature
from offres.models import Offre

from .models import Notification
from .services import notify

MEDIA_ROOT = tempfile.mkdtemp()


class NotifyHelperTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT
        )

    def test_notify_creates_notification(self):
        notification = notify(self.user, 'Bonjour', link='/candidatures/')
        self.assertIsNotNone(notification)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.message, 'Bonjour')
        self.assertEqual(notification.link, '/candidatures/')
        self.assertFalse(notification.is_read)

    def test_notify_without_user_returns_none(self):
        self.assertIsNone(notify(None, 'Bonjour'))


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class NotificationWorkflowTests(TestCase):
    """Notifications produced by the candidature workflow."""

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
        cls.offre = Offre.objects.create(
            encadrant_pro=cls.encadrant, titre='Stage Django',
            description='x', status=Offre.Status.PUBLIEE,
        )

    def _apply(self):
        cv = SimpleUploadedFile('cv.txt', b'mon cv', content_type='text/plain')
        return self.client.post(reverse('candidatures:postuler', args=[self.offre.pk]), {
            'cv': cv,
            'lettre_motivation': 'Je suis motivé.',
        })

    def test_applying_notifies_the_supervisor(self):
        self.client.force_login(self.etudiant)
        self._apply()
        notification = Notification.objects.get(user=self.encadrant)
        self.assertIn('Stage Django', notification.message)
        self.assertEqual(notification.link, reverse('candidatures:candidatures_recues'))

    def test_accepting_notifies_the_student(self):
        candidature = Candidature.objects.create(
            etudiant=self.etudiant, offre=self.offre,
            cv='cvs/demo.txt', lettre_motivation='x',
        )
        self.client.force_login(self.encadrant)
        self.client.post(reverse('candidatures:accepter', args=[candidature.pk]))
        notification = Notification.objects.get(user=self.etudiant)
        self.assertIn('acceptée', notification.message)

    def test_refusing_notifies_the_student(self):
        candidature = Candidature.objects.create(
            etudiant=self.etudiant, offre=self.offre,
            cv='cvs/demo.txt', lettre_motivation='x',
        )
        self.client.force_login(self.encadrant)
        self.client.post(reverse('candidatures:refuser', args=[candidature.pk]))
        notification = Notification.objects.get(user=self.etudiant)
        self.assertIn('refusée', notification.message)


class NotificationViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT)
        cls.autre = User.objects.create_user(
            username='autre', password='demo1234', role=User.Role.ENCADRANT_PRO)

    def test_list_requires_login(self):
        response = self.client.get(reverse('notifications:list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_list_is_visible_for_every_role(self):
        self.client.force_login(self.autre)
        self.assertEqual(self.client.get(reverse('notifications:list')).status_code, 200)

    def test_user_can_mark_own_notification_as_read(self):
        notification = notify(self.etudiant, 'Coucou', link='/candidatures/')
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('notifications:read', args=[notification.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/candidatures/')
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_user_cannot_read_another_users_notification(self):
        notification = notify(self.etudiant, 'Coucou')
        self.client.force_login(self.autre)
        response = self.client.get(reverse('notifications:read', args=[notification.pk]))
        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_mark_all_read(self):
        notify(self.etudiant, 'Un')
        notify(self.etudiant, 'Deux')
        notify(self.autre, 'Autre')
        self.client.force_login(self.etudiant)
        response = self.client.post(reverse('notifications:mark_all_read'))
        self.assertRedirects(response, reverse('notifications:list'))
        self.assertFalse(self.etudiant.notifications.filter(is_read=False).exists())
        # The other user's notification is untouched.
        self.assertTrue(self.autre.notifications.filter(is_read=False).exists())
