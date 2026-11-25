"""Génère un grand jeu de données réalistes (étudiants, encadrants, offres, PFE...).

Usage :
    python manage.py generate_data                       # valeurs par défaut
    python manage.py generate_data --students 100 --seed 7
    python manage.py generate_data --students 30 --acad 5 --pro 6 --jury 4

Crée (dans cet ordre) :
    1. des comptes : étudiants, encadrants académiques, encadrants pro, jury ;
    2. des offres (stage / PFE) avec des statuts variés ;
    3. des candidatures ;
    4. des projets PFE (issus des candidatures acceptées sur des offres PFE),
       avec livrables ;
    5. des soutenances avec jury et notes.

Les comptes générés sont préfixés (etu001, acad001, pro001, jury001...).
Chaque compte reçoit un mot de passe ALÉATOIRE UNIQUE, écrit dans un fichier CSV
(``--credentials``, défaut : generated_credentials.csv). Seuls les comptes créés
lors du lancement y figurent : les mots de passe ne sont pas récupérables ensuite
(la base ne stocke que des hash). Avec ``--password X``, tous les comptes
partageront le même mot de passe X (déconseillé).

Idempotente : relancer la commande ne crée pas de doublons. Avec le même
``--seed``, les données générées sont toujours identiques.
"""

import csv
import random
import secrets
import string
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import ProfilEncadrantPro, ProfilEtudiant, User
from candidatures.models import Candidature
from offres.models import Offre
from pfe.models import Livrable, ProjetPFE
from soutenances.models import NoteSoutenance, Soutenance

# ---------------------------------------------------------------------------
# Banques de données (noms tunisiens, filières, entreprises, sujets...)
# ---------------------------------------------------------------------------
PRENOMS_M = ['Mohamed', 'Ahmed', 'Ali', 'Sami', 'Yassine', 'Mehdi', 'Karim', 'Walid',
             'Amine', 'Oussama', 'Hamza', 'Aymen', 'Skander', 'Rami', 'Firas', 'Anis',
             'Bilel', 'Houssem', 'Marwen', 'Seifeddine', 'Ridha', 'Nizar']
PRENOMS_F = ['Ines', 'Nour', 'Leila', 'Sarra', 'Rim', 'Amel', 'Yosra', 'Mariem',
             'Emna', 'Hiba', 'Wafa', 'Syrine', 'Khaoula', 'Ghada', 'Rahma', 'Asma',
             'Salma', 'Manel', 'Cyrine', 'Dorra', 'Jihen', 'Fatma']
NOMS = ['Ben Ali', 'Trabelsi', 'Gharbi', 'Jebali', 'Mansouri', 'Bouazizi', 'Haddad',
        'Chaabane', 'Ben Salah', 'Mejri', 'Karoui', 'Ayadi', 'Sassi', 'Hamdi',
        'Zouari', 'Dridi', 'Ben Youssef', 'Khelifi', 'Jlassi', 'Bouzid', 'Triki',
        'Maaloul', 'Ferchichi', 'Belhaj', 'Nasri', 'Ouertani', 'Slimani', 'Baccouche']

FILIERES = {
    'Génie Logiciel': ['Python', 'Django', 'Java', 'Spring Boot', 'React', 'Angular',
                       'SQL', 'Git', 'Docker', 'REST'],
    'Informatique de Gestion': ['SQL', 'Power BI', 'Excel', 'ERP', 'PHP', 'Laravel',
                                'UML', 'Talend'],
    'Data Science': ['Python', 'pandas', 'scikit-learn', 'TensorFlow', 'SQL',
                     'Power BI', 'Spark', 'NLP'],
    'Réseaux et Sécurité': ['Linux', 'Cisco', 'Pentest', 'Firewall', 'VPN', 'Wireshark',
                            'Python', 'Docker'],
    'Systèmes Embarqués': ['C', 'C++', 'Arduino', 'STM32', 'IoT', 'MQTT', 'Python'],
}
NIVEAUX = ['Licence 3', 'Master 1', 'Master 2', 'Ingénieur 3']

ENTREPRISES = [
    ('Vermeg', 'Édition de logiciels', 'Tunis'),
    ('Sofrecom Tunisie', 'Télécoms', 'Tunis'),
    ('Telnet Holding', 'Ingénierie', 'Ariana'),
    ('Focus Corporation', 'Services numériques', 'Tunis'),
    ('Proxym Group', 'Développement logiciel', 'Sousse'),
    ('Ooredoo Tunisie', 'Télécoms', 'Tunis'),
    ('Delice Holding', 'Agroalimentaire', 'Ben Arous'),
    ('Poulina Group', 'Industrie', 'Ben Arous'),
    ('Sagemcom Tunisie', 'Électronique', 'Sfax'),
    ('Instadeep Tunis', 'Intelligence artificielle', 'Tunis'),
    ('Business & Decision', 'Conseil IT', 'Tunis'),
    ('Wevioo', 'Transformation digitale', 'Tunis'),
]
POSTES = ['Responsable IT', 'Lead Developer', 'Chef de projet', 'Directeur technique',
          'Architecte logiciel', 'Responsable Data', 'Manager R&D']

SALLES = ['Salle A1', 'Salle A2', 'Salle B1', 'Salle B2', 'Amphi 1', 'Amphi 2']

# (titre, compétences, durée, type)
MODELES_OFFRES = [
    ('Application web de gestion de stocks', 'Python, Django, SQL', '6 mois', Offre.Type.PFE),
    ('Plateforme e-learning', 'React, Node.js, MongoDB', '6 mois', Offre.Type.PFE),
    ('Détection de fraude par machine learning', 'Python, scikit-learn, pandas', '6 mois', Offre.Type.PFE),
    ('Application mobile de suivi de livraison', 'Flutter, Dart, REST', '6 mois', Offre.Type.PFE),
    ('Tableau de bord décisionnel Power BI', 'SQL, Power BI, Excel', '6 mois', Offre.Type.PFE),
    ('Supervision réseau et sécurité', 'Linux, Zabbix, Firewall', '6 mois', Offre.Type.PFE),
    ('Chatbot pour le support client', 'Python, NLP, Rasa', '6 mois', Offre.Type.PFE),
    ('Système IoT de monitoring industriel', 'C++, MQTT, Raspberry Pi', '6 mois', Offre.Type.PFE),
    ('Migration vers une architecture microservices', 'Java, Spring Boot, Docker', '6 mois', Offre.Type.PFE),
    ('Automatisation CI/CD', 'Docker, GitLab CI, Linux', '6 mois', Offre.Type.PFE),
    ('Stage développement web', 'HTML, CSS, JavaScript, PHP', '2 mois', Offre.Type.STAGE),
    ('Stage assistant data analyst', 'SQL, Excel, Python', '2 mois', Offre.Type.STAGE),
    ('Stage administration systèmes', 'Linux, Bash, Réseaux', '1 mois', Offre.Type.STAGE),
    ('Stage test et assurance qualité', 'Selenium, Postman, Jira', '2 mois', Offre.Type.STAGE),
    ('Stage développement mobile', 'Flutter, Firebase', '3 mois', Offre.Type.STAGE),
]

LETTRE = (
    "Bonjour,\n\nActuellement étudiant(e) en {niveau} ({filiere}), je suis très "
    "intéressé(e) par votre offre « {titre} ». Mes compétences en {competences} "
    "correspondent aux besoins décrits. Je serais ravi(e) d'échanger avec vous lors "
    "d'un entretien.\n\nCordialement,\n{nom}"
)

LIVRABLES = [
    ('Cahier des charges', Livrable.Status.VALIDE, 'Bien structuré, merci.'),
    ('Rapport intermédiaire', Livrable.Status.VALIDE, 'Bon travail, continuez.'),
    ('Rapport final', Livrable.Status.DEPOSE, ''),
]

REMARQUES_NOTE = ['Très bonne présentation.', 'Bon travail, démonstration claire.',
                  'Quelques points techniques à approfondir.', 'Excellent projet.',
                  'Travail sérieux, bonne maîtrise du sujet.']


class Command(BaseCommand):
    help = 'Génère un grand jeu de données réalistes (étudiants, encadrants, offres, PFE, soutenances).'

    def add_arguments(self, parser):
        parser.add_argument('--students', type=int, default=40, help='Nombre d\'étudiants (défaut 40)')
        parser.add_argument('--acad', type=int, default=6, help='Encadrants académiques (défaut 6)')
        parser.add_argument('--pro', type=int, default=8, help='Encadrants professionnels (défaut 8)')
        parser.add_argument('--jury', type=int, default=5, help='Membres du jury (défaut 5)')
        parser.add_argument('--seed', type=int, default=42, help='Graine aléatoire (défaut 42)')
        parser.add_argument('--password', default=None,
                            help='Mot de passe commun à tous les comptes (défaut : un mot de passe unique par compte)')
        parser.add_argument('--credentials', default='generated_credentials.csv',
                            help='Fichier CSV listant les identifiants créés (défaut generated_credentials.csv)')

    @transaction.atomic
    def handle(self, *args, **opts):
        self.rng = random.Random(opts['seed'])
        self.password = opts['password']
        self.credentials = []  # (username, nom, role, mot de passe) des comptes créés
        self.now = timezone.now()

        etudiants = self._users('etu', opts['students'], User.Role.ETUDIANT)
        acads = self._users('acad', opts['acad'], User.Role.ENCADRANT_ACAD)
        pros = self._users('pro', opts['pro'], User.Role.ENCADRANT_PRO)
        jurys = self._users('jury', opts['jury'], User.Role.JURY)

        for etu in etudiants:
            self._profil_etudiant(etu)
        for i, pro in enumerate(pros):
            self._profil_pro(pro, i)

        offres = self._offres(pros)
        n_cand = self._candidatures(etudiants, offres)
        n_proj, n_sout = self._projets(acads, jurys)

        self.stdout.write(self.style.SUCCESS(
            f'\nTerminé : {len(etudiants)} étudiants, {len(acads)} enc. académiques, '
            f'{len(pros)} enc. pro, {len(jurys)} jurys, {len(offres)} offres, '
            f'{n_cand} candidatures, {n_proj} projets PFE, {n_sout} soutenances.'
        ))
        if self.credentials:
            with open(opts['credentials'], 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['username', 'nom', 'role', 'mot_de_passe'])
                writer.writerows(self.credentials)
            self.stdout.write(f'{len(self.credentials)} identifiants écrits dans {opts["credentials"]} '
                              f'(ne pas versionner ce fichier !)')
        else:
            self.stdout.write('Aucun nouveau compte créé : pas de fichier d\'identifiants.')

    # -- 1. Comptes ---------------------------------------------------------
    def _users(self, prefix, count, role):
        users = []
        for i in range(1, count + 1):
            username = f'{prefix}{i:03d}'
            user = User.objects.filter(username=username).first()
            if not user:
                feminin = self.rng.random() < 0.5
                prenom = self.rng.choice(PRENOMS_F if feminin else PRENOMS_M)
                nom = self.rng.choice(NOMS)
                user = User(
                    username=username, first_name=prenom, last_name=nom,
                    email=f'{prenom}.{nom}'.lower().replace(' ', '') + f'.{i}@example.tn',
                    role=role,
                )
                password = self.password or self._random_password()
                user.set_password(password)
                user.save()
                self.credentials.append((username, user.get_full_name(), role, password))
            users.append(user)
        return users

    @staticmethod
    def _random_password(length=10):
        alphabet = string.ascii_letters.replace('l', '').replace('I', '').replace('O', '') + '23456789'
        while True:
            pwd = ''.join(secrets.choice(alphabet) for _ in range(length))
            if any(c.islower() for c in pwd) and any(c.isupper() for c in pwd) and any(c.isdigit() for c in pwd):
                return pwd

    def _profil_etudiant(self, etu):
        profil, _ = ProfilEtudiant.objects.get_or_create(user=etu)
        if profil.filiere:
            return
        filiere = self.rng.choice(list(FILIERES))
        competences = self.rng.sample(FILIERES[filiere], k=min(4, len(FILIERES[filiere])))
        profil.filiere = filiere
        profil.niveau = self.rng.choice(NIVEAUX)
        profil.competences = ', '.join(competences)
        profil.telephone = f'{self.rng.choice([2, 5, 9])}{self.rng.randint(0, 9)} ' \
                           f'{self.rng.randint(100, 999)} {self.rng.randint(100, 999)}'
        profil.bio = f'Étudiant(e) en {filiere}, passionné(e) par le développement et les nouvelles technologies.'
        profil.cv_base.save(f'cv_{etu.username}.txt', ContentFile(f'CV de {etu.get_full_name()}'), save=False)
        profil.save()

    def _profil_pro(self, pro, index):
        if ProfilEncadrantPro.objects.filter(user=pro).exists():
            return
        entreprise, secteur, ville = ENTREPRISES[index % len(ENTREPRISES)]
        slug = entreprise.lower().replace(' ', '').replace('&', '')
        ProfilEncadrantPro.objects.create(
            user=pro, entreprise=entreprise, poste=self.rng.choice(POSTES),
            secteur=secteur, ville=ville, site_web=f'https://www.{slug}.example.tn',
            telephone=f'7{self.rng.randint(0, 9)} {self.rng.randint(100, 999)} {self.rng.randint(100, 999)}',
            presentation=f'{entreprise} est une entreprise du secteur « {secteur} » basée à {ville}.',
        )

    # -- 2. Offres ----------------------------------------------------------
    def _offres(self, pros):
        statuts = [Offre.Status.PUBLIEE] * 7 + [Offre.Status.EN_VALIDATION] * 1 \
                  + [Offre.Status.BROUILLON] * 1 + [Offre.Status.REFUSEE] * 1
        offres = []
        for pro in pros:
            for titre, competences, duree, type_ in self.rng.sample(MODELES_OFFRES, k=min(4, len(MODELES_OFFRES))):
                status = self.rng.choice(statuts)
                offre, created = Offre.objects.get_or_create(
                    encadrant_pro=pro, titre=titre,
                    defaults={
                        'description': f'{titre} au sein de {pro.profil_encadrant_pro.entreprise}. '
                                       f'Vous participerez à la conception, au développement et aux tests.',
                        'competences': competences, 'duree': duree, 'type': type_, 'status': status,
                        'motif_refus': 'Description trop vague, merci de préciser les missions.'
                                       if status == Offre.Status.REFUSEE else '',
                        'date_publication': self.now - timedelta(days=self.rng.randint(1, 60))
                                            if status == Offre.Status.PUBLIEE else None,
                    },
                )
                offres.append(offre)
        return offres

    # -- 3. Candidatures ----------------------------------------------------
    def _candidatures(self, etudiants, offres):
        publiees = [o for o in offres if o.status == Offre.Status.PUBLIEE]
        if not publiees:
            return 0
        total = 0
        for etu in etudiants:
            if Candidature.objects.filter(etudiant=etu).exists():
                continue  # étudiant déjà traité lors d'un lancement précédent
            deja_accepte = Candidature.objects.filter(etudiant=etu, status=Candidature.Status.ACCEPTEE).exists()
            for offre in self.rng.sample(publiees, k=min(self.rng.randint(1, 3), len(publiees))):
                if Candidature.objects.filter(etudiant=etu, offre=offre).exists():
                    continue
                status = self.rng.choices(
                    [Candidature.Status.EN_ATTENTE, Candidature.Status.ACCEPTEE, Candidature.Status.REFUSEE],
                    weights=[40, 35, 25])[0]
                if status == Candidature.Status.ACCEPTEE and deja_accepte:
                    status = Candidature.Status.REFUSEE  # un seul stage/PFE accepté par étudiant
                if status == Candidature.Status.ACCEPTEE:
                    deja_accepte = True
                profil = etu.profil_etudiant
                cand = Candidature(
                    etudiant=etu, offre=offre, status=status,
                    lettre_motivation=LETTRE.format(
                        niveau=profil.niveau, filiere=profil.filiere, titre=offre.titre,
                        competences=', '.join(profil.competences_list[:3]), nom=etu.get_full_name()),
                )
                cand.cv.save(f'cv_{etu.username}.txt', ContentFile(f'CV de {etu.get_full_name()}'), save=False)
                cand.save()
                total += 1
        return total

    # -- 4 & 5. Projets PFE, livrables, soutenances -------------------------
    def _projets(self, acads, jurys):
        pdf_path = settings.BASE_DIR / 'fixtures' / 'demo_report.pdf'
        pdf_bytes = pdf_path.read_bytes() if pdf_path.exists() else b'%PDF-1.4\n%demo\n'

        acceptees = Candidature.objects.filter(
            status=Candidature.Status.ACCEPTEE, offre__type=Offre.Type.PFE,
        ).select_related('etudiant', 'offre')

        n_proj = n_sout = 0
        for cand in acceptees:
            etu = cand.etudiant
            if ProjetPFE.objects.filter(etudiant=etu).exists():
                continue
            status = self.rng.choices(
                [ProjetPFE.Status.EN_COURS, ProjetPFE.Status.TERMINE, ProjetPFE.Status.SOUTENU],
                weights=[45, 25, 30])[0]
            # ~20 % des projets attendent encore un encadrant académique
            encadrant = self.rng.choice(acads) if acads and self.rng.random() > 0.2 else None
            projet = ProjetPFE.objects.create(
                etudiant=etu, encadrant_acad=encadrant, offre=cand.offre,
                sujet=cand.offre.titre, description=cand.offre.description, status=status,
            )
            n_proj += 1

            nb_livrables = {ProjetPFE.Status.EN_COURS: 1, ProjetPFE.Status.TERMINE: 3,
                            ProjetPFE.Status.SOUTENU: 3}[status]
            for titre, l_status, commentaire in LIVRABLES[:nb_livrables]:
                liv = Livrable(projet=projet, titre=titre, status=l_status,
                               commentaire_encadrant=commentaire,
                               commentaire='Version à relire.')
                liv.fichier.save(f'{etu.username}_{titre.lower().replace(" ", "_")}.pdf',
                                 ContentFile(pdf_bytes), save=False)
                liv.save()

            if status in (ProjetPFE.Status.TERMINE, ProjetPFE.Status.SOUTENU) and len(jurys) >= 2:
                passee = status == ProjetPFE.Status.SOUTENU
                delta = timedelta(days=self.rng.randint(-30, -1) if passee else self.rng.randint(3, 40))
                date = (self.now + delta).replace(hour=self.rng.choice([9, 10, 11, 14, 15]),
                                                  minute=0, second=0, microsecond=0)
                sout = Soutenance.objects.create(projet=projet, date=date, salle=self.rng.choice(SALLES))
                membres = self.rng.sample(jurys, k=min(3, len(jurys)))
                sout.jury.set(membres)
                n_sout += 1
                if passee:
                    for membre in membres:
                        NoteSoutenance.objects.create(
                            soutenance=sout, jury_member=membre,
                            note=Decimal(str(round(self.rng.uniform(11, 19.5) * 4) / 4)),
                            remarque=self.rng.choice(REMARQUES_NOTE),
                        )
        return n_proj, n_sout