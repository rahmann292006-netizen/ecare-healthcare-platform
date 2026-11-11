# eCare API — Raichur Health Hub

Backend API for the eCare healthcare discovery platform serving Raichur, Karnataka, India.

## Database Architecture

The platform uses **PostgreSQL** with **SQLAlchemy 2.x** ORM and **Alembic** for database migrations.

### Tables

| Table | Description |
|-------|-------------|
| `hospitals` | Hospitals and healthcare facilities in Raichur |
| `doctors` | Doctors, optionally affiliated with a hospital |
| `diagnostic_labs` | Diagnostic laboratories and pathology centers |
| `diagnostic_tests` | Tests offered by diagnostic labs |

### Relationships

- **Hospital → Doctors**: One-to-many (a hospital can have many doctors; a doctor has at most one primary hospital via `hospital_id`, nullable, `ON DELETE SET NULL`)
- **DiagnosticLab → DiagnosticTests**: One-to-many (a lab offers many tests; deleting a lab cascades to its tests)

### Verification Status

All directory entities (`hospitals`, `doctors`, `diagnostic_labs`) support these statuses:
- `unverified` (default for new records)
- `pending`
- `verified`
- `rejected`

### Constraints & Validation

- Slugs are unique per table
- Prices (`consultation_fee`, `price`) are `NON-NEGATIVE` decimal values
- Coordinates (`latitude`, `longitude`) are validated within valid ranges
- Phone numbers stored as strings
- `city` defaults to `Raichur`, `state` defaults to `Karnataka`
- `is_active` defaults to `true`
- `verification_status` defaults to `unverified`
- `created_at` / `updated_at` managed with `server_default=now()` and `onupdate`

## Environment Setup

### Required Environment Variables

Create `apps/api/.env` (this file is Git-ignored — never commit it):

```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<database>
```

Do not include real credentials in this README or in version control.

### Production Deployment Checklist

The API image is defined in `Dockerfile`; it starts Uvicorn and does not apply database migrations. Configure runtime values in the hosting provider's secret/environment settings, never in the image or repository:

| Variable | Production requirement |
|----------|------------------------|
| `DATABASE_URL` | Managed PostgreSQL connection string stored as a secret; do not use the example `_test` URL. |
| `ECARE_SECRET_KEY` | At least 32 bytes of cryptographically random secret material; store as a secret. Rotating it invalidates existing access tokens. |
| `ECARE_CORS_ORIGINS` | Exact deployed frontend origin(s), comma-separated; do not use `*`. |
| `ECARE_ENVIRONMENT` | `production`. |
| `ECARE_DEV_MODE` | `false`. |
| `ECARE_SIMULATED_PAYMENTS_ENABLED` | `false`; no real payment gateway is implemented. |
| `ECARE_ACCESS_TOKEN_EXPIRE_MINUTES` | Optional; defaults to 30. |
| `PORT` | Use the platform-provided value when available; the container defaults to `8000`. |

`NEXT_PUBLIC_API_URL` is also required in the Vercel frontend environment and must be the actual deployed API origin. Set it only after that URL exists and has been verified.

**Deployment is not currently ready to execute.** Alembic is deliberately guarded to loopback PostgreSQL databases ending in `_test`; there is no approved production migration procedure in this repository. Do not weaken or bypass that guard to deploy. Define and review a separate production migration process before creating or using a production database. After an approved deployment, verify `/health`, `/health/db`, CORS preflight, authentication, and a package subscription flow. No backend URL or production environment has been verified, and no service or deployment has been created.

### Dependency Installation

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Migration Commands

```bash
cd apps/api
.venv\Scripts\activate

# Create a new migration from model changes
alembic revision --autogenerate -m "describe changes"

# Apply migrations to the database
alembic upgrade head

# Check current migration status
alembic current

# Show migration history
alembic history
```

## How to Run the API

```bash
cd apps/api
.venv\Scripts\activate
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

The API will be available at `http://127.0.0.1:8000`.

### Local Demo Data and Admin Bootstrap

The demo data utility is read-only by default. It requires `DATABASE_URL` to be
supplied in the process environment, then overrides the target to loopback
`ecare_test` and verifies the current schema revision before querying:

```powershell
Set-Location C:\Projects\ecare\apps\api
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

Applying the fictional listings and packages requires explicit operator approval
and an interactive database-name confirmation:

```powershell
.\.venv\Scripts\python.exe scripts\seed_demo_data.py --apply --confirm-target ecare_test
```

Do not run the apply command without explicit approval. The secure first-admin
bootstrap also requires `DATABASE_URL` and `ECARE_SECRET_KEY` in the process
environment, prompts for operator-supplied credentials without echoing the
password, and writes only after the same database checks and an interactive
`ecare_test` confirmation:

```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_demo_admin.py
```

These utilities do not open local environment files. No default administrator
credentials are provided.

### Health Endpoints

- `GET /health` — returns `{"status": "ok"}`
- `GET /health/db` — returns `{"database": "ok"}` when PostgreSQL is reachable

## API Endpoints

All API endpoints are prefixed with `/api/v1`.

### Hospitals

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/hospitals` | List hospitals (pagination + filters) | Public |
| GET | `/api/v1/hospitals/{id}` | Get hospital details | Public |
| POST | `/api/v1/hospitals` | Create a hospital listing | Write-protected |
| PATCH | `/api/v1/hospitals/{id}` | Update a hospital | Write-protected |
| GET | `/api/v1/hospitals/{id}/doctors` | List doctors at a hospital | Public |

**Query parameters (GET /hospitals):**
- `search` — search by hospital name
- `locality` — filter by locality
- `hospital_type` — filter by hospital type
- `verification_status` — filter by verification status
- `emergency_services` — filter by emergency services (true/false)
- `limit` — page size (1-100, default 20)
- `offset` — pagination offset (default 0)

### Doctors

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/doctors` | List doctors (pagination + filters) | Public |
| GET | `/api/v1/doctors/{id}` | Get doctor details | Public |
| POST | `/api/v1/doctors` | Create a doctor listing | Write-protected |
| PATCH | `/api/v1/doctors/{id}` | Update a doctor listing | Write-protected |

**Query parameters (GET /doctors):**
- `search` — search by doctor name
- `specialization` — filter by specialization
- `hospital_id` — filter by associated hospital
- `verification_status` — filter by verification status
- `limit`, `offset` — pagination

### Diagnostic Laboratories

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/labs` | List laboratories (pagination + filters) | Public |
| GET | `/api/v1/labs/{id}` | Get laboratory details | Public |
| POST | `/api/v1/labs` | Create a laboratory listing | Write-protected |
| PATCH | `/api/v1/labs/{id}` | Update a laboratory | Write-protected |

**Query parameters (GET /labs):**
- `search` — search by laboratory name
- `locality` — filter by locality
- `home_sample_collection` — filter by home sample collection (true/false)
- `verification_status` — filter by verification status
- `limit`, `offset` — pagination

### Diagnostic Tests

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/labs/{lab_id}/tests` | Add a test to a lab | Write-protected |
| GET | `/api/v1/labs/{lab_id}/tests` | List tests offered by a lab | Public |
| GET | `/api/v1/tests/{id}` | Get diagnostic test details | Public |
| PATCH | `/api/v1/tests/{id}` | Update test information | Write-protected |

### Responses

- `200 OK` — successful read
- `201 Created` — successful creation
- `403 Forbidden` — write operations disabled (development mode required)
- `404 Not Found` — record does not exist
- `409 Conflict` — duplicate slug or conflicting unique value
- `422 Unprocessable Entity` — invalid input

## Pagination

List endpoints use `limit` and `offset` query parameters:
- `limit`: maximum items per page (1–100, default 20)
- `offset`: number of items to skip (default 0)

Response includes `items`, `total`, `limit`, and `offset`.

## Write Authorization Restrictions

**This project does not yet have a complete authentication and authorization system.**

Write operations (POST, PATCH) are disabled by default and return `403 Forbidden`. To enable writes during development:

1. Set the environment variable `ECARE_DEV_MODE=true`, or
2. Send the header `X-Ecare-Dev-Mode: true` with the request

This is a development-only guardrail, not production authentication. Do not hardcode admin credentials or implement fake authentication.

Public read-only endpoints (GET) remain accessible without authentication.

**Trust model:**
- All new listings default to `verification_status = "unverified"`
- Clients cannot set `verification_status` to `"verified"` via the API
- Listing creation is separate from verification
- No real healthcare data is included

## How to Run Tests

```bash
cd apps/api
.venv\Scripts\activate
pytest tests/ -v
```

Tests verify:
- Model definitions, constraints, and relationships
- Database configuration
- API endpoint behavior (CRUD, pagination, filters, search)
- Error handling (404, 409, 422, 403)
- Foreign-key relationships
- Default unverified status
- Write authorization restrictions
- Health endpoints

Tests use the real PostgreSQL database via `DATABASE_URL`. All changes are rolled back after each test. No credentials are printed in test output.

If PostgreSQL is unavailable, database-dependent tests will fail with a connection error.

## Project Structure

```
apps/api/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app with /health and /health/db
│   ├── database.py      # SQLAlchemy engine, session, Base, get_db
│   ├── models.py        # Hospital, Doctor, DiagnosticLab, DiagnosticTest
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── auth.py          # Development-only write authorization
│   └── api/v1/
│       ├── __init__.py
│       ├── api.py       # Router aggregator
│       └── routers/
│           ├── hospitals.py
│           ├── doctors.py
│           ├── labs.py
│           └── tests.py
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api.py      # API integration tests
│   ├── test_database.py # Database configuration tests
│   └── test_models.py   # Model definition tests
├── .env                 # Git-ignored environment variables (DATABASE_URL)
├── alembic.ini          # Alembic configuration
└── requirements.txt     # Python dependencies
```