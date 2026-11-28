"""Give existing projects the field of the offer they come from.

Projects without an offer (or whose offer has no field) keep an empty field:
any academic supervisor can then take them, as for offers without a field.
"""

from django.db import migrations


def copier_domaine(apps, schema_editor):
    ProjetPFE = apps.get_model('pfe', 'ProjetPFE')
    for projet in ProjetPFE.objects.filter(domaine='', offre__isnull=False).select_related('offre'):
        if projet.offre.domaine:
            ProjetPFE.objects.filter(pk=projet.pk).update(domaine=projet.offre.domaine)


class Migration(migrations.Migration):

    dependencies = [
        ('pfe', '0004_projetpfe_domaine'),
        ('offres', '0002_offre_domaine'),
    ]

    operations = [
        migrations.RunPython(copier_domaine, migrations.RunPython.noop),
    ]
