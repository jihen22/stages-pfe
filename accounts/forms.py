from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import ProfilEtudiant, ProfilEncadrantPro, User


class BootstrapFormMixin:
    """Add Bootstrap 5 CSS classes to every widget of a form.

    Imported by the other apps so all forms look consistent without having to
    repeat widget classes everywhere.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')


class BootstrapAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    """Login form with Bootstrap styling (labels come from i18n)."""


class StudentRegistrationForm(BootstrapFormMixin, UserCreationForm):
    """Self-registration restricted to the ETUDIANT role."""

    first_name = forms.CharField(label='Prénom', max_length=150)
    last_name = forms.CharField(label='Nom', max_length=150)
    email = forms.EmailField(label='Adresse e-mail', required=False)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.ETUDIANT
        if commit:
            user.save()
        return user


class ProfilEtudiantForm(BootstrapFormMixin, forms.ModelForm):
    """Edit form for the student profile (``ProfilEtudiant``)."""

    class Meta:
        model = ProfilEtudiant
        fields = ('filiere', 'niveau', 'competences', 'cv_base', 'telephone', 'bio')
        widgets = {
            'competences': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Python, Django, SQL'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Présentez-vous en quelques lignes…'}),
            'telephone': forms.TextInput(attrs={'placeholder': '+216 …'}),
        }

class EncadrantProRegistrationForm(StudentRegistrationForm):

    """Inscription d'un encadrant professionnel.

    On hérite de StudentRegistrationForm pour réutiliser le prénom, le nom,
    le mot de passe et la validation. On change le rôle, on rend l'e-mail
    obligatoire et on ajoute l'entreprise et le poste.
    """
    email=forms.EmailField(label="Adresse e-mail profissionnelle")
    entreprise=forms.CharField(label="Entreprise", max_length=150)
    poste=forms.CharField(label="Poste occupé", max_length=150)
    telephone=forms.CharField(label="Téléphone", max_length=150, required=False)

    # Ordre d'affichage des champs dans le formulaire
    field_order=[
        "username","first_name" , "last_name", "email",
        'entreprise','poste','telephone',
        'password1','password2',
    ]

    def save(self, commit=True):
        user = super().save(commit=False)       # le parent met le rôle ETUDIANT...
        user.role = User.Role.ENCADRANT_PRO     # ...on le remplace avant d'enregistrer
        if commit:
            user.save()
            ProfilEncadrantPro.objects.create(
                user=user,
                entreprise=self.cleaned_data['entreprise'],
                poste=self.cleaned_data['poste'],
                telephone=self.cleaned_data['telephone'],
            )
        return user

