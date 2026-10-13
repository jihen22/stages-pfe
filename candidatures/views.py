from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from accounts.mixins import RoleRequiredMixin, role_required
from accounts.models import ProfilEtudiant, User
from notifications.services import notify
from offres.models import Offre

from .forms import CandidatureForm
from .models import Candidature


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------

class MesCandidaturesListView(RoleRequiredMixin, ListView):
    template_name = 'candidatures/mes_candidatures.html'
    context_object_name = 'candidatures'
    allowed_roles = (User.Role.ETUDIANT,)

    def get_queryset(self):
        return (
            Candidature.objects.filter(etudiant=self.request.user)
            .select_related('offre', 'offre__encadrant_pro')
        )


@role_required(User.Role.ETUDIANT)
def postuler(request, offre_pk):
    """Apply to a published offer (CV upload + cover letter)."""
    offre = get_object_or_404(Offre, pk=offre_pk, status=Offre.Status.PUBLIEE)

    if Candidature.objects.filter(etudiant=request.user, offre=offre).exists():
        messages.info(request, 'Vous avez déjà postulé à cette offre.')
        return redirect('candidatures:mes_candidatures')

    profil, _ = ProfilEtudiant.objects.get_or_create(user=request.user)
    profil_incomplet = not profil.is_complete
    avertissement = (
        'Votre profil étudiant est incomplet : complétez-le pour augmenter vos chances. '
        'La candidature reste possible.'
    )

    if request.method == 'POST':
        form = CandidatureForm(request.POST, request.FILES)
        if form.is_valid():
            candidature = form.save(commit=False)
            candidature.etudiant = request.user
            candidature.offre = offre
            candidature.save()
            notify(
                offre.encadrant_pro,
                f'{request.user.get_full_name() or request.user.username} a postulé à « {offre.titre} ».',
                reverse('candidatures:candidatures_recues'),
            )
            if profil_incomplet:
                messages.warning(request, avertissement)
            messages.success(request, 'Votre candidature a bien été envoyée.')
            return redirect('candidatures:mes_candidatures')
    else:
        form = CandidatureForm()
        if profil_incomplet:
            messages.warning(request, avertissement)

    return render(request, 'candidatures/candidature_form.html', {'form': form, 'offre': offre})


# ---------------------------------------------------------------------------
# Company supervisor
# ---------------------------------------------------------------------------

class CandidaturesRecuesListView(RoleRequiredMixin, ListView):
    template_name = 'candidatures/candidatures_recues.html'
    context_object_name = 'candidatures'
    allowed_roles = (User.Role.ENCADRANT_PRO,)

    def get_queryset(self):
        qs = (
            Candidature.objects.filter(offre__encadrant_pro=self.request.user)
            .select_related('etudiant', 'offre')
        )
        offre_id = self.request.GET.get('offre')
        if offre_id and offre_id.isdigit():
            qs = qs.filter(offre_id=offre_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mes_offres'] = Offre.objects.filter(encadrant_pro=self.request.user)
        context['offre_selected'] = self.request.GET.get('offre', '')
        return context


@role_required(User.Role.ENCADRANT_PRO)
@require_POST
def accepter_candidature(request, pk):
    candidature = get_object_or_404(Candidature, pk=pk, offre__encadrant_pro=request.user)
    candidature.status = Candidature.Status.ACCEPTEE
    candidature.save(update_fields=['status'])
    notify(
        candidature.etudiant,
        f'Votre candidature à « {candidature.offre.titre} » a été acceptée.',
        reverse('candidatures:mes_candidatures'),
    )
    messages.success(request, 'Candidature acceptée.')
    return redirect('candidatures:candidatures_recues')


@role_required(User.Role.ENCADRANT_PRO)
@require_POST
def refuser_candidature(request, pk):
    candidature = get_object_or_404(Candidature, pk=pk, offre__encadrant_pro=request.user)
    candidature.status = Candidature.Status.REFUSEE
    candidature.save(update_fields=['status'])
    notify(
        candidature.etudiant,
        f'Votre candidature à « {candidature.offre.titre} » a été refusée.',
        reverse('candidatures:mes_candidatures'),
    )
    messages.warning(request, 'Candidature refusée.')
    return redirect('candidatures:candidatures_recues')
