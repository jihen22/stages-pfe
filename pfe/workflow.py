"""State machine of a PFE project (backlog item 14).

Every status change of a ``ProjetPFE`` goes through :func:`appliquer`, which:

1. checks that the transition starts from the project's current status,
2. runs the transition's guard (business rule),
3. applies the change with a conditional ``UPDATE ... WHERE status = <source>``
   so two concurrent requests can never both move the same project,
4. records the change in ``HistoriqueStatut``.

Lifecycle::

    EN_ATTENTE --affecter--> EN_COURS --terminer--> TERMINE --planifier--> PLANIFIE --soutenir--> SOUTENU
        ^                       |  ^                   |
        +-------liberer---------+  +------rouvrir------+
"""

from dataclasses import dataclass
from typing import Callable, Optional

from django.db import transaction

from .models import HistoriqueStatut, Livrable, ProjetPFE
from .suggestion import raison_refus

S = ProjetPFE.Status


class TransitionInterdite(Exception):
    """Raised when a transition is not allowed from the current state or its guard fails."""


# ---------------------------------------------------------------------------
# Guards: return an error message, or None when the transition is allowed
# ---------------------------------------------------------------------------

def _garde_affecter(projet, encadrant_acad=None, **_):
    if encadrant_acad is None:
        return "Un encadrant académique est nécessaire pour démarrer le projet."
    if projet.encadrant_acad_id:
        return "Ce projet a déjà un encadrant académique."
    # Item 10: same field as the supervisor, and room left under their capacity.
    return raison_refus(projet, encadrant_acad)


def _garde_terminer(projet, **_):
    livrables = projet.livrables.all()
    if not livrables.filter(status=Livrable.Status.VALIDE).exists():
        return "Au moins un livrable doit être validé avant de terminer le projet."
    if livrables.filter(status=Livrable.Status.DEPOSE).exists():
        return "Des livrables attendent encore votre validation."
    return None


def _garde_planifier(projet, **_):
    if not hasattr(projet, 'soutenance'):
        return "Aucune soutenance n'est enregistrée pour ce projet."
    return None


def _garde_soutenir(projet, **_):
    soutenance = getattr(projet, 'soutenance', None)
    if soutenance is None:
        return "Aucune soutenance n'est enregistrée pour ce projet."
    jury_ids = set(soutenance.jury.values_list('pk', flat=True))
    notes_ids = set(soutenance.notes.values_list('jury_member_id', flat=True))
    if not jury_ids or not jury_ids <= notes_ids:
        return "Tous les membres du jury doivent avoir saisi leur note."
    return None


@dataclass(frozen=True)
class Transition:
    source: str
    cible: str
    garde: Optional[Callable] = None


TRANSITIONS = {
    'affecter': Transition(S.EN_ATTENTE, S.EN_COURS, _garde_affecter),
    'liberer': Transition(S.EN_COURS, S.EN_ATTENTE),
    'terminer': Transition(S.EN_COURS, S.TERMINE, _garde_terminer),
    'rouvrir': Transition(S.TERMINE, S.EN_COURS),
    'planifier': Transition(S.TERMINE, S.PLANIFIE, _garde_planifier),
    'soutenir': Transition(S.PLANIFIE, S.SOUTENU, _garde_soutenir),
}

# Fields a transition may change together with the status.
_CHAMPS = {
    'affecter': {'encadrant_acad'},
    'liberer': {'encadrant_acad'},
}

# States in which the student may still upload deliverables.
ETATS_DEPOT_OUVERT = (S.EN_ATTENTE, S.EN_COURS)
# States in which the jury may enter or correct grades.
ETATS_NOTATION_OUVERTE = (S.PLANIFIE, S.SOUTENU)


def peut(projet, nom, **params):
    """Return True when transition ``nom`` is currently allowed for ``projet``."""
    transition = TRANSITIONS[nom]
    if projet.status != transition.source:
        return False
    return transition.garde is None or transition.garde(projet, **params) is None


def appliquer(projet, nom, auteur=None, **params):
    """Apply transition ``nom`` to ``projet`` or raise :class:`TransitionInterdite`.

    ``params`` are passed to the guard; those listed in ``_CHAMPS`` are also saved
    on the project (e.g. ``encadrant_acad`` for ``affecter``).
    """
    transition = TRANSITIONS[nom]
    if projet.status != transition.source:
        raise TransitionInterdite(
            f"Action impossible : le projet est « {projet.get_status_display()} »."
        )
    if transition.garde is not None:
        erreur = transition.garde(projet, **params)
        if erreur:
            raise TransitionInterdite(erreur)

    changes = {'status': transition.cible}
    for champ in _CHAMPS.get(nom, ()):
        if champ in params:
            changes[champ] = params[champ]
    if nom == 'liberer':
        changes['encadrant_acad'] = None

    filtre = {'pk': projet.pk, 'status': transition.source}
    if nom == 'affecter':
        filtre['encadrant_acad__isnull'] = True

    with transaction.atomic():
        if not ProjetPFE.objects.filter(**filtre).update(**changes):
            # Someone else changed the project between our read and our write.
            raise TransitionInterdite("Le projet a été modifié entre-temps, rechargez la page.")
        HistoriqueStatut.objects.create(
            projet=projet, ancien=transition.source, nouveau=transition.cible, auteur=auteur,
        )

    for champ, valeur in changes.items():
        setattr(projet, champ, valeur)
    return projet
