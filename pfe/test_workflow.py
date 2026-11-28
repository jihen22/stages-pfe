"""Tests for the PFE state machine (backlog item 14)."""


from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from notifications.models import Notification
from soutenances import fabriques
from soutenances.models import NoteSoutenance, Soutenance

from .models import HistoriqueStatut, Livrable, ProjetPFE
from .workflow import TRANSITIONS, TransitionInterdite, appliquer, peut

S = ProjetPFE.Status


class WorkflowBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT)
        cls.etudiant2 = User.objects.create_user(
            username='etudiant2', password='demo1234', role=User.Role.ETUDIANT)
        cls.acad = User.objects.create_user(
            username='acad', password='demo1234', role=User.Role.ENCADRANT_ACAD)
        cls.acad2 = User.objects.create_user(
            username='acad2', password='demo1234', role=User.Role.ENCADRANT_ACAD)
        cls.admin = User.objects.create_user(
            username='admin', password='demo1234', role=User.Role.ADMIN)
        cls.jury = User.objects.create_user(
            username='jury', password='demo1234', role=User.Role.JURY)
        cls.jury2 = User.objects.create_user(
            username='jury2', password='demo1234', role=User.Role.JURY)

    def _projet(self, status=None, encadrant=True, etudiant=None):
        projet = ProjetPFE.objects.create(
            etudiant=etudiant or self.etudiant,
            encadrant_acad=self.acad if encadrant else None,
            sujet='Sujet',
        )
        if status:
            ProjetPFE.objects.filter(pk=projet.pk).update(status=status)
            projet.refresh_from_db()
        return projet

    def _livrable(self, projet, status):
        return Livrable.objects.create(projet=projet, titre='Rapport', fichier='x.pdf', status=status)


class InitialStateTests(WorkflowBaseTestCase):
    def test_new_project_without_supervisor_is_waiting(self):
        projet = self._projet(encadrant=False)
        self.assertEqual(projet.status, S.EN_ATTENTE)

    def test_new_project_with_supervisor_is_in_progress(self):
        projet = self._projet()
        self.assertEqual(projet.status, S.EN_COURS)

    def test_creation_is_recorded_in_history(self):
        projet = self._projet()
        historique = list(projet.historique.values_list('ancien', 'nouveau'))
        self.assertEqual(historique, [('', S.EN_COURS)])


class TransitionRulesTests(WorkflowBaseTestCase):
    def test_every_state_is_reachable(self):
        cibles = {t.cible for t in TRANSITIONS.values()} | {S.EN_ATTENTE}
        self.assertEqual(cibles, set(S.values))

    def test_transition_from_wrong_state_is_refused(self):
        projet = self._projet(encadrant=False)
        with self.assertRaises(TransitionInterdite):
            appliquer(projet, 'terminer')
        projet.refresh_from_db()
        self.assertEqual(projet.status, S.EN_ATTENTE)

    def test_cannot_skip_steps(self):
        projet = self._projet()
        for nom in ('planifier', 'soutenir', 'rouvrir'):
            with self.subTest(transition=nom), self.assertRaises(TransitionInterdite):
                appliquer(projet, nom)

    def test_affecter_sets_supervisor_and_records_author(self):
        projet = self._projet(encadrant=False)
        appliquer(projet, 'affecter', auteur=self.acad, encadrant_acad=self.acad)
        projet.refresh_from_db()
        self.assertEqual(projet.status, S.EN_COURS)
        self.assertEqual(projet.encadrant_acad, self.acad)
        dernier = projet.historique.last()
        self.assertEqual((dernier.ancien, dernier.nouveau, dernier.auteur),
                         (S.EN_ATTENTE, S.EN_COURS, self.acad))

    def test_liberer_removes_supervisor(self):
        projet = self._projet()
        appliquer(projet, 'liberer', auteur=self.acad)
        projet.refresh_from_db()
        self.assertEqual(projet.status, S.EN_ATTENTE)
        self.assertIsNone(projet.encadrant_acad)

    def test_terminer_requires_a_validated_deliverable(self):
        projet = self._projet()
        self.assertFalse(peut(projet, 'terminer'))
        self._livrable(projet, Livrable.Status.A_CORRIGER)
        with self.assertRaises(TransitionInterdite):
            appliquer(projet, 'terminer')

    def test_terminer_refused_while_a_deliverable_awaits_review(self):
        projet = self._projet()
        self._livrable(projet, Livrable.Status.VALIDE)
        self._livrable(projet, Livrable.Status.DEPOSE)
        self.assertFalse(peut(projet, 'terminer'))

    def test_terminer_then_rouvrir(self):
        projet = self._projet()
        self._livrable(projet, Livrable.Status.VALIDE)
        appliquer(projet, 'terminer', auteur=self.acad)
        self.assertEqual(projet.status, S.TERMINE)
        appliquer(projet, 'rouvrir', auteur=self.acad)
        projet.refresh_from_db()
        self.assertEqual(projet.status, S.EN_COURS)

    def test_stale_object_cannot_overwrite_a_newer_state(self):
        """Two requests read the same project; only the first change wins."""
        projet = self._projet()
        self._livrable(projet, Livrable.Status.VALIDE)
        copie = ProjetPFE.objects.get(pk=projet.pk)
        appliquer(projet, 'liberer', auteur=self.acad)
        with self.assertRaises(TransitionInterdite):
            appliquer(copie, 'terminer', auteur=self.acad)
        projet.refresh_from_db()
        self.assertEqual(projet.status, S.EN_ATTENTE)

    def test_soutenir_requires_every_jury_grade(self):
        projet = self._projet(S.PLANIFIE)
        soutenance = fabriques.soutenance(projet, jours=3, nom_salle='A1')
        soutenance.jury.set([self.jury, self.jury2])
        NoteSoutenance.objects.create(soutenance=soutenance, jury_member=self.jury, note=14)
        projet = ProjetPFE.objects.get(pk=projet.pk)
        self.assertFalse(peut(projet, 'soutenir'))
        NoteSoutenance.objects.create(soutenance=soutenance, jury_member=self.jury2, note=16)
        self.assertTrue(peut(projet, 'soutenir'))


class SupervisorLifecycleViewTests(WorkflowBaseTestCase):
    def test_supervisor_can_finish_a_project(self):
        projet = self._projet()
        self._livrable(projet, Livrable.Status.VALIDE)
        self.client.force_login(self.acad)
        response = self.client.post(reverse('pfe:terminer_projet', args=[projet.pk]))
        self.assertRedirects(response, reverse('pfe:mes_etudiants'))
        projet.refresh_from_db()
        self.assertEqual(projet.status, S.TERMINE)
        self.assertTrue(Notification.objects.filter(user=self.etudiant, message__contains='terminé').exists())

    def test_guard_failure_shows_an_error_and_keeps_the_state(self):
        projet = self._projet()
        self.client.force_login(self.acad)
        response = self.client.post(reverse('pfe:terminer_projet', args=[projet.pk]), follow=True)
        self.assertContains(response, 'Au moins un livrable doit être validé')
        projet.refresh_from_db()
        self.assertEqual(projet.status, S.EN_COURS)

    def test_supervisor_can_reopen_a_finished_project(self):
        projet = self._projet(S.TERMINE)
        self.client.force_login(self.acad)
        self.client.post(reverse('pfe:rouvrir_projet', args=[projet.pk]))
        projet.refresh_from_db()
        self.assertEqual(projet.status, S.EN_COURS)

    def test_only_the_projects_supervisor_can_change_it(self):
        projet = self._projet(S.TERMINE)
        self.client.force_login(self.acad2)
        response = self.client.post(reverse('pfe:rouvrir_projet', args=[projet.pk]))
        self.assertEqual(response.status_code, 404)

    def test_other_roles_are_forbidden(self):
        projet = self._projet(S.TERMINE)
        for user in (self.etudiant, self.admin, self.jury):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.post(reverse('pfe:rouvrir_projet', args=[projet.pk]))
                self.assertEqual(response.status_code, 403)

    def test_actions_require_post(self):
        projet = self._projet()
        self.client.force_login(self.acad)
        self.assertEqual(self.client.get(reverse('pfe:terminer_projet', args=[projet.pk])).status_code, 405)

    def test_finished_project_cannot_be_released(self):
        projet = self._projet(S.TERMINE)
        self.client.force_login(self.acad)
        self.client.post(reverse('pfe:liberer_projet', args=[projet.pk]))
        projet.refresh_from_db()
        self.assertEqual(projet.encadrant_acad, self.acad)
        self.assertEqual(projet.status, S.TERMINE)

    def test_list_shows_the_finish_button_only_when_allowed(self):
        pret = self._projet()
        self._livrable(pret, Livrable.Status.VALIDE)
        pas_pret = self._projet(etudiant=self.etudiant2)
        self.client.force_login(self.acad)
        response = self.client.get(reverse('pfe:mes_etudiants'))
        self.assertContains(response, reverse('pfe:terminer_projet', args=[pret.pk]))
        self.assertNotContains(response, reverse('pfe:terminer_projet', args=[pas_pret.pk]))


class StudentLifecycleViewTests(WorkflowBaseTestCase):
    def test_upload_is_closed_once_the_project_is_finished(self):
        projet = self._projet(S.TERMINE)
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('pfe:deposer_livrable', args=[projet.pk]))
        self.assertRedirects(response, reverse('pfe:mon_pfe'))
        page = self.client.get(reverse('pfe:mon_pfe'))
        self.assertContains(page, 'Dépôt fermé')

    def test_student_page_shows_the_current_step(self):
        self._projet()
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('pfe:mon_pfe'))
        self.assertContains(response, 'aria-current="step"')
        self.assertContains(response, 'Historique des changements de statut')


class DefenseLifecycleTests(WorkflowBaseTestCase):
    def _planifier(self, projet):
        self.client.force_login(self.admin)
        return self.client.post(reverse('soutenances:planifier'), {
            'projet': projet.pk,
            'creneau': fabriques.creneau(jours=10).pk,
            'salle': fabriques.salle('Amphi B').pk,
            'jury': [self.jury.pk, self.jury2.pk],
        })

    def test_only_finished_projects_can_be_scheduled(self):
        projet = self._projet()  # EN_COURS
        response = self._planifier(projet)
        self.assertEqual(response.status_code, 200)
        self.assertIn('projet', response.context['form'].errors)
        self.assertFalse(Soutenance.objects.exists())

    def test_scheduling_moves_the_project_to_planned(self):
        projet = self._projet(S.TERMINE)
        response = self._planifier(projet)
        self.assertRedirects(response, reverse('soutenances:planning'))
        projet.refresh_from_db()
        self.assertEqual(projet.status, S.PLANIFIE)
        self.assertTrue(HistoriqueStatut.objects.filter(
            projet=projet, nouveau=S.PLANIFIE, auteur=self.admin).exists())

    def test_last_jury_grade_marks_the_project_defended(self):
        projet = self._projet(S.TERMINE)
        self._planifier(projet)
        url = reverse('soutenances:saisir_note', args=[projet.soutenance.pk])

        self.client.force_login(self.jury)
        self.client.post(url, {'note': '15', 'remarque': ''})
        projet.refresh_from_db()
        self.assertEqual(projet.status, S.PLANIFIE)

        self.client.force_login(self.jury2)
        self.client.post(url, {'note': '17', 'remarque': ''})
        projet.refresh_from_db()
        self.assertEqual(projet.status, S.SOUTENU)
        self.assertTrue(Notification.objects.filter(user=self.etudiant, message__contains='16').exists())

    def test_grading_is_closed_before_the_defense_is_planned(self):
        projet = self._projet(S.EN_COURS)
        soutenance = fabriques.soutenance(projet, jours=3, nom_salle='A1')
        soutenance.jury.set([self.jury])
        self.client.force_login(self.jury)
        response = self.client.post(
            reverse('soutenances:saisir_note', args=[soutenance.pk]), {'note': '12'})
        self.assertRedirects(response, reverse('soutenances:saisir_notes'))
        self.assertFalse(NoteSoutenance.objects.exists())
