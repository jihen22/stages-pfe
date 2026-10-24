from django.conf import settings
from django.db import models

from offres.models import Offre


class ProjetPFE(models.Model):
    """Projet de Fin d'Études (PFE) associated with a student and supervisors."""

    class Status(models.TextChoices):
        EN_COURS = 'EN_COURS', 'En cours'
        TERMINE = 'TERMINE', 'Terminé'
        SOUTENU = 'SOUTENU', 'Soutenu'

    etudiant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='projets_pfe',
        limit_choices_to={'role': 'ETUDIANT'},
        verbose_name='Étudiant',
    )
    encadrant_acad = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='projets_encadres_acad',
        limit_choices_to={'role': 'ENCADRANT_ACAD'},
        verbose_name='Encadrant académique',
    )
    offre = models.ForeignKey(
        Offre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='projets_pfe',
        verbose_name='Offre',
    )
    sujet = models.CharField('Sujet', max_length=300)
    description = models.TextField('Description', blank=True)
    status = models.CharField(
        'Statut',
        max_length=20,
        choices=Status.choices,
        default=Status.EN_COURS,
    )
    date_creation = models.DateTimeField('Date de création', auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = 'projet PFE'
        verbose_name_plural = 'projets PFE'

    def __str__(self):
        return self.sujet


class Livrable(models.Model):
    """Livrable or document submitted by a student for their PFE."""

    class Status(models.TextChoices):
        DEPOSE = 'DEPOSE', 'Déposé'
        VALIDE = 'VALIDE', 'Validé'
        A_CORRIGER = 'A_CORRIGER', 'À corriger'

    projet = models.ForeignKey(
        ProjetPFE,
        on_delete=models.CASCADE,
        related_name='livrables',
        verbose_name='Projet PFE',
    )
    titre = models.CharField('Titre', max_length=200)
    fichier = models.FileField('Fichier', upload_to='livrables/%Y/%m/')
    commentaire = models.TextField('Commentaire', blank=True)
    status = models.CharField(
        'Statut',
        max_length=20,
        choices=Status.choices,
        default=Status.DEPOSE,
    )
    commentaire_encadrant = models.TextField("Commentaire de l'encadrant", blank=True)
    date_depot = models.DateTimeField('Date de dépôt', auto_now_add=True)

    class Meta:
        ordering = ['-date_depot']
        verbose_name = 'livrable'
        verbose_name_plural = 'livrables'

    def __str__(self):
        return self.titre
