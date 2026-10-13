from django.shortcuts import render

from accounts.mixins import role_required
from accounts.models import User


def _placeholder(request, title, subtitle, icon='tools'):
    return render(request, 'placeholder.html', {
        'title': title,
        'subtitle': subtitle,
        'icon': icon,
    })


@role_required(User.Role.ETUDIANT)
def ma_soutenance(request):
    return _placeholder(
        request,
        'Ma soutenance',
        'Date, salle, jury et résultats de votre soutenance.',
        'calendar-event',
    )


@role_required(User.Role.JURY)
def mes_soutenances(request):
    return _placeholder(
        request,
        'Mes soutenances',
        'Soutenances auxquelles vous participez en tant que membre du jury.',
        'calendar-check',
    )


@role_required(User.Role.JURY)
def saisir_notes(request):
    return _placeholder(
        request,
        'Saisir les notes',
        'Saisie des notes et remarques pour les soutenances passées.',
        'pencil-square',
    )


@role_required(User.Role.ADMIN)
def planning(request):
    return _placeholder(
        request,
        'Planning des soutenances',
        'Planification des dates, salles et jurys de soutenance.',
        'calendar3',
    )
