from django.conf import settings
from django.db import models
from django.urls import reverse


class Offre(models.Model):
    """A job/internship offer published by a company supervisor."""

    class Status(models.TextChoices):
        BROUILLON = 'BROUILLON', 'Brouillon'
        EN_VALIDATION = 'EN_VALIDATION', 'En attente de validation'
        PUBLIEE = 'PUBLIEE', 'Publiée'
        REFUSEE = 'REFUSEE', 'Refusée'

    class Type(models.TextChoices):
        STAGE = 'STAGE', 'Stage'
        PFE = 'PFE', 'PFE'

    encadrant_pro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='offres',
        verbose_name='Encadrant professionnel',
    )
    titre = models.CharField('Titre', max_length=200)
    description = models.TextField('Description')
    competences = models.CharField('Compétences requises', max_length=255, blank=True)
    duree = models.CharField('Durée', max_length=100, blank=True, help_text='Ex : 6 mois')
    type = models.CharField('Type', max_length=20, choices=Type.choices, default=Type.STAGE)
    status = models.CharField('Statut', max_length=20, choices=Status.choices, default=Status.BROUILLON)
    motif_refus = models.TextField('Motif du refus', blank=True)
    date_creation = models.DateTimeField('Date de création', auto_now_add=True)
    date_publication = models.DateTimeField('Date de publication', null=True, blank=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = 'offre'
        verbose_name_plural = 'offres'

    def __str__(self):
        return self.titre

    def get_absolute_url(self):
        return reverse('offres:offre_detail', args=[self.pk])

    @property
    def is_editable(self):
        """Draft and rejected offers can still be edited by their owner."""
        return self.status in (self.Status.BROUILLON, self.Status.REFUSEE)
