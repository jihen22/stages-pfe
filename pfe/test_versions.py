"""Tests for deliverable version history (backlog item 12)."""

import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from notifications.models import Notification

from .charge import charge_encadrant
from .models import Livrable, ProjetPFE, regrouper_versions
from .workflow import peut

MEDIA_ROOT = tempfile.mkdtemp()
S = ProjetPFE.Status
L = Livrable.Status


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class VersionBaseTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT)
        cls.autre = User.objects.create_user(
            username='autre', password='demo1234', role=User.Role.ETUDIANT)
        cls.acad = User.objects.create_user(
            username='acad', password='demo1234', role=User.Role.ENCADRANT_ACAD)
        cls.projet = ProjetPFE.objects.create(etudiant=cls.etudiant, encadrant_acad=cls.acad, sujet='Sujet')

    def _v1(self, status=L.DEPOSE, commentaire_encadrant=''):
        return Livrable.objects.create(
            projet=self.projet, titre='Rapport', fichier='v1.pdf', status=status,
            commentaire_encadrant=commentaire_encadrant)

    def _poster_version(self, livrable, contenu=b'v2', note='Corrections faites'):
        self.client.force_login(self.etudiant)
        return self.client.post(reverse('pfe:nouvelle_version', args=[livrable.pk]), {
            'fichier': SimpleUploadedFile('rapport.pdf', contenu, content_type='application/pdf'),
            'commentaire': note,
        })


class NewVersionTests(VersionBaseTestCase):
    def test_student_uploads_a_new_version_after_corrections(self):
        v1 = self._v1(L.A_CORRIGER, 'Revoir la conclusion')
        response = self._poster_version(v1)
        self.assertRedirects(response, reverse('pfe:mon_pfe'))

        v2 = Livrable.objects.get(version_precedente=v1)
        self.assertEqual((v2.titre, v2.version, v2.status), ('Rapport', 2, L.DEPOSE))
        v1.refresh_from_db()
        self.assertEqual(v1.status, L.A_CORRIGER)  # history is kept as it was
        self.assertEqual(v1.commentaire_encadrant, 'Revoir la conclusion')
        self.assertTrue(Notification.objects.filter(user=self.acad, message__contains='version 2').exists())

    def test_unreviewed_version_is_marked_replaced(self):
        v1 = self._v1(L.DEPOSE)
        self._poster_version(v1)
        v1.refresh_from_db()
        self.assertEqual(v1.status, L.REMPLACE)

    def test_only_the_latest_version_can_get_a_new_one(self):
        v1 = self._v1(L.A_CORRIGER)
        self._poster_version(v1)
        response = self._poster_version(v1, contenu=b'v2 bis')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Livrable.objects.count(), 2)

    def test_versions_chain_up(self):
        v1 = self._v1(L.A_CORRIGER)
        self._poster_version(v1)
        v2 = Livrable.objects.get(version_precedente=v1)
        Livrable.objects.filter(pk=v2.pk).update(status=L.A_CORRIGER)
        self._poster_version(v2)
        v3 = Livrable.objects.get(version_precedente=v2)
        self.assertEqual(v3.version, 3)
        self.assertEqual(list(Livrable.objects.dernieres_versions()), [v3])

    def test_file_is_required(self):
        v1 = self._v1(L.A_CORRIGER)
        self.client.force_login(self.etudiant)
        response = self.client.post(reverse('pfe:nouvelle_version', args=[v1.pk]), {'commentaire': 'x'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('fichier', response.context['form'].errors)

    def test_other_students_cannot_add_a_version(self):
        v1 = self._v1()
        self.client.force_login(self.autre)
        response = self.client.get(reverse('pfe:nouvelle_version', args=[v1.pk]))
        self.assertEqual(response.status_code, 404)

    def test_other_roles_are_forbidden(self):
        v1 = self._v1()
        self.client.force_login(self.acad)
        self.assertEqual(self.client.get(reverse('pfe:nouvelle_version', args=[v1.pk])).status_code, 403)

    def test_closed_project_refuses_new_versions(self):
        v1 = self._v1(L.VALIDE)
        ProjetPFE.objects.filter(pk=self.projet.pk).update(status=S.TERMINE)
        response = self._poster_version(v1)
        self.assertRedirects(response, reverse('pfe:mon_pfe'))
        self.assertEqual(Livrable.objects.count(), 1)

    def test_form_shows_the_current_version_and_feedback(self):
        v1 = self._v1(L.A_CORRIGER, 'Ajouter les tests')
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('pfe:nouvelle_version', args=[v1.pk]))
        self.assertContains(response, 'version 2')
        self.assertContains(response, 'Ajouter les tests')


class HistoryDisplayTests(VersionBaseTestCase):
    def test_regrouper_versions_groups_the_chain(self):
        v1 = self._v1(L.A_CORRIGER)
        v2 = Livrable.objects.create(projet=self.projet, titre='Rapport', fichier='v2.pdf',
                                     version=2, version_precedente=v1, status=L.A_CORRIGER)
        v3 = Livrable.objects.create(projet=self.projet, titre='Rapport', fichier='v3.pdf',
                                     version=3, version_precedente=v2)
        autre = Livrable.objects.create(projet=self.projet, titre='Maquettes', fichier='m.pdf')
        groupes = regrouper_versions(self.projet.livrables.all())
        self.assertEqual(groupes, [(autre, []), (v3, [v2, v1])])

    def test_student_page_shows_latest_version_and_history(self):
        v1 = self._v1(L.A_CORRIGER, 'Revoir la conclusion')
        self._poster_version(v1)
        response = self.client.get(reverse('pfe:mon_pfe'))
        self.assertContains(response, 'v2')
        self.assertContains(response, '1 version précédente')
        self.assertContains(response, 'Revoir la conclusion')
        self.assertContains(response, reverse('pfe:nouvelle_version', args=[Livrable.objects.get(version=2).pk]))
        self.assertNotContains(response, reverse('pfe:nouvelle_version', args=[v1.pk]))


class ReviewWithVersionsTests(VersionBaseTestCase):
    def test_supervisor_reviews_the_new_version_and_sees_the_previous_one(self):
        v1 = self._v1(L.A_CORRIGER, 'Revoir la conclusion')
        self._poster_version(v1)
        self.client.force_login(self.acad)
        response = self.client.get(reverse('pfe:livrables_a_valider'))
        self.assertEqual([lv.version for lv in response.context['livrables']], [2])
        self.assertContains(response, 'Votre remarque : Revoir la conclusion')

    def test_old_or_replaced_versions_cannot_be_reviewed(self):
        v1 = self._v1(L.DEPOSE)
        self._poster_version(v1)  # v1 becomes REMPLACE
        self.client.force_login(self.acad)
        for url in ('pfe:valider_livrable', 'pfe:corriger_livrable'):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(reverse(url, args=[v1.pk])).status_code, 404)
        v1.refresh_from_db()
        self.assertEqual(v1.status, L.REMPLACE)

    def test_already_reviewed_version_cannot_be_reviewed_again(self):
        v1 = self._v1(L.VALIDE)
        self.client.force_login(self.acad)
        response = self.client.post(reverse('pfe:corriger_livrable', args=[v1.pk]))
        self.assertEqual(response.status_code, 404)

    def test_finishing_uses_the_latest_versions(self):
        # v1 approved then v2 sent back for corrections: the deliverable is not approved any more.
        v1 = self._v1(L.VALIDE)
        Livrable.objects.create(projet=self.projet, titre='Rapport', fichier='v2.pdf',
                                version=2, version_precedente=v1, status=L.A_CORRIGER)
        self.assertFalse(peut(self.projet, 'terminer'))

    def test_workload_counts_latest_versions_only(self):
        v1 = self._v1(L.A_CORRIGER)
        Livrable.objects.create(projet=self.projet, titre='Rapport', fichier='v2.pdf',
                                version=2, version_precedente=v1, status=L.A_CORRIGER)
        self.assertEqual(charge_encadrant(self.acad)['livrables_a_corriger'], 1)
