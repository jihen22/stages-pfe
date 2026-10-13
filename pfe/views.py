from accounts.mixins import role_required
from accounts.models import User
from django.shortcuts import render


def _placeholder(request, title, subtitle, icon='tools'):
    return render(request, 'placeholder.html', {
        'title': title,
        'subtitle': subtitle,
        'icon': icon,
    })


@role_required(User.Role.ETUDIANT)
def mon_pfe(request):
    return _placeholder(
        request,
        'Mon PFE',
        'Suivi de votre projet de fin d\'études : sujet, encadrants, livrables.',
        'kanban',
    )


@role_required(User.Role.ENCADRANT_ACAD)
def mes_etudiants(request):
    return _placeholder(
        request,
        'Mes étudiants',
        'Liste des étudiants que vous encadrez et suivi de leurs projets.',
        'people',
    )


@role_required(User.Role.ENCADRANT_ACAD)
def livrables_a_valider(request):
    return _placeholder(
        request,
        'Livrables à valider',
        'Rapports et livrables déposés par vos étudiants en attente de validation.',
        'clipboard-check',
    )


@role_required(User.Role.ADMIN)
def affectations(request):
    return _placeholder(
        request,
        'Affectations',
        'Affectation des étudiants aux offres et aux encadrants.',
        'diagram-3',
    )
