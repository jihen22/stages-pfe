"""Scheduling conflicts between defenses (backlog item 20).

Two defenses conflict when their time slots overlap (``a.debut < b.fin`` and
``b.debut < a.fin``, so different but overlapping slots count too) and they:

- use the same room (double booking), or
- share at least one jury member (a person cannot be in two places).

A student has a single PFE project, hence a single defense, so students cannot
be double-booked.
"""

from dataclasses import dataclass, field

from django.utils import timezone

from .models import Creneau, Salle, Soutenance

SALLE = 'SALLE'
JURY = 'JURY'


@dataclass
class Conflit:
    type: str
    soutenance: Soutenance          # the existing defense we collide with
    autre: Soutenance = None        # the other defense (planning scan only)
    membres: list = field(default_factory=list)

    @property
    def message(self):
        cible = self.soutenance
        quand = _libelle_creneau(cible.creneau)
        etudiant = cible.projet.etudiant.get_full_name() or cible.projet.etudiant.username
        if self.type == SALLE:
            return f"Salle {cible.salle} déjà occupée {quand} (soutenance de {etudiant})."
        noms = ', '.join(m.get_full_name() or m.username for m in self.membres)
        return f"{noms} déjà dans le jury {quand} (soutenance de {etudiant})."


def _libelle_creneau(creneau):
    debut = timezone.localtime(creneau.debut)
    fin = timezone.localtime(creneau.fin)
    return f"le {debut:%d/%m/%Y} de {debut:%H:%M} à {fin:%H:%M}"


def _chevauchants(creneau):
    """Defenses whose slot overlaps ``creneau``."""
    return (
        Soutenance.objects.filter(creneau__debut__lt=creneau.fin, creneau__fin__gt=creneau.debut)
        .select_related('creneau', 'salle', 'projet', 'projet__etudiant')
        .prefetch_related('jury')
    )


def conflits_pour(creneau, salle, jury, exclure=None):
    """Conflicts that a defense in ``creneau`` / ``salle`` with ``jury`` would create."""
    if creneau is None:
        return []
    jury_ids = {m.pk for m in jury}
    resultat = []
    autres = _chevauchants(creneau)
    if exclure is not None and exclure.pk:
        autres = autres.exclude(pk=exclure.pk)
    for autre in autres:
        if salle is not None and autre.salle_id == salle.pk:
            resultat.append(Conflit(SALLE, autre))
        communs = [m for m in autre.jury.all() if m.pk in jury_ids]
        if communs:
            resultat.append(Conflit(JURY, autre, membres=communs))
    return resultat


def detecter_conflits(depuis=None):
    """Every conflict between defenses of the planning (upcoming ones by default).

    Each conflicting pair is reported once per type.
    """
    depuis = timezone.now() if depuis is None else depuis
    soutenances = list(
        Soutenance.objects.filter(creneau__fin__gte=depuis)
        .select_related('creneau', 'salle', 'projet', 'projet__etudiant')
        .prefetch_related('jury')
        .order_by('creneau__debut', 'pk')
    )
    resultat = []
    for i, a in enumerate(soutenances):
        jury_a = {m.pk: m for m in a.jury.all()}
        for b in soutenances[i + 1:]:
            if b.creneau.debut >= a.creneau.fin:
                break  # sorted by start: no later defense can overlap ``a``
            if b.creneau.fin <= a.creneau.debut:
                continue
            if a.salle_id == b.salle_id:
                resultat.append(Conflit(SALLE, a, autre=b))
            communs = [jury_a[m.pk] for m in b.jury.all() if m.pk in jury_a]
            if communs:
                resultat.append(Conflit(JURY, a, autre=b, membres=communs))
    return resultat


def ids_en_conflit(conflits):
    """Ids of every defense involved in at least one conflict."""
    ids = set()
    for c in conflits:
        ids.add(c.soutenance.pk)
        if c.autre is not None:
            ids.add(c.autre.pk)
    return ids


def alternatives(jury, souhait=None, salle_preferee=None, exclure=None, limite=5):
    """Free (slot, room) pairs for a defense with ``jury``, best first.

    A pair is free when the room and every jury member have no overlapping
    defense. Pairs are ranked by distance to the wished time, then the preferred
    room first.
    """
    maintenant = timezone.now()
    souhait = souhait or maintenant
    creneaux = list(Creneau.objects.filter(debut__gte=maintenant))
    salles = list(Salle.objects.filter(active=True))
    if not creneaux or not salles:
        return []

    occupees = list(
        Soutenance.objects.filter(creneau__fin__gt=maintenant)
        .exclude(pk=getattr(exclure, 'pk', None))
        .select_related('creneau')
        .prefetch_related('jury')
    )
    jury_ids = {m.pk for m in jury}

    def chevauche(c, s):
        return s.creneau.debut < c.fin and c.debut < s.creneau.fin

    candidats = []
    for c in creneaux:
        en_meme_temps = [s for s in occupees if chevauche(c, s)]
        if any(m.pk in jury_ids for s in en_meme_temps for m in s.jury.all()):
            continue  # a jury member is busy: no room helps
        salles_prises = {s.salle_id for s in en_meme_temps}
        for salle in salles:
            if salle.pk not in salles_prises:
                ecart = abs((c.debut - souhait).total_seconds())
                autre_salle = salle_preferee is None or salle.pk != salle_preferee.pk
                candidats.append((ecart, autre_salle, c.debut, salle.nom, c, salle))
    candidats.sort(key=lambda t: t[:4])
    return [(c, salle) for *_, c, salle in candidats[:limite]]
