from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.mixins import role_required
from accounts.models import User
from candidatures.models import Candidature
from notifications.services import notify

from .charge import charge_encadrant
from .suggestion import encadrants_avec_charge, raison_refus, suggerer_encadrants
from .forms import LivrableForm, NouvelleVersionForm, ProjetEncadrantForm, ProjetPFEForm
from .models import Livrable, ProjetPFE, regrouper_versions
from .workflow import ETATS_DEPOT_OUVERT, TransitionInterdite, appliquer, peut


# ---------------------------------------------------------------------------
# Deliverable review helpers (shared by the list and action views)
# ---------------------------------------------------------------------------

def _livrable_a_relire(request, pk):
    """A version the supervisor may review: theirs, latest, and still waiting (else 404)."""
    return get_object_or_404(
        Livrable.objects.dernieres_versions(),
        pk=pk,
        projet__encadrant_acad=request.user,
        status=Livrable.Status.DEPOSE,
    )


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

def _contexte_mon_pfe(projet):
    return {
        'projet': projet,
        'livrables': regrouper_versions(projet.livrables.all()),
        'historique': projet.historique.select_related('auteur'),
        'depot_ouvert': projet.status in ETATS_DEPOT_OUVERT,
    }


@role_required(User.Role.ETUDIANT)
def mon_pfe(request):
    """Display the student's PFE project or initialize it from an accepted offer."""
    projet = (
        ProjetPFE.objects.filter(etudiant=request.user)
        .select_related('encadrant_acad', 'offre', 'offre__encadrant_pro')
        .first()
    )

    if projet:
        return render(request, 'pfe/mon_pfe.html', _contexte_mon_pfe(projet))

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
            domaine=accepted_cand.offre.domaine,
        )
        messages.info(request, 'Votre projet PFE a été initialisé depuis votre candidature acceptée.')
        return render(request, 'pfe/mon_pfe.html', _contexte_mon_pfe(projet))

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
    if projet.status not in ETATS_DEPOT_OUVERT:
        messages.error(
            request,
            f"Le dépôt de livrables est fermé : le projet est « {projet.get_status_display()} ».",
        )
        return redirect('pfe:mon_pfe')

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


@role_required(User.Role.ETUDIANT)
def nouvelle_version(request, pk):
    """Upload a new version of one of the student's deliverables (item 12)."""
    precedente = get_object_or_404(
        Livrable.objects.dernieres_versions().select_related('projet', 'projet__encadrant_acad'),
        pk=pk,
        projet__etudiant=request.user,
    )
    projet = precedente.projet
    if projet.status not in ETATS_DEPOT_OUVERT:
        messages.error(
            request,
            f"Le dépôt de livrables est fermé : le projet est « {projet.get_status_display()} ».",
        )
        return redirect('pfe:mon_pfe')

    if request.method == 'POST':
        form = NouvelleVersionForm(request.POST, request.FILES)
        if form.is_valid():
            livrable = form.save(commit=False)
            livrable.projet = projet
            livrable.titre = precedente.titre
            livrable.version = precedente.version + 1
            livrable.version_precedente = precedente
            livrable.status = Livrable.Status.DEPOSE
            try:
                with transaction.atomic():
                    livrable.save()
                    if precedente.status == Livrable.Status.DEPOSE:
                        # Not reviewed yet: the supervisor only reviews the newest file.
                        Livrable.objects.filter(pk=precedente.pk).update(status=Livrable.Status.REMPLACE)
            except IntegrityError:
                # Another upload created this version first (one successor per version).
                messages.error(request, "Une version plus récente vient d'être déposée.")
                return redirect('pfe:mon_pfe')

            if projet.encadrant_acad:
                student_name = request.user.get_full_name() or request.user.username
                notify(
                    projet.encadrant_acad,
                    f"{student_name} a déposé la version {livrable.version} de « {livrable.titre} ».",
                    reverse('pfe:livrables_a_valider'),
                )
            messages.success(request, f"Version {livrable.version} de « {livrable.titre} » déposée.")
            return redirect('pfe:mon_pfe')
    else:
        form = NouvelleVersionForm()

    return render(request, 'pfe/deposer_livrable.html', {
        'projet': projet,
        'form': form,
        'precedente': precedente,
    })


# ---------------------------------------------------------------------------
# Academic supervisor views
# ---------------------------------------------------------------------------

def _a_une_suivante(livrable, projet):
    """True when another version of ``projet`` points to ``livrable`` (uses the prefetch)."""
    return any(lv.version_precedente_id == livrable.pk for lv in projet.livrables.all())


@role_required(User.Role.ENCADRANT_ACAD)
def mes_etudiants(request):
    """List all PFE projects supervised by the current academic supervisor."""
    projets = (
        ProjetPFE.objects.filter(encadrant_acad=request.user)
        .select_related('etudiant', 'etudiant__profil_etudiant', 'offre')
        .prefetch_related('livrables')
        .order_by('-date_creation')
    )
    for projet in projets:
        projet.nb_livrables = sum(1 for lv in projet.livrables.all() if not _a_une_suivante(lv, projet))
        projet.peut_terminer = peut(projet, 'terminer')
        projet.peut_rouvrir = peut(projet, 'rouvrir')
    return render(request, 'pfe/mes_etudiants.html', {'projets': projets})


@role_required(User.Role.ENCADRANT_ACAD)
def ma_charge(request):
    """Workload of the academic supervisor: active projects vs capacity, pending work."""
    return render(request, 'pfe/ma_charge.html', {'charge': charge_encadrant(request.user)})


@role_required(User.Role.ENCADRANT_ACAD)
def livrables_a_valider(request):
    """List pending deliverables waiting for review by the academic supervisor."""
    if request.method == 'POST':
        action = request.POST.get('action')
        livrable_id = request.POST.get('livrable_id')
        if livrable_id and action in ('valider', 'corriger'):
            livrable = _livrable_a_relire(request, livrable_id)
            if action == 'valider':
                _valider_livrable(request, livrable)
            else:
                _demander_corrections(request, livrable)
            return redirect('pfe:livrables_a_valider')

    livrables = (
        Livrable.objects.filter(projet__encadrant_acad=request.user, status=Livrable.Status.DEPOSE)
        .select_related('projet', 'projet__etudiant', 'projet__offre', 'version_precedente')
        .order_by('-date_depot')
    )
    return render(request, 'pfe/livrables_a_valider.html', {'livrables': livrables})


@role_required(User.Role.ENCADRANT_ACAD)
@require_POST
def valider_livrable(request, pk):
    """Validate a student's deliverable."""
    livrable = _livrable_a_relire(request, pk)
    _valider_livrable(request, livrable)
    return redirect('pfe:livrables_a_valider')


@role_required(User.Role.ENCADRANT_ACAD)
@require_POST
def corriger_livrable(request, pk):
    """Request corrections on a student's deliverable."""
    livrable = _livrable_a_relire(request, pk)
    _demander_corrections(request, livrable)
    return redirect('pfe:livrables_a_valider')


# ---------------------------------------------------------------------------
# Academic supervisor views: taking charge of projects
# ---------------------------------------------------------------------------

@role_required(User.Role.ENCADRANT_ACAD)
def affectations(request):
    """List projects waiting for a supervisor and the ones this supervisor already runs."""
    related = ('etudiant', 'offre', 'offre__encadrant_pro')
    disponibles = list(
        ProjetPFE.objects.filter(encadrant_acad__isnull=True)
        .select_related(*related)
        .order_by('-date_creation')
    )
    mes_projets = (
        ProjetPFE.objects.filter(encadrant_acad=request.user)
        .select_related(*related)
        .order_by('-date_creation')
    )

    # Item 10: rank supervisors for every waiting project (one query for all).
    encadrants = encadrants_avec_charge()
    moi = next((e for e in encadrants if e.pk == request.user.pk), None)
    ma_charge = moi.charge_active if moi else 0
    for projet in disponibles:
        projet.suggestions = suggerer_encadrants(projet, encadrants)
        projet.raison_refus = raison_refus(projet, request.user, charge=ma_charge)
        projet.recommande = bool(projet.suggestions) and projet.suggestions[0].encadrant.pk == request.user.pk
    # Projects recommended for me first, then the ones I can take, then the others.
    disponibles.sort(key=lambda p: (not p.recommande, p.raison_refus is not None))

    return render(request, 'pfe/affectations.html', {
        'disponibles': disponibles,
        'mes_projets': mes_projets,
        'nb_recommandes': sum(p.recommande for p in disponibles),
        'capacite_atteinte': ma_charge >= request.user.capacite_encadrement,
        'ma_charge': ma_charge,
    })


@role_required(User.Role.ENCADRANT_ACAD)
@require_POST
def prendre_en_charge(request, pk):
    """Assign the current supervisor to an unassigned project (atomic claim)."""
    projet = get_object_or_404(ProjetPFE.objects.select_related('etudiant'), pk=pk)

    if projet.encadrant_acad_id == request.user.pk:
        messages.info(request, "Vous encadrez déjà ce projet.")
        return redirect('pfe:affectations')
    try:
        appliquer(projet, 'affecter', auteur=request.user, encadrant_acad=request.user)
    except TransitionInterdite as exc:
        projet.refresh_from_db()
        if projet.encadrant_acad_id:
            messages.error(request, "Ce projet a déjà été pris en charge par un autre encadrant.")
        else:
            messages.error(request, str(exc))
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
    try:
        appliquer(projet, 'liberer', auteur=request.user)
    except TransitionInterdite as exc:
        messages.error(request, str(exc))
        return redirect('pfe:affectations')

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
        form = ProjetEncadrantForm(request.POST, encadrant=request.user)
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
        form = ProjetEncadrantForm(encadrant=request.user)

    return render(request, 'pfe/projet_form.html', {'form': form})


# ---------------------------------------------------------------------------
# Academic supervisor views: lifecycle of their projects
# ---------------------------------------------------------------------------

def _changer_statut(request, pk, nom, message_etudiant, message_succes):
    projet = get_object_or_404(
        ProjetPFE.objects.select_related('etudiant'),
        pk=pk,
        encadrant_acad=request.user,
    )
    try:
        appliquer(projet, nom, auteur=request.user)
    except TransitionInterdite as exc:
        messages.error(request, str(exc))
        return redirect('pfe:mes_etudiants')

    notify(projet.etudiant, message_etudiant.format(sujet=projet.sujet), reverse('pfe:mon_pfe'))
    messages.success(request, message_succes.format(sujet=projet.sujet))
    return redirect('pfe:mes_etudiants')


@role_required(User.Role.ENCADRANT_ACAD)
@require_POST
def terminer_projet(request, pk):
    """Declare the work finished: the project can then be scheduled for a defense."""
    return _changer_statut(
        request, pk, 'terminer',
        "Votre projet « {sujet} » est terminé : il peut maintenant être planifié en soutenance.",
        "Le projet « {sujet} » est marqué comme terminé.",
    )


@role_required(User.Role.ENCADRANT_ACAD)
@require_POST
def rouvrir_projet(request, pk):
    """Send a finished (not yet scheduled) project back to "en cours"."""
    return _changer_statut(
        request, pk, 'rouvrir',
        "Votre projet « {sujet} » a été rouvert : vous pouvez de nouveau déposer des livrables.",
        "Le projet « {sujet} » est de nouveau en cours.",
    )
