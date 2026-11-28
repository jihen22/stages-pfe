from django.conf import settings
from django.db import models

from offres.models import Offre


class ProjetPFE(models.Model):
    """Projet de Fin d'Études (PFE) associated with a student and supervisors."""

    class Status(models.TextChoices):
        """Lifecycle states. Allowed moves between them live in ``pfe/workflow.py``."""

        EN_ATTENTE = 'EN_ATTENTE', "En attente d'encadrant"
        EN_COURS = 'EN_COURS', 'En cours'
        TERMINE = 'TERMINE', 'Terminé'
        PLANIFIE = 'PLANIFIE', 'Soutenance planifiée'
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
        default=Status.EN_ATTENTE,
    )
    date_creation = models.DateTimeField('Date de création', auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = 'projet PFE'
        verbose_name_plural = 'projets PFE'

    def __str__(self):
        return self.sujet

    def save(self, *args, **kwargs):
        """Pick the initial state on creation and record it in the history.

        A new project starts "en attente", or directly "en cours" when it is created
        with its academic supervisor. Later changes go through ``pfe.workflow``.
        """
        adding = self._state.adding
        if adding and self.encadrant_acad_id and self.status == self.Status.EN_ATTENTE:
            self.status = self.Status.EN_COURS
        super().save(*args, **kwargs)
        if adding:
            HistoriqueStatut.objects.create(projet=self, ancien='', nouveau=self.status)

    @property
    def etapes(self):
        """Main path of the lifecycle with a flag for done / current steps (for the stepper)."""
        ordre = [self.Status.EN_ATTENTE, self.Status.EN_COURS, self.Status.TERMINE,
                 self.Status.PLANIFIE, self.Status.SOUTENU]
        index = ordre.index(self.status)
        return [
            {'code': code, 'label': code.label, 'fait': i < index, 'courant': i == index}
            for i, code in enumerate(ordre)
        ]


class HistoriqueStatut(models.Model):
    """One line per status change of a PFE project (who, when, from what to what)."""

    projet = models.ForeignKey(
        ProjetPFE,
        on_delete=models.CASCADE,
        related_name='historique',
        verbose_name='Projet PFE',
    )
    ancien = models.CharField('Ancien statut', max_length=20, choices=ProjetPFE.Status.choices, blank=True)
    nouveau = models.CharField('Nouveau statut', max_length=20, choices=ProjetPFE.Status.choices)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='Auteur',
    )
    date = models.DateTimeField('Date', auto_now_add=True)

    class Meta:
        ordering = ['date', 'pk']
        verbose_name = 'changement de statut'
        verbose_name_plural = 'historique des statuts'

    def __str__(self):
        return f'{self.projet} : {self.ancien or "—"} → {self.nouveau}'


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
