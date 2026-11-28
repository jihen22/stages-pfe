from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse , reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from candidatures.models import Candidature
from offres.models import Offre
from offres.views import offres_a_valider_pour
from pfe.models import ProjetPFE

from .forms import BootstrapAuthenticationForm, BootstrapPasswordChangeForm, ProfilEtudiantForm, StudentRegistrationForm , EncadrantProRegistrationForm , ProfilEncadrantProForm, UserInfoForm
from .mixins import role_required
from .models import ProfilEncadrantPro, ProfilEtudiant, User


def home(request):
    """Public landing page.

    Rendered for everyone (including authenticated users): the hero buttons
    simply switch to "Aller à mon tableau de bord" when logged in.
    """
    return render(request, 'home.html')


class LoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'
    authentication_form = BootstrapAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        """Send the user straight to the dashboard of their role."""
        return self.get_redirect_url() or self.request.user.get_dashboard_url()


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('accounts:login')


class RegisterView(CreateView):
    """Student self-registration."""

    form_class = StudentRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')
    extra_context = {'type_compte': 'etudiant'}

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Compte créé avec succès, vous pouvez vous connecter.')
        return super().form_valid(form)

class EncadrantProRegisterView(RegisterView):
    """Inscription d'un encadrant professionnel (réutilise toute la logique de RegisterView)."""

    form_class = EncadrantProRegistrationForm
    extra_context = {'type_compte': 'encadrant_pro'}


@login_required
def dashboard(request):
    """Single entry point redirecting to the dashboard of the user's role."""
    return redirect(request.user.get_dashboard_url())


# ---------------------------------------------------------------------------
# One dashboard per role
# ---------------------------------------------------------------------------

@role_required(User.Role.ETUDIANT)
def dashboard_etudiant(request):
    candidatures = request.user.candidatures.select_related('offre', 'offre__encadrant_pro')
    profil, _ = ProfilEtudiant.objects.get_or_create(user=request.user)
    offres_recentes = (
        Offre.objects.filter(status=Offre.Status.PUBLIEE).select_related('encadrant_pro')[:3]
    )
    context = {
        'candidatures_total': candidatures.count(),
        'candidatures_en_attente': candidatures.filter(status=Candidature.Status.EN_ATTENTE).count(),
        'candidatures_acceptees': candidatures.filter(status=Candidature.Status.ACCEPTEE).count(),
        'candidatures_refusees': candidatures.filter(status=Candidature.Status.REFUSEE).count(),
        'dernieres_candidatures': candidatures[:5],
        'offres_recentes': offres_recentes,
        'offres_postulees': set(candidatures.values_list('offre_id', flat=True)),
        'profil': profil,
        'profil_completion': profil.completion,
    }
    return render(request, 'accounts/dashboards/etudiant.html', context)


@role_required(User.Role.ENCADRANT_PRO)
def dashboard_encadrant_pro(request):
    offres = Offre.objects.filter(encadrant_pro=request.user)
    context = {
        'offres_count': offres.count(),
        'offres_publiees_count': offres.filter(status=Offre.Status.PUBLIEE).count(),
        'candidatures_count': Candidature.objects.filter(offre__encadrant_pro=request.user).count(),
        'candidatures_attente_count': Candidature.objects.filter(
            offre__encadrant_pro=request.user, status=Candidature.Status.EN_ATTENTE
        ).count(),
    }
    return render(request, 'accounts/dashboards/encadrant_pro.html', context)


@role_required(User.Role.ENCADRANT_ACAD)
def dashboard_encadrant_acad(request):
    context = {
        'projets_disponibles': ProjetPFE.objects.filter(encadrant_acad__isnull=True).count(),
        'offres_a_valider': offres_a_valider_pour(request.user).count(),
    }
    return render(request, 'accounts/dashboards/encadrant_acad.html', context)


@role_required(User.Role.ADMIN)
def dashboard_admin(request):
    context = {
        'offres_en_validation': Offre.objects.filter(status=Offre.Status.EN_VALIDATION).count(),
        'offres_publiees': Offre.objects.filter(status=Offre.Status.PUBLIEE).count(),
        'candidatures_total': Candidature.objects.count(),
        'utilisateurs_total': User.objects.count(),
    }
    return render(request, 'accounts/dashboards/admin.html', context)


@role_required(User.Role.JURY)
def dashboard_jury(request):
    return render(request, 'accounts/dashboards/jury.html')


# ---------------------------------------------------------------------------
# Profile & appearance (theme / accent)
# ---------------------------------------------------------------------------

@login_required
def preferences(request):
    """Page profil : version riche pour l'encadrant pro, version standard pour les autres."""
    if request.user.is_encadrant_pro:
        return profil_encadrant_pro(request)
    return render(request, 'accounts/preferences.html', {
        'themes': User.Theme.choices,
        'accents': User.Accent.choices,
    })


SECTION_MESSAGES = {
    'infos': 'Vos informations ont été mises à jour.',
    'entreprise': "Les informations de l'entreprise ont été enregistrées.",
    'securite': 'Votre mot de passe a été modifié.',
}


def profil_encadrant_pro(request):
    """Profil de l'encadrant pro : infos, entreprise, sécurité, apparence."""
    user = request.user
    profil, _ = ProfilEncadrantPro.objects.get_or_create(user=user)

    forms_ = {
        'infos': UserInfoForm(instance=user),
        'entreprise': ProfilEncadrantProForm(instance=profil),
        'securite': BootstrapPasswordChangeForm(user),
    }
    active = 'infos'

    if request.method == 'POST':
        section = request.POST.get('section')
        if section == 'infos':
            form = UserInfoForm(request.POST, instance=user)
        elif section == 'entreprise':
            form = ProfilEncadrantProForm(request.POST, instance=profil)
        elif section == 'securite':
            form = BootstrapPasswordChangeForm(user, request.POST)
        else:
            return redirect('accounts:preferences')

        if form.is_valid():
            saved = form.save()
            if section == 'securite':
                # Sans cette ligne, changer le mot de passe déconnecte l'utilisateur
                update_session_auth_hash(request, saved)
            messages.success(request, SECTION_MESSAGES[section])
            return redirect(f"{reverse('accounts:preferences')}#{section}")

        forms_[section] = form   # on réaffiche le formulaire avec ses erreurs
        active = section

    offres = Offre.objects.filter(encadrant_pro=user)
    return render(request, 'accounts/profil_encadrant_pro.html', {
        'profil': profil,
        'form_infos': forms_['infos'],
        'form_entreprise': forms_['entreprise'],
        'form_securite': forms_['securite'],
        'active': active,
        'stats': {
            'offres': offres.count(),
            'publiees': offres.filter(status=Offre.Status.PUBLIEE).count(),
            'candidatures': Candidature.objects.filter(offre__encadrant_pro=user).count(),
        },
        'themes': User.Theme.choices,
        'accents': User.Accent.choices,
    })


@role_required(User.Role.ETUDIANT)
def profil_etudiant(request):
    """Edit page for the student profile."""
    profil, _ = ProfilEtudiant.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfilEtudiantForm(request.POST, request.FILES, instance=profil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre profil étudiant a été mis à jour.')
            return redirect('accounts:profil_etudiant')
    else:
        form = ProfilEtudiantForm(instance=profil)
    return render(request, 'accounts/profil_etudiant.html', {'form': form, 'profil': profil})


@login_required
@require_POST
def set_theme(request):
    """Persist the visitor's theme/accent on the User model (AJAX endpoint).

    Visitors (anonymous) never reach this view: they keep their choice in
    ``localStorage`` only, handled client-side.
    """
    theme = request.POST.get('theme')
    accent = request.POST.get('accent')
    updated = []
    if theme in User.Theme.values and theme != request.user.theme:
        request.user.theme = theme
        updated.append('theme')
    if accent in User.Accent.values and accent != request.user.accent:
        request.user.accent = accent
        updated.append('accent')
    if updated:
        request.user.save(update_fields=updated)
    return JsonResponse({
        'theme': request.user.theme,
        'accent': request.user.accent,
    })

