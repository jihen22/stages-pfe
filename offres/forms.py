from django import forms

from accounts.forms import BootstrapFormMixin

from .models import Offre


class OffreForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Offre
        fields = ('titre', 'description', 'competences', 'duree', 'type')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'competences': forms.TextInput(attrs={'placeholder': 'Ex : Python, Django, SQL'}),
        }
