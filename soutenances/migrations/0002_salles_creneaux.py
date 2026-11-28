"""Rooms and time slots for defenses (backlog item 19).

Existing defenses are converted without losing anything:
- each distinct room name becomes a ``Salle``;
- each defense date becomes a one-hour ``Creneau`` starting at that date.
Then the old ``date`` and free-text ``salle`` columns are replaced by the
``creneau`` and ``salle`` foreign keys.
"""

from datetime import timedelta

import django.db.models.deletion
from django.db import migrations, models

DUREE_PAR_DEFAUT = timedelta(hours=1)


def convertir(apps, schema_editor):
    Soutenance = apps.get_model('soutenances', 'Soutenance')
    Salle = apps.get_model('soutenances', 'Salle')
    Creneau = apps.get_model('soutenances', 'Creneau')
    for soutenance in Soutenance.objects.all():
        nom = (soutenance.salle or '').strip() or 'Salle à préciser'
        salle, _ = Salle.objects.get_or_create(nom=nom)
        creneau, _ = Creneau.objects.get_or_create(
            debut=soutenance.date, fin=soutenance.date + DUREE_PAR_DEFAUT)
        soutenance.salle_ref = salle
        soutenance.creneau = creneau
        soutenance.save(update_fields=['salle_ref', 'creneau'])


class Migration(migrations.Migration):

    dependencies = [
        ('soutenances', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Salle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100, unique=True, verbose_name='Nom')),
                ('batiment', models.CharField(blank=True, max_length=100, verbose_name='Bâtiment')),
                ('capacite', models.PositiveSmallIntegerField(default=30, verbose_name='Capacité (places)')),
                ('active', models.BooleanField(default=True, help_text="Une salle désactivée n'est plus proposée pour les nouvelles soutenances.", verbose_name='Disponible')),
            ],
            options={
                'verbose_name': 'salle',
                'verbose_name_plural': 'salles',
                'ordering': ['nom'],
            },
        ),
        migrations.CreateModel(
            name='Creneau',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('debut', models.DateTimeField(verbose_name='Début')),
                ('fin', models.DateTimeField(verbose_name='Fin')),
            ],
            options={
                'verbose_name': 'créneau',
                'verbose_name_plural': 'créneaux',
                'ordering': ['debut', 'fin'],
                'constraints': [
                    models.CheckConstraint(condition=models.Q(('fin__gt', models.F('debut'))), name='creneau_fin_apres_debut'),
                    models.UniqueConstraint(fields=('debut', 'fin'), name='creneau_unique'),
                ],
            },
        ),
        # Temporary ordering while the old "date" column is removed.
        migrations.AlterModelOptions(
            name='soutenance',
            options={'ordering': ['pk'], 'verbose_name': 'soutenance', 'verbose_name_plural': 'soutenances'},
        ),
        migrations.AddField(
            model_name='soutenance',
            name='creneau',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='soutenances', to='soutenances.creneau', verbose_name='Créneau'),
        ),
        migrations.AddField(
            model_name='soutenance',
            name='salle_ref',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='soutenances', to='soutenances.salle', verbose_name='Salle'),
        ),
        migrations.RunPython(convertir, migrations.RunPython.noop),
        migrations.RemoveField(model_name='soutenance', name='date'),
        migrations.RemoveField(model_name='soutenance', name='salle'),
        migrations.RenameField(model_name='soutenance', old_name='salle_ref', new_name='salle'),
        migrations.AlterField(
            model_name='soutenance',
            name='creneau',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='soutenances', to='soutenances.creneau', verbose_name='Créneau'),
        ),
        migrations.AlterField(
            model_name='soutenance',
            name='salle',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='soutenances', to='soutenances.salle', verbose_name='Salle'),
        ),
        migrations.AlterModelOptions(
            name='soutenance',
            options={'ordering': ['creneau__debut'], 'verbose_name': 'soutenance', 'verbose_name_plural': 'soutenances'},
        ),
    ]
