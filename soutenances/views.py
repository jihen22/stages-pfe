from django.contrib import messages
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.mixins import role_required
from accounts.models import User
from notifications.services import notify
from pfe.models import ProjetPFE
from pfe.workflow import ETATS_NOTATION_OUVERTE, TransitionInterdite, appliquer, peut

from .conflits import alternatives, conflits_pour, detecter_conflits, ids_en_conflit
from .forms import (
    CreneauForm, JourneeCreneauxForm, ModifierSoutenanceForm, NoteSoutenanceForm, SalleForm,
    SoutenanceForm,
)
from .models import Creneau, NoteSoutenance, Salle, Soutenance


def _notify_soutenance(soutenance, deplacee=False, anciens_membres=()):
    """Notify the student and every jury member about a scheduled (or moved) defense.

    ``anciens_membres`` are jury members removed by a change: they are told too.
    """
    debut = timezone.localtime(soutenance.creneau.debut)
    fin = timezone.localtime(soutenance.creneau.fin)
    date_str = f"{debut:%d/%m/%Y} de {debut:%H:%M} à {fin:%H:%M}"
    verbe = 'a été déplacée' if deplacee else 'a été planifiée'
    sujet = soutenance.projet.sujet

    etudiant = getattr(soutenance.projet, 'etudiant', None)
    if etudiant:
        notify(
            etudiant,
            f"Votre soutenance pour le PFE « {sujet} » {verbe} : le {date_str} en salle {soutenance.salle}.",
            reverse('soutenances:ma_soutenance'),
        )

    membres = list(soutenance.jury.all())
    for member in membres:
        notify(
            member,
            f"Soutenance de « {sujet} » ({'déplacée' if deplacee else 'jury'}) : le {date_str}, salle {soutenance.salle}.",
            reverse('soutenances:mes_soutenances'),
        )
    for member in anciens_membres:
        if member not in membres:
            notify(member, f"Vous ne faites plus partie du jury de la soutenance de « {sujet} ».",
                   reverse('soutenances:mes_soutenances'))


def _cloturer_si_complet(soutenance, auteur):
    """Move the project to SOUTENU once every jury member has graded it."""
    projet = soutenance.projet
    if not peut(projet, 'soutenir'):
        return
    try:
        appliquer(projet, 'soutenir', auteur=auteur)
    except TransitionInterdite:
        return  # another jury member closed it at the same time
    notify(
        projet.etudiant,
        f"Votre soutenance pour « {projet.sujet} » est notée : moyenne {soutenance.moyenne}/20.",
        reverse('soutenances:ma_soutenance'),
    )


@role_required(User.Role.ETUDIANT)
def ma_soutenance(request):
    """Display the authenticated student's soutenance info and grade average."""
    soutenance = (
        Soutenance.objects.filter(projet__etudiant=request.user)
        .select_related('projet', 'projet__etudiant', 'projet__encadrant_acad', 'creneau', 'salle')
        .prefetch_related('jury', 'notes')
        .first()
    )
    context = {
        'soutenance': soutenance,
        'moyenne': soutenance.moyenne if soutenance else None,
    }
    return render(request, 'soutenances/ma_soutenance.html', context)


@role_required(User.Role.JURY)
def mes_soutenances(request):
    """List all soutenances where the user is an assigned jury member."""
    soutenances = (
        Soutenance.objects.filter(jury=request.user)
        .select_related('projet', 'projet__etudiant', 'creneau', 'salle')
        .prefetch_related('jury', 'notes')
        .order_by('creneau__debut')
    )
    soutenances_data = []
    for s in soutenances:
        ma_note = next(
            (n for n in s.notes.all() if n.jury_member_id == request.user.id),
            None,
        )
        soutenances_data.append({
            'soutenance': s,
            'ma_note': ma_note,
        })

    return render(
        request,
        'soutenances/mes_soutenances.html',
        {
            'soutenances_data': soutenances_data,
        },
    )


@role_required(User.Role.JURY)
def saisir_notes_list(request):
    """List soutenances assigned to the jury member with their grading status."""
    soutenances = (
        Soutenance.objects.filter(jury=request.user)
        .select_related('projet', 'projet__etudiant', 'creneau', 'salle')
        .prefetch_related('notes')
        .order_by('creneau__debut')
    )
    soutenances_info = []
    for s in soutenances:
        note_obj = next(
            (n for n in s.notes.all() if n.jury_member_id == request.user.id),
            None,
        )
        soutenances_info.append({
            'soutenance': s,
            'note': note_obj,
            'est_notee': note_obj is not None,
        })

    return render(
        request,
        'soutenances/saisir_notes_list.html',
        {
            'soutenances_info': soutenances_info,
        },
    )


@role_required(User.Role.JURY)
def saisir_notes(request, pk):
    """Enter or update the grade and remark for a given soutenance."""
    soutenance = get_object_or_404(
        Soutenance.objects.select_related('projet', 'projet__etudiant', 'creneau', 'salle'),
        pk=pk,
    )
    if not soutenance.jury.filter(pk=request.user.pk).exists():
        messages.error(request, 'Vous ne faites pas partie du jury de cette soutenance.')
        return redirect('soutenances:saisir_notes')
    if soutenance.projet.status not in ETATS_NOTATION_OUVERTE:
        messages.error(
            request,
            f"La notation n'est pas ouverte : le projet est « {soutenance.projet.get_status_display()} ».",
        )
        return redirect('soutenances:saisir_notes')

    note_obj = NoteSoutenance.objects.filter(
        soutenance=soutenance,
        jury_member=request.user,
    ).first()

    if request.method == 'POST':
        # Never persist a grade before validation: build an unsaved instance instead.
        instance = note_obj or NoteSoutenance(
            soutenance=soutenance,
            jury_member=request.user,
        )
        form = NoteSoutenanceForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"La note pour le projet « {soutenance.projet.sujet} » a bien été enregistrée.",
            )
            _cloturer_si_complet(soutenance, request.user)
            return redirect('soutenances:saisir_notes')
    else:
        form = NoteSoutenanceForm(instance=note_obj)

    return render(
        request,
        'soutenances/saisir_note.html',
        {
            'form': form,
            'soutenance': soutenance,
            'note_obj': note_obj,
        },
    )


@role_required(User.Role.ADMIN)
def planning(request):
    """Admin view: list all scheduled soutenances with an action to plan new ones."""
    soutenances = (
        Soutenance.objects.select_related('projet', 'projet__etudiant', 'projet__encadrant_acad', 'creneau', 'salle')
        .prefetch_related('jury', 'notes')
        .order_by('creneau__debut')
    )
    conflits = detecter_conflits()
    return render(
        request,
        'soutenances/planning.html',
        {
            'soutenances': soutenances,
            'journees': _grille_par_jour(soutenances),
            'nb_creneaux_libres': Creneau.objects.filter(debut__gte=timezone.now()).count(),
            'nb_conflits': len(conflits),
            'en_conflit': ids_en_conflit(conflits),
        },
    )


def _grille_par_jour(soutenances):
    """Upcoming sessions as one grid per day: rows are slots, columns are rooms.

    Each cell is the list of defenses in that slot and room (more than one would be
    a double booking: item 20 detects and resolves those).
    """
    maintenant = timezone.now()
    creneaux = list(Creneau.objects.filter(fin__gte=maintenant))
    salles_actives = list(Salle.objects.filter(active=True))
    par_cellule = {}
    for s in soutenances:
        if s.creneau.fin >= maintenant:
            par_cellule.setdefault((s.creneau_id, s.salle_id), []).append(s)

    journees = {}
    for creneau in creneaux:
        jour = timezone.localtime(creneau.debut).date()
        journees.setdefault(jour, []).append(creneau)

    resultat = []
    for jour, creneaux_du_jour in journees.items():
        ids = {c.pk for c in creneaux_du_jour}
        salles_utilisees = {s.salle for s in soutenances if s.creneau_id in ids}
        salles = sorted(set(salles_actives) | salles_utilisees, key=lambda salle: salle.nom)
        lignes = [
            {'creneau': c, 'cellules': [par_cellule.get((c.pk, salle.pk), []) for salle in salles]}
            for c in creneaux_du_jour
        ]
        nb = sum(len(cell) for ligne in lignes for cell in ligne['cellules'])
        resultat.append({'jour': jour, 'salles': salles, 'lignes': lignes, 'nb_soutenances': nb})
    return resultat


@role_required(User.Role.ADMIN)
def planifier_soutenance(request):
    """Admin view: schedule a new soutenance and notify the student and jury members."""
    if request.method == 'POST':
        form = SoutenanceForm(request.POST)
        if form.is_valid():
            projet = form.cleaned_data['projet']
            if Soutenance.objects.filter(projet=projet).exists():
                # Guards the OneToOneField against a race between two admins.
                form.add_error('projet', 'Ce projet a déjà une soutenance planifiée.')
            else:
                try:
                    with transaction.atomic():
                        soutenance = form.save()
                        appliquer(projet, 'planifier', auteur=request.user)
                except TransitionInterdite as exc:
                    form.add_error('projet', str(exc))
                else:
                    _notify_soutenance(soutenance)
                    messages.success(
                        request,
                        f"La soutenance pour « {soutenance.projet.sujet} » a été planifiée avec succès.",
                    )
                    return redirect('soutenances:planning')
    else:
        form = SoutenanceForm()
    return _rendu_formulaire(request, form)


def _rendu_formulaire(request, form, soutenance=None):
    """Planning / editing page, with free alternatives when the choice conflicts."""
    suggestions = []
    if form.conflits:
        suggestions = alternatives(
            form.cleaned_data.get('jury') or [],
            souhait=form.cleaned_data['creneau'].debut,
            salle_preferee=form.cleaned_data.get('salle'),
            exclure=soutenance,
        )
    return render(request, 'soutenances/planifier.html', {
        'form': form,
        'soutenance': soutenance,
        'suggestions': suggestions,
        'aucun_creneau': not form.fields['creneau'].queryset.exists(),
        'aucune_salle': not form.fields['salle'].queryset.exists(),
    })


def _page_suivante(request, defaut):
    """Where to go back after a change: only the two known pages (no arbitrary URL)."""
    pages = {'conflits': 'soutenances:conflits', 'planning': 'soutenances:planning'}
    return pages.get(request.POST.get('suivant'), defaut)


def _soutenance_modifiable(pk):
    """A defense the admin may still move: its project is « soutenance planifiée »."""
    return get_object_or_404(
        Soutenance.objects.select_related('projet', 'projet__etudiant', 'creneau', 'salle')
        .filter(projet__status=ProjetPFE.Status.PLANIFIE),
        pk=pk,
    )


@role_required(User.Role.ADMIN)
def modifier_soutenance(request, pk):
    """Move a planned defense to another slot / room, or change its jury (item 20)."""
    soutenance = _soutenance_modifiable(pk)
    anciens_membres = list(soutenance.jury.all())
    if request.method == 'POST':
        form = ModifierSoutenanceForm(request.POST, instance=soutenance)
        if form.is_valid():
            soutenance = form.save()
            _notify_soutenance(soutenance, deplacee=True, anciens_membres=anciens_membres)
            messages.success(request, f"La soutenance de « {soutenance.projet.sujet} » a été modifiée.")
            return redirect(_page_suivante(request, 'soutenances:planning'))
    else:
        form = ModifierSoutenanceForm(instance=soutenance)
    return _rendu_formulaire(request, form, soutenance)


@role_required(User.Role.ADMIN)
@require_POST
def deplacer_soutenance(request, pk):
    """One-click move to a suggested free slot and room (same jury)."""
    soutenance = _soutenance_modifiable(pk)
    creneau = get_object_or_404(Creneau, pk=request.POST.get('creneau'), debut__gte=timezone.now())
    salle = get_object_or_404(Salle, pk=request.POST.get('salle'), active=True)
    jury = list(soutenance.jury.all())
    conflits = conflits_pour(creneau, salle, jury, exclure=soutenance)
    if conflits:
        messages.error(request, "Ce créneau n'est plus libre : " + " ".join(c.message for c in conflits))
    else:
        soutenance.creneau = creneau
        soutenance.salle = salle
        soutenance.save(update_fields=['creneau', 'salle'])
        _notify_soutenance(soutenance, deplacee=True)
        messages.success(
            request, f"Soutenance de « {soutenance.projet.sujet} » déplacée : {creneau}, {salle}.")
    return redirect(_page_suivante(request, 'soutenances:conflits'))


@role_required(User.Role.ADMIN)
def conflits(request):
    """Every scheduling conflict of the upcoming planning, with ways to resolve it."""
    lignes = []
    for conflit in detecter_conflits():
        # Propose to move the later defense (the other one keeps its place).
        a_deplacer = conflit.autre
        lignes.append({
            'conflit': conflit,
            'a_deplacer': a_deplacer,
            'modifiable': a_deplacer.projet.status == ProjetPFE.Status.PLANIFIE,
            'suggestions': alternatives(
                list(a_deplacer.jury.all()), souhait=a_deplacer.creneau.debut,
                salle_preferee=a_deplacer.salle, exclure=a_deplacer, limite=3,
            ),
        })
    return render(request, 'soutenances/conflits.html', {'lignes': lignes})


# ---------------------------------------------------------------------------
# Administration: rooms and time slots (item 19)
# ---------------------------------------------------------------------------

@role_required(User.Role.ADMIN)
def ressources(request):
    """Manage rooms and slots: add a room, add one slot or generate a day of slots."""
    salle_form = SalleForm(prefix='salle')
    creneau_form = CreneauForm(prefix='creneau')
    journee_form = JourneeCreneauxForm(prefix='journee')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'salle':
            salle_form = SalleForm(request.POST, prefix='salle')
            if salle_form.is_valid():
                salle = salle_form.save()
                messages.success(request, f"Salle « {salle.nom} » ajoutée.")
                return redirect('soutenances:ressources')
        elif action == 'creneau':
            creneau_form = CreneauForm(request.POST, prefix='creneau')
            if creneau_form.is_valid():
                creneau = creneau_form.save()
                messages.success(request, f"Créneau {creneau} ajouté.")
                return redirect('soutenances:ressources')
        elif action == 'journee':
            journee_form = JourneeCreneauxForm(request.POST, prefix='journee')
            if journee_form.is_valid():
                crees = 0
                for debut, fin in journee_form.creneaux():
                    _, cree = Creneau.objects.get_or_create(debut=debut, fin=fin)
                    crees += cree
                if crees:
                    messages.success(request, f"{crees} créneau{'x' if crees > 1 else ''} créé{'s' if crees > 1 else ''}.")
                else:
                    messages.info(request, "Aucun nouveau créneau : ils existaient déjà ou la plage est trop courte.")
                return redirect('soutenances:ressources')

    a_venir = Creneau.objects.filter(fin__gte=timezone.now()).prefetch_related('soutenances')
    journees = {}
    for creneau in a_venir:
        journees.setdefault(timezone.localtime(creneau.debut).date(), []).append(creneau)

    return render(request, 'soutenances/ressources.html', {
        'salles': Salle.objects.all(),
        'journees': sorted(journees.items()),
        'salle_form': salle_form,
        'creneau_form': creneau_form,
        'journee_form': journee_form,
    })


@role_required(User.Role.ADMIN)
@require_POST
def basculer_salle(request, pk):
    """Make a room unavailable for new defenses, or available again."""
    salle = get_object_or_404(Salle, pk=pk)
    salle.active = not salle.active
    salle.save(update_fields=['active'])
    etat = 'de nouveau disponible' if salle.active else 'désactivée'
    messages.success(request, f"Salle « {salle.nom} » {etat}.")
    return redirect('soutenances:ressources')


@role_required(User.Role.ADMIN)
@require_POST
def supprimer_creneau(request, pk):
    """Delete a slot that no defense uses."""
    creneau = get_object_or_404(Creneau, pk=pk)
    try:
        creneau.delete()
    except ProtectedError:
        messages.error(request, f"Le créneau {creneau} est utilisé par une soutenance : il ne peut pas être supprimé.")
    else:
        messages.success(request, f"Créneau {creneau} supprimé.")
    return redirect('soutenances:ressources')
