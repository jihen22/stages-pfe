from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse


class User(AbstractUser):
    """Custom user with a ``role`` used to drive dashboards and permissions."""

    class Role(models.TextChoices):
        ETUDIANT = 'ETUDIANT', 'Étudiant'
        ENCADRANT_PRO = 'ENCADRANT_PRO', 'Encadrant professionnel'
        ENCADRANT_ACAD = 'ENCADRANT_ACAD', 'Encadrant académique'
        ADMIN = 'ADMIN', 'Administration'
        JURY = 'JURY', 'Jury'

    class Theme(models.TextChoices):
        LIGHT = 'LIGHT', 'Clair'
        DARK = 'DARK', 'Sombre'
        AUTO = 'AUTO', 'Automatique'

    class Accent(models.TextChoices):
        BLUE = 'BLUE', 'Bleu'
        GREEN = 'GREEN', 'Vert'
        PURPLE = 'PURPLE', 'Violet'
        ORANGE = 'ORANGE', 'Orange'

    role = models.CharField(
        'Rôle',
        max_length=20,
        choices=Role.choices,
        default=Role.ETUDIANT,
    )
    theme = models.CharField(
        'Thème',
        max_length=10,
        choices=Theme.choices,
        default=Theme.AUTO,
    )
    accent = models.CharField(
        'Couleur d\'accent',
        max_length=10,
        choices=Accent.choices,
        default=Accent.BLUE,
    )

    class Meta:
        verbose_name = 'utilisateur'
        verbose_name_plural = 'utilisateurs'

    def __str__(self):
        nom = self.get_full_name() or self.username
        return f'{nom} ({self.get_role_display()})'

    # -- Convenience role helpers -----------------------------------------
    @property
    def is_etudiant(self):
        return self.role == self.Role.ETUDIANT

    @property
    def is_encadrant_pro(self):
        return self.role == self.Role.ENCADRANT_PRO

    @property
    def is_encadrant_acad(self):
        return self.role == self.Role.ENCADRANT_ACAD

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_jury(self):
        return self.role == self.Role.JURY

    def get_dashboard_url(self):
        """Return the URL of the dashboard matching this user's role."""
        mapping = {
            self.Role.ETUDIANT: 'accounts:dashboard_etudiant',
            self.Role.ENCADRANT_PRO: 'accounts:dashboard_encadrant_pro',
            self.Role.ENCADRANT_ACAD: 'accounts:dashboard_encadrant_acad',
            self.Role.ADMIN: 'accounts:dashboard_admin',
            self.Role.JURY: 'accounts:dashboard_jury',
        }
        return reverse(mapping.get(self.role, 'accounts:dashboard_etudiant'))


class ProfilEtudiant(models.Model):
    """Extra information a student fills in to complete their profile.

    One is created automatically for every student account (see the
    ``post_save`` receiver below); the fields are optional so the profile can
    be completed progressively. ``completion`` drives the progress bar shown
    on the student dashboard.
    """

    COMPLETION_FIELDS = ('filiere', 'niveau', 'competences', 'cv_base', 'telephone', 'bio')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profil_etudiant',
        verbose_name='Étudiant',
    )
    filiere = models.CharField('Filière', max_length=150, blank=True)
    niveau = models.CharField('Niveau', max_length=100, blank=True, help_text='Ex. : Master 2')
    competences = models.TextField(
        'Compétences',
        blank=True,
        help_text='Séparez les compétences par des virgules (ex. : Python, Django, SQL).',
    )
    cv_base = models.FileField('CV de base', upload_to='cvs_base/%Y/%m/', blank=True, null=True)
    telephone = models.CharField('Téléphone', max_length=30, blank=True)
    bio = models.TextField('Bio', blank=True)

    class Meta:
        verbose_name = 'profil étudiant'
        verbose_name_plural = 'profils étudiants'

    def __str__(self):
        return f'Profil de {self.user}'

    @property
    def completion(self):
        """Return the percentage (0-100) of filled profile fields."""
        total = len(self.COMPLETION_FIELDS)
        if not total:
            return 100
        filled = sum(1 for field in self.COMPLETION_FIELDS if getattr(self, field))
        return round(filled * 100 / total)

    @property
    def is_complete(self):
        return self.completion >= 100

    @property
    def competences_list(self):
        return [item.strip() for item in self.competences.split(',') if item.strip()]


@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    """Create an empty ``ProfilEtudiant`` for every new student account."""
    if created and instance.role == User.Role.ETUDIANT:
        ProfilEtudiant.objects.get_or_create(user=instance)
