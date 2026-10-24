from django import forms

from accounts.forms import BootstrapFormMixin
from accounts.models import User

from .models import Livrable, ProjetPFE


class ProjetPFEForm(BootstrapFormMixin, forms.ModelForm):
    """Form for student to create or edit their PFE subject and description."""

    class Meta:
        model = ProjetPFE
        fields = ('sujet', 'description')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Décrivez les objectifs et le contexte du projet…'}),
        }


class LivrableForm(BootstrapFormMixin, forms.ModelForm):
    """Form for student to upload a new deliverable/report."""

    class Meta:
        model = Livrable
        fields = ('titre', 'fichier', 'commentaire')
        widgets = {
            'commentaire': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notes ou commentaires éventuels sur ce livrable…'}),
        }


class AffectationForm(BootstrapFormMixin, forms.ModelForm):
    """Form for administration to assign an academic supervisor to a PFE project."""

    class Meta:
        model = ProjetPFE
        fields = ('encadrant_acad',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['encadrant_acad'].queryset = User.objects.filter(role=User.Role.ENCADRANT_ACAD)
        self.fields['encadrant_acad'].empty_label = '-- Non affecté --'
        self.fields['encadrant_acad'].required = False
