"""Suggestion of academic supervisors for a PFE project (backlog item 10).

Web part (rule based), built before the AI as CLAUDE.md requires:

- a supervisor is *eligible* when their field matches the project's field
  (a project without a field is open to everyone) and they still have room
  under their capacity (``User.capacite_encadrement``, item 16);
- eligible supervisors are ranked by a score out of 100:
  60 points for the same field (30 when the project has no field),
  plus up to 40 points for free places (free places / capacity).

AI extension point: :func:`ajuster_par_ia` receives the rule-based ranking and
returns it unchanged for now. The future ``ia`` app (items 24-27) will plug a
model here to re-rank or explain suggestions, without touching the views.
"""

from dataclasses import dataclass, field

from accounts.models import User

from .charge import ETATS_ACTIFS, annoter_charge
from .models import ProjetPFE

POINTS_DOMAINE = 60
POINTS_SANS_DOMAINE = 30
POINTS_CHARGE = 40


@dataclass
class Suggestion:
    encadrant: User
    score: int
    raisons: list = field(default_factory=list)


def domaine_compatible(projet_domaine, encadrant_domaine):
    """A project without a field is open to everyone; otherwise fields must match."""
    return not projet_domaine or projet_domaine == encadrant_domaine


def charge_active(encadrant):
    """Number of active projects (counted against the capacity) of one supervisor."""
    return ProjetPFE.objects.filter(encadrant_acad=encadrant, status__in=ETATS_ACTIFS).count()


def raison_refus(projet, encadrant, charge=None):
    """Why ``encadrant`` cannot take ``projet`` (None when they can)."""
    if not domaine_compatible(projet.domaine, encadrant.domaine):
        return f"Ce projet relève du domaine « {projet.get_domaine_display()} », pas du vôtre."
    if charge is None:
        charge = charge_active(encadrant)
    if charge >= encadrant.capacite_encadrement:
        return (
            f"Votre capacité d'encadrement est atteinte "
            f"({charge} / {encadrant.capacite_encadrement} projets actifs)."
        )
    return None


def encadrants_avec_charge():
    """All academic supervisors annotated with ``charge_active`` / ``places_libres``."""
    return list(annoter_charge(User.objects.filter(role=User.Role.ENCADRANT_ACAD, is_active=True)))


def _score(projet, encadrant):
    places = max(encadrant.places_libres, 0)
    raisons = []
    if projet.domaine:
        points = POINTS_DOMAINE
        raisons.append(f"Domaine : {projet.get_domaine_display()}")
    else:
        points = POINTS_SANS_DOMAINE
        raisons.append("Projet sans domaine précisé")
    capacite = encadrant.capacite_encadrement or 1
    points += round(POINTS_CHARGE * places / capacite)
    raisons.append(f"{places} place{'s' if places > 1 else ''} libre{'s' if places > 1 else ''} "
                   f"sur {encadrant.capacite_encadrement}")
    return Suggestion(encadrant=encadrant, score=points, raisons=raisons)


def ajuster_par_ia(projet, suggestions):
    """AI extension point (empty for now): return the ranking unchanged.

    The ``ia`` app will replace this with a model call that may re-order the
    suggestions, change their score and add explanations (items 26-27).
    """
    return suggestions


def suggerer_encadrants(projet, encadrants=None, limite=3):
    """Best academic supervisors for ``projet``, best first.

    ``encadrants`` can be passed (from :func:`encadrants_avec_charge`) to rank
    many projects with a single query.
    """
    if encadrants is None:
        encadrants = encadrants_avec_charge()
    suggestions = [
        _score(projet, e) for e in encadrants
        if domaine_compatible(projet.domaine, e.domaine) and e.places_libres > 0
    ]
    suggestions.sort(key=lambda s: (-s.score, -s.encadrant.places_libres, s.encadrant.username))
    return ajuster_par_ia(projet, suggestions)[:limite]
