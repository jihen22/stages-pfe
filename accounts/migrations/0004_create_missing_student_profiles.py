"""Create a ``ProfilEtudiant`` for every existing student user.

New students get a profile automatically through the ``post_save`` signal;
this handles accounts that existed before the model was introduced.
"""

from django.db import migrations


def create_profiles(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    ProfilEtudiant = apps.get_model('accounts', 'ProfilEtudiant')

    existing_user_ids = set(ProfilEtudiant.objects.values_list('user_id', flat=True))
    to_create = [
        ProfilEtudiant(user_id=user_id)
        for user_id in User.objects.filter(role='ETUDIANT').values_list('pk', flat=True)
        if user_id not in existing_user_ids
    ]
    ProfilEtudiant.objects.bulk_create(to_create)


def delete_profiles(apps, schema_editor):
    # Reversing simply removes the profiles; users are left untouched.
    ProfilEtudiant = apps.get_model('accounts', 'ProfilEtudiant')
    ProfilEtudiant.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_profiletudiant'),
    ]

    operations = [
        migrations.RunPython(create_profiles, delete_profiles),
    ]
