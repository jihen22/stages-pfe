"""Tests for scheduling conflict detection and resolution (backlog item 20)."""

from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from notifications.models import Notification
from pfe.models import ProjetPFE

from . import fabriques
from .conflits import JURY, SALLE, alternatives, conflits_pour, detecter_conflits
from .models import Soutenance

S = ProjetPFE.Status


class ConflitBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username='admin', password='demo1234', role=User.Role.ADMIN)
        cls.acad = User.objects.create_user(username='acad', password='demo1234', role=User.Role.ENCADRANT_ACAD)
        cls.jury_a = User.objects.create_user(username='jury_a', password='demo1234', role=User.Role.JURY)
        cls.jury_b = User.objects.create_user(username='jury_b', password='demo1234', role=User.Role.JURY)
        cls.jury_c = User.objects.create_user(username='jury_c', password='demo1234', role=User.Role.JURY)
        cls.etudiants = [
            User.objects.create_user(username=f'etu{i}', password='demo1234', role=User.Role.ETUDIANT)
            for i in range(4)
        ]
        cls.jour = timezone.localdate() + timedelta(days=10)
        cls.amphi = fabriques.salle('Amphi A')
        cls.b12 = fabriques.salle('Salle B12')

    def setUp(self):
        self.client.force_login(self.admin)

    def heure(self, h, minute=0):
        return timezone.make_aware(datetime(self.jour.year, self.jour.month, self.jour.day, h, minute))

    def creneau(self, h, minute=0, minutes=60):
        return fabriques.creneau(self.heure(h, minute), minutes=minutes)

    def projet(self, i, status=S.PLANIFIE):
        return ProjetPFE.objects.create(
            etudiant=self.etudiants[i], encadrant_acad=self.acad, sujet=f'Sujet {i}', status=status)

    def soutenance(self, i, creneau, salle, jury, status=S.PLANIFIE):
        s = Soutenance.objects.create(projet=self.projet(i, status), creneau=creneau, salle=salle)
        s.jury.set(jury)
        return s


class DetectionTests(ConflitBaseTestCase):
    def test_same_room_same_slot(self):
        c9 = self.creneau(9)
        existante = self.soutenance(0, c9, self.amphi, [self.jury_a])
        conflits = conflits_pour(c9, self.amphi, [self.jury_b])
        self.assertEqual([(c.type, c.soutenance) for c in conflits], [(SALLE, existante)])
        self.assertIn('Amphi A déjà occupée', conflits[0].message)

    def test_overlapping_slots_conflict_but_back_to_back_do_not(self):
        self.soutenance(0, self.creneau(9), self.amphi, [self.jury_a])
        chevauche = self.creneau(9, 30)          # 09:30-10:30 overlaps 09:00-10:00
        a_la_suite = self.creneau(10)            # 10:00-11:00 starts when the other ends
        self.assertEqual(len(conflits_pour(chevauche, self.amphi, [])), 1)
        self.assertEqual(conflits_pour(a_la_suite, self.amphi, [self.jury_a]), [])

    def test_same_jury_member_in_another_room(self):
        c9 = self.creneau(9)
        self.soutenance(0, c9, self.amphi, [self.jury_a, self.jury_b])
        conflits = conflits_pour(c9, self.b12, [self.jury_b, self.jury_c])
        self.assertEqual([c.type for c in conflits], [JURY])
        self.assertEqual(conflits[0].membres, [self.jury_b])
        self.assertIn('jury_b', conflits[0].message)

    def test_free_room_and_jury_is_not_a_conflict(self):
        c9 = self.creneau(9)
        self.soutenance(0, c9, self.amphi, [self.jury_a])
        self.assertEqual(conflits_pour(c9, self.b12, [self.jury_b]), [])

    def test_a_defense_does_not_conflict_with_itself(self):
        c9 = self.creneau(9)
        s = self.soutenance(0, c9, self.amphi, [self.jury_a])
        self.assertEqual(conflits_pour(c9, self.amphi, [self.jury_a], exclure=s), [])

    def test_planning_scan_finds_each_pair_once_and_ignores_the_past(self):
        c9 = self.creneau(9)
        a = self.soutenance(0, c9, self.amphi, [self.jury_a])
        b = Soutenance.objects.create(projet=self.projet(1), creneau=c9, salle=self.amphi)
        b.jury.set([self.jury_a])
        passe = fabriques.creneau(jours=-3)
        self.soutenance(2, passe, self.b12, [self.jury_b], status=S.SOUTENU)
        self.soutenance(3, passe, self.b12, [self.jury_b], status=S.SOUTENU)

        conflits = detecter_conflits()
        self.assertEqual(sorted(c.type for c in conflits), [JURY, SALLE])
        self.assertTrue(all({c.soutenance, c.autre} == {a, b} for c in conflits))


class AlternativesTests(ConflitBaseTestCase):
    def test_free_slots_skip_busy_rooms_and_busy_jury_closest_first(self):
        c9, c10, c11 = self.creneau(9), self.creneau(10), self.creneau(11)
        self.soutenance(0, c9, self.amphi, [self.jury_a])        # Amphi A busy at 9
        self.soutenance(1, c10, self.b12, [self.jury_b])         # jury_b busy at 10
        resultat = alternatives([self.jury_b], souhait=c9.debut, salle_preferee=self.amphi)
        self.assertEqual(
            [(timezone.localtime(c.debut).hour, s.nom) for c, s in resultat],
            [(9, 'Salle B12'), (11, 'Amphi A'), (11, 'Salle B12')],
        )

    def test_inactive_rooms_and_past_slots_are_never_proposed(self):
        self.creneau(9)
        fabriques.creneau(jours=-2)
        self.b12.active = False
        self.b12.save()
        resultat = alternatives([self.jury_a])
        self.assertEqual({s.nom for _, s in resultat}, {'Amphi A'})
        self.assertTrue(all(c.debut >= timezone.now() for c, _ in resultat))


class PlanningPreventionTests(ConflitBaseTestCase):
    def test_planning_a_conflict_is_refused_with_alternatives(self):
        c9, c10 = self.creneau(9), self.creneau(10)
        self.soutenance(0, c9, self.amphi, [self.jury_a])
        projet = self.projet(1, S.TERMINE)
        response = self.client.post(reverse('soutenances:planifier'), {
            'projet': projet.pk, 'creneau': c9.pk, 'salle': self.amphi.pk, 'jury': [self.jury_a.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Conflit de planning')
        self.assertContains(response, 'Amphi A déjà occupée')
        self.assertIn((c10, self.amphi), response.context['suggestions'])
        self.assertFalse(Soutenance.objects.filter(projet=projet).exists())
        projet.refresh_from_db()
        self.assertEqual(projet.status, S.TERMINE)

    def test_planning_in_a_free_room_works(self):
        c9 = self.creneau(9)
        self.soutenance(0, c9, self.amphi, [self.jury_a])
        projet = self.projet(1, S.TERMINE)
        response = self.client.post(reverse('soutenances:planifier'), {
            'projet': projet.pk, 'creneau': c9.pk, 'salle': self.b12.pk, 'jury': [self.jury_b.pk]})
        self.assertRedirects(response, reverse('soutenances:planning'))


class ModificationTests(ConflitBaseTestCase):
    def test_admin_moves_a_defense_and_participants_are_told(self):
        s = self.soutenance(0, self.creneau(9), self.amphi, [self.jury_a, self.jury_b])
        c14 = self.creneau(14)
        response = self.client.post(reverse('soutenances:modifier', args=[s.pk]), {
            'creneau': c14.pk, 'salle': self.b12.pk, 'jury': [self.jury_a.pk, self.jury_c.pk]})
        self.assertRedirects(response, reverse('soutenances:planning'))
        s.refresh_from_db()
        self.assertEqual((s.creneau, s.salle), (c14, self.b12))
        self.assertIn('déplacée', Notification.objects.get(user=self.etudiants[0]).message)
        self.assertTrue(Notification.objects.filter(user=self.jury_c).exists())
        self.assertIn('ne faites plus partie', Notification.objects.get(user=self.jury_b).message)

    def test_keeping_the_same_slot_is_not_a_conflict_with_itself(self):
        c9 = self.creneau(9)
        s = self.soutenance(0, c9, self.amphi, [self.jury_a])
        response = self.client.post(reverse('soutenances:modifier', args=[s.pk]), {
            'creneau': c9.pk, 'salle': self.amphi.pk, 'jury': [self.jury_a.pk, self.jury_b.pk]})
        self.assertRedirects(response, reverse('soutenances:planning'))
        self.assertEqual(s.jury.count(), 2)

    def test_moving_into_a_conflict_is_refused(self):
        c9, c10 = self.creneau(9), self.creneau(10)
        self.soutenance(0, c9, self.amphi, [self.jury_a])
        s = self.soutenance(1, c10, self.b12, [self.jury_a])
        response = self.client.post(reverse('soutenances:modifier', args=[s.pk]), {
            'creneau': c9.pk, 'salle': self.b12.pk, 'jury': [self.jury_a.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'jury_a déjà dans le jury')
        s.refresh_from_db()
        self.assertEqual(s.creneau, c10)

    def test_defended_project_cannot_be_moved(self):
        s = self.soutenance(0, self.creneau(9), self.amphi, [self.jury_a], status=S.SOUTENU)
        self.assertEqual(self.client.get(reverse('soutenances:modifier', args=[s.pk])).status_code, 404)

    def test_edit_form_has_no_project_field(self):
        s = self.soutenance(0, self.creneau(9), self.amphi, [self.jury_a])
        response = self.client.get(reverse('soutenances:modifier', args=[s.pk]))
        self.assertNotIn('projet', response.context['form'].fields)
        self.assertContains(response, 'Modifier une soutenance')


class ResolutionTests(ConflitBaseTestCase):
    def _conflit(self):
        c9 = self.creneau(9)
        a = self.soutenance(0, c9, self.amphi, [self.jury_a])
        b = Soutenance.objects.create(projet=self.projet(1), creneau=c9, salle=self.amphi)
        b.jury.set([self.jury_b])
        return a, b

    def test_conflicts_page_lists_them_with_suggestions(self):
        a, b = self._conflit()
        self.creneau(10)
        response = self.client.get(reverse('soutenances:conflits'))
        lignes = response.context['lignes']
        self.assertEqual(len(lignes), 1)
        self.assertEqual(lignes[0]['a_deplacer'], b)
        self.assertTrue(lignes[0]['suggestions'])
        self.assertContains(response, 'réservée deux fois')

    def test_one_click_move_resolves_the_conflict(self):
        a, b = self._conflit()
        response = self.client.post(reverse('soutenances:deplacer', args=[b.pk]), {
            'creneau': a.creneau.pk, 'salle': self.b12.pk, 'suivant': 'conflits'})
        self.assertRedirects(response, reverse('soutenances:conflits'))
        b.refresh_from_db()
        self.assertEqual(b.salle, self.b12)
        self.assertEqual(detecter_conflits(), [])
        self.assertContains(self.client.get(reverse('soutenances:conflits')), 'Aucun conflit')

    def test_one_click_move_rechecks_the_target(self):
        a, b = self._conflit()
        c10 = self.creneau(10)
        self.soutenance(2, c10, self.b12, [self.jury_b])  # jury_b now busy at 10
        response = self.client.post(reverse('soutenances:deplacer', args=[b.pk]), {
            'creneau': c10.pk, 'salle': self.amphi.pk}, follow=True)
        self.assertContains(response, "plus libre")
        b.refresh_from_db()
        self.assertEqual(b.creneau, a.creneau)

    def test_redirect_only_to_known_pages(self):
        a, b = self._conflit()
        response = self.client.post(reverse('soutenances:deplacer', args=[b.pk]), {
            'creneau': a.creneau.pk, 'salle': self.b12.pk, 'suivant': 'https://example.com/'})
        self.assertRedirects(response, reverse('soutenances:conflits'))

    def test_planning_and_dashboard_show_the_conflict_count(self):
        a, b = self._conflit()
        planning = self.client.get(reverse('soutenances:planning'))
        self.assertEqual(planning.context['nb_conflits'], 1)
        self.assertEqual(planning.context['en_conflit'], {a.pk, b.pk})
        self.assertContains(planning, 'table-danger')
        dashboard = self.client.get(reverse('accounts:dashboard_admin'))
        self.assertContains(dashboard, 'conflit')
        self.assertContains(dashboard, reverse('soutenances:conflits'))

    def test_admin_only_and_post_only(self):
        a, b = self._conflit()
        self.assertEqual(self.client.get(reverse('soutenances:deplacer', args=[b.pk])).status_code, 405)
        for user in (self.jury_a, self.acad, self.etudiants[0]):
            self.client.force_login(user)
            with self.subTest(role=user.role):
                self.assertEqual(self.client.get(reverse('soutenances:conflits')).status_code, 403)
                self.assertEqual(self.client.get(reverse('soutenances:modifier', args=[b.pk])).status_code, 403)
