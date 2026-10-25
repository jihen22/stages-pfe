from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.mixins import role_required
from accounts.models import User
from notifications.services import notify

from .forms import NoteSoutenanceForm, SoutenanceForm
from .models import NoteSoutenance, Soutenance


def _notify_soutenance(soutenance):
    """Notify the student and every jury member about a newly scheduled defense."""
    date_str = soutenance.date.strftime('%d/%m/%Y à %H:%M')

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


@role_required(User.Role.ETUDIANT)
def ma_soutenance(request):
    """Display the authenticated student's soutenance info and grade average."""
    soutenance = (
        Soutenance.objects.filter(projet__etudiant=request.user)
        .select_related('projet', 'projet__etudiant', 'projet__encadrant_acad')
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
        .select_related('projet', 'projet__etudiant')
        .prefetch_related('jury', 'notes')
        .order_by('date')
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
        .select_related('projet', 'projet__etudiant')
        .prefetch_related('notes')
        .order_by('date')
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
        Soutenance.objects.select_related('projet', 'projet__etudiant'),
        pk=pk,
    )
    if not soutenance.jury.filter(pk=request.user.pk).exists():
        messages.error(request, 'Vous ne faites pas partie du jury de cette soutenance.')
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
        Soutenance.objects.select_related('projet', 'projet__etudiant')
        .prefetch_related('jury', 'notes')
        .order_by('date')
    )
    return render(
        request,
        'soutenances/planning.html',
        {
            'soutenances': soutenances,
        },
    )


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
                soutenance = form.save()
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
        },
    )
