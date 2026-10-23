# eCare Project Audit Report

**Project:** `C:\Projects\ecare`  
**Audit continuation:** 2026-10-23 (Asia/Calcutta)  
**Scope:** Read-only source review; report is the only file written by this continuation.

## 1. Executive summary

eCare is a Raichur healthcare directory with a FastAPI/PostgreSQL backend and a Next.js frontend. The repository is an in-progress working tree with substantial modified and untracked files. The API is mounted in the current working tree, and the frontend now has a real read-only provider-search integration; the earlier report incorrectly described the frontend as only a design-token preview. Other screens remain demo/sample-only. No appointment request endpoint, user authentication, or provider verification workflow is implemented. No AI integration was found.

This continuation verified source, routes, models, migration, frontend integration, and project state. It did not rerun tests or builds: test execution depends on a live database and can write test/cache state, while a Next build creates `.next` files. The prior report's test results are historical and were not independently reproduced here.

## 2. Structure and technology stack

- `apps/api/`: Python FastAPI service, SQLAlchemy ORM, Alembic migration, Pydantic schemas, pytest tests.
- `apps/web/`: Next.js App Router, React, TypeScript, Tailwind; routes include home, `/find`, `/dashboard`, `/packages`, `/packages/[id]`, `/reminders`, `/notifications`, `/provider`.
- `data/`: empty `imports`, `research`, and `seed` placeholders.
- `docs/`: `architecture.md`, `data-workflow.md`, and `privacy.md` remain `TBD`.
- Dependency manifests are `apps/api/requirements.txt` and `apps/web/package.json` (Next 16.4.2, React 19.3.0 as declared). Backend exact declared versions are in requirements.txt; runtime versions were not rechecked during this continuation.

Repository status at inspection showed pre-existing modifications to `apps/api/app/main.py`, `apps/api/requirements.txt`, `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`, `apps/web/tsconfig.json`, plus untracked report/API/frontend files. A pytest cache directory was inaccessible to status enumeration. No conclusion is made that these changes were authored by this audit.

## 3. Architecture and data flow

The current `apps/api/app/main.py` loads `.env`, imports database/models, mounts `api_router`, and exposes `/health` and `/health/db`. The `/api/v1` aggregator registers hospitals, doctors, labs, and tests routers. Routers use `get_db` to access SQLAlchemy sessions and `require_write_access` on writes. The session dependency commits on successful completion and rolls back on exceptions.

The frontend is no longer wholly disconnected. `apps/web/app/lib/api.ts` calls `NEXT_PUBLIC_API_URL` (fallback `http://localhost:8000`) and exposes typed-ish read helpers; `/find` calls list APIs for hospitals, doctors, and labs and supports search/locality filtering. Package, reminder, notification, dashboard, and provider views use local demo data or static content, and do not persist to the backend. The API client uses `any[]` for list items, so type coverage is partial. Cross-origin configuration was not found in the app setup.

## 4. API endpoint inventory

The current source declares these routes; writes use the development-only guard (`ECARE_DEV_MODE=true` or `X-Ecare-Dev-Mode: true`), not real authentication.

| Method | Path | Purpose | Access |
|---|---|---|---|
| GET | `/health` | App health | Public |
| GET | `/health/db` | Database connectivity | Public |
| GET | `/api/v1/hospitals` | Search/filter/paginated hospitals | Public |
| GET | `/api/v1/hospitals/{hospital_id}` | Hospital details | Public |
| POST/PATCH | `/api/v1/hospitals[/{hospital_id}]` | Create/update hospital | Dev guard |
| GET | `/api/v1/hospitals/{hospital_id}/doctors` | Doctors at hospital | Public |
| GET | `/api/v1/doctors` | Search/filter/paginated doctors | Public |
| GET | `/api/v1/doctors/{doctor_id}` | Doctor details | Public |
| POST/PATCH | `/api/v1/doctors[/{doctor_id}]` | Create/update doctor | Dev guard |
| GET | `/api/v1/labs` | Search/filter/paginated labs | Public |
| GET | `/api/v1/labs/{lab_id}` | Lab details | Public |
| POST/PATCH | `/api/v1/labs[/{lab_id}]` | Create/update lab | Dev guard |
| POST/GET | `/api/v1/labs/{lab_id}/tests` | Add/list tests for a lab | Dev guard / public |
| GET/PATCH | `/api/v1/tests/{test_id}` | Test detail/update | Public / dev guard |

There is no top-level test-list route, appointment-request route, login/user route, or verification review route. The report claims routes based on source decorators and router registration, not runtime requests during this continuation.

## 5. Database schema and relationships

The ORM and initial Alembic migration define four tables:

- `hospitals`: identity/name/slug, address and locality, city/state defaults, contact details, coordinates, emergency services, verification and active flags, timestamps.
- `doctors`: identity/name/slug, qualifications, specialization, experience, languages, fee, optional hospital link, verification and active flags, timestamps.
- `diagnostic_labs`: identity/name/slug, address/locality, city/state defaults, phone, home collection, verification and active flags, timestamps.
- `diagnostic_tests`: lab link, name/description/price/preparation, availability, timestamps.

`Hospital` to `Doctor` is one-to-many; `doctors.hospital_id` is nullable and has `ON DELETE SET NULL`. `DiagnosticLab` to `DiagnosticTest` is one-to-many; test `lab_id` is required and has `ON DELETE CASCADE`. Models/migration include slug uniqueness, coordinate bounds, nonnegative fees/prices/experience, verification status and test availability checks, plus indexes. The migration creates redundant single-column/composite indexes (including both `doctors.specializations` indexes and city indexes where city is also part of a city/state index).

## 6. Feature status and code-quality/security findings

| Feature | Status and evidence |
|---|---|
| Provider directory reads | Implemented in API routers; `/find` consumes hospital, doctor, and lab list helpers. |
| Provider create/update | Implemented in API but guarded only by a client-controllable dev header or environment flag. |
| Provider detail UI | API client has detail helpers, but reviewed routes do not provide provider detail pages. |
| Packages | Demo-only local sample data; no package model/API. |
| Reminders/notifications/dashboard | Demo/static state; reminder changes live only in component state. |
| Provider dashboard | Explicitly demo-only; no account or actual listing management. |
| Appointment requests | Not implemented despite home-page explanatory copy. |
| Authentication/verification review | Not implemented; no user model, login, role system, or review endpoint found. |
| AI | Not present. |
| Tests/docs/seed data | Tests exist; docs are TBD; seed directory is empty. |

Findings, prioritized:

1. **High — Write authorization is not authentication.** `require_write_access` trusts a public request header or a global env flag. Do not expose writes publicly with this guard.
2. **High — No appointment request flow or persistence.** Frontend copy describes requests, but no request endpoint/schema/model exists.
3. **High — Demo screens may be mistaken for working product features.** Packages/reminders/notifications use sample data; reminder edits are transient and account data is not stored.
4. **Medium — Frontend integration is partial.** `/find` uses backend read APIs; the rest of the product screens do not. API base URL fallback is localhost, and CORS is not configured in the FastAPI app.
5. **Medium — Test portability and verification remain uncertain.** Tests target PostgreSQL via `DATABASE_URL`; no independent test run was made now. Prior report's 70-pass result is historical only.
6. **Medium — Migration index duplication.** Confirmed duplicate doctor specialization indexes and overlapping city indexes in the migration.
7. **Medium — Privacy/architecture documentation is unfinished.** All three docs inspected contain only `TBD`.
8. **Credential hygiene — Prior report stated a local ignored `.env` contains a database credential.** This continuation did not inspect or disclose its value, and therefore does not independently verify the credential's current contents. Keep it excluded from version control and rotate if it is a real/shared credential.
9. **Working-tree divergence —** many changes are modified/untracked; current `main.py` includes router mounting, while earlier report's HEAD-vs-working-tree claim was not revalidated against commit contents during this continuation. Review and preserve the existing work before committing or reverting anything.

## 7. Test/build results

No tests, lint, or build were run during this continuation. The previous report recorded 70 passing backend tests against local PostgreSQL; that result is not a fresh result and was not reverified. A backend test run requires PostgreSQL and may alter database/test cache state. A frontend build creates `.next` artifacts. The current `package.json` lint script is `eslint`; the earlier report's `next lint` command is stale for this manifest. Run checks in a disposable checkout or explicitly permit their side effects before treating them as verified.

## 8. Prioritized recommendations

1. Replace development-header write authorization with authenticated identities and role checks before enabling any externally reachable writes.
2. Define and implement the appointment request model/API and user-facing request flow; make clear that a request is not a confirmed booking.
3. Label demo-only packages/reminders/notifications throughout the UI, or connect them to persistent APIs and user accounts.
4. Configure explicit allowed CORS origins and a deployment-specific API URL; improve frontend API types and error handling.
5. Establish a safe PostgreSQL-backed test setup and CI; run backend tests and frontend lint/build in an isolated environment.
6. Add administrative verification/review workflow and audit trail; preserve default unverified status.
7. Finish architecture, data workflow, and privacy documentation; define data minimization and retention before adding user data.
8. Remove redundant migration indexes through a reviewed follow-up migration if query plans confirm they are unnecessary.
9. Review existing modified/untracked working-tree files as a separate change-management task; do not assume the repository reflects a clean committed release.
10. Verify any local database credential privately and rotate it if real, shared, or exposed; do not place secrets in source or audit output.

## Audit limitations

This continuation did not run tests/build/lint or connect to the database. It did not inspect secret values. It performed read-only inspection of source and git status. The existing audit report was updated as explicitly requested; no other project files were written by this continuation.
