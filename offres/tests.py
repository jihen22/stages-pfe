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


class OffreSearchTests(TestCase):
    """Item 5: students search, filter and open published offers only."""

    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT)
        cls.pro = User.objects.create_user(
            username='pro', password='demo1234', role=User.Role.ENCADRANT_PRO)

        def offre(titre, type_=Offre.Type.STAGE, status=Offre.Status.PUBLIEE, **extra):
            return Offre.objects.create(
                encadrant_pro=cls.pro, titre=titre, description=extra.pop('description', 'x'),
                type=type_, status=status, **extra)

        cls.django = offre('Stage Django', competences='Python, Django')
        cls.ml = offre('PFE Machine Learning', Offre.Type.PFE, description='Modèles de prédiction en Python')
        cls.flutter = offre('PFE Flutter', Offre.Type.PFE, competences='Dart')
        cls.brouillon = offre('Brouillon Django', status=Offre.Status.BROUILLON)
        cls.en_validation = offre('Django en validation', status=Offre.Status.EN_VALIDATION)
        cls.refusee = offre('Django refusé', status=Offre.Status.REFUSEE)

    def setUp(self):
        self.client.force_login(self.etudiant)

    def _liste(self, **params):
        response = self.client.get(reverse('offres:offre_list'), params)
        self.assertEqual(response.status_code, 200)
        return set(response.context['offres'])

    def test_list_shows_only_published_offers(self):
        self.assertEqual(self._liste(), {self.django, self.ml, self.flutter})

    def test_search_matches_title_description_and_skills(self):
        self.assertEqual(self._liste(q='django'), {self.django})          # title + skills
        self.assertEqual(self._liste(q='prédiction'), {self.ml})         # description
        self.assertEqual(self._liste(q='dart'), {self.flutter})          # skills
        self.assertEqual(self._liste(q='python'), {self.django, self.ml})

    def test_type_filter_and_combination_with_search(self):
        self.assertEqual(self._liste(type=Offre.Type.PFE), {self.ml, self.flutter})
        self.assertEqual(self._liste(type=Offre.Type.PFE, q='python'), {self.ml})

    def test_unknown_type_is_ignored(self):
        self.assertEqual(self._liste(type='INCONNU'), {self.django, self.ml, self.flutter})

    def test_no_result_shows_the_empty_state(self):
        self.assertEqual(self._liste(q='cobol'), set())

    def test_results_are_paginated_and_keep_the_search(self):
        for i in range(10):
            Offre.objects.create(encadrant_pro=self.pro, titre=f'Stage Java {i}', description='x',
                                 status=Offre.Status.PUBLIEE)
        response = self.client.get(reverse('offres:offre_list'), {'q': 'java & spring'})
        self.assertEqual(len(response.context['offres']), 0)
        response = self.client.get(reverse('offres:offre_list'), {'q': 'java'})
        self.assertEqual(len(response.context['offres']), 9)
        self.assertTrue(response.context['is_paginated'])
        self.assertContains(response, '?page=2&q=java')
        page2 = self.client.get(reverse('offres:offre_list'), {'q': 'java', 'page': 2})
        self.assertEqual(len(page2.context['offres']), 1)

    def test_search_term_is_url_encoded_in_pagination_links(self):
        for i in range(10):
            Offre.objects.create(encadrant_pro=self.pro, titre=f'C++ & Qt {i}', description='x',
                                 status=Offre.Status.PUBLIEE)
        response = self.client.get(reverse('offres:offre_list'), {'q': 'C++ & Qt'})
        self.assertContains(response, 'q=C%2B%2B%20%26%20Qt')

    def test_student_opens_a_published_offer(self):
        response = self.client.get(reverse('offres:offre_detail', args=[self.django.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Stage Django')
        self.assertFalse(response.context['deja_postule'])
        self.assertContains(response, reverse('candidatures:postuler', args=[self.django.pk]))

    def test_unpublished_offers_cannot_be_opened_by_url(self):
        for offre in (self.brouillon, self.en_validation, self.refusee):
            with self.subTest(status=offre.status):
                response = self.client.get(reverse('offres:offre_detail', args=[offre.pk]))
                self.assertEqual(response.status_code, 404)

    def test_search_is_student_only(self):
        self.client.force_login(self.pro)
        self.assertEqual(self.client.get(reverse('offres:offre_list')).status_code, 403)
