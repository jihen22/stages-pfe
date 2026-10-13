from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import ProfilEtudiant, User


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
