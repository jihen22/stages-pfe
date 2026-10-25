import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from candidatures.models import Candidature
from notifications.models import Notification
from offres.models import Offre

from .models import Livrable, ProjetPFE

MEDIA_ROOT = tempfile.mkdtemp()


class PfeBaseTestCase(TestCase):
    """Fixtures shared by the PFE tests: two supervised projects, one bare student."""

    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT,
        )
        cls.autre_etudiant = User.objects.create_user(
            username='etudiant2', password='demo1234', role=User.Role.ETUDIANT,
        )
        cls.etudiant_sans_projet = User.objects.create_user(
            username='etudiant3', password='demo1234', role=User.Role.ETUDIANT,
        )
        cls.etudiant_en_attente = User.objects.create_user(
            username='etudiant4', password='demo1234', role=User.Role.ETUDIANT,
        )
        cls.encadrant_acad = User.objects.create_user(
            username='acad', password='demo1234', role=User.Role.ENCADRANT_ACAD,
        )
        cls.autre_encadrant_acad = User.objects.create_user(
            username='acad2', password='demo1234', role=User.Role.ENCADRANT_ACAD,
        )
        cls.encadrant_pro = User.objects.create_user(
            username='pro', password='demo1234', role=User.Role.ENCADRANT_PRO,
        )
        cls.admin = User.objects.create_user(
            username='admin', password='demo1234', role=User.Role.ADMIN,
        )

        cls.offre = Offre.objects.create(
            encadrant_pro=cls.encadrant_pro,
            titre='PFE - Plateforme de gestion des stages',
            description='Développement d\'une plateforme Django.',
            type=Offre.Type.PFE,
            status=Offre.Status.PUBLIEE,
        )
        cls.projet = ProjetPFE.objects.create(
            etudiant=cls.etudiant,
            encadrant_acad=cls.encadrant_acad,
            offre=cls.offre,
            sujet='Plateforme de gestion des stages et PFE',
        )
        cls.projet_autre = ProjetPFE.objects.create(
            etudiant=cls.autre_etudiant,
            encadrant_acad=cls.autre_encadrant_acad,
            sujet='Application mobile Flutter',
        )
        cls.projet_en_attente = ProjetPFE.objects.create(
            etudiant=cls.etudiant_en_attente,
            sujet="Sujet en attente d'un encadrant",
        )
        cls.livrable = Livrable.objects.create(
            projet=cls.projet,
            titre='Rapport d\'avancement',
            fichier='livrables/demo.txt',
        )
        cls.livrable_autre = Livrable.objects.create(
            projet=cls.projet_autre,
            titre='Maquettes',
            fichier='livrables/demo2.txt',
        )


class PfeRoleAccessTests(PfeBaseTestCase):
    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse('pfe:mon_pfe'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_mon_pfe_is_student_only(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('pfe:mon_pfe')).status_code, 403)

    def test_supervisor_pages_are_forbidden_to_students(self):
        self.client.force_login(self.etudiant)
        self.assertEqual(self.client.get(reverse('pfe:mes_etudiants')).status_code, 403)
        self.assertEqual(self.client.get(reverse('pfe:livrables_a_valider')).status_code, 403)

    def test_affectations_is_academic_only(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('pfe:affectations')).status_code, 403)

    def test_review_actions_require_post(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.get(reverse('pfe:valider_livrable', args=[self.livrable.pk]))
        self.assertEqual(response.status_code, 405)


class MonPfeViewTests(PfeBaseTestCase):
    def test_student_sees_their_project_and_deliverables(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('pfe:mon_pfe'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['projet'], self.projet)
        self.assertIn(self.livrable, response.context['livrables'])

    def test_invalid_submission_rerenders_the_form_without_crashing(self):
        """Regression: an invalid POST used to fall through to ``projet.livrables``."""
        self.client.force_login(self.etudiant_sans_projet)
        response = self.client.post(reverse('pfe:mon_pfe'), {'sujet': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['projet'])
        self.assertIn('form', response.context)
        self.assertFalse(ProjetPFE.objects.filter(etudiant=self.etudiant_sans_projet).exists())

    def test_student_can_declare_a_project(self):
        self.client.force_login(self.etudiant_sans_projet)
        response = self.client.post(reverse('pfe:mon_pfe'), {
            'sujet': 'Nouveau sujet',
            'description': 'Description du sujet.',
        })
        self.assertRedirects(response, reverse('pfe:mon_pfe'))
        self.assertTrue(
            ProjetPFE.objects.filter(
                etudiant=self.etudiant_sans_projet, sujet='Nouveau sujet',
            ).exists()
        )

    def test_accepted_candidature_initialises_the_project(self):
        Candidature.objects.create(
            etudiant=self.etudiant_sans_projet,
            offre=self.offre,
            cv='cvs/demo.txt',
            lettre_motivation='Lettre.',
            status=Candidature.Status.ACCEPTEE,
        )
        self.client.force_login(self.etudiant_sans_projet)
        response = self.client.get(reverse('pfe:mon_pfe'))
        self.assertEqual(response.status_code, 200)
        projet = ProjetPFE.objects.get(etudiant=self.etudiant_sans_projet)
        self.assertEqual(projet.sujet, self.offre.titre)
        self.assertEqual(projet.offre, self.offre)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class DeliverableUploadTests(PfeBaseTestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_student_can_submit_a_deliverable(self):
        self.client.force_login(self.etudiant)
        upload = SimpleUploadedFile(
            'rapport.pdf', b'%PDF-1.4 demo', content_type='application/pdf',
        )
        response = self.client.post(
            reverse('pfe:deposer_livrable', args=[self.projet.pk]),
            {'titre': 'Rapport final', 'fichier': upload, 'commentaire': 'Version finale'},
        )
        self.assertRedirects(response, reverse('pfe:mon_pfe'))
        livrable = Livrable.objects.get(projet=self.projet, titre='Rapport final')
        self.assertEqual(livrable.status, Livrable.Status.DEPOSE)
        self.assertTrue(Notification.objects.filter(user=self.encadrant_acad).exists())

    def test_student_cannot_submit_to_another_students_project(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(
            reverse('pfe:deposer_livrable', args=[self.projet_autre.pk]),
        )
        self.assertEqual(response.status_code, 404)

    def test_get_renders_the_upload_form(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('pfe:deposer_livrable', args=[self.projet.pk]))
        self.assertEqual(response.status_code, 200)


class DeliverableReviewTests(PfeBaseTestCase):
    def test_supervisor_only_sees_their_own_students_deliverables(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.get(reverse('pfe:livrables_a_valider'))
        self.assertEqual(response.context['livrables'].count(), 1)
        self.assertIn(self.livrable, response.context['livrables'])
        self.assertNotIn(self.livrable_autre, response.context['livrables'])
        self.assertNotContains(response, self.livrable_autre.titre)

    def test_validate_action_updates_status_and_notifies_student(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.post(
            reverse('pfe:valider_livrable', args=[self.livrable.pk]),
        )
        self.assertRedirects(response, reverse('pfe:livrables_a_valider'))
        self.livrable.refresh_from_db()
        self.assertEqual(self.livrable.status, Livrable.Status.VALIDE)
        self.assertTrue(Notification.objects.filter(user=self.etudiant).exists())

    def test_correction_action_saves_the_comment(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.post(
            reverse('pfe:corriger_livrable', args=[self.livrable.pk]),
            {'commentaire_encadrant': 'Merci de détailler les tests.'},
        )
        self.assertRedirects(response, reverse('pfe:livrables_a_valider'))
        self.livrable.refresh_from_db()
        self.assertEqual(self.livrable.status, Livrable.Status.A_CORRIGER)
        self.assertEqual(self.livrable.commentaire_encadrant, 'Merci de détailler les tests.')

    def test_list_view_accepts_inline_decisions(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.post(reverse('pfe:livrables_a_valider'), {
            'action': 'valider',
            'livrable_id': self.livrable.pk,
        })
        self.assertRedirects(response, reverse('pfe:livrables_a_valider'))
        self.livrable.refresh_from_db()
        self.assertEqual(self.livrable.status, Livrable.Status.VALIDE)

    def test_supervisor_cannot_review_another_supervisors_deliverable(self):
        self.client.force_login(self.autre_encadrant_acad)
        response = self.client.post(
            reverse('pfe:valider_livrable', args=[self.livrable.pk]),
        )
        self.assertEqual(response.status_code, 404)


class ProjectClaimTests(PfeBaseTestCase):
    def test_page_lists_only_unassigned_projects(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.get(reverse('pfe:affectations'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.projet_en_attente, response.context['disponibles'])
        self.assertNotIn(self.projet, response.context['disponibles'])
        self.assertNotIn(self.projet_autre, response.context['disponibles'])
        self.assertIn(self.projet, response.context['mes_projets'])
        self.assertNotIn(self.projet_en_attente, response.context['mes_projets'])

    def test_supervisor_can_claim_an_unassigned_project(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.post(
            reverse('pfe:prendre_en_charge', args=[self.projet_en_attente.pk]),
        )
        self.assertRedirects(response, reverse('pfe:affectations'))

        self.projet_en_attente.refresh_from_db()
        self.assertEqual(self.projet_en_attente.encadrant_acad, self.encadrant_acad)
        self.assertTrue(
            Notification.objects.filter(user=self.etudiant_en_attente).exists()
        )

    def test_a_project_cannot_be_claimed_by_two_supervisors(self):
        self.client.force_login(self.autre_encadrant_acad)
        self.client.post(
            reverse('pfe:prendre_en_charge', args=[self.projet.pk]),
        )
        self.projet.refresh_from_db()
        self.assertEqual(self.projet.encadrant_acad, self.encadrant_acad)

    def test_claiming_your_own_project_is_harmless(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.post(
            reverse('pfe:prendre_en_charge', args=[self.projet.pk]),
        )
        self.assertRedirects(response, reverse('pfe:affectations'))
        self.projet.refresh_from_db()
        self.assertEqual(self.projet.encadrant_acad, self.encadrant_acad)

    def test_supervisor_can_release_their_own_project(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.post(
            reverse('pfe:liberer_projet', args=[self.projet.pk]),
        )
        self.assertRedirects(response, reverse('pfe:affectations'))

        self.projet.refresh_from_db()
        self.assertIsNone(self.projet.encadrant_acad)
        self.assertTrue(Notification.objects.filter(user=self.etudiant).exists())

    def test_cannot_release_another_supervisors_project(self):
        self.client.force_login(self.autre_encadrant_acad)
        response = self.client.post(
            reverse('pfe:liberer_projet', args=[self.projet.pk]),
        )
        self.assertEqual(response.status_code, 404)

        self.projet.refresh_from_db()
        self.assertEqual(self.projet.encadrant_acad, self.encadrant_acad)

    def test_claim_actions_require_post(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.get(
            reverse('pfe:prendre_en_charge', args=[self.projet_en_attente.pk]),
        )
        self.assertEqual(response.status_code, 405)

    def test_page_is_forbidden_to_other_roles(self):
        for user in (self.admin, self.etudiant, self.encadrant_pro):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                self.assertEqual(
                    self.client.get(reverse('pfe:affectations')).status_code, 403,
                )

    def test_admin_cannot_claim_a_project(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('pfe:prendre_en_charge', args=[self.projet_en_attente.pk]),
        )
        self.assertEqual(response.status_code, 403)

        self.projet_en_attente.refresh_from_db()
        self.assertIsNone(self.projet_en_attente.encadrant_acad)


class SupervisorProjectCreationTests(PfeBaseTestCase):
    def test_supervisor_can_create_a_project_for_a_student(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.post(reverse('pfe:creer_projet_encadrant'), {
            'etudiant': self.etudiant_sans_projet.pk,
            'offre': self.offre.pk,
            'sujet': "Sujet proposé par l'encadrant",
            'description': 'Description du sujet.',
        })
        self.assertRedirects(response, reverse('pfe:affectations'))

        projet = ProjetPFE.objects.get(etudiant=self.etudiant_sans_projet)
        self.assertEqual(projet.sujet, "Sujet proposé par l'encadrant")
        self.assertEqual(projet.encadrant_acad, self.encadrant_acad)
        self.assertEqual(projet.offre, self.offre)
        self.assertTrue(
            Notification.objects.filter(user=self.etudiant_sans_projet).exists()
        )

    def test_students_with_a_project_are_not_offered(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.get(reverse('pfe:creer_projet_encadrant'))
        etudiants = response.context['form'].fields['etudiant'].queryset
        self.assertIn(self.etudiant_sans_projet, etudiants)
        self.assertNotIn(self.etudiant, etudiants)

    def test_cannot_create_a_second_project_for_the_same_student(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.post(reverse('pfe:creer_projet_encadrant'), {
            'etudiant': self.etudiant.pk,
            'sujet': 'Doublon',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('etudiant', response.context['form'].errors)
        self.assertEqual(ProjetPFE.objects.filter(etudiant=self.etudiant).count(), 1)

    def test_creation_is_academic_only(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse('pfe:creer_projet_encadrant')).status_code, 403,
        )
