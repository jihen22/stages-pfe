from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Salle(models.Model):
    """A room where defenses can take place (item 19)."""

    nom = models.CharField('Nom', max_length=100, unique=True)
    batiment = models.CharField('Bâtiment', max_length=100, blank=True)
    capacite = models.PositiveSmallIntegerField('Capacité (places)', default=30)
    active = models.BooleanField(
        'Disponible', default=True,
        help_text="Une salle désactivée n'est plus proposée pour les nouvelles soutenances.",
    )

    class Meta:
        ordering = ['nom']
        verbose_name = 'salle'
        verbose_name_plural = 'salles'

    def __str__(self):
        return self.nom


class Creneau(models.Model):
    """A time slot of a defense session (item 19)."""

    debut = models.DateTimeField('Début')
    fin = models.DateTimeField('Fin')

    class Meta:
        ordering = ['debut', 'fin']
        verbose_name = 'créneau'
        verbose_name_plural = 'créneaux'
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__gt=models.F('debut')), name='creneau_fin_apres_debut'),
            models.UniqueConstraint(fields=['debut', 'fin'], name='creneau_unique'),
        ]

    def __str__(self):
        debut = timezone.localtime(self.debut)
        fin = timezone.localtime(self.fin)
        return f"{debut:%d/%m/%Y} {debut:%H:%M}–{fin:%H:%M}"

    def clean(self):
        if self.debut and self.fin and self.fin <= self.debut:
            raise ValidationError({'fin': 'La fin du créneau doit être après son début.'})

    @property
    def duree_minutes(self):
        return int((self.fin - self.debut).total_seconds() // 60)


class Soutenance(models.Model):
    projet = models.OneToOneField(
        'pfe.ProjetPFE',
        on_delete=models.CASCADE,
        related_name='soutenance',
        verbose_name='Projet PFE',
    )
    creneau = models.ForeignKey(
        Creneau,
        on_delete=models.PROTECT,
        related_name='soutenances',
        verbose_name='Créneau',
    )
    salle = models.ForeignKey(
        Salle,
        on_delete=models.PROTECT,
        related_name='soutenances',
        verbose_name='Salle',
    )
    jury = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='soutenances_jury',
        blank=True,
        limit_choices_to={'role': 'JURY'},
        verbose_name='Membres du jury',
    )
    remarques = models.TextField('Remarques', blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['creneau__debut']
        verbose_name = 'soutenance'
        verbose_name_plural = 'soutenances'

    def __str__(self):
        try:
            return f'Soutenance : {self.projet.sujet}'
        except Exception:
            return f'Soutenance #{self.pk}'

    @property
    def date(self):
        """Start of the defense (its slot's start); kept so pages can use ``soutenance.date``."""
        return self.creneau.debut

    @property
    def fin(self):
        return self.creneau.fin

    @property
    def moyenne(self):
        notes = self.notes.all()
        if not notes:
            return None
        return round(sum(n.note for n in notes) / len(notes), 2)


class NoteSoutenance(models.Model):
    soutenance = models.ForeignKey(
        Soutenance,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name='Soutenance',
    )
    jury_member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notes_attribuees',
        limit_choices_to={'role': 'JURY'},
        verbose_name='Membre du jury',
    )
    note = models.DecimalField(
        'Note',
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    remarque = models.TextField('Remarque', blank=True)
    date_saisie = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('soutenance', 'jury_member')
        verbose_name = 'note de soutenance'
        verbose_name_plural = 'notes de soutenance'

    def __str__(self):
        return f'{self.jury_member} → {self.soutenance} : {self.note}/20'
