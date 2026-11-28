from django import forms

from accounts.forms import BootstrapFormMixin
from accounts.models import User
from offres.models import Offre

from .models import Livrable, ProjetPFE
from .suggestion import raison_refus


class ProjetPFEForm(BootstrapFormMixin, forms.ModelForm):
    """Form for student to create or edit their PFE subject and description."""

    class Meta:
        model = ProjetPFE
        fields = ('sujet', 'domaine', 'description')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Décrivez les objectifs et le contexte du projet…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Needed to suggest an academic supervisor of the right field (item 10).
        self.fields['domaine'].required = True


class LivrableForm(BootstrapFormMixin, forms.ModelForm):
    """Form for student to upload a new deliverable/report."""

    class Meta:
        model = Livrable
        fields = ('titre', 'fichier', 'commentaire')
        widgets = {
            'commentaire': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notes ou commentaires éventuels sur ce livrable…'}),
        }


class NouvelleVersionForm(BootstrapFormMixin, forms.ModelForm):
    """New version of an existing deliverable: same title, new file and note."""

    class Meta:
        model = Livrable
        fields = ('fichier', 'commentaire')
        labels = {'commentaire': 'Ce qui a changé'}
        widgets = {
            'commentaire': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Corrections apportées, nouvelles sections…'}),
        }


class ProjetEncadrantForm(BootstrapFormMixin, forms.ModelForm):
    """Form for an academic supervisor to create a PFE project for a student."""

    etudiant = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Étudiant',
        empty_label='-- Sélectionner un étudiant --',
    )

    class Meta:
        model = ProjetPFE
        fields = ('etudiant', 'offre', 'sujet', 'description')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Objectifs, périmètre et contexte du projet…'}),
        }

    def __init__(self, *args, encadrant=None, **kwargs):
        self.encadrant = encadrant
        super().__init__(*args, **kwargs)
        # Only students who do not already have a PFE project can be assigned one.
        self.fields['etudiant'].queryset = User.objects.filter(
            role=User.Role.ETUDIANT,
            projets_pfe__isnull=True,
        ).order_by('last_name', 'first_name', 'username')
        self.fields['offre'].queryset = Offre.objects.filter(
            type=Offre.Type.PFE,
            status=Offre.Status.PUBLIEE,
        ).order_by('titre')
        self.fields['offre'].required = False

        if encadrant is not None and encadrant.domaine:
            # Item 10: a supervisor creates projects in their own field.
            self.fields['offre'].queryset = self.fields['offre'].queryset.filter(
                domaine__in=['', encadrant.domaine])
            self.fields['offre'].help_text = (
                f"Seules les offres PFE de votre domaine ({encadrant.get_domaine_display()}) sont proposées."
            )

    def clean_etudiant(self):
        etudiant = self.cleaned_data['etudiant']
        if ProjetPFE.objects.filter(etudiant=etudiant).exists():
            raise forms.ValidationError('Cet étudiant a déjà un projet PFE.')
        return etudiant

    def clean(self):
        cleaned = super().clean()
        if self.encadrant is not None:
            offre = cleaned.get('offre')
            self.instance.domaine = (offre.domaine if offre and offre.domaine else self.encadrant.domaine)
            erreur = raison_refus(self.instance, self.encadrant)
            if erreur:
                raise forms.ValidationError(erreur)
        return cleaned
