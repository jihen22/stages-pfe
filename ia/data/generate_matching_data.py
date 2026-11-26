"""Génère un jeu de données pour le matching sémantique CV <-> offre.

Script autonome : il n'a pas besoin de Django, seulement de Python 3.9+.

    python generate_matching_data.py                       # 200 CV, 60 offres
    python generate_matching_data.py --cvs 500 --offres 100 --seed 7 --out data

Fichiers produits (dans --out, défaut : matching_data/) :
    cvs.csv     un CV par ligne (texte libre + compétences déclarées)
    offres.csv  une offre par ligne (description + compétences requises)
    pairs.csv   la vérité terrain : pour chaque couple (cv, offre), une pertinence
                  2 = très bon match, 1 = match partiel, 0 = pas de match

Les colonnes ``domaine`` de cvs.csv et offres.csv servent UNIQUEMENT à analyser
tes erreurs après coup. Ne les utilise jamais comme entrée de ton modèle.

Difficultés volontaires (pour que le problème ne soit pas trivial) :
    - des compétences communes à plusieurs domaines (Python, SQL, Git, Docker...) ;
    - ~40 % des compétences d'un CV sont écrites par une paraphrase dans le texte
      (« pare-feu » au lieu de « Firewall ») : la recherche par mots-clés les rate ;
    - ~10 % de CV vagues, ~30 % de CV avec un second domaine, ~15 % en anglais.
"""

import argparse
import csv
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Domaines : compétences, thèmes de projets, missions d'offres
# ---------------------------------------------------------------------------
DOMAINES = {
    'web_backend': {
        'filiere': 'Génie Logiciel',
        'skills': ['Python', 'Django', 'Flask', 'FastAPI', 'PostgreSQL', 'SQL', 'REST API', 'Docker', 'Git', 'Redis'],
        'titres': ['Développeur backend Django', 'Développeur web Python', 'Ingénieur API REST'],
        'themes_fr': ['de gestion de stocks', 'de réservation en ligne', "d'e-commerce"],
        'themes_en': ['inventory management', 'online booking', 'e-commerce'],
        'missions': ["concevoir et développer des API REST", "modéliser la base de données et optimiser les requêtes",
                     "développer les modules métier de notre plateforme web", "écrire des tests automatisés et documenter le code"],
    },
    'web_frontend': {
        'filiere': 'Génie Logiciel',
        'skills': ['React', 'JavaScript', 'TypeScript', 'HTML', 'CSS', 'Angular', 'Vue.js', 'Tailwind', 'Figma', 'Git'],
        'titres': ['Développeur frontend React', 'Intégrateur web', 'Développeur JavaScript'],
        'themes_fr': ['de suivi de commandes', 'de e-learning', 'de tableau de bord'],
        'themes_en': ['order tracking', 'e-learning', 'dashboard'],
        'missions': ["développer des interfaces web réactives", "intégrer les maquettes en composants réutilisables",
                     "améliorer les performances et l'accessibilité du site", "connecter l'interface aux API du backend"],
    },
    'data_science': {
        'filiere': 'Data Science',
        'skills': ['Python', 'pandas', 'scikit-learn', 'TensorFlow', 'PyTorch', 'NLP', 'SQL', 'Jupyter', 'Matplotlib', 'Statistiques'],
        'titres': ['Stagiaire data scientist', 'Ingénieur machine learning', 'Chargé de modélisation prédictive'],
        'themes_fr': ['de détection de fraude', 'de prédiction de churn', "d'analyse de sentiments"],
        'themes_en': ['fraud detection', 'churn prediction', 'sentiment analysis'],
        'missions': ["explorer les données et construire des modèles prédictifs", "entraîner et évaluer des modèles de classification",
                     "mettre en place un pipeline de traitement du langage", "documenter les expériences dans des notebooks"],
    },
    'data_analyst_bi': {
        'filiere': 'Informatique de Gestion',
        'skills': ['Power BI', 'SQL', 'Excel', 'Tableau', 'ETL', 'Talend', 'Data warehouse', 'DAX', 'Python', 'Reporting'],
        'titres': ['Data analyst BI', 'Développeur décisionnel', 'Analyste reporting'],
        'themes_fr': ['de suivi des ventes', 'de pilotage financier', 'de suivi RH'],
        'themes_en': ['sales monitoring', 'financial reporting', 'HR analytics'],
        'missions': ["construire des tableaux de bord pour la direction", "alimenter l'entrepôt de données avec des flux ETL",
                     "automatiser le reporting mensuel", "définir les indicateurs de performance avec les métiers"],
    },
    'reseaux_securite': {
        'filiere': 'Réseaux et Sécurité',
        'skills': ['Cisco', 'Linux', 'Pentest', 'Firewall', 'VPN', 'Wireshark', 'Kali Linux', 'SIEM', 'Bash', 'TCP/IP'],
        'titres': ['Stagiaire sécurité informatique', 'Administrateur réseau', 'Analyste SOC'],
        'themes_fr': ["de supervision réseau", "d'audit de sécurité", 'de segmentation par VLAN'],
        'themes_en': ['network monitoring', 'security audit', 'VLAN segmentation'],
        'missions': ["réaliser des audits de sécurité et des tests d'intrusion", "configurer et superviser les équipements réseau",
                     "analyser les alertes de sécurité", "renforcer la configuration des pare-feu et des accès distants"],
    },
    'embarque_iot': {
        'filiere': 'Systèmes Embarqués',
        'skills': ['C', 'C++', 'Arduino', 'STM32', 'Raspberry Pi', 'MQTT', 'FreeRTOS', 'I2C', 'Capteurs', 'Python'],
        'titres': ['Ingénieur systèmes embarqués', 'Développeur IoT', 'Stagiaire électronique embarquée'],
        'themes_fr': ['de monitoring industriel', "d'irrigation intelligente", 'de suivi de température'],
        'themes_en': ['industrial monitoring', 'smart irrigation', 'temperature tracking'],
        'missions': ["programmer le firmware d'une carte à microcontrôleur", "connecter des capteurs et transmettre les mesures",
                     "développer une passerelle IoT communiquant en MQTT", "tester le système sur banc réel"],
    },
    'devops_cloud': {
        'filiere': 'Génie Logiciel',
        'skills': ['Docker', 'Kubernetes', 'GitLab CI', 'Jenkins', 'Terraform', 'AWS', 'Linux', 'Ansible', 'Prometheus', 'Bash'],
        'titres': ['Stagiaire DevOps', 'Ingénieur cloud', 'Responsable automatisation CI/CD'],
        'themes_fr': ['de déploiement continu', "d'infrastructure as code", 'de supervision applicative'],
        'themes_en': ['continuous deployment', 'infrastructure as code', 'application monitoring'],
        'missions': ["automatiser la chaîne d'intégration et de déploiement", "conteneuriser les applications et gérer leur orchestration",
                     "décrire l'infrastructure sous forme de code", "mettre en place la supervision et les alertes"],
    },
    'mobile': {
        'filiere': 'Génie Logiciel',
        'skills': ['Flutter', 'Dart', 'Kotlin', 'Android', 'Swift', 'Firebase', 'React Native', 'REST API', 'Git', 'UI/UX'],
        'titres': ['Développeur mobile Flutter', 'Développeur Android', 'Stagiaire applications mobiles'],
        'themes_fr': ['de livraison', 'de suivi sportif', 'de paiement mobile'],
        'themes_en': ['delivery', 'fitness tracking', 'mobile payment'],
        'missions': ["développer une application mobile multiplateforme", "consommer des API et gérer le mode hors ligne",
                     "publier l'application sur les stores", "soigner l'expérience utilisateur sur mobile"],
    },
}

# Paraphrases : comment un étudiant peut écrire une compétence sans la nommer.
PARAPHRASES = {
    'Django': ['framework web Python'], 'FastAPI': ['framework Python asynchrone pour API'],
    'PostgreSQL': ['base de données relationnelle'], 'SQL': ['interrogation de bases de données'],
    'REST API': ['services web', 'interfaces de programmation'], 'Docker': ['conteneurisation'],
    'Redis': ['cache en mémoire'], 'React': ["bibliothèque JavaScript pour interfaces"],
    'Angular': ["framework JavaScript de Google"], 'Tailwind': ['framework CSS utilitaire'],
    'Figma': ['maquettage'], 'scikit-learn': ['apprentissage automatique classique'],
    'TensorFlow': ['réseaux de neurones'], 'PyTorch': ['deep learning'],
    'NLP': ['traitement du langage naturel'], 'pandas': ['manipulation de données tabulaires'],
    'Statistiques': ['analyse statistique'], 'Power BI': ['tableaux de bord décisionnels'],
    'ETL': ["alimentation d'entrepôt de données"], 'Data warehouse': ['entrepôt de données'],
    'Reporting': ['production de rapports'], 'Pentest': ["tests d'intrusion"],
    'Firewall': ['pare-feu'], 'VPN': ['accès distant sécurisé'], 'SIEM': ["corrélation d'événements de sécurité"],
    'Cisco': ['équipements réseau'], 'Wireshark': ['analyse de trames réseau'],
    'MQTT': ['protocole de messagerie IoT'], 'Arduino': ['microcontrôleurs'], 'STM32': ['cartes à microcontrôleur ARM'],
    'FreeRTOS': ['système temps réel'], 'Capteurs': ['acquisition de mesures'],
    'Kubernetes': ['orchestration de conteneurs'], 'GitLab CI': ['intégration continue'],
    'Jenkins': ['automatisation de builds'], 'Terraform': ['infrastructure as code'],
    'AWS': ['cloud public'], 'Ansible': ['automatisation de configuration'],
    'Prometheus': ['supervision de métriques'], 'Linux': ['administration système'],
    'Flutter': ['applications mobiles multiplateformes'], 'Kotlin': ['développement Android natif'],
    'Swift': ['développement iOS'], 'Firebase': ['backend mobile hébergé'], 'UI/UX': ["conception d'interfaces"],
}

NIVEAUX = ['Licence 3', 'Master 1', 'Master 2', 'Ingénieur 3']
ENTREPRISES = ['Vermeg', 'Sofrecom Tunisie', 'Telnet', 'Focus Corporation', 'Proxym', 'Ooredoo', 'Sagemcom',
               'InstaDeep', 'Business & Decision', 'Wevioo', 'Poulina Group', 'Delice Holding']
GENERIC_SKILLS = ['Travail en équipe', 'Communication', 'Gestion de projet', 'Anglais technique']


def phrase_competence(rng, skill, p_paraphrase=0.4):
    """Écrit une compétence telle quelle, ou par une paraphrase si elle en a une."""
    if skill in PARAPHRASES and rng.random() < p_paraphrase:
        return rng.choice(PARAPHRASES[skill])
    return skill


def pick_skills(rng, domaine, k):
    return rng.sample(DOMAINES[domaine]['skills'], k=min(k, len(DOMAINES[domaine]['skills'])))


# ---------------------------------------------------------------------------
# CV
# ---------------------------------------------------------------------------
def make_cv(rng, cv_id, domaines):
    d1 = rng.choice(domaines)
    vague = rng.random() < 0.10
    d2 = None
    if not vague and rng.random() < 0.30:
        d2 = rng.choice([d for d in domaines if d != d1])
    english = rng.random() < 0.15
    niveau = rng.choice(NIVEAUX)
    filiere = DOMAINES[d1]['filiere']

    skills = pick_skills(rng, d1, 2 if vague else rng.randint(5, 7))
    if d2:
        skills += [s for s in pick_skills(rng, d2, 3) if s not in skills]
    noise = [s for s in rng.sample(DOMAINES[rng.choice([d for d in domaines if d not in (d1, d2)])]['skills'], 2)
             if s not in skills]
    skills += noise[:1]  # un peu de bruit : compétence hors domaine

    ecrites = [phrase_competence(rng, s) for s in skills]

    projets = []
    for dom in [d1] + ([d2] if d2 else []):
        if vague:
            break
        sk = pick_skills(rng, dom, 3)
        e = [phrase_competence(rng, s, 0.5) for s in sk]
        if english:
            theme = rng.choice(DOMAINES[dom]['themes_en'])
            projets.append(f"Project: built a {theme} application using {e[0]} and {e[1]}, tested with {e[2]}.")
        else:
            theme = rng.choice(DOMAINES[dom]['themes_fr'])
            projets.append(f"Projet : réalisation d'une application {theme} avec {e[0]} et {e[1]}, validée avec {e[2]}.")

    if english:
        lignes = [f"Profile: {niveau} student in {filiere}, looking for an internship or end-of-studies project.",
                  "Skills: " + ', '.join(ecrites) + '.']
        if vague:
            lignes.append("Motivated, quick learner, team player.")
        lignes += projets
        lignes.append("Languages: Arabic (native), French (fluent), English (good).")
    else:
        lignes = [f"Profil : étudiant(e) en {niveau}, filière {filiere}, à la recherche d'un stage ou d'un PFE.",
                  "Compétences : " + ', '.join(ecrites) + '.']
        if vague:
            lignes.append("Motivé(e), sérieux(se), capacité d'adaptation et esprit d'équipe.")
        lignes += projets
        lignes.append("Langues : arabe (langue maternelle), français (courant), anglais (bon niveau).")

    return {
        'cv_id': f'cv{cv_id:04d}', 'filiere': filiere, 'niveau': niveau,
        'langue': 'en' if english else 'fr',
        'competences': ', '.join(skills),
        'texte': '\n'.join(lignes),
        'domaine': d1 + (f'+{d2}' if d2 else ''),
    }


# ---------------------------------------------------------------------------
# Offres
# ---------------------------------------------------------------------------
def make_offre(rng, offre_id, domaine):
    info = DOMAINES[domaine]
    requis = pick_skills(rng, domaine, rng.randint(4, 6))
    ecrites = [phrase_competence(rng, s, 0.3) for s in requis]
    missions = rng.sample(info['missions'], k=2)
    type_ = rng.choice(['PFE', 'PFE', 'STAGE'])
    duree = '6 mois' if type_ == 'PFE' else rng.choice(['1 mois', '2 mois', '3 mois'])
    entreprise = rng.choice(ENTREPRISES)
    description = (f"{entreprise} propose un {'PFE' if type_ == 'PFE' else 'stage'} de {duree}. "
                   f"Vos missions : {missions[0]}, puis {missions[1]}. "
                   f"Environnement technique : {', '.join(ecrites)}. "
                   f"Profil recherché : étudiant(e) en {rng.choice(NIVEAUX)}, rigoureux(se) et autonome.")
    return {
        'offre_id': f'off{offre_id:03d}', 'titre': rng.choice(info['titres']), 'type': type_,
        'filiere': info['filiere'], 'duree': duree,
        'competences_requises': ', '.join(requis),
        'description': description, 'domaine': domaine,
    }


# ---------------------------------------------------------------------------
# Vérité terrain
# ---------------------------------------------------------------------------
def relevance(cv, offre):
    cv_domaines = cv['domaine'].split('+')
    common = set(cv['competences'].split(', ')) & set(offre['competences_requises'].split(', '))
    if offre['domaine'] == cv_domaines[0]:
        return (2 if len(common) >= 3 else 1), len(common)
    if offre['domaine'] in cv_domaines[1:]:
        return 1, len(common)
    return 0, len(common)


def write_csv(path, rows, fields):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cvs', type=int, default=200)
    ap.add_argument('--offres', type=int, default=60)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--out', default='matching_data')
    a = ap.parse_args()

    rng = random.Random(a.seed)
    domaines = list(DOMAINES)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    cvs = [make_cv(rng, i + 1, domaines) for i in range(a.cvs)]
    offres = [make_offre(rng, i + 1, domaines[i % len(domaines)]) for i in range(a.offres)]  # domaines équilibrés
    pairs, stats = [], {0: 0, 1: 0, 2: 0}
    for cv in cvs:
        for off in offres:
            rel, n_common = relevance(cv, off)
            stats[rel] += 1
            pairs.append({'cv_id': cv['cv_id'], 'offre_id': off['offre_id'], 'relevance': rel,
                          'competences_communes': n_common})

    write_csv(out / 'cvs.csv', cvs, ['cv_id', 'filiere', 'niveau', 'langue', 'competences', 'texte', 'domaine'])
    write_csv(out / 'offres.csv', offres, ['offre_id', 'titre', 'type', 'filiere', 'duree',
                                           'competences_requises', 'description', 'domaine'])
    write_csv(out / 'pairs.csv', pairs, ['cv_id', 'offre_id', 'relevance', 'competences_communes'])

    print(f'{len(cvs)} CV, {len(offres)} offres, {len(pairs)} couples écrits dans {out}/')
    print(f'Pertinence : 2 (fort) = {stats[2]}, 1 (partiel) = {stats[1]}, 0 (aucun) = {stats[0]}')


if __name__ == '__main__':
    main()
