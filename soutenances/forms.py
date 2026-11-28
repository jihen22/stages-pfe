from datetime import datetime, timedelta

from django import forms
from django.db.models import Q
from django.utils import timezone

from accounts.forms import BootstrapFormMixin
from accounts.models import User
from pfe.models import ProjetPFE

from .models import Creneau, NoteSoutenance, Salle, Soutenance


class SoutenanceForm(BootstrapFormMixin, forms.ModelForm):
    """Form for administration to schedule a defense: project, slot, room and jury."""

    class Meta:
        model = Soutenance
        fields = ('projet', 'creneau', 'salle', 'jury')
        labels = {
            'projet': 'Projet PFE',
            'creneau': 'Créneau',
            'salle': 'Salle',
            'jury': 'Membres du jury',
        }
        widgets = {
            'jury': forms.SelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only finished projects (state machine, pfe/workflow.py) can get a defense.
        projets = ProjetPFE.objects.all()
        if self.instance.pk and self.instance.projet_id:
            # Editing an existing defense: allow keeping its current project.
            projets = projets.filter(
                Q(soutenance__isnull=True, status=ProjetPFE.Status.TERMINE)
                | Q(pk=self.instance.projet_id)
            )
        else:
            projets = projets.filter(soutenance__isnull=True, status=ProjetPFE.Status.TERMINE)
        self.fields['projet'].queryset = projets

        # Item 19: upcoming slots and available rooms only.
        self.fields['creneau'].queryset = Creneau.objects.filter(debut__gte=timezone.now())
        self.fields['creneau'].empty_label = '-- Choisir un créneau --'
        self.fields['salle'].queryset = Salle.objects.filter(active=True)
        self.fields['salle'].empty_label = '-- Choisir une salle --'
        self.fields['salle'].label_from_instance = (
            lambda s: f'{s.nom} ({s.batiment}, {s.capacite} places)' if s.batiment else f'{s.nom} ({s.capacite} places)'
        )

        self.fields['jury'].queryset = User.objects.filter(role=User.Role.JURY)
        self.fields['jury'].required = True


class SalleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Salle
        fields = ('nom', 'batiment', 'capacite')
        widgets = {
            'nom': forms.TextInput(attrs={'placeholder': 'Ex. : Amphi A'}),
            'batiment': forms.TextInput(attrs={'placeholder': 'Ex. : Bloc B'}),
        }


class CreneauForm(BootstrapFormMixin, forms.ModelForm):
    """One slot, entered with its start and end."""

    class Meta:
        model = Creneau
        fields = ('debut', 'fin')
        widgets = {
            'debut': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('debut', 'fin'):
            self.fields[name].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M']

    def clean(self):
        cleaned = super().clean()
        debut, fin = cleaned.get('debut'), cleaned.get('fin')
        if debut and fin and Creneau.objects.filter(debut=debut, fin=fin).exists():
            raise forms.ValidationError('Ce créneau existe déjà.')
        return cleaned


class JourneeCreneauxForm(BootstrapFormMixin, forms.Form):
    """Generate the slots of a whole defense day in one go."""

    jour = forms.DateField(label='Jour', widget=forms.DateInput(attrs={'type': 'date'}))
    heure_debut = forms.TimeField(label='De', initial='09:00', widget=forms.TimeInput(attrs={'type': 'time'}))
    heure_fin = forms.TimeField(label='À', initial='17:00', widget=forms.TimeInput(attrs={'type': 'time'}))
    duree = forms.IntegerField(label='Durée (min)', initial=60, min_value=15, max_value=240)
    pause = forms.IntegerField(label='Pause entre deux (min)', initial=0, min_value=0, max_value=120)

    def clean(self):
        cleaned = super().clean()
        debut, fin = cleaned.get('heure_debut'), cleaned.get('heure_fin')
        if debut and fin and fin <= debut:
            raise forms.ValidationError("L'heure de fin doit être après l'heure de début.")
        return cleaned

    def creneaux(self):
        """(start, end) aware datetimes of every slot that fits in the day."""
        jour = self.cleaned_data['jour']
        tz = timezone.get_current_timezone()
        debut = timezone.make_aware(datetime.combine(jour, self.cleaned_data['heure_debut']), tz)
        limite = timezone.make_aware(datetime.combine(jour, self.cleaned_data['heure_fin']), tz)
        duree = timedelta(minutes=self.cleaned_data['duree'])
        pause = timedelta(minutes=self.cleaned_data['pause'])
        resultat = []
        while debut + duree <= limite:
            resultat.append((debut, debut + duree))
            debut += duree + pause
        return resultat


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
