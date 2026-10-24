import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('offres', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjetPFE',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sujet', models.CharField(max_length=300, verbose_name='Sujet')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('status', models.CharField(choices=[('EN_COURS', 'En cours'), ('TERMINE', 'Terminé'), ('SOUTENU', 'Soutenu')], default='EN_COURS', max_length=20, verbose_name='Statut')),
                ('date_creation', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('encadrant_acad', models.ForeignKey(blank=True, limit_choices_to={'role': 'ENCADRANT_ACAD'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='projets_encadres_acad', to=settings.AUTH_USER_MODEL, verbose_name='Encadrant académique')),
                ('etudiant', models.ForeignKey(limit_choices_to={'role': 'ETUDIANT'}, on_delete=django.db.models.deletion.CASCADE, related_name='projets_pfe', to=settings.AUTH_USER_MODEL, verbose_name='Étudiant')),
                ('offre', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='projets_pfe', to='offres.offre', verbose_name='Offre')),
            ],
            options={
                'verbose_name': 'projet PFE',
                'verbose_name_plural': 'projets PFE',
                'ordering': ['-date_creation'],
            },
        ),
        migrations.CreateModel(
            name='Livrable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=200, verbose_name='Titre')),
                ('fichier', models.FileField(upload_to='livrables/%Y/%m/', verbose_name='Fichier')),
                ('commentaire', models.TextField(blank=True, verbose_name='Commentaire')),
                ('status', models.CharField(choices=[('DEPOSE', 'Déposé'), ('VALIDE', 'Validé'), ('A_CORRIGER', 'À corriger')], default='DEPOSE', max_length=20, verbose_name='Statut')),
                ('commentaire_encadrant', models.TextField(blank=True, verbose_name="Commentaire de l'encadrant")),
                ('date_depot', models.DateTimeField(auto_now_add=True, verbose_name='Date de dépôt')),
                ('projet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='livrables', to='pfe.projetpfe', verbose_name='Projet PFE')),
            ],
            options={
                'verbose_name': 'livrable',
                'verbose_name_plural': 'livrables',
                'ordering': ['-date_depot'],
            },
        ),
    ]
