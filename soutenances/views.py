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
from pfe.workflow import ETATS_NOTATION_OUVERTE, TransitionInterdite, appliquer, peut

from .forms import CreneauForm, JourneeCreneauxForm, NoteSoutenanceForm, SalleForm, SoutenanceForm
from .models import Creneau, NoteSoutenance, Salle, Soutenance


def _notify_soutenance(soutenance):
    """Notify the student and every jury member about a newly scheduled defense."""
    debut = timezone.localtime(soutenance.creneau.debut)
    fin = timezone.localtime(soutenance.creneau.fin)
    date_str = f"{debut:%d/%m/%Y} de {debut:%H:%M} à {fin:%H:%M}"

    etudiant = getattr(soutenance.projet, 'etudiant', None)
    if etudiant:
        notify(
            etudiant,
            f"Votre soutenance pour le PFE « {soutenance.projet.sujet} » a été planifiée le {date_str} en salle {soutenance.salle}.",
            reverse('soutenances:ma_soutenance'),
        )

    for member in soutenance.jury.all():
        notify(
            member,
            f"Vous avez été désigné(e) membre du jury pour la soutenance de « {soutenance.projet.sujet} » le {date_str} (salle {soutenance.salle}).",
            reverse('soutenances:mes_soutenances'),
        )


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
    return render(
        request,
        'soutenances/planning.html',
        {
            'soutenances': soutenances,
            'journees': _grille_par_jour(soutenances),
            'nb_creneaux_libres': Creneau.objects.filter(debut__gte=timezone.now()).count(),
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
                    return render(request, 'soutenances/planifier.html', {'form': form})
                _notify_soutenance(soutenance)
                messages.success(
                    request,
                    f"La soutenance pour « {soutenance.projet.sujet} » a été planifiée avec succès.",
                )
                return redirect('soutenances:planning')
    else:
        form = SoutenanceForm()

    return render(
        request,
        'soutenances/planifier.html',
        {
            'form': form,
            'aucun_creneau': not form.fields['creneau'].queryset.exists(),
            'aucune_salle': not form.fields['salle'].queryset.exists(),
        },
    )


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
