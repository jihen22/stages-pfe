# Progress: backlog status

Audit date: 2026-11-28. Last update: item 10 done (2026-11-28).
Rules: CLAUDE.md and BACKLOG.md as of this date (items 1–39, 168 jours-homme, SQLite, no Docker).
Method: I read the code only and changed nothing.

## Tests

`python manage.py test` → **Ran 174 tests, OK** (0 failures, 0 errors).

| App | Tests |
|---|---|
| accounts | 38 |
| pfe | 87 (30 in `tests.py` + 27 in `test_workflow.py` + 11 in `test_charge.py` + 19 in `test_suggestion.py`) |
| soutenances | 17 |
| notifications | 10 |
| candidatures | 3 |
| offres | 19 |

## Definition of done (CLAUDE.md)

1. Models + migrations · 2. Views, URLs, templates · 3. Access limited to the right role(s) · 4. Responsive (Bootstrap) · 5. At least one automated test covers the main case.

Shared proof for criteria 3 and 4, which every item below relies on:
- Roles: `accounts/mixins.py` (`RoleRequiredMixin`, `role_required`)
- Bootstrap 5.3.3: `templates/base.html:13`

For criterion 5, a test only counts when it checks the item's main behaviour. A test that only checks the page loads does not count.

## Jours-homme

| | Done | Total | % |
|---|---|---|---|
| All items | **40 j** | 168 j | **23.8 %** |
| Non-AI items | **40 j** | 107 j | **37.4 %** |

DONE items: 1 (5 j) + 3 (3 j) + 4 (2 j) + 5 (3 j) + 6 (4 j) + 7 (4 j) + 8 (2 j) + 10 (6 j) + 13 (3 j) + 14 (6 j) + 16 (2 j) = 40 j.
PARTIAL items count for 0 j.

## Summary

| Status | Count | Items |
|---|---|---|
| DONE | 11 | 1, 3, 4, 5, 6, 7, 8, 10, 13, 14, 16 |
| PARTIAL | 8 | 2, 12, 19, 21, 22, 35, 36, 38 |
| NOT STARTED | 20 | 9, 11, 15, 17, 18, 20, 23, 24–34, 37, 39 |
| **Total** | **39** | |

## Detail per item

| ID | Item (short) | j | Type | Status | Proof (files) | What's missing |
|---|---|---|---|---|---|---|
| 1 | Sign up / log in by role | 5 | Web | **DONE** | `accounts/models.py` (`User.role`, `get_dashboard_url`), `accounts/forms.py` (`StudentRegistrationForm`, `EncadrantProRegistrationForm`), `accounts/views.py:29-64` (login → role dashboard, student sign-up, company-supervisor sign-up), `accounts/urls.py`, `templates/accounts/login.html`, `register.html`. Tests: `accounts/tests.py:375-454` (`RegistrationTests`, 8 tests: sign-up then login for both roles, no role escalation, password mismatch, unique username, required company fields, wrong password) and `accounts/tests.py:121-138` (login redirect by role) | — Academic supervisors, admin and jury have no self sign-up by design: the admin creates them (Django admin or `create_demo_users`). |
| 2 | View / edit my profile | 2 | Web | PARTIAL | Student: `accounts/models.py:90-140`, `accounts/views.py:209-221`, tests `accounts/tests.py:249-283`. Company supervisor: `accounts/models.py:150-182`, `accounts/views.py:158-206`, `templates/accounts/profil_encadrant_pro.html` | Academic supervisor, admin and jury can only pick theme/accent (`accounts/views.py:140-148`). They cannot edit their name, email or password. No test for the company-supervisor profile form. |
| 3 | Company supervisor publishes an offer | 3 | Web | **DONE** | `offres/models.py`, `offres/migrations/0001_initial.py`, `offres/views.py:73-133`, `offres/urls.py`, `templates/offres/offre_form.html`, `mes_offres.html`, test `candidatures/tests.py:34-50` | Publication goes through approval, see item 4. |
| 4 | Academic supervisor approves offers in their field | 2 | Web | **DONE** | Field: `Domaine` choices + `User.domaine` (`accounts/models.py:9-16, 58-64`, migration `accounts/migrations/0007_user_domaine.py`), `Offre.domaine` (`offres/models.py:31-37`, migration `offres/migrations/0002_offre_domaine.py`), required in `offres/forms.py`. Approval: `offres/views.py:141-192` (`offres_a_valider_pour`, queue + approve + refuse limited to `ENCADRANT_ACAD`, own field only, owner notified). Screens: `templates/offres/offres_a_valider.html`, `_sidebar.html`, `dashboards/encadrant_acad.html`. Tests: `offres/tests.py` (9 tests), `accounts/tests.py:25-66`, `candidatures/tests.py:34-60` | Offers created before this change have no field: every academic supervisor sees them. A supervisor's field is set in the Django admin (their own profile page can't edit it yet, see item 2). |
| 5 | Student searches / views offers | 3 | Web | **DONE** | `offres/views.py:22-72` (`OffreListView`: published offers only, search `q` on title/description/skills, `type` filter, pagination by 9; `OffreDetailView`: published offers only, « déjà postulé » flag), `templates/offres/offre_list.html`, `offre_detail.html`. Tests: `offres/tests.py:125-209` (`OffreSearchTests`, 10 tests: search by each field, type filter + search, pagination keeps the search, URL-encoded search, detail page, unpublished offers return 404, student only) | — |
| 6 | Apply with CV + cover letter | 4 | Web | **DONE** | `candidatures/models.py` (CV, letter, unique student+offer), `candidatures/migrations/0001_initial.py`, `candidatures/views.py:32-69`, `templates/candidatures/candidature_form.html`, tests `candidatures/tests.py:58-100` | — |
| 7 | Track my application + notifications | 4 | Web | **DONE** | `candidatures/views.py:20-29, 98-125`, `templates/candidatures/mes_candidatures.html`, `notifications/models.py`, `notifications/services.py`, `notifications/views.py`, `notifications/context_processors.py`, tests `notifications/tests.py:38-130` | In-app notifications only, no email (not required). |
| 8 | Company supervisor sees applications received | 2 | Web | **DONE** | `candidatures/views.py:76-125` (list, filter by offer, accept/refuse), `templates/candidatures/candidatures_recues.html`, tests `candidatures/tests.py:76-81`, `notifications/tests.py:71-90` | — |
| 9 | Anonymised data collection for AI | 3 | AI | NOT STARTED | No `ia` app in `INSTALLED_APPS` (`crud/settings.py:28-42`). | Everything. |
| 10 | Academic supervisor assigns a PFE (+ suggestion by field/workload) | 6 | Mixed | **DONE** | Project field: `ProjetPFE.domaine` (`pfe/models.py:45-51`, migrations `pfe/migrations/0004_projetpfe_domaine.py` + `0005_domaine_depuis_offre.py`), required when a student declares a project (`pfe/forms.py`), copied from the offer for an accepted application (`pfe/views.py:96`). Suggestion: `pfe/suggestion.py` (`suggerer_encadrants`: same field + free places, score /100 with reasons; `raison_refus`; **empty AI hook `ajuster_par_ia`**). Rules: field + capacity enforced in the `affecter` guard (`pfe/workflow.py:37`) and in the creation form (`ProjetEncadrantForm.clean`, offers limited to the supervisor's field). Screen: `pfe/views.py:220-254`, `templates/pfe/affectations.html` (field, suggested supervisors with scores and reasons, « Suggéré pour vous » first, locked button with reason, capacity / missing-field alerts). Tests: `pfe/test_suggestion.py` (19 tests) | AI part (re-ranking, explanations) waits for the `ia` app: items 24–27 plug into `ajuster_par_ia`. |
| 11 | Discussion space between student and supervisor | 4 | Web | NOT STARTED | No message/thread model. `Livrable.commentaire_encadrant` (`pfe/models.py:81`) is a one-way comment on a deliverable. | Everything. |
| 12 | Upload deliverables with version history | 4 | Web | PARTIAL | `pfe/models.py:58-90` (`Livrable`), `pfe/views.py:108-134`, `templates/pfe/deposer_livrable.html`, `mon_pfe.html`, tests `pfe/tests.py:154-185` | No version history: no version number and no link between successive uploads of the same deliverable. |
| 13 | Approve a deliverable / ask for a correction | 3 | Web | **DONE** | `pfe/views.py:19-53, 153-190`, `pfe/urls.py`, `templates/pfe/livrables_a_valider.html`, tests `pfe/tests.py:187-233` | — |
| 14 | PFE lifecycle state machine | 6 | Web | **DONE** | States `EN_ATTENTE → EN_COURS → TERMINE → PLANIFIE → SOUTENU` (`pfe/models.py:10-17`), initial state + history on creation (`pfe/models.py:61-72`), `HistoriqueStatut` (`pfe/models.py:86-113`), migrations `pfe/migrations/0002_cycle_de_vie.py` and `0003_statuts_existants.py` (converts existing projects). Transitions, guards and atomic conditional update: `pfe/workflow.py` (`TRANSITIONS`, `appliquer`, `peut`). Wired into: claim/release (`pfe/views.py:240, 265`), finish/reopen (`pfe/views.py:311-349`, academic supervisor only), upload closed after « terminé » (`pfe/views.py:116`), scheduling only of finished projects (`soutenances/forms.py:38-42`, `soutenances/views.py:208`), grading only once planned and auto « soutenu » after the last grade (`soutenances/views.py:35-50, 136`). Screens: stepper + history in `templates/pfe/mon_pfe.html`, buttons in `templates/pfe/mes_etudiants.html`. Tests: `pfe/test_workflow.py` (27 tests) | — (status is read-only in the Django admin on purpose: it only changes through `pfe/workflow.py`). |
| 15 | Company supervisor follows progress + evaluates the internship | 3 | Web | NOT STARTED | `accounts/views.py:98-109`: the dashboard only counts offers/applications. No view on `ProjetPFE` for this role, no evaluation model. | Everything. |
| 16 | Academic supervisor sees their workload | 2 | Web | **DONE** | Capacity: `User.capacite_encadrement` (`accounts/models.py:66-71`, migration `accounts/migrations/0008_user_capacite_encadrement.py`, editable in the Django admin). Workload service: `pfe/charge.py` (`charge_encadrant`, `annoter_charge` for item 10, `niveau`). Page: `pfe/views.py:168` (`ma_charge`, academic supervisor only), URL `pfe:ma_charge`, `templates/pfe/ma_charge.html` (gauge vs capacity, overload alert, breakdown by status, deliverables to review / in correction, per-student follow-up, upcoming defenses). Also on `templates/accounts/dashboards/encadrant_acad.html` and in the sidebar. Tests: `pfe/test_charge.py` (11 tests) | — (capacity is set by the admin; the supervisor only reads it). |
| 17 | Admin generates documents (agreement, certificate, minutes) | 5 | Web | NOT STARTED | No document model, no PDF library in `requirements.txt` (only `Django==5.2.18`). The wording only appears in marketing text, `templates/home.html:165`. | Everything. |
| 18 | Company supervisor approves the generated agreement | 2 | Web | NOT STARTED | Depends on 17. No agreement model. | Everything. |
| 19 | Plan defenses (juries, rooms, time slots) | 6 | Web | PARTIAL | `soutenances/models.py:6-41`, `soutenances/migrations/0001_initial.py`, `soutenances/views.py:152-196`, `soutenances/forms.py:11-48`, `templates/soutenances/planning.html`, `planifier.html`, tests `soutenances/tests.py:190-240` | Room is free text (no `Salle` model). No time slots (a single `DateTimeField`, no duration). |
| 20 | Detect / fix scheduling conflicts | 5 | Web | NOT STARTED | `SoutenanceForm` (`soutenances/forms.py:11-48`) has no overlap check for room, jury or time. Only "one defense per project" is blocked (`soutenances/views.py:176`). | Everything. |
| 21 | Jury: notice, schedule, reports, grades | 5 | Web | PARTIAL | Schedule: `soutenances/views.py:49-75`, `templates/soutenances/mes_soutenances.html`. Grades: `soutenances/models.py:44-73`, `soutenances/views.py:78-149`, `saisir_note.html`. Tests `soutenances/tests.py:128-188` | No notice (nothing to view/download). The jury cannot open the student's reports (no link to `Livrable` in `templates/soutenances/`). |
| 22 | Student: defense schedule + notice | 2 | Web | PARTIAL | `soutenances/views.py:33-46`, `templates/soutenances/ma_soutenance.html` (date, room, jury, average), tests `soutenances/tests.py:113-126` | No notice document. |
| 23 | Log of critical actions | 3 | Web | NOT STARTED | No log/audit model. Django admin's `LogEntry` does not track the app's views. | Everything. |
| 24 | Standalone async AI service | 5 | AI | NOT STARTED | No `ia` app, no async worker. | Everything. |
| 25 | Extract skills from CVs + embeddings | 5 | AI | NOT STARTED | No code. | Everything. |
| 26 | CV–offer match score shown to the student | 8 | Mixed | NOT STARTED | No score field or score display. | Everything (web part + AI part). |
| 27 | Explanation + confidence score | 4 | AI | NOT STARTED | No code. | Everything. |
| 28 | Rank applications by relevance | 3 | AI | NOT STARTED | No code. `candidatures/views.py:81-89` sorts by date. | Everything. |
| 29 | Recommend offers to the student | 4 | AI | NOT STARTED | No code. Only advertised in `templates/home.html:298`. | Everything. |
| 30 | Report similarity | 8 | AI | NOT STARTED | No code. Only advertised in `templates/home.html:311`. | Everything. |
| 31 | Risk indicator (delay/difficulty) | 8 | AI | NOT STARTED | No code. | Everything. |
| 32 | Detect unusual applications | 6 | AI | NOT STARTED | No code. | Everything. |
| 33 | Log model versions | 3 | AI | NOT STARTED | No code. | Everything. |
| 34 | Data quality / privacy for models | 4 | AI | NOT STARTED | No code. | Everything. |
| 35 | Admin analytics dashboards (+ predictive indicators) | 6 | Mixed | PARTIAL | `accounts/views.py:120-128` (4 counters), `templates/accounts/dashboards/admin.html` | No real analytics (trends, breakdowns, charts). No empty extension point for predictive indicators. Only a "page loads" test (`accounts/tests.py:98`). |
| 36 | Fast, stable app (integration tests, optimisation, bug fixes) | 6 | Web | PARTIAL | 174 passing tests, including a full workflow test (`candidatures/tests.py:34-81`) and role-access tests in every app. `select_related`/`prefetch_related` in the views. | No integration test across the whole chain (offer → PFE → deliverable → defense → grade). No performance check. |
| 37 | Stable production URL | 5 | Web | NOT STARTED | `crud/settings.py` is in development mode only (DEBUG, no `ALLOWED_HOSTS`/static config for production). No deployment files. | Everything. |
| 38 | Technical docs + user manual | 4 | Web | PARTIAL | `README.md` (install, demo data, demo accounts), `CONTRIBUTING.md` | No user manual per role. No architecture/technical documentation (models, roles, flows). |
| 39 | Final acceptance testing | 5 | Web | NOT STARTED | No acceptance checklist or report. | Everything (comes last). |

## Next 5 non-AI items to build (dependency order)

1. **Item 12: version history for deliverables** (4 j).
   - Needed before the jury can read the reports (21). AI similarity (30) needs it later.
2. **Item 19: plan defenses with rooms and time slots** (6 j).
   - Builds on the `TERMINE → PLANIFIE` transition. Conflict detection (20) needs rooms and slots.
3. **Item 20: detect and fix scheduling conflicts** (5 j).
   - Needs the rooms and slots from item 19.
4. **Item 17: admin generates documents (agreement, certificate, minutes)** (5 j).
   - The certificate and minutes depend on the « soutenu » state and the grades (items 14, 21).
5. **Item 18: company supervisor approves the generated agreement** (2 j).
   - Needs the agreement from item 17.

After these: 21 / 22 (notices, reports for the jury) → 11, 15, 23.


## Change log

### Item 4: academic supervisor approves offers (done 2026-11-28)

Files changed:
- Models and migrations: `accounts/models.py`, `accounts/migrations/0007_user_domaine.py`, `offres/models.py`, `offres/migrations/0002_offre_domaine.py`
- Logic: `offres/forms.py`, `offres/views.py`, `offres/urls.py`, `accounts/views.py`, `accounts/admin.py`
- Templates: `templates/offres/offres_a_valider.html`, `offre_form.html`, `offre_detail.html`, `offre_list.html`, `templates/partials/_sidebar.html`, `templates/accounts/dashboards/admin.html`, `encadrant_acad.html`
- Demo data: `accounts/management/commands/create_demo_users.py`, `seed_demo.py`, `seed_showcase.py` (`encadrant_acad` = Data science et IA, `encadrant_acad2` = Génie logiciel)
- Tests: `offres/tests.py` (new), `accounts/tests.py`, `candidatures/tests.py`

What's left (outside item 4): academic supervisors can't edit their own field yet (item 2).

### Item 14: PFE state machine (done 2026-11-28)

Lifecycle: `EN_ATTENTE --affecter--> EN_COURS --terminer--> TERMINE --planifier--> PLANIFIE --soutenir--> SOUTENU`,
plus `liberer` (EN_COURS → EN_ATTENTE) and `rouvrir` (TERMINE → EN_COURS).

| Transition | Who triggers it | Guard |
|---|---|---|
| affecter | academic supervisor (« Prendre en charge ») | project has no supervisor yet |
| liberer | its academic supervisor (« Retirer ») | project is EN_COURS |
| terminer | its academic supervisor (« Terminer ») | ≥ 1 approved deliverable, none waiting for review |
| rouvrir | its academic supervisor (« Rouvrir ») | project is TERMINE (not yet scheduled) |
| planifier | admin, when scheduling the defense | project is TERMINE and has a defense |
| soutenir | automatic, after the last jury grade | every jury member has graded |

Files changed:
- Models and migrations: `pfe/models.py`, `pfe/migrations/0002_cycle_de_vie.py`, `pfe/migrations/0003_statuts_existants.py`
- State machine: `pfe/workflow.py` (new)
- Views and URLs: `pfe/views.py`, `pfe/urls.py`, `soutenances/views.py`, `soutenances/forms.py`, `pfe/admin.py`
- Templates: `templates/pfe/mon_pfe.html`, `mes_etudiants.html`, `affectations.html`, `templates/soutenances/planifier.html`, `templates/partials/_status_badge.html`
- Demo data: `accounts/management/commands/seed_showcase.py`
- Tests: `pfe/test_workflow.py` (new), `soutenances/tests.py` (fixtures follow the new rules)

Checked: migration run on a copy of the real database (5 projects converted as expected); student page checked in the browser on desktop and phone.

What's left (outside item 14): nothing blocks. Items 15, 17 and 22 can now rely on the project status.

### Item 16: academic supervisor's workload (done 2026-11-28)

- A project counts as **active** while it is « en cours », « terminé » or « soutenance planifiée ». Defended projects are shown apart.
- Load = active projects / `capacite_encadrement` (default 8, between 1 and 30, set by the admin in the Django admin).
- Gauge colour: green under 80 %, orange from 80 %, red at 100 %; an alert appears above capacity.

Files changed:
- Model and migration: `accounts/models.py`, `accounts/migrations/0008_user_capacite_encadrement.py`, `accounts/admin.py`
- Service: `pfe/charge.py` (new)
- View, URL, templates: `pfe/views.py`, `pfe/urls.py`, `templates/pfe/ma_charge.html` (new), `templates/partials/_sidebar.html`, `accounts/views.py`, `templates/accounts/dashboards/encadrant_acad.html`
- Tests: `pfe/test_charge.py` (new)

Checked: page and dashboard read in the browser with demo data (`encadrant_acad`: 1 / 8 active projects). The browser pane was hidden, so the layout was not checked visually; it uses the standard Bootstrap grid.

What's left (outside item 16): supervisors can't change their own capacity (admin only, by choice).

### Item 1: sign up / log in by role (done 2026-11-28)

The feature already existed; it lacked a test of the sign-up itself.

Files changed:
- Tests: `accounts/tests.py` (new `RegistrationTests`, 8 tests)

What's left (outside item 1): nothing.

### Item 5: students search and view offers (done 2026-11-28)

Writing the tests found two bugs, both fixed:
- **A student could open an unpublished offer by its URL** (draft, under review or refused): the detail page now only serves published offers (404 otherwise).
- **The search term was not URL-encoded in the pagination links**, so a search like « C++ & Qt » broke on page 2.

Files changed:
- `offres/views.py` (`OffreDetailView` limited to published offers)
- `templates/offres/offre_list.html` (`q|urlencode` in the pagination links)
- Tests: `offres/tests.py` (new `OffreSearchTests`, 10 tests)

What's left (outside item 5): nothing.

### Item 10: assign a PFE by field and workload (done 2026-11-28)

- Every project has a field: chosen by the student who declares it, taken from the offer for an accepted application, or the supervisor's field when they create it. Existing projects got their offer's field (migration 0005); the others stay without a field and remain open to every supervisor.
- **Suggestion** (web part, rule based): eligible supervisors have the project's field and free places. Score /100 = 60 for the field (30 if the project has no field) + up to 40 for free places / capacity. The top 3 are shown with their reasons.
- **Rules**: a supervisor can only take or create a project of their field, and only under their capacity (defended projects don't count). Enforced in the state machine guard, so every path applies it.
- **AI extension point**: `pfe.suggestion.ajuster_par_ia(projet, suggestions)` returns the ranking unchanged; the `ia` app will replace it (a test checks the hook is called with the ranking).

Files changed:
- Model and migrations: `pfe/models.py`, `pfe/migrations/0004_projetpfe_domaine.py`, `pfe/migrations/0005_domaine_depuis_offre.py`
- Suggestion and rules: `pfe/suggestion.py` (new), `pfe/workflow.py`, `pfe/forms.py`, `pfe/views.py`
- Templates: `templates/pfe/affectations.html`, `templates/pfe/projet_form.html`
- Demo data: `accounts/management/commands/seed_showcase.py` (fields of the demo projects)
- Tests: `pfe/test_suggestion.py` (new), `pfe/tests.py` (declaration now sends a field)

Checked: migrations on a copy of the real database; assignment page rendered for both demo supervisors (each sees their field's project suggested, the other one locked with its reason).

What's left (outside item 10): the AI re-ranking itself (items 24–27).
