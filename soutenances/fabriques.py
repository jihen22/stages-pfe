"""Small helpers to create rooms, slots and defenses in tests and scripts."""

from datetime import timedelta

from django.utils import timezone

from .models import Creneau, Salle, Soutenance


def salle(nom='Amphi A', **extra):
    return Salle.objects.get_or_create(nom=nom, defaults=extra)[0]


def creneau(debut=None, minutes=60, jours=7):
    """A slot starting at ``debut`` (default: in ``jours`` days, on the hour)."""
    if debut is None:
        debut = (timezone.now() + timedelta(days=jours)).replace(minute=0, second=0, microsecond=0)
    return Creneau.objects.get_or_create(debut=debut, fin=debut + timedelta(minutes=minutes))[0]


def soutenance(projet, debut=None, nom_salle='Amphi A', jury=(), jours=7):
    s = Soutenance.objects.create(
        projet=projet, creneau=creneau(debut, jours=jours), salle=salle(nom_salle))
    if jury:
        s.jury.set(jury)
    return s
