# Offline provider data import

`scripts/import_providers.py` validates a local JSON manifest and compares it
with current database slugs, provider names, and active speciality slugs. It
does not fetch or scrape data. No provider dataset is included in this repo.

## Manifest format (version 1)

The root object has `version: 1` and optional arrays `hospitals`, `doctors`,
and `labs`. OPDs are intentionally not supported by this importer. The
existing OPD table can store an OPD and optional hospital link, but this import
workflow does not currently define or validate an OPD source format.

Each provider object must include these provenance fields:

| Field | Rule |
|---|---|
| `source` | Required, non-empty attribution label supplied with the dataset. |
| `source_url` | Required key; absolute HTTP(S) URL or `null` if the source has no URL. URLs containing user credentials are rejected. |
| `verified_at` | Required key; `null` unless verification has actually been completed, otherwise an ISO-8601 timestamp with timezone. |
| `verification_status` | Required; `unverified`, `pending`, `verified`, or `rejected`. |
| `is_verified` | Required JSON boolean; must agree with `verification_status`. |
| `is_demo` | Required JSON boolean; demo records must remain `unverified` and `false` for `is_verified`. |
| `operational_status` | Optional; `unknown` by default. Allowed values: `unknown`, `operational`, `not_operational`. It is never inferred from `is_active`, a provider name, or directory presence. |

An imported row may be marked verified only after a human has checked the
source evidence. For this format, `source_url` is the evidence pointer and
`verified_at` is the time of that check. The importer does not independently
authenticate that evidence. Do not set verified fields based solely on the
provider's unreviewed submission.

| Provider | Required provider fields | Supported optional fields |
|---|---|---|
| Hospital | `name`, `address`, `city`, `state` | `slug`, `description`, `hospital_type`, `locality`, `pincode`, `latitude`, `longitude`, `phone`, `email`, `website`, nullable `emergency_services`, `operating_hours`, `speciality_slugs` |
| Doctor | `full_name` | `slug`, `qualifications`, legacy `specializations` text, `experience_years`, `languages`, `consultation_fee`, `phone`, `hospital_slug`, `speciality_slugs` |
| Lab | `name`, `address`, `city`, `state` | `slug`, `description`, `locality`, `phone`, nullable `home_sample_collection` |

For hospital `emergency_services` and lab `home_sample_collection`, JSON
`true` and `false` are explicit values; `null` means unknown. Omitting either
field also leaves it unknown. Do not convert unknown to false. The lab field
retains its existing `home_sample_collection` name for compatibility.

`operational_status` is independent of `is_active` and verification status.
Only source-backed human confirmation may set `operational` or
`not_operational`; imports that omit it receive `unknown`. Existing rows are
backfilled to `unknown` by migration `c8f1a2d4e6b0`.

The common provenance fields above are required for every provider type.
When omitted, `slug` is generated using the existing API slugification rule;
collisions are errors, never auto-numbered. Hospital and lab city/state are
required explicitly because the current database columns are non-null and
default to Raichur/Karnataka. An unknown location therefore cannot be imported
without a future schema change; it is not silently assigned those defaults.
The Doctor model has no independent locality/address fields. `hospital_slug`
may link to an existing hospital or one included in the same manifest.

`speciality_slugs` is optional and defaults to an empty list. It is supported
only for hospitals and doctors. Every value must exactly match an active
speciality slug already present in the database. Only explicitly supplied
slugs create links; free-text `specializations` is retained as legacy text and
is never parsed or converted into a structured link. The importer does not
create speciality vocabulary.

A manifest with no records is shaped like this (this is a format skeleton, not
provider data):

```json
{
  "version": 1,
  "hospitals": [],
  "doctors": [],
  "labs": []
}
```

Unknown fields and OPD sections are rejected. Text lengths, email/URL formats,
coordinates, non-negative numeric fields, timestamps, booleans, references,
and required values are validated. Duplicate slugs are errors. Case- and
punctuation-insensitive or near-identical names (similarity at least 0.92) are
reported as human-review conflicts; any error or conflict blocks the entire
apply. The importer only creates rows; it does not update/upsert existing
providers.

## Preview and apply

Run these commands from `C:\Projects\ecare\apps\api`. Provide `DATABASE_URL`
to this PowerShell process using your approved secure method; do not put
credentials in this document, a manifest, or `.env`. Both preview and apply
require `ECARE_DATABASE_ENV=test`, a PostgreSQL database name ending in
`_test`, and an exact loopback host (`localhost`, `127.0.0.1`, or `::1`). A
test-like database name on a non-loopback server is refused. Test setup does
not load `.env`; set the variables in the process before running the command.

```powershell
Set-Location C:\Projects\ecare\apps\api
$env:PYTHONPATH = (Get-Location).Path
$env:ECARE_DATABASE_ENV = 'test'
$env:PYTHON_DOTENV_DISABLED = '1'
if (-not $env:DATABASE_URL) { throw 'Set process-scoped DATABASE_URL first.' }
.\.venv\Scripts\python.exe -m scripts.import_providers C:\path\to\approved-providers.json --dry-run
```

After reviewing a clean preview, apply first to `ecare_test` (the apply
operation is one transaction):

```powershell
.\.venv\Scripts\python.exe -m scripts.import_providers C:\path\to\approved-providers.json --apply
```

For a separately approved staging/production import, set
`ECARE_DATABASE_ENV` to exactly `staging` or `production`, and use a
non-loopback PostgreSQL host. Known development database names are always
refused. The opt-in requires `--apply` and prompts the operator to type the
exact database name before the importer opens a database session. A `*_test`
target still must pass the local host and `ECARE_DATABASE_ENV=test` checks;
the override cannot bypass those checks. Do not use this option for tests.

```powershell
.\.venv\Scripts\python.exe -m scripts.import_providers C:\path\to\approved-providers.json --apply --allow-non-test-database
```

The CLI reports counts and issue locations without echoing provider field
values, credentials, URLs, or exception text. Tests use the existing
`tests.database_guard` to refuse test collection unless the explicit
environment marker, test database name, and loopback host all agree. The
importer tests use pure validation and a read-only session spy and do not
apply provider rows.
