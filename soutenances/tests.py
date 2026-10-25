from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from notifications.models import Notification
from offres.models import Offre
from pfe.models import ProjetPFE

from .models import NoteSoutenance, Soutenance


class SoutenanceBaseTestCase(TestCase):
    """Fixtures shared by the defense tests."""

    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT,
        )
        cls.autre_etudiant = User.objects.create_user(
            username='etudiant2', password='demo1234', role=User.Role.ETUDIANT,
        )
        cls.encadrant_acad = User.objects.create_user(
            username='acad', password='demo1234', role=User.Role.ENCADRANT_ACAD,
        )
        cls.encadrant_pro = User.objects.create_user(
            username='pro', password='demo1234', role=User.Role.ENCADRANT_PRO,
        )
        cls.admin = User.objects.create_user(
            username='admin', password='demo1234', role=User.Role.ADMIN,
        )
        cls.jury = User.objects.create_user(
            username='jury', password='demo1234', role=User.Role.JURY,
        )
        cls.jury2 = User.objects.create_user(
            username='jury2', password='demo1234', role=User.Role.JURY,
        )
        cls.jury_externe = User.objects.create_user(
            username='jury3', password='demo1234', role=User.Role.JURY,
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
        cls.projet_sans_soutenance = ProjetPFE.objects.create(
            etudiant=cls.autre_etudiant,
            sujet='Application mobile Flutter',
        )

        cls.soutenance = Soutenance.objects.create(
            projet=cls.projet,
            date=timezone.now() + timedelta(days=7),
            salle='Amphi A',
        )
        cls.soutenance.jury.set([cls.jury, cls.jury2])
        cls.note = NoteSoutenance.objects.create(
            soutenance=cls.soutenance,
            jury_member=cls.jury,
            note=15.5,
        )


class SoutenanceRoleAccessTests(SoutenanceBaseTestCase):
    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse('soutenances:ma_soutenance'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_student_can_read_their_own_defense(self):
        self.client.force_login(self.etudiant)
        self.assertEqual(
            self.client.get(reverse('soutenances:ma_soutenance')).status_code, 200,
        )

    def test_defense_page_is_student_only(self):
        self.client.force_login(self.jury)
        self.assertEqual(
            self.client.get(reverse('soutenances:ma_soutenance')).status_code, 403,
        )

    def test_jury_pages_are_forbidden_to_students(self):
        self.client.force_login(self.etudiant)
        self.assertEqual(
            self.client.get(reverse('soutenances:mes_soutenances')).status_code, 403,
        )
        self.assertEqual(
            self.client.get(reverse('soutenances:saisir_notes')).status_code, 403,
        )

    def test_admin_pages_are_forbidden_to_jury(self):
        self.client.force_login(self.jury)
        self.assertEqual(
            self.client.get(reverse('soutenances:planning')).status_code, 403,
        )
        self.assertEqual(
            self.client.get(reverse('soutenances:planifier')).status_code, 403,
        )


class MaSoutenanceTests(SoutenanceBaseTestCase):
    def test_student_sees_the_defense_and_average(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('soutenances:ma_soutenance'))
        self.assertEqual(response.context['soutenance'], self.soutenance)
        self.assertEqual(response.context['moyenne'], 15.5)

    def test_student_without_defense_gets_an_empty_page(self):
        self.client.force_login(self.autre_etudiant)
        response = self.client.get(reverse('soutenances:ma_soutenance'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['soutenance'])
        self.assertIsNone(response.context['moyenne'])


class MesSoutenancesTests(SoutenanceBaseTestCase):
    def test_jury_only_sees_assigned_defenses(self):
        self.client.force_login(self.jury)
        response = self.client.get(reverse('soutenances:mes_soutenances'))
        self.assertEqual(len(response.context['soutenances_data']), 1)
        self.assertEqual(
            response.context['soutenances_data'][0]['soutenance'], self.soutenance,
        )

    def test_unassigned_jury_gets_an_empty_list(self):
        self.client.force_login(self.jury_externe)
        response = self.client.get(reverse('soutenances:mes_soutenances'))
        self.assertEqual(len(response.context['soutenances_data']), 0)


class SaisirNotesTests(SoutenanceBaseTestCase):
    def test_jury_can_submit_a_grade(self):
        self.client.force_login(self.jury)
        response = self.client.post(
            reverse('soutenances:saisir_note', args=[self.soutenance.pk]),
            {'note': '17.25', 'remarque': 'Très bonne prestation.'},
        )
        self.assertRedirects(response, reverse('soutenances:saisir_notes'))
        self.note.refresh_from_db()
        self.assertEqual(float(self.note.note), 17.25)
        self.assertEqual(self.note.remarque, 'Très bonne prestation.')

    def test_invalid_grade_does_not_create_a_phantom_note(self):
        """Regression: a rejected form used to leave a 0/20 grade behind."""
        self.client.force_login(self.jury2)
        response = self.client.post(
            reverse('soutenances:saisir_note', args=[self.soutenance.pk]),
            {'note': '25'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            NoteSoutenance.objects.filter(
                soutenance=self.soutenance, jury_member=self.jury2,
            ).exists()
        )

    def test_non_member_cannot_grade(self):
        self.client.force_login(self.jury_externe)
        response = self.client.post(
            reverse('soutenances:saisir_note', args=[self.soutenance.pk]),
            {'note': '18'},
        )
        self.assertRedirects(response, reverse('soutenances:saisir_notes'))
        self.assertFalse(
            NoteSoutenance.objects.filter(
                soutenance=self.soutenance, jury_member=self.jury_externe,
            ).exists()
        )

    def test_non_member_is_redirected_on_get(self):
        self.client.force_login(self.jury_externe)
        response = self.client.get(
            reverse('soutenances:saisir_note', args=[self.soutenance.pk]),
        )
        self.assertRedirects(response, reverse('soutenances:saisir_notes'))


class PlanningTests(SoutenanceBaseTestCase):
    def test_admin_can_open_the_planning_pages(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('soutenances:planning')).status_code, 200)
        self.assertEqual(self.client.get(reverse('soutenances:planifier')).status_code, 200)

    def test_admin_can_schedule_a_defense(self):
        date = (timezone.now() + timedelta(days=14)).strftime('%Y-%m-%dT%H:%M')
        self.client.force_login(self.admin)
        response = self.client.post(reverse('soutenances:planifier'), {
            'projet': self.projet_sans_soutenance.pk,
            'date': date,
            'salle': 'Amphi B',
            'jury': [self.jury.pk, self.jury2.pk],
        })
        self.assertRedirects(response, reverse('soutenances:planning'))

        soutenance = Soutenance.objects.get(projet=self.projet_sans_soutenance)
        self.assertEqual(soutenance.salle, 'Amphi B')
        self.assertEqual(soutenance.jury.count(), 2)
        self.assertTrue(Notification.objects.filter(user=self.autre_etudiant).exists())
        self.assertTrue(Notification.objects.filter(user=self.jury).exists())

    def test_jury_is_required(self):
        """Regression from the last commit: the jury field must be mandatory."""
        date = (timezone.now() + timedelta(days=14)).strftime('%Y-%m-%dT%H:%M')
        self.client.force_login(self.admin)
        response = self.client.post(reverse('soutenances:planifier'), {
            'projet': self.projet_sans_soutenance.pk,
            'date': date,
            'salle': 'Amphi B',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('jury', response.context['form'].errors)
        self.assertFalse(
            Soutenance.objects.filter(projet=self.projet_sans_soutenance).exists()
        )

    def test_a_project_cannot_be_scheduled_twice(self):
        date = (timezone.now() + timedelta(days=14)).strftime('%Y-%m-%dT%H:%M')
        self.client.force_login(self.admin)
        response = self.client.post(reverse('soutenances:planifier'), {
            'projet': self.projet.pk,
            'date': date,
            'salle': 'Amphi B',
            'jury': [self.jury.pk],
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('projet', response.context['form'].errors)
        self.assertEqual(Soutenance.objects.filter(projet=self.projet).count(), 1)
