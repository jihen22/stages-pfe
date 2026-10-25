from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.mixins import role_required
from accounts.models import User
from candidatures.models import Candidature
from notifications.services import notify

from .forms import LivrableForm, ProjetEncadrantForm, ProjetPFEForm
from .models import Livrable, ProjetPFE


# ---------------------------------------------------------------------------
# Deliverable review helpers (shared by the list and action views)
# ---------------------------------------------------------------------------

def _valider_livrable(request, livrable):
    """Mark a deliverable as validated, save the optional comment and notify the student."""
    commentaire = request.POST.get('commentaire_encadrant', '').strip()
    livrable.status = Livrable.Status.VALIDE
    fields = ['status']
    if commentaire:
        livrable.commentaire_encadrant = commentaire
        fields.append('commentaire_encadrant')
    livrable.save(update_fields=fields)

    notify(
        livrable.projet.etudiant,
        f"Votre livrable « {livrable.titre} » a été validé.",
        reverse('pfe:mon_pfe'),
    )
    messages.success(request, f"Le livrable « {livrable.titre} » a été validé.")


def _demander_corrections(request, livrable):
    """Ask the student for corrections, save the optional comment and notify them."""
    commentaire = request.POST.get('commentaire_encadrant', '').strip()
    livrable.status = Livrable.Status.A_CORRIGER
    fields = ['status']
    if commentaire:
        livrable.commentaire_encadrant = commentaire
        fields.append('commentaire_encadrant')
    livrable.save(update_fields=fields)

    suffix = f" Remarque : {commentaire}" if commentaire else ""
    notify(
        livrable.projet.etudiant,
        f"Des corrections ont été demandées pour le livrable « {livrable.titre} ».{suffix}",
        reverse('pfe:mon_pfe'),
    )
    messages.warning(request, f"Des corrections ont été demandées pour « {livrable.titre} ».")


# ---------------------------------------------------------------------------
# Student views
# ---------------------------------------------------------------------------

@role_required(User.Role.ETUDIANT)
def mon_pfe(request):
    """Display the student's PFE project or initialize it from an accepted offer."""
    projet = (
        ProjetPFE.objects.filter(etudiant=request.user)
        .select_related('encadrant_acad', 'offre', 'offre__encadrant_pro')
        .first()
    )

    if projet:
        return render(request, 'pfe/mon_pfe.html', {
            'projet': projet,
            'livrables': projet.livrables.all(),
        })

    # Check if the student has an accepted candidature to auto-create the project
    accepted_cand = (
        Candidature.objects.filter(etudiant=request.user, status=Candidature.Status.ACCEPTEE)
        .select_related('offre')
        .first()
    )
    if accepted_cand:
        projet = ProjetPFE.objects.create(
            etudiant=request.user,
            offre=accepted_cand.offre,
            sujet=accepted_cand.offre.titre,
            description=accepted_cand.offre.description,
        )
        messages.info(request, 'Votre projet PFE a été initialisé depuis votre candidature acceptée.')
        return render(request, 'pfe/mon_pfe.html', {
            'projet': projet,
            'livrables': projet.livrables.all(),
        })

    if request.method == 'POST':
        form = ProjetPFEForm(request.POST)
        if form.is_valid():
            projet = form.save(commit=False)
            projet.etudiant = request.user
            projet.save()
            messages.success(request, 'Votre projet PFE a été créé avec succès.')
            return redirect('pfe:mon_pfe')
    else:
        form = ProjetPFEForm()

    return render(request, 'pfe/mon_pfe.html', {'projet': None, 'form': form})


@role_required(User.Role.ETUDIANT)
def deposer_livrable(request, projet_pk):
    """Upload a new deliverable (report, presentation, code archive, etc.)."""
    projet = get_object_or_404(ProjetPFE, pk=projet_pk, etudiant=request.user)

    if request.method == 'POST':
        form = LivrableForm(request.POST, request.FILES)
        if form.is_valid():
            livrable = form.save(commit=False)
            livrable.projet = projet
            livrable.status = Livrable.Status.DEPOSE
            livrable.save()

            if projet.encadrant_acad:
                student_name = request.user.get_full_name() or request.user.username
                notify(
                    projet.encadrant_acad,
                    f"{student_name} a déposé un nouveau livrable : « {livrable.titre} ».",
                    reverse('pfe:livrables_a_valider'),
                )

            messages.success(request, 'Votre livrable a été déposé avec succès.')
            return redirect('pfe:mon_pfe')
    else:
        form = LivrableForm()

    return render(request, 'pfe/deposer_livrable.html', {'projet': projet, 'form': form})


# ---------------------------------------------------------------------------
# Academic supervisor views
# ---------------------------------------------------------------------------

@role_required(User.Role.ENCADRANT_ACAD)
def mes_etudiants(request):
    """List all PFE projects supervised by the current academic supervisor."""
    projets = (
        ProjetPFE.objects.filter(encadrant_acad=request.user)
        .select_related('etudiant', 'etudiant__profil_etudiant', 'offre')
        .prefetch_related('livrables')
        .order_by('-date_creation')
    )
    return render(request, 'pfe/mes_etudiants.html', {'projets': projets})


@role_required(User.Role.ENCADRANT_ACAD)
def livrables_a_valider(request):
    """List pending deliverables waiting for review by the academic supervisor."""
    if request.method == 'POST':
        action = request.POST.get('action')
        livrable_id = request.POST.get('livrable_id')
        if livrable_id and action in ('valider', 'corriger'):
            livrable = get_object_or_404(Livrable, pk=livrable_id, projet__encadrant_acad=request.user)
            if action == 'valider':
                _valider_livrable(request, livrable)
            else:
                _demander_corrections(request, livrable)
            return redirect('pfe:livrables_a_valider')

    livrables = (
        Livrable.objects.filter(projet__encadrant_acad=request.user, status=Livrable.Status.DEPOSE)
        .select_related('projet', 'projet__etudiant', 'projet__offre')
        .order_by('-date_depot')
    )
    return render(request, 'pfe/livrables_a_valider.html', {'livrables': livrables})


@role_required(User.Role.ENCADRANT_ACAD)
@require_POST
def valider_livrable(request, pk):
    """Validate a student's deliverable."""
    livrable = get_object_or_404(Livrable, pk=pk, projet__encadrant_acad=request.user)
    _valider_livrable(request, livrable)
    return redirect('pfe:livrables_a_valider')


@role_required(User.Role.ENCADRANT_ACAD)
@require_POST
def corriger_livrable(request, pk):
    """Request corrections on a student's deliverable."""
    livrable = get_object_or_404(Livrable, pk=pk, projet__encadrant_acad=request.user)
    _demander_corrections(request, livrable)
    return redirect('pfe:livrables_a_valider')


# ---------------------------------------------------------------------------
# Academic supervisor views: taking charge of projects
# ---------------------------------------------------------------------------

@role_required(User.Role.ENCADRANT_ACAD)
def affectations(request):
    """List projects waiting for a supervisor and the ones this supervisor already runs."""
    related = ('etudiant', 'offre', 'offre__encadrant_pro')
    disponibles = (
        ProjetPFE.objects.filter(encadrant_acad__isnull=True)
        .select_related(*related)
        .order_by('-date_creation')
    )
    mes_projets = (
        ProjetPFE.objects.filter(encadrant_acad=request.user)
        .select_related(*related)
        .order_by('-date_creation')
    )
    return render(request, 'pfe/affectations.html', {
        'disponibles': disponibles,
        'mes_projets': mes_projets,
    })


@role_required(User.Role.ENCADRANT_ACAD)
@require_POST
def prendre_en_charge(request, pk):
    """Assign the current supervisor to an unassigned project (atomic claim)."""
    projet = get_object_or_404(ProjetPFE.objects.select_related('etudiant'), pk=pk)

    claimed = ProjetPFE.objects.filter(pk=pk, encadrant_acad__isnull=True).update(
        encadrant_acad=request.user,
    )
    if not claimed:
        if projet.encadrant_acad_id == request.user.pk:
            messages.info(request, "Vous encadrez déjà ce projet.")
        else:
            messages.error(
                request,
                "Ce projet a déjà été pris en charge par un autre encadrant.",
            )
        return redirect('pfe:affectations')

    supervisor_name = request.user.get_full_name() or request.user.username
    notify(
        projet.etudiant,
        f"Votre encadrant académique a été désigné : {supervisor_name}.",
        reverse('pfe:mon_pfe'),
    )
    messages.success(request, f"Vous encadrez désormais le projet « {projet.sujet} ».")
    return redirect('pfe:affectations')


@role_required(User.Role.ENCADRANT_ACAD)
@require_POST
def liberer_projet(request, pk):
    """Put one of the supervisor's own projects back into the unassigned pool."""
    projet = get_object_or_404(
        ProjetPFE.objects.select_related('etudiant'),
        pk=pk,
        encadrant_acad=request.user,
    )
    ProjetPFE.objects.filter(pk=pk, encadrant_acad=request.user).update(encadrant_acad=None)

    notify(
        projet.etudiant,
        f"Votre projet « {projet.sujet} » est de nouveau en attente d'un encadrant académique.",
        reverse('pfe:mon_pfe'),
    )
    messages.info(request, f"Le projet « {projet.sujet} » a été retiré de votre encadrement.")
    return redirect('pfe:affectations')


@role_required(User.Role.ENCADRANT_ACAD)
def creer_projet_encadrant(request):
    """Create a PFE project for a student who does not have one yet."""
    if request.method == 'POST':
        form = ProjetEncadrantForm(request.POST)
        if form.is_valid():
            projet = form.save(commit=False)
            projet.encadrant_acad = request.user
            projet.save()

            supervisor_name = request.user.get_full_name() or request.user.username
            notify(
                projet.etudiant,
                f"Un projet PFE vous a été assigné par {supervisor_name} : « {projet.sujet} ».",
                reverse('pfe:mon_pfe'),
            )
            student_name = projet.etudiant.get_full_name() or projet.etudiant.username
            messages.success(
                request,
                f"Le projet « {projet.sujet} » a été créé pour {student_name}.",
            )
            return redirect('pfe:affectations')
    else:
        form = ProjetEncadrantForm()

    return render(request, 'pfe/projet_form.html', {'form': form})
