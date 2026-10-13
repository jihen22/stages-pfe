from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.mixins import RoleRequiredMixin, role_required
from accounts.models import User
from candidatures.models import Candidature

from .forms import OffreForm
from .models import Offre


# ---------------------------------------------------------------------------
# Student: browse published offers
# ---------------------------------------------------------------------------

class OffreListView(RoleRequiredMixin, ListView):
    """List published offers with search + type filter (students only)."""

    model = Offre
    template_name = 'offres/offre_list.html'
    context_object_name = 'offres'
    paginate_by = 9
    allowed_roles = (User.Role.ETUDIANT,)

    def get_queryset(self):
        qs = Offre.objects.filter(status=Offre.Status.PUBLIEE).select_related('encadrant_pro')
        q = self.request.GET.get('q', '').strip()
        type_ = self.request.GET.get('type', '').strip()
        if q:
            qs = qs.filter(
                Q(titre__icontains=q)
                | Q(description__icontains=q)
                | Q(competences__icontains=q)
            )
        if type_ in Offre.Type.values:
            qs = qs.filter(type=type_)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['type_selected'] = self.request.GET.get('type', '')
        context['types'] = Offre.Type.choices
        return context


class OffreDetailView(RoleRequiredMixin, DetailView):
    model = Offre
    template_name = 'offres/offre_detail.html'
    context_object_name = 'offre'
    allowed_roles = (User.Role.ETUDIANT,)

    def get_queryset(self):
        return Offre.objects.select_related('encadrant_pro')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['deja_postule'] = Candidature.objects.filter(
            etudiant=self.request.user, offre=self.object
        ).exists()
        return context


# ---------------------------------------------------------------------------
# Company supervisor: manage own offers
# ---------------------------------------------------------------------------

class MesOffresListView(RoleRequiredMixin, ListView):
    template_name = 'offres/mes_offres.html'
    context_object_name = 'offres'
    allowed_roles = (User.Role.ENCADRANT_PRO,)

    def get_queryset(self):
        return Offre.objects.filter(encadrant_pro=self.request.user)


class OffreCreateView(RoleRequiredMixin, CreateView):
    model = Offre
    form_class = OffreForm
    template_name = 'offres/offre_form.html'
    allowed_roles = (User.Role.ENCADRANT_PRO,)

    def form_valid(self, form):
        form.instance.encadrant_pro = self.request.user
        if self.request.POST.get('action') == 'soumettre':
            form.instance.status = Offre.Status.EN_VALIDATION
            messages.success(self.request, 'Offre créée et soumise à validation.')
        else:
            messages.success(self.request, 'Offre enregistrée en brouillon.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('offres:mes_offres')


class OffreUpdateView(RoleRequiredMixin, UpdateView):
    model = Offre
    form_class = OffreForm
    template_name = 'offres/offre_form.html'
    allowed_roles = (User.Role.ENCADRANT_PRO,)

    def get_queryset(self):
        return Offre.objects.filter(encadrant_pro=self.request.user)

    def form_valid(self, form):
        if self.request.POST.get('action') == 'soumettre':
            form.instance.status = Offre.Status.EN_VALIDATION
            form.instance.motif_refus = ''
            messages.success(self.request, 'Offre soumise à validation.')
        else:
            messages.success(self.request, 'Offre mise à jour.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('offres:mes_offres')


@role_required(User.Role.ENCADRANT_PRO)
@require_POST
def soumettre_offre(request, pk):
    """Move a draft/rejected own offer to the validation queue."""
    offre = get_object_or_404(Offre, pk=pk, encadrant_pro=request.user)
    if offre.status in (Offre.Status.BROUILLON, Offre.Status.REFUSEE):
        offre.status = Offre.Status.EN_VALIDATION
        offre.motif_refus = ''
        offre.save(update_fields=['status', 'motif_refus'])
        messages.success(request, f'L\'offre « {offre.titre} » est soumise à validation.')
    return redirect('offres:mes_offres')


# ---------------------------------------------------------------------------
# Administration: validate / reject offers
# ---------------------------------------------------------------------------

class OffresAValiderListView(RoleRequiredMixin, ListView):
    template_name = 'offres/offres_a_valider.html'
    context_object_name = 'offres'
    allowed_roles = (User.Role.ADMIN,)

    def get_queryset(self):
        return Offre.objects.filter(status=Offre.Status.EN_VALIDATION).select_related('encadrant_pro')


@role_required(User.Role.ADMIN)
@require_POST
def valider_offre(request, pk):
    offre = get_object_or_404(Offre, pk=pk)
    offre.status = Offre.Status.PUBLIEE
    offre.date_publication = timezone.now()
    offre.motif_refus = ''
    offre.save(update_fields=['status', 'date_publication', 'motif_refus'])
    messages.success(request, f'L\'offre « {offre.titre} » est publiée.')
    return redirect('offres:offres_a_valider')


@role_required(User.Role.ADMIN)
@require_POST
def refuser_offre(request, pk):
    offre = get_object_or_404(Offre, pk=pk)
    offre.status = Offre.Status.REFUSEE
    offre.motif_refus = request.POST.get('motif', '').strip()
    offre.save(update_fields=['status', 'motif_refus'])
    messages.warning(request, f'L\'offre « {offre.titre} » est refusée.')
    return redirect('offres:offres_a_valider')
