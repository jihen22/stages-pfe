import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('pfe', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Soutenance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(verbose_name='Date et heure')),
                ('salle', models.CharField(max_length=100, verbose_name='Salle')),
                ('remarques', models.TextField(blank=True, verbose_name='Remarques')),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('jury', models.ManyToManyField(blank=True, limit_choices_to={'role': 'JURY'}, related_name='soutenances_jury', to=settings.AUTH_USER_MODEL, verbose_name='Membres du jury')),
                ('projet', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='soutenance', to='pfe.projetpfe', verbose_name='Projet PFE')),
            ],
            options={
                'verbose_name': 'soutenance',
                'verbose_name_plural': 'soutenances',
                'ordering': ['date'],
            },
        ),
        migrations.CreateModel(
            name='NoteSoutenance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note', models.DecimalField(decimal_places=2, max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(20)], verbose_name='Note')),
                ('remarque', models.TextField(blank=True, verbose_name='Remarque')),
                ('date_saisie', models.DateTimeField(auto_now_add=True)),
                ('jury_member', models.ForeignKey(limit_choices_to={'role': 'JURY'}, on_delete=django.db.models.deletion.CASCADE, related_name='notes_attribuees', to=settings.AUTH_USER_MODEL, verbose_name='Membre du jury')),
                ('soutenance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='soutenances.soutenance', verbose_name='Soutenance')),
            ],
            options={
                'verbose_name': 'note de soutenance',
                'verbose_name_plural': 'notes de soutenance',
                'unique_together': {('soutenance', 'jury_member')},
            },
        ),
    ]
