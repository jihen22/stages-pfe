from django import forms

from accounts.forms import BootstrapFormMixin

from .models import Candidature


class CandidatureForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Candidature
        fields = ('cv', 'lettre_motivation')
        widgets = {
            'lettre_motivation': forms.Textarea(
                attrs={'rows': 6, 'placeholder': 'Expliquez pourquoi cette offre vous intéresse...'}
            ),
        }
