"""Create (or reset) one demo account per role.

Usage:
    python manage.py create_demo_users
"""

from django.core.management.base import BaseCommand

from accounts.models import User

DEMO_PASSWORD = 'demo1234'

DEMO_USERS = [
    {
        'username': 'etudiant',
        'role': User.Role.ETUDIANT,
        'first_name': 'Sami',
        'last_name': 'Ben Ali',
        'email': 'etudiant@example.com',
    },
    {
        'username': 'encadrant_pro',
        'role': User.Role.ENCADRANT_PRO,
        'first_name': 'Karim',
        'last_name': 'Trabelsi',
        'email': 'encadrant.pro@example.com',
    },
    {
        'username': 'encadrant_acad',
        'role': User.Role.ENCADRANT_ACAD,
        'first_name': 'Leila',
        'last_name': 'Mansouri',
        'email': 'encadrant.acad@example.com',
    },
    {
        'username': 'admin',
        'role': User.Role.ADMIN,
        'first_name': 'Nadia',
        'last_name': 'Gharbi',
        'email': 'admin@example.com',
        # is_staff lets this account also reach the Django admin site.
        'is_staff': True,
    },
    {
        'username': 'jury',
        'role': User.Role.JURY,
        'first_name': 'Hatem',
        'last_name': 'Jaziri',
        'email': 'jury@example.com',
    },
]


class Command(BaseCommand):
    help = 'Crée un utilisateur de démonstration par rôle (mot de passe : demo1234).'

    def handle(self, *args, **options):
        for data in DEMO_USERS:
            username = data['username']
            user, created = User.objects.get_or_create(username=username)

            for field, value in data.items():
                if field != 'username':
                    setattr(user, field, value)

            user.set_password(DEMO_PASSWORD)
            user.is_active = True
            user.save()

            action = 'créé' if created else 'mis à jour'
            self.stdout.write(self.style.SUCCESS(
                f'[{action}] {username:15s} -> {user.get_role_display()}'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\nComptes de démonstration prêts (mot de passe : {DEMO_PASSWORD}).'
        ))
