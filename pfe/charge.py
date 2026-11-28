"""Workload of academic supervisors (backlog item 16).

A project counts in a supervisor's workload while it is *active*: in progress,
finished but not defended yet, or with a defense planned. Defended projects are
shown separately as history.

``annoter_charge`` is a queryset helper so other screens (e.g. the PFE assignment
suggestion of item 10) can compare supervisors without one query per person.
"""

from django.db.models import Count, F, Max, Q
from django.utils import timezone

from soutenances.models import Soutenance

from .models import Livrable, ProjetPFE

S = ProjetPFE.Status

ETATS_ACTIFS = (S.EN_COURS, S.TERMINE, S.PLANIFIE)
SEUIL_ALERTE = 80  # percent of the capacity from which the gauge turns orange


def annoter_charge(encadrants):
    """Annotate a ``User`` queryset with ``charge_active`` and ``places_libres``."""
    return encadrants.annotate(
        charge_active=Count(
            'projets_encadres_acad',
            filter=Q(projets_encadres_acad__status__in=ETATS_ACTIFS),
            distinct=True,
        ),
    ).annotate(places_libres=F('capacite_encadrement') - F('charge_active'))


def niveau(taux):
    """Bootstrap colour of the gauge for a load percentage."""
    if taux >= 100:
        return 'danger'
    if taux >= SEUIL_ALERTE:
        return 'warning'
    return 'success'


def charge_encadrant(encadrant):
    """Everything the workload page needs for one academic supervisor."""
    projets = ProjetPFE.objects.filter(encadrant_acad=encadrant)
    # order_by() clears the model's default ordering so GROUP BY is on status only.
    compte = dict(
        projets.order_by().values('status').annotate(n=Count('pk')).values_list('status', 'n')
    )

    actifs = sum(compte.get(etat, 0) for etat in ETATS_ACTIFS)
    capacite = encadrant.capacite_encadrement
    taux = round(actifs * 100 / capacite) if capacite else 0

    projets_actifs = (
        projets.filter(status__in=ETATS_ACTIFS)
        .select_related('etudiant', 'soutenance')
        .annotate(
            livrables_en_attente=Count(
                'livrables', filter=Q(livrables__status=Livrable.Status.DEPOSE), distinct=True),
            livrables_a_corriger=Count(
                'livrables',
                filter=Q(livrables__status=Livrable.Status.A_CORRIGER,
                         livrables__version_suivante__isnull=True),
                distinct=True),
            dernier_depot=Max('livrables__date_depot'),
        )
        .order_by('-livrables_en_attente', 'etudiant__last_name', 'etudiant__username')
    )

    return {
        'capacite': capacite,
        'actifs': actifs,
        'taux': taux,
        'jauge': min(taux, 100),
        'niveau': niveau(taux),
        'places_libres': max(capacite - actifs, 0),
        'surcharge': actifs > capacite,
        'par_statut': [
            {'code': etat, 'label': etat.label, 'nombre': compte.get(etat, 0)}
            for etat in (S.EN_COURS, S.TERMINE, S.PLANIFIE, S.SOUTENU)
        ],
        'soutenus': compte.get(S.SOUTENU, 0),
        'livrables_a_valider': Livrable.objects.filter(
            projet__encadrant_acad=encadrant, status=Livrable.Status.DEPOSE).count(),
        'livrables_a_corriger': Livrable.objects.dernieres_versions().filter(
            projet__encadrant_acad=encadrant, status=Livrable.Status.A_CORRIGER).count(),
        'soutenances_a_venir': (
            Soutenance.objects.filter(projet__encadrant_acad=encadrant, date__gte=timezone.now())
            .select_related('projet', 'projet__etudiant')
            .order_by('date')
        ),
        'projets_actifs': projets_actifs,
    }
