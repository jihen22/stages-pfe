from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Soutenance(models.Model):
    projet = models.OneToOneField(
        'pfe.ProjetPFE',
        on_delete=models.CASCADE,
        related_name='soutenance',
        verbose_name='Projet PFE',
    )
    date = models.DateTimeField('Date et heure')
    salle = models.CharField('Salle', max_length=100)
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
        ordering = ['date']
        verbose_name = 'soutenance'
        verbose_name_plural = 'soutenances'

    def __str__(self):
        try:
            return f'Soutenance : {self.projet.sujet}'
        except Exception:
            return f'Soutenance #{self.pk}'

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
