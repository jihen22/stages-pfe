"""Tests for the academic supervisor's workload (backlog item 16)."""


from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from soutenances import fabriques

from .charge import annoter_charge, charge_encadrant, niveau
from .models import Livrable, ProjetPFE

S = ProjetPFE.Status


class ChargeBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.acad = User.objects.create_user(
            username='acad', password='demo1234', role=User.Role.ENCADRANT_ACAD,
            capacite_encadrement=4)
        cls.acad2 = User.objects.create_user(
            username='acad2', password='demo1234', role=User.Role.ENCADRANT_ACAD)
        cls.etudiants = [
            User.objects.create_user(username=f'etu{i}', password='demo1234', role=User.Role.ETUDIANT)
            for i in range(6)
        ]

    def _projet(self, etudiant, status, encadrant=None):
        projet = ProjetPFE.objects.create(
            etudiant=etudiant, encadrant_acad=encadrant or self.acad, sujet=f'Sujet {etudiant}')
        ProjetPFE.objects.filter(pk=projet.pk).update(status=status)
        projet.refresh_from_db()
        return projet


class ChargeServiceTests(ChargeBaseTestCase):
    def test_counts_only_active_projects_against_capacity(self):
        e = self.etudiants
        self._projet(e[0], S.EN_COURS)
        self._projet(e[1], S.TERMINE)
        self._projet(e[2], S.PLANIFIE)
        self._projet(e[3], S.SOUTENU)
        self._projet(e[4], S.EN_COURS, encadrant=self.acad2)

        charge = charge_encadrant(self.acad)
        self.assertEqual(charge['actifs'], 3)
        self.assertEqual(charge['capacite'], 4)
        self.assertEqual(charge['taux'], 75)
        self.assertEqual(charge['places_libres'], 1)
        self.assertEqual(charge['soutenus'], 1)
        self.assertFalse(charge['surcharge'])
        self.assertEqual(
            {etat['code']: etat['nombre'] for etat in charge['par_statut']},
            {S.EN_COURS: 1, S.TERMINE: 1, S.PLANIFIE: 1, S.SOUTENU: 1},
        )

    def test_overload_is_flagged(self):
        for etudiant in self.etudiants[:5]:
            self._projet(etudiant, S.EN_COURS)
        charge = charge_encadrant(self.acad)
        self.assertTrue(charge['surcharge'])
        self.assertEqual(charge['taux'], 125)
        self.assertEqual(charge['jauge'], 100)
        self.assertEqual(charge['places_libres'], 0)
        self.assertEqual(charge['niveau'], 'danger')

    def test_gauge_colour_levels(self):
        self.assertEqual(niveau(50), 'success')
        self.assertEqual(niveau(80), 'warning')
        self.assertEqual(niveau(100), 'danger')

    def test_pending_work_and_upcoming_defenses(self):
        projet = self._projet(self.etudiants[0], S.PLANIFIE)
        Livrable.objects.create(projet=projet, titre='A', fichier='a.pdf', status=Livrable.Status.DEPOSE)
        Livrable.objects.create(projet=projet, titre='B', fichier='b.pdf', status=Livrable.Status.DEPOSE)
        Livrable.objects.create(projet=projet, titre='C', fichier='c.pdf', status=Livrable.Status.A_CORRIGER)
        fabriques.soutenance(projet, jours=5, nom_salle='Amphi A')
        passe = self._projet(self.etudiants[1], S.SOUTENU)
        fabriques.soutenance(passe, jours=-5, nom_salle='Amphi B')

        charge = charge_encadrant(self.acad)
        self.assertEqual(charge['livrables_a_valider'], 2)
        self.assertEqual(charge['livrables_a_corriger'], 1)
        self.assertEqual([s.salle.nom for s in charge['soutenances_a_venir']], ['Amphi A'])
        ligne = charge['projets_actifs'].get(pk=projet.pk)
        self.assertEqual((ligne.livrables_en_attente, ligne.livrables_a_corriger), (2, 1))

    def test_annoter_charge_compares_supervisors_in_one_query(self):
        self._projet(self.etudiants[0], S.EN_COURS)
        self._projet(self.etudiants[1], S.SOUTENU)
        self._projet(self.etudiants[2], S.EN_COURS, encadrant=self.acad2)
        self._projet(self.etudiants[3], S.TERMINE, encadrant=self.acad2)
        with self.assertNumQueries(1):
            resultats = {
                u.username: (u.charge_active, u.places_libres)
                for u in annoter_charge(User.objects.filter(role=User.Role.ENCADRANT_ACAD))
            }
        self.assertEqual(resultats, {'acad': (1, 3), 'acad2': (2, 6)})

    def test_capacity_must_be_between_1_and_30(self):
        self.acad.capacite_encadrement = 0
        with self.assertRaises(ValidationError):
            self.acad.full_clean()


class ChargeViewTests(ChargeBaseTestCase):
    def test_supervisor_sees_their_workload(self):
        self._projet(self.etudiants[0], S.EN_COURS)
        self._projet(self.etudiants[1], S.EN_COURS, encadrant=self.acad2)
        self.client.force_login(self.acad)
        response = self.client.get(reverse('pfe:ma_charge'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'etu0')
        self.assertNotContains(response, 'etu1')
        self.assertEqual(response.context['charge']['actifs'], 1)

    def test_overload_warning_is_shown(self):
        for etudiant in self.etudiants[:5]:
            self._projet(etudiant, S.EN_COURS)
        self.client.force_login(self.acad)
        response = self.client.get(reverse('pfe:ma_charge'))
        self.assertContains(response, 'Évitez de prendre de nouveaux projets')

    def test_empty_workload_renders(self):
        self.client.force_login(self.acad2)
        response = self.client.get(reverse('pfe:ma_charge'))
        self.assertContains(response, 'Aucun projet actif')

    def test_page_is_academic_supervisor_only(self):
        self.client.force_login(self.etudiants[0])
        self.assertEqual(self.client.get(reverse('pfe:ma_charge')).status_code, 403)
        self.client.logout()
        response = self.client.get(reverse('pfe:ma_charge'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_shows_the_load_summary(self):
        self._projet(self.etudiants[0], S.EN_COURS)
        self.client.force_login(self.acad)
        response = self.client.get(reverse('accounts:dashboard_encadrant_acad'))
        self.assertContains(response, '1 / 4 projets actifs')
        self.assertContains(response, reverse('pfe:ma_charge'))
