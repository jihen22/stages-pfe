"""Tests for defense planning with rooms and time slots (backlog item 19)."""

from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from notifications.models import Notification
from pfe.models import ProjetPFE

from . import fabriques
from .forms import JourneeCreneauxForm
from .models import Creneau, Salle, Soutenance


def local(jour, heure, minute=0):
    return timezone.make_aware(datetime(jour.year, jour.month, jour.day, heure, minute))


class PlanningBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username='admin', password='demo1234', role=User.Role.ADMIN)
        cls.jury = User.objects.create_user(username='jury', password='demo1234', role=User.Role.JURY)
        cls.etudiant = User.objects.create_user(username='etu', password='demo1234', role=User.Role.ETUDIANT)
        cls.acad = User.objects.create_user(username='acad', password='demo1234', role=User.Role.ENCADRANT_ACAD)
        cls.projet = ProjetPFE.objects.create(
            etudiant=cls.etudiant, encadrant_acad=cls.acad, sujet='Plateforme', status=ProjetPFE.Status.TERMINE)
        cls.jour = timezone.localdate() + timedelta(days=10)

    def setUp(self):
        self.client.force_login(self.admin)


class ModelTests(PlanningBaseTestCase):
    def test_slot_end_must_be_after_start(self):
        debut = local(self.jour, 10)
        with self.assertRaises(ValidationError):
            Creneau(debut=debut, fin=debut).full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Creneau.objects.create(debut=debut, fin=debut - timedelta(hours=1))

    def test_same_slot_cannot_exist_twice(self):
        debut = local(self.jour, 10)
        Creneau.objects.create(debut=debut, fin=debut + timedelta(hours=1))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Creneau.objects.create(debut=debut, fin=debut + timedelta(hours=1))

    def test_defense_date_and_end_come_from_its_slot(self):
        c = fabriques.creneau(local(self.jour, 9), minutes=45)
        s = Soutenance.objects.create(projet=self.projet, creneau=c, salle=fabriques.salle())
        self.assertEqual((s.date, s.fin), (c.debut, c.fin))
        self.assertEqual(c.duree_minutes, 45)

    def test_used_slot_and_room_cannot_be_deleted(self):
        s = fabriques.soutenance(self.projet)
        for obj in (s.creneau, s.salle):
            with self.subTest(obj=obj), self.assertRaises(Exception), transaction.atomic():
                obj.delete()


class DayGenerationTests(PlanningBaseTestCase):
    def _form(self, **data):
        valeurs = {'jour': self.jour.isoformat(), 'heure_debut': '09:00', 'heure_fin': '12:00',
                   'duree': 60, 'pause': 0}
        valeurs.update(data)
        return JourneeCreneauxForm(valeurs)

    def test_slots_fill_the_range(self):
        form = self._form()
        self.assertTrue(form.is_valid())
        heures = [(timezone.localtime(d).strftime('%H:%M'), timezone.localtime(f).strftime('%H:%M'))
                  for d, f in form.creneaux()]
        self.assertEqual(heures, [('09:00', '10:00'), ('10:00', '11:00'), ('11:00', '12:00')])

    def test_break_between_slots_and_partial_slot_dropped(self):
        form = self._form(duree=50, pause=10, heure_fin='11:30')
        self.assertTrue(form.is_valid())
        self.assertEqual([timezone.localtime(d).strftime('%H:%M') for d, _ in form.creneaux()], ['09:00', '10:00'])

    def test_end_before_start_is_refused(self):
        self.assertFalse(self._form(heure_debut='12:00', heure_fin='09:00').is_valid())

    def test_generating_a_day_from_the_page_skips_existing_slots(self):
        url = reverse('soutenances:ressources')
        data = {'action': 'journee', 'journee-jour': self.jour.isoformat(), 'journee-heure_debut': '09:00',
                'journee-heure_fin': '12:00', 'journee-duree': 60, 'journee-pause': 0}
        self.client.post(url, data)
        self.assertEqual(Creneau.objects.count(), 3)
        response = self.client.post(url, data, follow=True)
        self.assertEqual(Creneau.objects.count(), 3)
        self.assertContains(response, 'Aucun nouveau créneau')


class ResourcesPageTests(PlanningBaseTestCase):
    def test_admin_adds_a_room(self):
        self.client.post(reverse('soutenances:ressources'), {
            'action': 'salle', 'salle-nom': 'Salle B14', 'salle-batiment': 'Bloc B', 'salle-capacite': 30})
        salle = Salle.objects.get(nom='Salle B14')
        self.assertTrue(salle.active)

    def test_room_names_are_unique(self):
        fabriques.salle('Amphi A')
        response = self.client.post(reverse('soutenances:ressources'), {
            'action': 'salle', 'salle-nom': 'Amphi A', 'salle-capacite': 30})
        self.assertIn('nom', response.context['salle_form'].errors)

    def test_admin_adds_one_slot(self):
        self.client.post(reverse('soutenances:ressources'), {
            'action': 'creneau',
            'creneau-debut': f'{self.jour.isoformat()}T14:00', 'creneau-fin': f'{self.jour.isoformat()}T15:30'})
        c = Creneau.objects.get()
        self.assertEqual(c.duree_minutes, 90)

    def test_slot_with_end_before_start_is_refused(self):
        response = self.client.post(reverse('soutenances:ressources'), {
            'action': 'creneau',
            'creneau-debut': f'{self.jour.isoformat()}T14:00', 'creneau-fin': f'{self.jour.isoformat()}T13:00'})
        self.assertIn('fin', response.context['creneau_form'].errors)
        self.assertFalse(Creneau.objects.exists())

    def test_deactivated_room_is_no_longer_offered(self):
        salle = fabriques.salle('Amphi A')
        self.client.post(reverse('soutenances:basculer_salle', args=[salle.pk]))
        salle.refresh_from_db()
        self.assertFalse(salle.active)
        form = self.client.get(reverse('soutenances:planifier')).context['form']
        self.assertNotIn(salle, form.fields['salle'].queryset)
        self.client.post(reverse('soutenances:basculer_salle', args=[salle.pk]))
        salle.refresh_from_db()
        self.assertTrue(salle.active)

    def test_unused_slot_can_be_deleted_but_not_a_used_one(self):
        libre = fabriques.creneau(jours=20)
        utilise = fabriques.soutenance(self.projet).creneau
        self.client.post(reverse('soutenances:supprimer_creneau', args=[libre.pk]))
        response = self.client.post(reverse('soutenances:supprimer_creneau', args=[utilise.pk]), follow=True)
        self.assertFalse(Creneau.objects.filter(pk=libre.pk).exists())
        self.assertTrue(Creneau.objects.filter(pk=utilise.pk).exists())
        self.assertContains(response, 'ne peut pas être supprimé')

    def test_pages_and_actions_are_admin_only(self):
        salle = fabriques.salle()
        for user in (self.jury, self.etudiant, self.acad):
            self.client.force_login(user)
            with self.subTest(role=user.role):
                self.assertEqual(self.client.get(reverse('soutenances:ressources')).status_code, 403)
                self.assertEqual(
                    self.client.post(reverse('soutenances:basculer_salle', args=[salle.pk])).status_code, 403)

    def test_actions_require_post(self):
        salle = fabriques.salle()
        self.assertEqual(self.client.get(reverse('soutenances:basculer_salle', args=[salle.pk])).status_code, 405)


class PlanningWithSlotsTests(PlanningBaseTestCase):
    def test_form_offers_upcoming_slots_and_active_rooms_only(self):
        futur = fabriques.creneau(jours=3)
        passe = fabriques.creneau(jours=-3)
        active = fabriques.salle('Amphi A')
        inactive = fabriques.salle('Vieille salle', active=False)
        form = self.client.get(reverse('soutenances:planifier')).context['form']
        self.assertIn(futur, form.fields['creneau'].queryset)
        self.assertNotIn(passe, form.fields['creneau'].queryset)
        self.assertIn(active, form.fields['salle'].queryset)
        self.assertNotIn(inactive, form.fields['salle'].queryset)

    def test_admin_schedules_in_a_slot_and_room_and_participants_are_notified(self):
        c = fabriques.creneau(local(self.jour, 9), minutes=60)
        salle = fabriques.salle('Amphi A')
        response = self.client.post(reverse('soutenances:planifier'), {
            'projet': self.projet.pk, 'creneau': c.pk, 'salle': salle.pk, 'jury': [self.jury.pk]})
        self.assertRedirects(response, reverse('soutenances:planning'))
        s = Soutenance.objects.get(projet=self.projet)
        self.assertEqual((s.creneau, s.salle), (c, salle))
        message = Notification.objects.get(user=self.etudiant).message
        self.assertIn('de 09:00 à 10:00', message)
        self.assertIn('Amphi A', message)

    def test_form_warns_when_there_is_no_slot_or_room(self):
        response = self.client.get(reverse('soutenances:planifier'))
        self.assertTrue(response.context['aucun_creneau'])
        self.assertTrue(response.context['aucune_salle'])
        self.assertContains(response, 'Créer des salles et des créneaux')

    def test_planning_shows_a_grid_per_day(self):
        c9 = fabriques.creneau(local(self.jour, 9))
        fabriques.creneau(local(self.jour, 10))
        fabriques.salle('Amphi A')
        fabriques.salle('Salle B12')
        Soutenance.objects.create(projet=self.projet, creneau=c9, salle=Salle.objects.get(nom='Salle B12'))

        response = self.client.get(reverse('soutenances:planning'))
        journees = response.context['journees']
        self.assertEqual([j['jour'] for j in journees], [self.jour])
        grille = journees[0]
        self.assertEqual([s.nom for s in grille['salles']], ['Amphi A', 'Salle B12'])
        premiere_ligne = grille['lignes'][0]
        self.assertEqual(premiere_ligne['creneau'], c9)
        self.assertEqual([len(cell) for cell in premiere_ligne['cellules']], [0, 1])
        self.assertEqual(grille['nb_soutenances'], 1)
        self.assertContains(response, 'Libre')

    def test_student_and_jury_see_the_time_range(self):
        c = fabriques.creneau(local(self.jour, 14), minutes=90)
        s = Soutenance.objects.create(projet=self.projet, creneau=c, salle=fabriques.salle('Amphi A'))
        s.jury.set([self.jury])
        self.client.force_login(self.etudiant)
        self.assertContains(self.client.get(reverse('soutenances:ma_soutenance')), '14:00–15:30')
        self.client.force_login(self.jury)
        self.assertContains(self.client.get(reverse('soutenances:mes_soutenances')), '14:00–15:30')
