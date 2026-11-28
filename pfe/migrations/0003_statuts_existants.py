"""Move existing projects to the new lifecycle states and seed their history.

- project with a defense: SOUTENU if it was already "soutenu", else PLANIFIE
- project without a supervisor (and not finished): EN_ATTENTE
- every other project keeps its status
Each project gets one history line with its resulting status.
"""

from django.db import migrations


def convertir(apps, schema_editor):
    ProjetPFE = apps.get_model('pfe', 'ProjetPFE')
    HistoriqueStatut = apps.get_model('pfe', 'HistoriqueStatut')
    Soutenance = apps.get_model('soutenances', 'Soutenance')

    avec_soutenance = set(Soutenance.objects.values_list('projet_id', flat=True))
    for projet in ProjetPFE.objects.all():
        if projet.pk in avec_soutenance:
            nouveau = 'SOUTENU' if projet.status == 'SOUTENU' else 'PLANIFIE'
        elif projet.encadrant_acad_id is None and projet.status == 'EN_COURS':
            nouveau = 'EN_ATTENTE'
        else:
            nouveau = projet.status
        if nouveau != projet.status:
            ProjetPFE.objects.filter(pk=projet.pk).update(status=nouveau)
        if not HistoriqueStatut.objects.filter(projet_id=projet.pk).exists():
            HistoriqueStatut.objects.create(projet_id=projet.pk, ancien='', nouveau=nouveau)


class Migration(migrations.Migration):

    dependencies = [
        ('pfe', '0002_cycle_de_vie'),
        ('soutenances', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(convertir, migrations.RunPython.noop),
    ]
