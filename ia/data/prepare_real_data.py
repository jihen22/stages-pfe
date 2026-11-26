"""Prépare un jeu de données « réel » pour le matching CV <-> offre.

Entrées (à télécharger toi-même sur Kaggle) :
    --resumes   Resume.csv     « Resume Dataset » de Snehaan Bhawal
                               (colonnes attendues : une colonne de texte et « Category »)
    --postings  postings.csv   « LinkedIn Job Postings » de arshkon
                               (colonnes attendues : « title » et « description »)

Sortie : le MÊME format que generate_matching_data.py, donc ton notebook marche
sans changement (il suffit de changer le dossier) :
    cvs.csv     cv_id, langue, texte, domaine
    offres.csv  offre_id, titre, description, domaine
    pairs.csv   cv_id, offre_id, relevance   (2 = même catégorie, 1 = catégories proches, 0 = autre)

Usage :
    python prepare_real_data.py --resumes Resume.csv --postings postings.csv --out real_data

ATTENTION : ces étiquettes sont FAIBLES. Aucun humain n'a dit « ce CV correspond à
cette offre ». On suppose qu'un CV de catégorie X correspond à une offre dont le titre
relève de la catégorie X. La catégorie de l'offre est déduite du titre par des règles
simples (TITLE_RULES ci-dessous) : elles se trompent parfois. Dans ton rapport, appelle
ça « évaluation sur données réelles à étiquettes faibles ».
"""

import argparse
import html
import re
import sys
from pathlib import Path

import pandas as pd

RESUME_TEXT_COLS = ['Resume_str', 'resume_str', 'Resume', 'resume', 'Text', 'text']
RESUME_CAT_COLS = ['Category', 'category']
RESUME_ID_COLS = ['ID', 'id', 'Id']
JOB_TITLE_COLS = ['title', 'Title', 'job_title']
JOB_DESC_COLS = ['description', 'Description', 'job_description']
JOB_ID_COLS = ['job_id', 'id', 'ID']

# Règles titre d'offre -> catégorie de CV. L'ORDRE COMPTE : la première règle qui
# correspond gagne, donc les règles précises sont avant les règles générales.
TITLE_RULES = [
    ('ACCOUNTANT', r'accountant|accounting|bookkeep|\bauditor\b'),
    ('BANKING', r'\bbank|\bteller\b|loan officer|mortgage'),
    ('FINANCE', r'financ|treasury|\bcfo\b'),
    ('HR', r'\bhr\b|human resources|recruit|talent acquisition|payroll'),
    ('HEALTHCARE', r'\bnurse|\brn\b|physician|medical|clinical|therapist|pharmac|health ?care|dental|caregiver'),
    ('TEACHER', r'teacher|instructor|professor|tutor|educator|teaching'),
    ('ADVOCATE', r'attorney|lawyer|paralegal|legal counsel|\blegal\b|advocate'),
    ('CHEF', r'\bchef\b|\bcook\b|sous chef|kitchen'),
    ('FITNESS', r'fitness|personal trainer|\bgym\b|yoga'),
    ('AVIATION', r'\bpilot\b|aviation|aircraft|airline|flight'),
    ('AUTOMOBILE', r'automotive|auto mechanic|automobile|vehicle technician'),
    ('AGRICULTURE', r'agricultur|\bfarm|agronom|livestock'),
    ('CONSTRUCTION', r'construction|site supervisor|carpenter|electrician|plumber|foreman'),
    ('BUSINESS-DEVELOPMENT', r'business development'),
    ('CONSULTANT', r'consultant'),
    ('BPO', r'customer service|call cent(er|re)|customer support|\bbpo\b'),
    ('SALES', r'\bsales\b|account executive'),
    ('PUBLIC-RELATIONS', r'public relations|communications|\bpr\b'),
    ('DIGITAL-MEDIA', r'digital marketing|social media|content (creator|writer|manager)|\bseo\b|video editor'),
    ('DESIGNER', r'designer|graphic design|\bux\b|\bui\b'),
    ('ARTS', r'\bartist\b|illustrat|animator|curator'),
    ('APPAREL', r'apparel|fashion|garment|textile'),
    ('INFORMATION-TECHNOLOGY',
     r'software|developer|devops|data (scientist|engineer|analyst)|\bit\b|network|systems? admin|cyber|'
     r'security analyst|programmer|\bweb\b|database|cloud|machine learning'),
    ('ENGINEERING', r'engineer'),
]

# Groupes de catégories voisines : pertinence 1 au lieu de 0.
RELATED_GROUPS = [
    {'ACCOUNTANT', 'FINANCE', 'BANKING'},
    {'INFORMATION-TECHNOLOGY', 'ENGINEERING'},
    {'SALES', 'BUSINESS-DEVELOPMENT', 'BPO'},
    {'DIGITAL-MEDIA', 'PUBLIC-RELATIONS', 'DESIGNER', 'ARTS'},
    {'HEALTHCARE', 'FITNESS'},
    {'CONSTRUCTION', 'ENGINEERING'},
    {'AUTOMOBILE', 'ENGINEERING'},
]


def find_col(df_cols, candidates, what, required=True):
    for c in candidates:
        if c in df_cols:
            return c
    if required:
        sys.exit(f"Colonne introuvable pour « {what} ». Colonnes présentes : {list(df_cols)}\n"
                 f"Adapte la liste de candidats en haut du script.")
    return None


def clean(text, max_chars):
    text = html.unescape(str(text))
    text = re.sub(r'<[^>]+>', ' ', text)        # enlève un éventuel HTML
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(' ', 1)[0]  # coupe proprement sur un mot
    return text


def title_to_category(title):
    t = str(title).lower()
    for cat, pattern in TITLE_RULES:
        if re.search(pattern, t):
            return cat
    return None


def relevance(cv_cat, job_cat):
    if cv_cat == job_cat:
        return 2
    if any(cv_cat in g and job_cat in g for g in RELATED_GROUPS):
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--resumes', required=True, help='chemin de Resume.csv')
    ap.add_argument('--postings', required=True, help='chemin de postings.csv')
    ap.add_argument('--out', default='real_data')
    ap.add_argument('--per-category', type=int, default=30, help='CV max par catégorie (défaut 30)')
    ap.add_argument('--jobs-per-category', type=int, default=10, help='offres max par catégorie (défaut 10)')
    ap.add_argument('--max-chars', type=int, default=3000, help='longueur max des textes (défaut 3000)')
    ap.add_argument('--seed', type=int, default=42)
    a = ap.parse_args()

    # --- CV ---------------------------------------------------------------
    header = pd.read_csv(a.resumes, nrows=0).columns
    c_text = find_col(header, RESUME_TEXT_COLS, 'texte du CV')
    c_cat = find_col(header, RESUME_CAT_COLS, 'catégorie du CV')
    c_id = find_col(header, RESUME_ID_COLS, 'identifiant du CV', required=False)
    resumes = pd.read_csv(a.resumes, usecols=[c for c in (c_id, c_text, c_cat) if c])
    resumes = resumes.dropna(subset=[c_text, c_cat])
    resumes['domaine'] = resumes[c_cat].astype(str).str.upper().str.strip()
    print(f"{len(resumes)} CV lus, {resumes['domaine'].nunique()} catégories")

    # --- Offres -----------------------------------------------------------
    header = pd.read_csv(a.postings, nrows=0).columns
    c_title = find_col(header, JOB_TITLE_COLS, "titre de l'offre")
    c_desc = find_col(header, JOB_DESC_COLS, "description de l'offre")
    c_jid = find_col(header, JOB_ID_COLS, "identifiant de l'offre", required=False)
    jobs = pd.read_csv(a.postings, usecols=[c for c in (c_jid, c_title, c_desc) if c])
    jobs = jobs.dropna(subset=[c_title, c_desc])
    jobs['domaine'] = jobs[c_title].map(title_to_category)
    n_all = len(jobs)
    jobs = jobs.dropna(subset=['domaine'])
    print(f"{n_all} offres lues, {len(jobs)} rattachées à une catégorie par les règles de titre")

    # --- Échantillonnage équilibré sur les catégories communes ------------
    communes = sorted(set(resumes['domaine']) & set(jobs['domaine']))
    sans_offre = sorted(set(resumes['domaine']) - set(jobs['domaine']))
    if not communes:
        sys.exit("Aucune catégorie commune entre CV et offres. Vérifie les fichiers et TITLE_RULES.")
    if sans_offre:
        print(f"Catégories de CV sans aucune offre (ignorées) : {', '.join(sans_offre)}")

    cv_parts, job_parts = [], []
    for cat in communes:
        r = resumes[resumes['domaine'] == cat]
        j = jobs[jobs['domaine'] == cat]
        cv_parts.append(r.sample(n=min(a.per_category, len(r)), random_state=a.seed))
        job_parts.append(j.sample(n=min(a.jobs_per_category, len(j)), random_state=a.seed))
    cvs = pd.concat(cv_parts).reset_index(drop=True)
    jobs = pd.concat(job_parts).reset_index(drop=True)

    cvs_out = pd.DataFrame({
        'cv_id': [f'rcv{i + 1:04d}' for i in range(len(cvs))],
        'langue': 'en',
        'texte': cvs[c_text].map(lambda t: clean(t, a.max_chars)),
        'domaine': cvs['domaine'],
    })
    jobs_out = pd.DataFrame({
        'offre_id': [f'roff{i + 1:04d}' for i in range(len(jobs))],
        'titre': jobs[c_title].astype(str).str.strip(),
        'description': jobs[c_desc].map(lambda t: clean(t, a.max_chars)),
        'domaine': jobs['domaine'],
    })

    pairs = [{'cv_id': cv.cv_id, 'offre_id': off.offre_id, 'relevance': relevance(cv.domaine, off.domaine)}
             for cv in cvs_out.itertuples() for off in jobs_out.itertuples()]
    pairs_out = pd.DataFrame(pairs)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cvs_out.to_csv(out / 'cvs.csv', index=False, encoding='utf-8')
    jobs_out.to_csv(out / 'offres.csv', index=False, encoding='utf-8')
    pairs_out.to_csv(out / 'pairs.csv', index=False, encoding='utf-8')

    counts = pairs_out['relevance'].value_counts().to_dict()
    print(f"\n{len(cvs_out)} CV, {len(jobs_out)} offres, {len(pairs_out)} couples écrits dans {out}/")
    print(f"Catégories gardées ({len(communes)}) : {', '.join(communes)}")
    print(f"Pertinence : 2 = {counts.get(2, 0)}, 1 = {counts.get(1, 0)}, 0 = {counts.get(0, 0)}")


if __name__ == '__main__':
    main()