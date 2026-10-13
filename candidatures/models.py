from django.conf import settings
from django.db import models
from django.urls import reverse

from offres.models import Offre


class Candidature(models.Model):
    """A student's application to a single offer (unique per student + offer)."""

    class Status(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        ACCEPTEE = 'ACCEPTEE', 'Acceptée'
        REFUSEE = 'REFUSEE', 'Refusée'

    etudiant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='candidatures',
        verbose_name='Étudiant',
    )
    offre = models.ForeignKey(
        Offre,
        on_delete=models.CASCADE,
        related_name='candidatures',
        verbose_name='Offre',
    )
    cv = models.FileField('CV', upload_to='cvs/%Y/%m/')
    lettre_motivation = models.TextField('Lettre de motivation')
    status = models.CharField('Statut', max_length=20, choices=Status.choices, default=Status.EN_ATTENTE)
    date_candidature = models.DateTimeField('Date de candidature', auto_now_add=True)

    class Meta:
        ordering = ['-date_candidature']
        constraints = [
            models.UniqueConstraint(fields=['etudiant', 'offre'], name='unique_candidature_etudiant_offre'),
        ]
        verbose_name = 'candidature'
        verbose_name_plural = 'candidatures'

    def __str__(self):
        return f'{self.etudiant} → {self.offre}'

    def get_absolute_url(self):
        return reverse('candidatures:mes_candidatures')
