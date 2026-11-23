# Deploying the eCare API

## Recommended host

Use a Render Docker web service with managed PostgreSQL in the Singapore region. This repository already has a Dockerfile, binds Uvicorn to `0.0.0.0`, accepts the platform `PORT`, and exposes `/health`; Render supports Docker web services, HTTP health checks, PostgreSQL, private service-to-database networking, and a Singapore region. The root [`render.yaml`](../../../render.yaml) describes the API service. It does not create a database or run migrations.

This recommendation is for deploying the current application infrastructure. Before storing real patient health information, confirm that the hosting account, contractual terms, data location, and applicable privacy/compliance requirements are suitable. A hosting platform does not make an application compliant by itself.

## Configuration

The Blueprint sets non-secret production flags and keeps auto-deploy off. Provide the following values through the Render Dashboard/Blueprint setup only; never add them to Git or the Docker image.

| Variable | Required value / handling |
| --- | --- |
| `DATABASE_URL` | Required secret. Use the Render PostgreSQL **internal** connection URL. Change only its scheme from `postgresql://` to `postgresql+psycopg://`; this project installs psycopg 3. Keep the rest of the URL unchanged. |
| `ECARE_SECRET_KEY` | Required signing key. The Blueprint asks Render to generate a 256-bit random value; keep it private. Rotating it invalidates existing access tokens. |
| `ECARE_CORS_ORIGINS` | Required. Exact Vercel production origin, including `https://` and no trailing slash. Use the stable production domain from Vercel project settings, not a preview/deployment URL. Multiple origins may be comma-separated. |
| `ECARE_ENVIRONMENT` | Blueprint sets `production`. |
| `ECARE_DEV_MODE` | Blueprint sets `false`. |
| `ECARE_SIMULATED_PAYMENTS_ENABLED` | Blueprint sets `false`; this project has no real payment gateway. |
| `ECARE_ACCESS_TOKEN_EXPIRE_MINUTES` | Blueprint sets `30`; optional in the application. |
| `PORT` | Blueprint sets `8000` to match the current Dockerfile. |

`ECARE_CORS_ORIGINS` is matched as a literal origin by FastAPI CORS middleware. Do not add a path, trailing slash, wildcard, or guessed Vercel host. After deployment, update the Vercel frontend's `NEXT_PUBLIC_API_URL` to the API's HTTPS origin and redeploy the frontend.

## PostgreSQL and migrations

Use managed PostgreSQL and the internal connection URL so the API and database communicate over the host's private network. Do not put database credentials in `render.yaml`, source control, Docker build arguments, or image layers. The API requires a reachable PostgreSQL database and an existing schema for database-backed endpoints.

`GET /health` is a process/liveness check and returns `{"status":"ok"}` without querying PostgreSQL. `GET /health/db` executes `SELECT 1`; it checks connectivity only and does not verify that migrations have been applied.

**Production schema migration is currently a deployment blocker.** Alembic's existing fail-closed guard in `alembic/env.py` accepts only PostgreSQL on loopback, a database name ending in `_test`, and `ECARE_DATABASE_ENV=test`. This guard must remain unchanged. The repository has no approved production migration runner or procedure. Do not set test flags against production, bypass the guard, or configure a pre-deploy migration command. Before using database-backed production routes, define and review a separate production migration process with backups and an explicit operator-controlled target. The test-only Alembic commands in the API README are not production instructions.

## Deployment steps

1. Resolve the production migration-process blocker above before enabling production database-backed functionality. Decide whether this deployment is for health checks only or for a migrated production schema.
2. In Render, create a PostgreSQL database in Singapore. Select an appropriate paid plan and backup/retention settings for the intended data. Do not load real patient data during setup.
3. In Vercel project settings, identify the stable production frontend domain. Do not use a preview URL.
4. Commit and push this repository configuration. In Render, choose **New + → Blueprint**, connect the repository, and select the root `render.yaml`. Review the proposed service before confirming. `autoDeployTrigger: off` prevents code pushes from deploying automatically.
5. Supply `DATABASE_URL` and `ECARE_CORS_ORIGINS` in the Blueprint setup/Render service environment. Use the database's internal URL and convert its scheme as described above. Render generates `ECARE_SECRET_KEY`; do not copy a local credential into the service.
6. Once the migration plan and schema are ready, manually deploy `ecare-api`. Check `https://<render-service-host>/health` for HTTP 200 and `/health/db` for HTTP 200. A failing `/health/db` means the database is unreachable; a passing result does not mean the schema exists.
7. Set Vercel's production `NEXT_PUBLIC_API_URL` to `https://<render-service-host>` (origin only, no path or trailing slash), then redeploy the frontend. Verify browser CORS preflight and a test account login only after the schema is ready.

Render references: [Docker web services](https://render.com/docs/docker), [HTTP health checks](https://render.com/docs/health-checks), [Blueprint configuration](https://render.com/docs/blueprint-spec), and [private networking](https://render.com/docs/private-network).
