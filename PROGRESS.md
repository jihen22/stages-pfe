# Progress: backlog status

Audit date: 2026-11-28. Code at commit `621cafc` (style: redesign jury dashboard).
Rules: CLAUDE.md and BACKLOG.md as of this date (items 1–39, 168 jours-homme, SQLite, no Docker).
Method: I read the code only and changed nothing.

## Tests

`python manage.py test` → **Ran 89 tests, OK** (0 failures, 0 errors).

| App | Tests |
|---|---|
| accounts | 29 |
| pfe | 30 |
| soutenances | 17 |
| notifications | 10 |
| candidatures | 3 |
| offres | 0 (its workflow is tested in `candidatures/tests.py`) |

## Definition of done (CLAUDE.md)

1. Models + migrations · 2. Views, URLs, templates · 3. Access limited to the right role(s) · 4. Responsive (Bootstrap) · 5. At least one automated test covers the main case.

Shared proof for criteria 3 and 4, which every item below relies on:
- Roles: `accounts/mixins.py` (`RoleRequiredMixin`, `role_required`)
- Bootstrap 5.3.3: `templates/base.html:13`

For criterion 5, a test only counts when it checks the item's main behaviour. A test that only checks the page loads does not count.

## Jours-homme

| | Done | Total | % |
|---|---|---|---|
| All items | **16 j** | 168 j | **9.5 %** |
| Non-AI items | **16 j** | 107 j | **15.0 %** |

DONE items: 3 (3 j) + 6 (4 j) + 7 (4 j) + 8 (2 j) + 13 (3 j) = 16 j.
PARTIAL items count for 0 j.
Items 1 and 5 (8 j together) each only lack one test. Once those tests are written, the non-AI total becomes 24 / 107 j (22.4 %).

## Summary

| Status | Count | Items |
|---|---|---|
| DONE | 5 | 3, 6, 7, 8, 13 |
| PARTIAL | 14 | 1, 2, 4, 5, 10, 12, 14, 16, 19, 21, 22, 35, 36, 38 |
| NOT STARTED | 20 | 9, 11, 15, 17, 18, 20, 23, 24–34, 37, 39 |
| **Total** | **39** | |

## Detail per item

| ID | Item (short) | j | Type | Status | Proof (files) | What's missing |
|---|---|---|---|---|---|---|
| 1 | Sign up / log in by role | 5 | Web | PARTIAL | `accounts/models.py:9-87` (`User.role`, `get_dashboard_url`), `accounts/views.py:29-64` (login, student sign-up, company-supervisor sign-up), `accounts/urls.py`, `templates/accounts/login.html`, `register.html`, tests `accounts/tests.py:121-138` (login → role dashboard) | No test submits the sign-up form: only "page loads" (`accounts/tests.py:116`). The other roles have no self sign-up and are created by `create_demo_users` or the Django admin. That is fine if intended. |
| 2 | View / edit my profile | 2 | Web | PARTIAL | Student: `accounts/models.py:90-140`, `accounts/views.py:209-221`, tests `accounts/tests.py:249-283`. Company supervisor: `accounts/models.py:150-182`, `accounts/views.py:158-206`, `templates/accounts/profil_encadrant_pro.html` | Academic supervisor, admin and jury can only pick theme/accent (`accounts/views.py:140-148`). They cannot edit their name, email or password. No test for the company-supervisor profile form. |
| 3 | Company supervisor publishes an offer | 3 | Web | **DONE** | `offres/models.py`, `offres/migrations/0001_initial.py`, `offres/views.py:73-133`, `offres/urls.py`, `templates/offres/offre_form.html`, `mes_offres.html`, test `candidatures/tests.py:34-50` | Publication goes through approval, see item 4. |
| 4 | Academic supervisor approves offers in their field | 2 | Web | PARTIAL | `offres/views.py:140-169`, `templates/offres/offres_a_valider.html`, `Offre.Status.EN_VALIDATION` (`offres/models.py:9-13`) | **Wrong role**: approval is limited to `User.Role.ADMIN` (`offres/views.py:143, 149, 161`) and the test approves as admin (`candidatures/tests.py:52-57`). No field (`domaine`) on `User`/`Offre`, so offers can't be sent to the supervisor of the right field. |
| 5 | Student searches / views offers | 3 | Web | PARTIAL | `offres/views.py:21-66` (search `q` on title/description/skills, `type` filter, pagination, detail), `templates/offres/offre_list.html`, `offre_detail.html` | No test checks search, the filter or the detail page. Only "list page loads" (`candidatures/tests.py:60`, `accounts/tests.py:84`). |
| 6 | Apply with CV + cover letter | 4 | Web | **DONE** | `candidatures/models.py` (CV, letter, unique student+offer), `candidatures/migrations/0001_initial.py`, `candidatures/views.py:32-69`, `templates/candidatures/candidature_form.html`, tests `candidatures/tests.py:58-100` | — |
| 7 | Track my application + notifications | 4 | Web | **DONE** | `candidatures/views.py:20-29, 98-125`, `templates/candidatures/mes_candidatures.html`, `notifications/models.py`, `notifications/services.py`, `notifications/views.py`, `notifications/context_processors.py`, tests `notifications/tests.py:38-130` | In-app notifications only, no email (not required). |
| 8 | Company supervisor sees applications received | 2 | Web | **DONE** | `candidatures/views.py:76-125` (list, filter by offer, accept/refuse), `templates/candidatures/candidatures_recues.html`, tests `candidatures/tests.py:76-81`, `notifications/tests.py:71-90` | — |
| 9 | Anonymised data collection for AI | 3 | AI | NOT STARTED | No `ia` app in `INSTALLED_APPS` (`crud/settings.py:28-42`). | Everything. |
| 10 | Academic supervisor assigns a PFE (+ suggestion by field/workload) | 6 | Mixed | PARTIAL | `pfe/views.py:197-291` (`affectations`, atomic `prendre_en_charge`, `liberer_projet`, `creer_projet_encadrant`), `pfe/forms.py:32-65`, `templates/pfe/affectations.html`, `projet_form.html`, tests `pfe/tests.py:235-365` | No suggestion by field or workload (no field data, no workload count). No empty AI extension point (required by CLAUDE.md for mixed items). |
| 11 | Discussion space between student and supervisor | 4 | Web | NOT STARTED | No message/thread model. `Livrable.commentaire_encadrant` (`pfe/models.py:81`) is a one-way comment on a deliverable. | Everything. |
| 12 | Upload deliverables with version history | 4 | Web | PARTIAL | `pfe/models.py:58-90` (`Livrable`), `pfe/views.py:108-134`, `templates/pfe/deposer_livrable.html`, `mon_pfe.html`, tests `pfe/tests.py:154-185` | No version history: no version number and no link between successive uploads of the same deliverable. |
| 13 | Approve a deliverable / ask for a correction | 3 | Web | **DONE** | `pfe/views.py:19-53, 153-190`, `pfe/urls.py`, `templates/pfe/livrables_a_valider.html`, tests `pfe/tests.py:187-233` | — |
| 14 | PFE lifecycle state machine | 6 | Web | PARTIAL | `pfe/models.py:10-46` (`EN_COURS`, `TERMINE`, `SOUTENU`) | Only the states exist. No allowed transitions, no guards, nothing that ever changes `ProjetPFE.status`, no test. |
| 15 | Company supervisor follows progress + evaluates the internship | 3 | Web | NOT STARTED | `accounts/views.py:98-109`: the dashboard only counts offers/applications. No view on `ProjetPFE` for this role, no evaluation model. | Everything. |
| 16 | Academic supervisor sees their workload | 2 | Web | PARTIAL | `pfe/views.py:141-150` (`mes_etudiants`), `templates/pfe/mes_etudiants.html` | No workload indicator (number of students, limit, breakdown by status). The dashboard (`accounts/views.py:112-117`) only shows unassigned projects. Only access tests (`pfe/tests.py:92`, `accounts/tests.py:94`). |
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
| 36 | Fast, stable app (integration tests, optimisation, bug fixes) | 6 | Web | PARTIAL | 89 passing tests, including a full workflow test (`candidatures/tests.py:34-81`) and role-access tests in every app. `select_related`/`prefetch_related` in the views. | No integration test across the whole chain (offer → PFE → deliverable → defense → grade). No `offres/tests.py`. No performance check. |
| 37 | Stable production URL | 5 | Web | NOT STARTED | `crud/settings.py` is in development mode only (DEBUG, no `ALLOWED_HOSTS`/static config for production). No deployment files. | Everything. |
| 38 | Technical docs + user manual | 4 | Web | PARTIAL | `README.md` (install, demo data, demo accounts), `CONTRIBUTING.md` | No user manual per role. No architecture/technical documentation (models, roles, flows). |
| 39 | Final acceptance testing | 5 | Web | NOT STARTED | No acceptance checklist or report. | Everything (comes last). |

## Next 5 non-AI items to build (dependency order)

1. **Item 4: the academic supervisor approves offers in their field** (2 j).
   - Add a `domaine` field (new migration) and move approval from `ADMIN` to `ENCADRANT_ACAD`.
   - It fixes a rule CLAUDE.md says not to change, and items 10 and 16 need the field.
2. **Item 14: PFE state machine** (6 j).
   - Define the states, the allowed transitions and the guards on `ProjetPFE`.
   - Deliverables (12), the company supervisor's follow-up (15), defense planning (19) and documents (17) all depend on the project status.
3. **Item 16: workload of the academic supervisor** (2 j).
   - Count students per supervisor, by status.
   - This count is the "charge" input for the suggestion in item 10.
4. **Item 10: assign a PFE by field and workload, with an empty AI hook** (6 j).
   - Needs the field from item 4 and the workload from item 16.
5. **Item 12: version history for deliverables** (4 j).
   - Needed before the jury can read the reports (21). AI similarity (30) needs it later.

After these: 19 → 20 (rooms/slots, then conflicts) → 17 → 18 (documents, agreement) → 21 / 22 (notices, reports for the jury) → 11, 15, 23.

Quick wins to do along the way: one sign-up test (item 1) and one search test (item 5). They move 8 j to DONE.
