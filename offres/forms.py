from django import forms

from accounts.forms import BootstrapFormMixin

from .models import Offre


class OffreForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Offre
        fields = ('titre', 'description', 'domaine', 'competences', 'duree', 'type')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'competences': forms.TextInput(attrs={'placeholder': 'Ex : Python, Django, SQL'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Blank in the database for older offers, but required for every new or edited one.
        self.fields['domaine'].required = True
