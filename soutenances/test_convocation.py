"""Tests for the defense notice and the jury's defense file (backlog items 21 and 22)."""

from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from notifications.models import Notification
from pfe.models import Livrable, ProjetPFE

from . import fabriques
from .models import NoteSoutenance, Soutenance


class ConvocationBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        def user(username, role, **extra):
            return User.objects.create_user(username=username, password='demo1234', role=role, **extra)

        cls.etudiant = user('sami', User.Role.ETUDIANT, first_name='Sami', last_name='Ben Ali')
        cls.autre_etudiant = user('ines', User.Role.ETUDIANT)
        cls.acad = user('leila', User.Role.ENCADRANT_ACAD, first_name='Leila', last_name='Mansouri')
        cls.pro = user('karim', User.Role.ENCADRANT_PRO)
        cls.admin = user('admin', User.Role.ADMIN)
        cls.jury = user('hatem', User.Role.JURY, first_name='Hatem', last_name='Jaziri')
        cls.jury2 = user('sonia', User.Role.JURY, first_name='Sonia', last_name='Khelifi')
        cls.autre_jury = user('autre_jury', User.Role.JURY)

        cls.projet = ProjetPFE.objects.create(
            etudiant=cls.etudiant, encadrant_acad=cls.acad, sujet='Plateforme de stages',
            status=ProjetPFE.Status.PLANIFIE)
        jour = timezone.localdate() + timedelta(days=5)
        debut = timezone.make_aware(datetime(jour.year, jour.month, jour.day, 9))
        cls.soutenance = Soutenance.objects.create(
            projet=cls.projet, creneau=fabriques.creneau(debut, minutes=45),
            salle=fabriques.salle('Amphi A', batiment='Bloc A'))
        cls.soutenance.jury.set([cls.jury, cls.jury2])

        v1 = Livrable.objects.create(projet=cls.projet, titre='Rapport final', fichier='v1.pdf',
                                     status=Livrable.Status.A_CORRIGER)
        cls.v2 = Livrable.objects.create(projet=cls.projet, titre='Rapport final', fichier='v2.pdf',
                                         version=2, version_precedente=v1, status=Livrable.Status.VALIDE)
        cls.slides = Livrable.objects.create(projet=cls.projet, titre='Présentation', fichier='p.pdf',
                                             status=Livrable.Status.DEPOSE)


class ConvocationTests(ConvocationBaseTestCase):
    def url(self):
        return reverse('soutenances:convocation', args=[self.soutenance.pk])

    def test_jury_member_gets_their_notice(self):
        self.client.force_login(self.jury)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['role'], 'jury')
        for texte in ('Convocation à la soutenance de PFE', 'en tant que membre du jury', 'de 09:00 à 09:45',
                      'Amphi A', 'Bloc A', 'Plateforme de stages', 'Sami Ben Ali', 'Leila Mansouri',
                      'Sonia Khelifi', 'Imprimer'):
            self.assertContains(response, texte)

    def test_reference_is_stable(self):
        self.client.force_login(self.admin)
        reference = self.client.get(self.url()).context['reference']
        self.assertRegex(reference, r'^CONV-\d{4}-\d{4}$')
        self.assertTrue(reference.endswith(f'{self.soutenance.pk:04d}'))

    def test_student_gets_their_notice_with_student_instructions(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(self.url())
        self.assertEqual(response.context['role'], 'etudiant')
        self.assertContains(response, 'vous êtes convoqué(e)')
        self.assertContains(response, '15 minutes avant')

    def test_admin_can_open_any_notice(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_people_outside_the_defense_are_refused(self):
        for user in (self.autre_etudiant, self.autre_jury, self.acad, self.pro):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.url()).status_code, 403)

    def test_login_required(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 302)

    def test_print_styles_hide_the_navigation(self):
        css = open('accounts/static/css/theme.css', encoding='utf-8').read()
        self.assertIn('@media print', css)
        self.assertIn('.app-sidebar', css.split('@media print')[1])


class DossierTests(ConvocationBaseTestCase):
    def url(self):
        return reverse('soutenances:dossier', args=[self.soutenance.pk])

    def test_jury_sees_latest_version_of_each_report(self):
        self.client.force_login(self.jury)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        dernieres = [lv for lv, _ in response.context['livrables']]
        self.assertCountEqual(dernieres, [self.v2, self.slides])
        self.assertEqual(response.context['nb_valides'], 1)
        self.assertContains(response, 'v2.pdf')
        self.assertNotContains(response, 'v1.pdf')
        self.assertContains(response, '1 version précédente')

    def test_jury_sees_their_grade_link(self):
        NoteSoutenance.objects.create(soutenance=self.soutenance, jury_member=self.jury, note=15)
        self.client.force_login(self.jury)
        response = self.client.get(self.url())
        self.assertContains(response, 'Modifier ma note (15')
        self.assertContains(response, reverse('soutenances:saisir_note', args=[self.soutenance.pk]))

    def test_other_jury_members_and_roles_are_refused(self):
        self.client.force_login(self.autre_jury)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        for user in (self.etudiant, self.acad, self.pro):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.url()).status_code, 403)

    def test_admin_can_open_the_file(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_jury_schedule_links_to_notice_and_file(self):
        self.client.force_login(self.jury)
        response = self.client.get(reverse('soutenances:mes_soutenances'))
        self.assertContains(response, self.url())
        self.assertContains(response, reverse('soutenances:convocation', args=[self.soutenance.pk]))


class StudentDefenseTests(ConvocationBaseTestCase):
    """Item 22: the student sees their schedule and reaches their notice."""

    def test_student_page_shows_schedule_and_links_to_the_notice(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('soutenances:ma_soutenance'))
        self.assertContains(response, '09:00–09:45')
        self.assertContains(response, 'Amphi A')
        self.assertContains(response, 'Ma convocation')
        self.assertContains(response, reverse('soutenances:convocation', args=[self.soutenance.pk]))

    def test_student_without_defense_has_no_notice_link(self):
        self.client.force_login(self.autre_etudiant)
        response = self.client.get(reverse('soutenances:ma_soutenance'))
        self.assertNotContains(response, 'Ma convocation')

    def test_student_cannot_open_another_students_notice(self):
        projet = ProjetPFE.objects.create(etudiant=self.autre_etudiant, encadrant_acad=self.acad,
                                          sujet='Autre', status=ProjetPFE.Status.PLANIFIE)
        autre = fabriques.soutenance(projet, nom_salle='Salle B12', jours=6)
        self.client.force_login(self.etudiant)
        self.assertEqual(
            self.client.get(reverse('soutenances:convocation', args=[autre.pk])).status_code, 403)

    def test_planning_notification_mentions_the_notice(self):
        projet = ProjetPFE.objects.create(etudiant=self.autre_etudiant, encadrant_acad=self.acad,
                                          sujet='Autre', status=ProjetPFE.Status.TERMINE)
        self.client.force_login(self.admin)
        self.client.post(reverse('soutenances:planifier'), {
            'projet': projet.pk, 'creneau': fabriques.creneau(jours=8).pk,
            'salle': fabriques.salle('Salle B12').pk, 'jury': [self.autre_jury.pk]})
        message = Notification.objects.get(user=self.autre_etudiant).message
        self.assertIn('convocation est disponible', message)
