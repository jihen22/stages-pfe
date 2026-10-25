from django import forms
from django.db.models import Q

from accounts.forms import BootstrapFormMixin
from accounts.models import User
from pfe.models import ProjetPFE

from .models import NoteSoutenance, Soutenance


class SoutenanceForm(BootstrapFormMixin, forms.ModelForm):
    """Form for administration to schedule a defense and pick its jury."""

    class Meta:
        model = Soutenance
        fields = ('projet', 'date', 'salle', 'jury')
        labels = {
            'projet': 'Projet PFE',
            'date': 'Date et heure',
            'salle': 'Salle',
            'jury': 'Membres du jury',
        }
        widgets = {
            'date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'jury': forms.SelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        projets = ProjetPFE.objects.all()
        if self.instance.pk and self.instance.projet_id:
            # Editing an existing defense: allow keeping its current project.
            projets = projets.filter(Q(soutenance__isnull=True) | Q(pk=self.instance.projet_id))
        else:
            projets = projets.filter(soutenance__isnull=True)
        self.fields['projet'].queryset = projets

        self.fields['jury'].queryset = User.objects.filter(role=User.Role.JURY)
        self.fields['jury'].required = True
        self.fields['date'].input_formats = [
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
        ]


class NoteSoutenanceForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = NoteSoutenance
        fields = ('note', 'remarque')
        labels = {
            'note': 'Note (/20)',
            'remarque': 'Remarques',
        }
        widgets = {
            'note': forms.NumberInput(
                attrs={
                    'step': '0.25',
                    'min': '0',
                    'max': '20',
                    'placeholder': 'Ex. : 15.5',
                }
            ),
            'remarque': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': 'Observations ou remarques sur la prestation…',
                }
            ),
        }
