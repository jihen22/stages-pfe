from django.test import TestCase
from django.urls import reverse

from accounts.models import Domaine, User
from notifications.models import Notification

from .models import Offre


class OffreValidationTests(TestCase):
    """Item 4: an academic supervisor validates the offers of their own field."""

    @classmethod
    def setUpTestData(cls):
        cls.pro = User.objects.create_user(
            username='pro', password='demo1234', role=User.Role.ENCADRANT_PRO)
        cls.acad_gl = User.objects.create_user(
            username='acad_gl', password='demo1234', role=User.Role.ENCADRANT_ACAD,
            domaine=Domaine.GENIE_LOGICIEL)
        cls.acad_data = User.objects.create_user(
            username='acad_data', password='demo1234', role=User.Role.ENCADRANT_ACAD,
            domaine=Domaine.DATA_IA)
        cls.acad_sans_domaine = User.objects.create_user(
            username='acad_vide', password='demo1234', role=User.Role.ENCADRANT_ACAD)
        cls.admin = User.objects.create_user(
            username='admin', password='demo1234', role=User.Role.ADMIN)

    def _offre(self, titre, domaine, status=Offre.Status.EN_VALIDATION):
        return Offre.objects.create(
            encadrant_pro=self.pro, titre=titre, description='x',
            domaine=domaine, status=status,
        )

    def test_queue_lists_only_own_field_and_offers_without_field(self):
        gl = self._offre('Offre GL', Domaine.GENIE_LOGICIEL)
        data = self._offre('Offre Data', Domaine.DATA_IA)
        sans = self._offre('Offre ancienne', '')
        self._offre('Brouillon GL', Domaine.GENIE_LOGICIEL, Offre.Status.BROUILLON)

        self.client.force_login(self.acad_gl)
        offres = list(self.client.get(reverse('offres:offres_a_valider')).context['offres'])
        self.assertCountEqual(offres, [gl, sans])

        self.client.force_login(self.acad_data)
        offres = list(self.client.get(reverse('offres:offres_a_valider')).context['offres'])
        self.assertCountEqual(offres, [data, sans])

    def test_supervisor_without_field_only_sees_offers_without_field(self):
        self._offre('Offre GL', Domaine.GENIE_LOGICIEL)
        sans = self._offre('Offre ancienne', '')
        self.client.force_login(self.acad_sans_domaine)
        response = self.client.get(reverse('offres:offres_a_valider'))
        self.assertEqual(list(response.context['offres']), [sans])
        self.assertContains(response, "domaine d'expertise n'est pas renseigné")

    def test_supervisor_validates_an_offer_of_their_field(self):
        offre = self._offre('Offre GL', Domaine.GENIE_LOGICIEL)
        self.client.force_login(self.acad_gl)
        response = self.client.post(reverse('offres:offre_valider', args=[offre.pk]))
        self.assertRedirects(response, reverse('offres:offres_a_valider'))
        offre.refresh_from_db()
        self.assertEqual(offre.status, Offre.Status.PUBLIEE)
        self.assertIsNotNone(offre.date_publication)
        self.assertTrue(Notification.objects.filter(user=self.pro, message__contains='validée').exists())

    def test_supervisor_refuses_with_a_reason(self):
        offre = self._offre('Offre GL', Domaine.GENIE_LOGICIEL)
        self.client.force_login(self.acad_gl)
        self.client.post(reverse('offres:offre_refuser', args=[offre.pk]), {'motif': 'Trop vague'})
        offre.refresh_from_db()
        self.assertEqual(offre.status, Offre.Status.REFUSEE)
        self.assertEqual(offre.motif_refus, 'Trop vague')
        notification = Notification.objects.get(user=self.pro)
        self.assertIn('Trop vague', notification.message)

    def test_supervisor_cannot_decide_on_another_field(self):
        offre = self._offre('Offre Data', Domaine.DATA_IA)
        self.client.force_login(self.acad_gl)
        self.assertEqual(
            self.client.post(reverse('offres:offre_valider', args=[offre.pk])).status_code, 404)
        self.assertEqual(
            self.client.post(reverse('offres:offre_refuser', args=[offre.pk])).status_code, 404)
        offre.refresh_from_db()
        self.assertEqual(offre.status, Offre.Status.EN_VALIDATION)

    def test_offer_not_waiting_for_validation_cannot_be_validated(self):
        offre = self._offre('Brouillon', Domaine.GENIE_LOGICIEL, Offre.Status.BROUILLON)
        self.client.force_login(self.acad_gl)
        response = self.client.post(reverse('offres:offre_valider', args=[offre.pk]))
        self.assertEqual(response.status_code, 404)

    def test_admin_and_other_roles_cannot_validate(self):
        offre = self._offre('Offre GL', Domaine.GENIE_LOGICIEL)
        for user in (self.admin, self.pro):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.post(reverse('offres:offre_valider', args=[offre.pk]))
                self.assertEqual(response.status_code, 403)
        offre.refresh_from_db()
        self.assertEqual(offre.status, Offre.Status.EN_VALIDATION)

    def test_validation_requires_post(self):
        offre = self._offre('Offre GL', Domaine.GENIE_LOGICIEL)
        self.client.force_login(self.acad_gl)
        response = self.client.get(reverse('offres:offre_valider', args=[offre.pk]))
        self.assertEqual(response.status_code, 405)


class OffreFormDomaineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pro = User.objects.create_user(
            username='pro', password='demo1234', role=User.Role.ENCADRANT_PRO)

    def test_field_is_required_when_creating_an_offer(self):
        self.client.force_login(self.pro)
        response = self.client.post(reverse('offres:offre_create'), {
            'titre': 'Stage', 'description': 'x', 'type': Offre.Type.STAGE, 'action': 'soumettre',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('domaine', response.context['form'].errors)
        self.assertFalse(Offre.objects.exists())
