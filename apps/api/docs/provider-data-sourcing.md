# Provider data sourcing and evidence rules

Research checked on **2026-10-23**. No provider records are proposed or
included in this document. The source URLs below are official directory or
registry entry points reviewed for suitability; their presence does not mean
any particular provider has been researched or verified.

## Candidate authoritative sources

| Provider type | Source and URL | What it can support | Limits and evidence to retain |
|---|---|---|---|
| Hospitals and other facilities | ABDM Health Facility Registry (HFR), [facility search](https://facility.abdm.gov.in/searchV2), [HFR overview](https://ahpr.abdm.gov.in/about) | A listing for a facility in the national registry; the HFR scope includes public and private hospitals, clinics, diagnostic laboratories, imaging centers, and other facilities. Use the exact facility page/identifier and fields shown there. | Registry listing alone does not establish current operation, every address/contact field, specialties, or service availability. Capture the displayed facility identifier and listing fields, and manually confirm current address and contact details through the facility's official channel before marking the provider verified. HFR pages may be JavaScript-driven. |
| Hospitals, local public directory | Raichur District Administration, [Hospitals public utility](https://raichur.nic.in/en/public-utility-category/hospitals/) | Facility name, address, category/type, and any listed phone, email, PIN code, or linked official site, when present. The page identifies district-administration ownership and displayed a page update date of 2026-08-06 when reviewed. | Local directory coverage may be partial and details can become stale. Retain the exact listing/page and its displayed update date. Confirm current operation, exact location, and contact details with the facility or district authority. It is not a source for private-provider completeness. |
| Hospitals, candidate discovery only | Karnataka Open Government Data, [District Wise Private Hospitals in Karnataka](https://karnataka.data.gov.in/resource/district-wise-private-hospitals-karnataka) | The dataset metadata lists hospital, taluk, and district, attributed to Karnataka Health and Family Welfare. It reports publication/update on 2022-02-03 and annual granularity. | Too old and too sparse for current addresses, contacts, operating status, or verification. Use only to identify candidates for independent, current confirmation; do not load its rows as current provider records. Confirm the dataset's licence/terms and inspect the downloaded resource metadata before reuse. |
| Doctors (modern/allopathic medicine) | National Medical Commission, [National Medical Register search](https://nmr.nmc.org.in/search-doctor), [NMR FAQ](https://nmr.nmc.org.in/faq), [legacy Indian Medical Register](https://nmc.org.in/information-desk/indian-medical-register) | NMR is the NMC's register for allopathic registered doctors. Publicly visible entries may support the displayed name, registration/status, and recognized qualifications. | The NMR FAQ says specialization information is in process; do not use it as evidence for a speciality until an explicit field is displayed and independently checked. It does not establish current practice location, hospital affiliation, phone, fees, availability, or language. The legacy IMR page explicitly says its data is being updated. Retain registration identifier, displayed status, qualification evidence, exact page/record URL, and manual confirmation of current practice/contact/affiliation. |
| Diagnostic labs | NABL, [accredited laboratory search](https://nabl-india.org/lab-accreditation-with-details/), [medical laboratory accreditation](https://nabl-india.org/medical-testing-laboratories-iso-15189/) | For a listed accredited lab, the directory exposes laboratory name/address and CAB/certificate identifiers, status, validity, and certificate links; NABL says directory data is synchronized daily from its official records. A certificate/scope can support accreditation and the activities within that scope. | NABL is not a complete directory of all diagnostic labs. Accreditation does not establish current phone, hours, home collection, prices, or every test offered. Verify certificate validity/status and scope for each relevant service, and separately confirm current location/contact and service availability with the lab. HFR can support facility registration, not NABL accreditation. |

The URLs and source observations above were accessed on **2026-10-23** for
this source review. For each actual future provider row, record the date of
that row's individual lookup in the evidence ledger; do not copy this review
date as if it were the row's access date.

## Per-record evidence ledger

The importer manifest has one `source` and one `source_url` per provider and
does not have an access-date field, source-record identifier, evidence file,
or field-by-field provenance. Keep a separate controlled ledger for each row
with at least:

- manifest section and stable `slug`;
- source organization/name and exact provider-record URL;
- date accessed (`YYYY-MM-DD`; include time/time zone if freshness needs it);
- source record ID (HFR ID, NMC/State Council registration number, or NABL CAB/certificate number), when applicable;
- exact fields supported by that source and a retained evidence reference (approved capture path or document identifier; do not put sensitive credentials in it);
- which fields were separately confirmed, by whom/when, and through which official contact channel;
- unresolved fields and conflicts.

Use the strongest primary source URL in the manifest and keep the complete
multi-source evidence in the ledger. Do not set `is_verified=true` or
`verification_status="verified"` until a human has reviewed the record and
evidence for current identity and required directory facts. For a verified
row, the importer additionally requires a timezone-aware `verified_at`,
`source_url`, and `is_demo=false`. No field should be filled from a name,
nearby facility, search snippet, or presumed default.

## Schema fit and manual confirmation

- Hospital rows can store name, address, locality, city/state, PIN, coordinates,
  phone, email, website, hospital type, emergency flag, and operating-hours
  text. City and state are mandatory to the importer although the database and
  API schemas default them to Raichur/Karnataka; enter only source-confirmed
  values. The importer currently requires address too.
- Doctor rows can store name, qualifications, legacy free-text
  `specializations`, experience years, languages, consultation fee, phone, and
  an optional hospital link. The model has no registration number, address,
  locality, city, email, website, registration status, or field-level evidence
  fields. Use the doctor only when current practice/location can be established
  by approved evidence; do not put registration numbers into unrelated fields.
- Lab rows can store name, address, locality, city/state, phone, description,
  and the `home_sample_collection` boolean. City and state must be explicit.
  There are no fields for accreditation body, certificate/scope/expiry, email,
  website, test catalogue, or per-test prices. Do not claim accreditation or
  particular tests from this schema alone.
- Hospital/doctor `speciality_slugs` create explicit structured links only to
  active vocabulary already in the database. The approved starter vocabulary is
  in `scripts/seed_specialities.py`; it contains General Medicine, Cardiology,
  Orthopaedics, Paediatrics, Gynaecology, ENT, Dermatology, Ophthalmology,
  Dentistry, and Diabetology. The vocabulary alone is not evidence that a
  provider offers a speciality. The importer does not infer links from
  `specializations`; it rejects speciality links for labs.
- The regular API response schemas expose the provider provenance and
  verification status, but not the evidence ledger, and create schemas do not
  accept provenance or speciality links. The offline importer is the current
  supported path for those fields.

## Template file

`provider-manifest.template.json` is a placeholder-only example, not a
provider dataset. It has no real provider details. Its `source_url` values are
intentionally invalid and every entry is flagged `is_demo=true` and
unverified, so it must be replaced and reviewed before any preview. It should
not be applied or presented as real directory information.
