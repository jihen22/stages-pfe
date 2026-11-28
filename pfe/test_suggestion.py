"""Tests for PFE assignment by field and workload (backlog item 10)."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import Domaine, User
from candidatures.models import Candidature
from offres.models import Offre

from . import suggestion
from .models import ProjetPFE
from .suggestion import Suggestion, raison_refus, suggerer_encadrants

S = ProjetPFE.Status


class AffectationBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        def acad(username, domaine, capacite=8):
            return User.objects.create_user(
                username=username, password='demo1234', role=User.Role.ENCADRANT_ACAD,
                domaine=domaine, capacite_encadrement=capacite)

        cls.data_libre = acad('data_libre', Domaine.DATA_IA, capacite=4)
        cls.data_charge = acad('data_charge', Domaine.DATA_IA, capacite=4)
        cls.gl = acad('gl', Domaine.GENIE_LOGICIEL, capacite=2)
        cls.etudiants = [
            User.objects.create_user(username=f'etu{i}', password='demo1234', role=User.Role.ETUDIANT)
            for i in range(8)
        ]
        cls.pro = User.objects.create_user(
            username='pro', password='demo1234', role=User.Role.ENCADRANT_PRO)

        # data_charge already supervises 3 active projects, data_libre 1 active + 1 defended.
        for i, (encadrant, status) in enumerate([
            (cls.data_charge, S.EN_COURS), (cls.data_charge, S.TERMINE), (cls.data_charge, S.PLANIFIE),
            (cls.data_libre, S.EN_COURS), (cls.data_libre, S.SOUTENU),
        ]):
            projet = ProjetPFE.objects.create(
                etudiant=cls.etudiants[i], encadrant_acad=encadrant, sujet=f'Actif {i}',
                domaine=Domaine.DATA_IA)
            ProjetPFE.objects.filter(pk=projet.pk).update(status=status)

    def _attente(self, domaine, etudiant_index=5):
        return ProjetPFE.objects.create(
            etudiant=self.etudiants[etudiant_index], sujet='Sujet en attente', domaine=domaine)


class SuggestionServiceTests(AffectationBaseTestCase):
    def test_suggests_same_field_supervisors_least_loaded_first(self):
        projet = self._attente(Domaine.DATA_IA)
        suggestions = suggerer_encadrants(projet)
        self.assertEqual([s.encadrant for s in suggestions], [self.data_libre, self.data_charge])
        # 60 for the field + 40 * 3/4 free places, and 60 + 40 * 1/4.
        self.assertEqual([s.score for s in suggestions], [90, 70])
        self.assertIn('3 places libres sur 4', suggestions[0].raisons)

    def test_other_fields_and_full_supervisors_are_not_suggested(self):
        projet = self._attente(Domaine.GENIE_LOGICIEL)
        self.assertEqual([s.encadrant for s in suggerer_encadrants(projet)], [self.gl])
        for i in (6, 7):
            p = ProjetPFE.objects.create(etudiant=self.etudiants[i], encadrant_acad=self.gl,
                                         sujet='x', domaine=Domaine.GENIE_LOGICIEL)
            self.assertEqual(p.status, S.EN_COURS)
        self.assertEqual(suggerer_encadrants(projet), [])

    def test_project_without_field_is_open_to_everyone_with_room(self):
        projet = self._attente('')
        noms = [s.encadrant.username for s in suggerer_encadrants(projet, limite=10)]
        self.assertEqual(noms, ['gl', 'data_libre', 'data_charge'])
        self.assertTrue(all(s.score < 60 + 40 for s in suggerer_encadrants(projet)))

    def test_ai_extension_point_is_called_with_the_ranking(self):
        projet = self._attente(Domaine.DATA_IA)
        recus = []

        def faux_modele(p, suggestions):
            recus.append((p, [s.encadrant for s in suggestions]))
            return list(reversed(suggestions))

        original = suggestion.ajuster_par_ia
        suggestion.ajuster_par_ia = faux_modele
        try:
            resultat = suggerer_encadrants(projet)
        finally:
            suggestion.ajuster_par_ia = original
        self.assertEqual(recus, [(projet, [self.data_libre, self.data_charge])])
        self.assertEqual([s.encadrant for s in resultat], [self.data_charge, self.data_libre])

    def test_default_ai_hook_changes_nothing(self):
        liste = [Suggestion(encadrant=self.gl, score=1)]
        self.assertIs(suggestion.ajuster_par_ia(None, liste), liste)

    def test_refusal_reasons(self):
        projet = self._attente(Domaine.DATA_IA)
        self.assertIsNone(raison_refus(projet, self.data_libre))
        self.assertIn('domaine', raison_refus(projet, self.gl))
        self.data_charge.capacite_encadrement = 3
        self.assertIn('capacité', raison_refus(projet, self.data_charge))


class AffectationsPageTests(AffectationBaseTestCase):
    def test_page_shows_suggestions_and_highlights_mine(self):
        projet = self._attente(Domaine.DATA_IA)
        self.client.force_login(self.data_libre)
        response = self.client.get(reverse('pfe:affectations'))
        ligne = response.context['disponibles'][0]
        self.assertEqual(ligne, projet)
        self.assertTrue(ligne.recommande)
        self.assertIsNone(ligne.raison_refus)
        self.assertContains(response, 'Suggéré pour vous')
        self.assertContains(response, 'Data science et IA')

    def test_other_field_button_is_disabled_with_reason(self):
        self._attente(Domaine.DATA_IA)
        self.client.force_login(self.gl)
        response = self.client.get(reverse('pfe:affectations'))
        ligne = response.context['disponibles'][0]
        self.assertFalse(ligne.recommande)
        self.assertIn('domaine', ligne.raison_refus)
        self.assertNotContains(response, reverse('pfe:prendre_en_charge', args=[ligne.pk]))

    def test_recommended_projects_are_listed_first(self):
        autre = self._attente(Domaine.GENIE_LOGICIEL, etudiant_index=6)
        mien = self._attente(Domaine.DATA_IA, etudiant_index=7)
        self.client.force_login(self.data_libre)
        response = self.client.get(reverse('pfe:affectations'))
        self.assertEqual(response.context['disponibles'][:2], [mien, autre])

    def test_full_supervisor_sees_a_warning(self):
        self.client.force_login(self.data_charge)
        self.data_charge.capacite_encadrement = 3
        self.data_charge.save(update_fields=['capacite_encadrement'])
        response = self.client.get(reverse('pfe:affectations'))
        self.assertTrue(response.context['capacite_atteinte'])
        self.assertContains(response, "Votre capacité d'encadrement est atteinte")


class PrendreEnChargeRulesTests(AffectationBaseTestCase):
    def test_supervisor_takes_a_project_of_their_field(self):
        projet = self._attente(Domaine.DATA_IA)
        self.client.force_login(self.data_libre)
        self.client.post(reverse('pfe:prendre_en_charge', args=[projet.pk]))
        projet.refresh_from_db()
        self.assertEqual((projet.encadrant_acad, projet.status), (self.data_libre, S.EN_COURS))

    def test_supervisor_cannot_take_another_field(self):
        projet = self._attente(Domaine.DATA_IA)
        self.client.force_login(self.gl)
        response = self.client.post(reverse('pfe:prendre_en_charge', args=[projet.pk]), follow=True)
        self.assertContains(response, 'pas du vôtre')
        projet.refresh_from_db()
        self.assertIsNone(projet.encadrant_acad)
        self.assertEqual(projet.status, S.EN_ATTENTE)

    def test_supervisor_at_capacity_cannot_take_more(self):
        self.data_charge.capacite_encadrement = 3
        self.data_charge.save(update_fields=['capacite_encadrement'])
        projet = self._attente(Domaine.DATA_IA)
        self.client.force_login(self.data_charge)
        response = self.client.post(reverse('pfe:prendre_en_charge', args=[projet.pk]), follow=True)
        self.assertContains(response, 'capacité')
        projet.refresh_from_db()
        self.assertIsNone(projet.encadrant_acad)

    def test_defended_projects_do_not_count_against_capacity(self):
        # data_libre: capacity 2 here, 1 active + 1 defended project -> still one place.
        self.data_libre.capacite_encadrement = 2
        self.data_libre.save(update_fields=['capacite_encadrement'])
        projet = self._attente(Domaine.DATA_IA)
        self.client.force_login(self.data_libre)
        self.client.post(reverse('pfe:prendre_en_charge', args=[projet.pk]))
        projet.refresh_from_db()
        self.assertEqual(projet.encadrant_acad, self.data_libre)


class ProjectCreationFieldTests(AffectationBaseTestCase):
    def _offre(self, domaine):
        return Offre.objects.create(encadrant_pro=self.pro, titre=f'PFE {domaine}', description='x',
                                    type=Offre.Type.PFE, status=Offre.Status.PUBLIEE, domaine=domaine)

    def test_created_project_takes_the_supervisor_field(self):
        self.client.force_login(self.gl)
        self.client.post(reverse('pfe:creer_projet_encadrant'), {
            'etudiant': self.etudiants[6].pk, 'sujet': 'API REST', 'description': '',
        })
        projet = ProjetPFE.objects.get(etudiant=self.etudiants[6])
        self.assertEqual((projet.domaine, projet.encadrant_acad), (Domaine.GENIE_LOGICIEL, self.gl))

    def test_only_offers_of_the_supervisor_field_are_offered(self):
        gl_offre = self._offre(Domaine.GENIE_LOGICIEL)
        data_offre = self._offre(Domaine.DATA_IA)
        self.client.force_login(self.gl)
        form = self.client.get(reverse('pfe:creer_projet_encadrant')).context['form']
        offres = set(form.fields['offre'].queryset)
        self.assertIn(gl_offre, offres)
        self.assertNotIn(data_offre, offres)

    def test_supervisor_at_capacity_cannot_create_a_project(self):
        self.gl.capacite_encadrement = 1
        self.gl.save(update_fields=['capacite_encadrement'])
        ProjetPFE.objects.create(etudiant=self.etudiants[6], encadrant_acad=self.gl, sujet='x')
        self.client.force_login(self.gl)
        response = self.client.post(reverse('pfe:creer_projet_encadrant'), {
            'etudiant': self.etudiants[7].pk, 'sujet': 'Encore un', 'description': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'capacité')
        self.assertFalse(ProjetPFE.objects.filter(etudiant=self.etudiants[7]).exists())

    def test_student_declared_project_needs_a_field(self):
        self.client.force_login(self.etudiants[6])
        response = self.client.post(reverse('pfe:mon_pfe'), {'sujet': 'Mon sujet', 'description': ''})
        self.assertIn('domaine', response.context['form'].errors)

    def test_project_from_accepted_application_gets_the_offer_field(self):
        offre = self._offre(Domaine.DATA_IA)
        Candidature.objects.create(etudiant=self.etudiants[6], offre=offre, cv='cv.pdf',
                                   lettre_motivation='x', status=Candidature.Status.ACCEPTEE)
        self.client.force_login(self.etudiants[6])
        self.client.get(reverse('pfe:mon_pfe'))
        projet = ProjetPFE.objects.get(etudiant=self.etudiants[6])
        self.assertEqual(projet.domaine, Domaine.DATA_IA)
