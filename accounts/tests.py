import shutil
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from candidatures.models import Candidature
from offres.models import Offre

from .models import Domaine, ProfilEtudiant, User

MEDIA_ROOT = tempfile.mkdtemp()


class DemoUserCommandTests(TestCase):
    def test_command_creates_one_user_per_role(self):
        from django.core.management import call_command

        call_command('create_demo_users')
        self.assertEqual(User.objects.count(), len(User.Role.choices))
        for user in User.objects.all():
            self.assertTrue(user.check_password('demo1234'))


class RoleProtectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT
        )
        cls.encadrant_pro = User.objects.create_user(
            username='pro', password='demo1234', role=User.Role.ENCADRANT_PRO
        )
        cls.admin = User.objects.create_user(
            username='admin', password='demo1234', role=User.Role.ADMIN
        )
        cls.encadrant_acad = User.objects.create_user(
            username='acad', password='demo1234', role=User.Role.ENCADRANT_ACAD
        )

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse('offres:offres_a_valider'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_student_cannot_access_offers_to_validate(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('offres:offres_a_valider'))
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_create_offre(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('offres:offre_create'))
        self.assertEqual(response.status_code, 403)

    def test_encadrant_pro_cannot_access_offers_to_validate(self):
        self.client.force_login(self.encadrant_pro)
        response = self.client.get(reverse('offres:offres_a_valider'))
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_access_offers_to_validate(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('offres:offres_a_valider'))
        self.assertEqual(response.status_code, 403)

    def test_academic_supervisor_can_access_offers_to_validate(self):
        self.client.force_login(self.encadrant_acad)
        response = self.client.get(reverse('offres:offres_a_valider'))
        self.assertEqual(response.status_code, 200)


class PageSmokeTests(TestCase):
    """Every role page must render for the right role (catches template errors)."""

    @classmethod
    def setUpTestData(cls):
        cls.users = {
            User.Role.ETUDIANT: User.objects.create_user(
                username='etudiant', password='demo1234', role=User.Role.ETUDIANT),
            User.Role.ENCADRANT_PRO: User.objects.create_user(
                username='pro', password='demo1234', role=User.Role.ENCADRANT_PRO),
            User.Role.ENCADRANT_ACAD: User.objects.create_user(
                username='acad', password='demo1234', role=User.Role.ENCADRANT_ACAD),
            User.Role.ADMIN: User.objects.create_user(
                username='admin', password='demo1234', role=User.Role.ADMIN),
            User.Role.JURY: User.objects.create_user(
                username='jury', password='demo1234', role=User.Role.JURY),
        }

    ROLE_PAGES = {
        User.Role.ETUDIANT: [
            'accounts:dashboard_etudiant', 'offres:offre_list',
            'candidatures:mes_candidatures', 'pfe:mon_pfe', 'soutenances:ma_soutenance',
            'accounts:profil_etudiant', 'notifications:list',
        ],
        User.Role.ENCADRANT_PRO: [
            'accounts:dashboard_encadrant_pro', 'offres:mes_offres',
            'offres:offre_create', 'candidatures:candidatures_recues', 'notifications:list',
        ],
        User.Role.ENCADRANT_ACAD: [
            'accounts:dashboard_encadrant_acad', 'pfe:affectations',
            'pfe:creer_projet_encadrant', 'pfe:mes_etudiants', 'pfe:livrables_a_valider',
            'offres:offres_a_valider', 'notifications:list',
        ],
        User.Role.ADMIN: [
            'accounts:dashboard_admin', 'soutenances:planning', 'notifications:list',
        ],
        User.Role.JURY: [
            'accounts:dashboard_jury', 'soutenances:mes_soutenances', 'soutenances:saisir_notes',
            'notifications:list',
        ],
    }

    def test_role_pages_render(self):
        for role, names in self.ROLE_PAGES.items():
            self.client.force_login(self.users[role])
            for name in names:
                with self.subTest(role=role, page=name):
                    response = self.client.get(reverse(name))
                    self.assertEqual(response.status_code, 200)

    def test_public_pages_render(self):
        for name in ('home', 'accounts:login', 'accounts:register'):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)


class LoginRedirectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT
        )

    def test_login_redirects_to_role_dashboard(self):
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'etudiant', 'password': 'demo1234'},
        )
        self.assertRedirects(response, reverse('accounts:dashboard_etudiant'))

    def test_dashboard_redirects_by_role(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertRedirects(response, reverse('accounts:dashboard_etudiant'))


class LandingPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT
        )

    def test_home_renders_for_anonymous(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Se connecter')

    def test_home_renders_for_authenticated_user(self):
        """Logged-in visitors keep the landing page but see the dashboard CTA."""
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aller à mon tableau de bord')


class ThemePreferenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT
        )

    def test_preferences_requires_login(self):
        response = self.client.get(reverse('accounts:preferences'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_preferences_renders_for_authenticated_user(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('accounts:preferences'))
        self.assertEqual(response.status_code, 200)

    def test_set_theme_requires_login(self):
        response = self.client.post(
            reverse('accounts:set_theme'), {'theme': 'DARK', 'accent': 'GREEN'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_set_theme_requires_post(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('accounts:set_theme'))
        self.assertEqual(response.status_code, 405)

    def test_set_theme_persists_values(self):
        self.client.force_login(self.etudiant)
        response = self.client.post(
            reverse('accounts:set_theme'), {'theme': 'DARK', 'accent': 'PURPLE'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'theme': 'DARK', 'accent': 'PURPLE'})
        self.etudiant.refresh_from_db()
        self.assertEqual(self.etudiant.theme, User.Theme.DARK)
        self.assertEqual(self.etudiant.accent, User.Accent.PURPLE)

    def test_set_theme_ignores_invalid_values(self):
        self.client.force_login(self.etudiant)
        response = self.client.post(
            reverse('accounts:set_theme'), {'theme': 'HACKED', 'accent': 'RAINBOW'}
        )
        self.assertEqual(response.status_code, 200)
        self.etudiant.refresh_from_db()
        self.assertEqual(self.etudiant.theme, User.Theme.AUTO)
        self.assertEqual(self.etudiant.accent, User.Accent.BLUE)


class StudentProfileModelTests(TestCase):
    def test_profile_is_created_for_new_student(self):
        etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT
        )
        self.assertTrue(ProfilEtudiant.objects.filter(user=etudiant).exists())

    def test_profile_is_not_created_for_other_roles(self):
        pro = User.objects.create_user(
            username='pro', password='demo1234', role=User.Role.ENCADRANT_PRO
        )
        self.assertFalse(ProfilEtudiant.objects.filter(user=pro).exists())

    def test_completion_starts_at_zero(self):
        etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT
        )
        profil = etudiant.profil_etudiant
        self.assertEqual(profil.completion, 0)
        self.assertFalse(profil.is_complete)

    def test_completion_reaches_hundred_when_all_fields_filled(self):
        etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT
        )
        profil = etudiant.profil_etudiant
        profil.filiere = 'Génie logiciel'
        profil.niveau = 'Master 2'
        profil.competences = 'Python, Django'
        profil.telephone = '+216 20 000 000'
        profil.bio = 'Présentation.'
        profil.cv_base = 'cvs_base/demo.txt'
        profil.save()
        self.assertEqual(profil.completion, 100)
        self.assertTrue(profil.is_complete)


class StudentProfileViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT
        )
        cls.encadrant = User.objects.create_user(
            username='pro', password='demo1234', role=User.Role.ENCADRANT_PRO
        )

    def test_requires_login(self):
        response = self.client.get(reverse('accounts:profil_etudiant'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_forbidden_for_non_student(self):
        self.client.force_login(self.encadrant)
        response = self.client.get(reverse('accounts:profil_etudiant'))
        self.assertEqual(response.status_code, 403)

    def test_student_can_view_and_update_profile(self):
        self.client.force_login(self.etudiant)
        self.assertEqual(self.client.get(reverse('accounts:profil_etudiant')).status_code, 200)
        response = self.client.post(reverse('accounts:profil_etudiant'), {
            'filiere': 'Génie logiciel',
            'niveau': 'Master 2',
            'competences': 'Python, Django',
            'telephone': '+216 20 000 000',
            'bio': 'Présentation.',
        })
        self.assertRedirects(response, reverse('accounts:profil_etudiant'))
        profil = self.etudiant.profil_etudiant
        profil.refresh_from_db()
        self.assertEqual(profil.filiere, 'Génie logiciel')
        self.assertEqual(profil.completion, 83)  # 5 fields out of 6 (cv_base empty)


class StudentDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etudiant = User.objects.create_user(
            username='etudiant', password='demo1234', role=User.Role.ETUDIANT
        )
        cls.encadrant = User.objects.create_user(
            username='pro', password='demo1234', role=User.Role.ENCADRANT_PRO
        )
        cls.offre_publiee = Offre.objects.create(
            encadrant_pro=cls.encadrant, titre='PFE IA',
            description='x', status=Offre.Status.PUBLIEE, type=Offre.Type.PFE,
        )
        Offre.objects.create(
            encadrant_pro=cls.encadrant, titre='Brouillon',
            description='x', status=Offre.Status.BROUILLON,
        )
        # One application per offer (unique constraint), one per status.
        for index, status in enumerate(
            (Candidature.Status.EN_ATTENTE, Candidature.Status.ACCEPTEE, Candidature.Status.REFUSEE),
            start=1,
        ):
            offre = Offre.objects.create(
                encadrant_pro=cls.encadrant, titre=f'Offre {index}',
                description='x', status=Offre.Status.PUBLIEE,
            )
            Candidature.objects.create(
                etudiant=cls.etudiant, offre=offre,
                cv='cvs/demo.txt', lettre_motivation='x', status=status,
            )

    def test_dashboard_counters(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('accounts:dashboard_etudiant'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['candidatures_total'], 3)
        self.assertEqual(response.context['candidatures_en_attente'], 1)
        self.assertEqual(response.context['candidatures_acceptees'], 1)
        self.assertEqual(response.context['candidatures_refusees'], 1)

    def test_dashboard_exposes_profile_progress_and_recent_offers(self):
        self.client.force_login(self.etudiant)
        response = self.client.get(reverse('accounts:dashboard_etudiant'))
        self.assertEqual(response.context['profil_completion'], 0)
        self.assertEqual(len(response.context['offres_recentes']), 3)
        self.assertTrue(
            all(o.status == Offre.Status.PUBLIEE for o in response.context['offres_recentes'])
        )
        # The three applied offers are flagged, the draft one is not.
        self.assertEqual(len(response.context['offres_postulees']), 3)
        self.assertNotIn(
            Offre.objects.get(titre='Brouillon').pk, response.context['offres_postulees']
        )

    def test_dashboard_forbidden_for_non_student(self):
        self.client.force_login(self.encadrant)
        response = self.client.get(reverse('accounts:dashboard_etudiant'))
        self.assertEqual(response.status_code, 403)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class SeedDemoCommandTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_seed_demo_is_idempotent(self):
        from django.core.management import call_command

        call_command('seed_demo')
        call_command('seed_demo')

        etudiant = User.objects.get(username='etudiant')
        encadrant = User.objects.get(username='encadrant_pro')

        self.assertEqual(Offre.objects.filter(encadrant_pro=encadrant).count(), 6)
        self.assertEqual(Candidature.objects.filter(etudiant=etudiant).count(), 3)
        self.assertEqual(etudiant.notifications.count(), 3)
        self.assertTrue(etudiant.profil_etudiant.is_complete)


class RegistrationTests(TestCase):
    """Item 1: self sign-up for students and company supervisors, then role-based login."""

    PASSWORD = 'Tek-Up#2026!'

    def _student_data(self, **extra):
        data = {
            'username': 'nouvel_etudiant', 'first_name': 'Amal', 'last_name': 'Ben Salem',
            'email': 'amal@example.com', 'password1': self.PASSWORD, 'password2': self.PASSWORD,
        }
        data.update(extra)
        return data

    def test_student_can_sign_up_then_log_in_to_their_dashboard(self):
        response = self.client.post(reverse('accounts:register'), self._student_data())
        self.assertRedirects(response, reverse('accounts:login'))

        user = User.objects.get(username='nouvel_etudiant')
        self.assertEqual(user.role, User.Role.ETUDIANT)
        self.assertTrue(ProfilEtudiant.objects.filter(user=user).exists())

        response = self.client.post(reverse('accounts:login'), {
            'username': 'nouvel_etudiant', 'password': self.PASSWORD,
        })
        self.assertRedirects(response, reverse('accounts:dashboard_etudiant'))

    def test_sign_up_cannot_choose_a_privileged_role(self):
        self.client.post(reverse('accounts:register'), self._student_data(role=User.Role.ADMIN))
        self.assertEqual(User.objects.get(username='nouvel_etudiant').role, User.Role.ETUDIANT)

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            reverse('accounts:register'), self._student_data(password2='Autre#2026!'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('password2', response.context['form'].errors)
        self.assertFalse(User.objects.filter(username='nouvel_etudiant').exists())

    def test_username_must_be_unique(self):
        User.objects.create_user(username='nouvel_etudiant', password='x')
        response = self.client.post(reverse('accounts:register'), self._student_data())
        self.assertIn('username', response.context['form'].errors)

    def test_company_supervisor_can_sign_up_with_their_company(self):
        response = self.client.post(reverse('accounts:register_encadrant_pro'), {
            'username': 'karim_pro', 'first_name': 'Karim', 'last_name': 'T',
            'email': 'karim@entreprise.tn', 'entreprise': 'Vermeg', 'poste': 'Lead dev',
            'password1': self.PASSWORD, 'password2': self.PASSWORD,
        })
        self.assertRedirects(response, reverse('accounts:login'))
        user = User.objects.get(username='karim_pro')
        self.assertEqual(user.role, User.Role.ENCADRANT_PRO)
        self.assertEqual(user.profil_encadrant_pro.entreprise, 'Vermeg')

        response = self.client.post(reverse('accounts:login'), {
            'username': 'karim_pro', 'password': self.PASSWORD,
        })
        self.assertRedirects(response, reverse('accounts:dashboard_encadrant_pro'))

    def test_company_supervisor_needs_email_and_company(self):
        response = self.client.post(reverse('accounts:register_encadrant_pro'), {
            'username': 'karim_pro', 'password1': self.PASSWORD, 'password2': self.PASSWORD,
        })
        errors = response.context['form'].errors
        for field in ('email', 'entreprise', 'poste'):
            self.assertIn(field, errors)
        self.assertFalse(User.objects.filter(username='karim_pro').exists())

    def test_wrong_password_does_not_log_in(self):
        User.objects.create_user(username='sami', password=self.PASSWORD, role=User.Role.ETUDIANT)
        response = self.client.post(reverse('accounts:login'), {
            'username': 'sami', 'password': 'mauvais',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logged_in_user_is_sent_away_from_sign_up(self):
        user = User.objects.create_user(username='sami', password=self.PASSWORD, role=User.Role.ETUDIANT)
        self.client.force_login(user)
        response = self.client.get(reverse('accounts:register'))
        self.assertRedirects(response, reverse('accounts:dashboard'), target_status_code=302)


class ProfileEditTests(TestCase):
    """Item 2: every role can view and edit its identity and password."""

    PASSWORD = 'Tek-Up#2026!'

    @classmethod
    def setUpTestData(cls):
        cls.users = {
            role: User.objects.create_user(
                username=f'u_{role.lower()}', password=cls.PASSWORD, role=role,
                first_name='Ancien', last_name='Nom', email=f'{role.lower()}@example.com')
            for role in User.Role.values
        }

    def test_every_role_can_update_name_and_email(self):
        for role, user in self.users.items():
            with self.subTest(role=role):
                self.client.force_login(user)
                response = self.client.post(reverse('accounts:preferences'), {
                    'section': 'infos', 'first_name': 'Nouveau', 'last_name': role.title(),
                    'email': f'nouveau.{role.lower()}@example.com',
                })
                self.assertRedirects(response, reverse('accounts:preferences') + '#infos',
                                     fetch_redirect_response=False)
                user.refresh_from_db()
                self.assertEqual((user.first_name, user.email), ('Nouveau', f'nouveau.{role.lower()}@example.com'))

    def test_every_role_can_change_password_and_stays_logged_in(self):
        for role, user in self.users.items():
            with self.subTest(role=role):
                self.client.force_login(user)
                self.client.post(reverse('accounts:preferences'), {
                    'section': 'securite', 'old_password': self.PASSWORD,
                    'new_password1': 'Nouveau#Mot2Passe', 'new_password2': 'Nouveau#Mot2Passe',
                })
                user.refresh_from_db()
                self.assertTrue(user.check_password('Nouveau#Mot2Passe'))
                # update_session_auth_hash keeps the session valid
                self.assertEqual(self.client.get(reverse('accounts:preferences')).status_code, 200)

    def test_wrong_current_password_is_refused(self):
        user = self.users[User.Role.JURY]
        self.client.force_login(user)
        response = self.client.post(reverse('accounts:preferences'), {
            'section': 'securite', 'old_password': 'faux',
            'new_password1': 'Nouveau#Mot2Passe', 'new_password2': 'Nouveau#Mot2Passe',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('old_password', response.context['form_securite'].errors)
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.PASSWORD))

    def test_invalid_email_is_shown_again(self):
        self.client.force_login(self.users[User.Role.ADMIN])
        response = self.client.post(reverse('accounts:preferences'), {
            'section': 'infos', 'first_name': 'A', 'last_name': 'B', 'email': 'pas-un-email'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active'], 'infos')
        self.assertIn('email', response.context['form_infos'].errors)

    def test_role_cannot_be_changed_through_the_form(self):
        user = self.users[User.Role.ETUDIANT]
        self.client.force_login(user)
        self.client.post(reverse('accounts:preferences'), {
            'section': 'infos', 'first_name': 'A', 'last_name': 'B', 'email': 'a@b.tn',
            'role': User.Role.ADMIN, 'capacite_encadrement': 30})
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.ETUDIANT)

    def test_unknown_section_is_ignored(self):
        self.client.force_login(self.users[User.Role.ADMIN])
        response = self.client.post(reverse('accounts:preferences'), {'section': 'entreprise'})
        self.assertRedirects(response, reverse('accounts:preferences'))

    def test_academic_supervisor_sees_field_and_capacity_read_only(self):
        user = self.users[User.Role.ENCADRANT_ACAD]
        user.domaine = Domaine.DATA_IA
        user.save()
        self.client.force_login(user)
        response = self.client.get(reverse('accounts:preferences'))
        self.assertContains(response, 'Data science et IA')
        self.assertContains(response, "fixés par l'administration")
        self.assertNotIn('domaine', response.context['form_infos'].fields)

    def test_company_supervisor_profile_still_works(self):
        user = self.users[User.Role.ENCADRANT_PRO]
        self.client.force_login(user)
        response = self.client.post(reverse('accounts:preferences'), {
            'section': 'entreprise', 'entreprise': 'Vermeg', 'poste': 'CTO'})
        self.assertRedirects(response, reverse('accounts:preferences') + '#entreprise',
                             fetch_redirect_response=False)
        self.assertEqual(user.profil_encadrant_pro.entreprise, 'Vermeg')

    def test_profile_requires_login(self):
        response = self.client.post(reverse('accounts:preferences'), {'section': 'infos'})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)
