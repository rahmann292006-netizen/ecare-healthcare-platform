# Raichur provider candidate evidence ledger

Research date: **2026-10-23**. This ledger is separate from the importer
manifest. It records candidates only; inclusion here is not a verification
claim. No provider records were imported, and no actual provider manifest was
created from these candidates.

## Candidate summary

| Provider type | Exact provider name | Official source URL | Source access date | Registry/certificate identifier | Fields directly supported by source | Fields requiring manual confirmation | Evidence reference | Verification status | Import eligibility and reason |
|---|---|---|---|---|---|---|---|---|---|
| Hospital | Raichur Institute of Medical Sciences (RIMS) | [Raichur District Administration provider page](https://raichur.nic.in/en/public-utility/raichur-institute-of-medical-sciences-rims/) | 2026-10-23 | Not shown | Name; address "Near BSNL Head Office, Hyderabad Road, Raichur"; phone; email; official website link; category/type "Hospitals"; PIN 584102. City "Raichur" appears in address. The page is on the official Raichur district site; page lists district administration as content owner and was updated Aug 06, 2026. | Current operation; current address/contact reconfirmation; emergency-services yes/no; operating hours; locality/coordinates; any speciality offering. No speciality is inferred from the name/type. | `HOSP-01`, page fields under "Raichur Institute of Medical Sciences (RIMS)". | Unverified. The listing supports directory facts, not current operation, emergency services, or ECARE verification. | **Not import-ready.** Name/address/contacts/type/PIN have official listing evidence, but importer/model defaults cannot distinguish unknown emergency services from no service, and `is_active` defaults true. Confirm operation and emergency status; resolve unknown-value representation before importing. Then run duplicate preview. |
| Hospital | Rajiv Gandhi Super Speciality Hospital (OPEC) | [Raichur District Administration provider page](https://raichur.nic.in/en/public-utility/rajiv-gandhi-super-speciality-hospital-opec/) | 2026-10-23 | Not shown | Name; address "Opposite to BSNL Head Office, Hyderabad Road, Raichur"; phone; email; category/type "Hospitals"; PIN 584103. City "Raichur" appears in address. The page is on the official Raichur district site; it was updated Aug 06, 2026. | Current operation; current address/contact reconfirmation; emergency-services yes/no; operating hours; locality/coordinates; any speciality offering. Do not infer speciality from "Super Speciality" in the name. | `HOSP-02`, page fields under "Rajiv Gandhi Super Speciality Hospital (OPEC)". | Unverified. Directory presence is not proof of current operation or ECARE verification. | **Not import-ready.** Official directory facts are available, but current operation and emergency-services status remain unknown. The model's false default would turn unknown into a negative; `is_active` defaults true. Resolve status representation and confirm both facts, then run duplicate preview. |
| Lab | Tuberculosis C&DST Laboratory, Raichur Institute of Medical Sciences, Raichur | [NABL withdrawal-of-accreditation report, as on 2026-05-20](https://nabl-india.org/nabl/uploads/Withdrawal_of_Accreditation_as_on_20-05-2026.pdf) | 2026-10-23 | CAB ID `M-1881`; certificate `MC-6127` | Exact lab name; CAB ID/certificate; Medical discipline; the report lists accreditation withdrawal effective 2025-09-17. This establishes a historical withdrawal only, not today's status or current operation. | Current operation; lab's actual street address, city/state, contact; current NABL status, scope and any current certificate; home-sample-collection yes/no; current services. Do not copy RIMS address to the lab without confirmation. | `LAB-01`, withdrawal report entry 49 for CAB `M-1881` / certificate `MC-6127`. | Unverified. Do not describe the lab as currently accredited based on the withdrawal report or an old certificate. | **Not import-ready.** Required location fields and current operation are unconfirmed. The historical withdrawal must be resolved against NABL's live search; a current listing/certificate or direct NABL confirmation is needed for any accreditation claim. The false default for home collection also cannot represent unknown. |

## Doctor search outcome

**Zero doctor candidates** are included. The NMC National Medical Register is
an appropriate official source for identifiable allopathic registration
records, but this research did not retrieve a Raichur-specific person record
with a registration identifier and record URL. The NMC search form is not a
provider roster that can be responsibly converted into doctor candidates
without querying identifiable entries. Do not infer names, current practice,
hospital links, speciality, fees, or availability. A future candidate needs
an exact NMC/State Medical Council record URL and registration ID before being
entered here.

## Evidence and next steps

1. For RIMS and OPEC, use the contact channel on each [official district
   listing](https://raichur.nic.in/en/public-utility/) to ask the hospital's
   administration to confirm whether it currently operates, its present
   address and contact details, and emergency-services yes/no. Record date,
   channel, office/respondent role, and the exact answer as manual evidence.
   Ask about hours or specialities only if those fields will be published;
   retain unavailable fields as unknown. The listings themselves do not
   establish current operation or emergency services.
2. For the RIMS lab, use NABL's [current accredited-laboratory search](https://nabl-india.org/lab-accreditation-with-details/)
   and search CAB ID `M-1881` and certificate `MC-6127` under Medical. Save
   the result date, exact current status, scope, validity dates, and current
   certificate/record URL. If the live search is ambiguous or has no entry,
   request written clarification from NABL; do not treat the May 2026
   withdrawal list as current accreditation. Separately contact RIMS
   administration to establish whether the lab currently operates, its own
   physical address and contact details, and home-collection yes/no. The
   hospital address is not evidence of the lab's specific location.
3. Add doctors only after an exact NMC/State Council record has been found.
   Independently confirm local practice and affiliation. Link a speciality
   only when an explicit source supports it and its slug exists in the seeded
   active vocabulary.
4. Keep the access date, exact source/record URL, registry ID, captured
   evidence reference, and the fields supported by each source in this ledger.
   The current manifest schema does not store access dates or field-level
   evidence. Only after outstanding facts are resolved should an unverified
   draft manifest be prepared and previewed against the safe test database.

## Current status and schema/importer limitations

The district listings directly support each hospital's name, address, phone,
email, type and PIN as listed on 2026-10-23 (the pages say they were updated
Aug 06, 2026). They do not establish current operation, emergency-service
availability, specialities or hours. The Tuberculosis C&DST Laboratory has an
official historical withdrawal entry effective 2025-09-17; this research did
not establish whether it currently operates or whether it has since regained
accreditation. No doctor candidate has an identifiable official registration
record. Therefore **zero candidates are import-ready**.

The current models make `Hospital.emergency_services` and
`DiagnosticLab.home_sample_collection` non-nullable booleans with
`server_default=false`. The importer accepts only boolean values for these
fields, so omission stores `false`; it cannot preserve unknown. Pydantic create
schemas also default these fields to false. This is not safe evidence
handling: an unconfirmed value would look like a confirmed absence. The
provider models also set `is_active=true` by default, and the importer does
not accept that field. `is_active` is a publication/soft-disable flag and
should not be reused as operational status; the two meanings differ.

### Smallest safe design change (proposal only; not implemented)

1. Make `emergency_services` and `home_sample_collection` nullable booleans,
   remove their false server/Pydantic defaults, and let importer/API schemas
   accept `null`. `true`/`false` then mean sourced yes/no; `null` means
   unknown. Keep missing locations null/invalid rather than allowing the
   model's Raichur/Karnataka defaults to fill them silently.
2. Add a constrained `operational_status` field to hospital and diagnostic
   lab (and doctor for model consistency), with values such as `unknown`,
   `operating`, `temporarily_closed`, and `closed`. Do not infer this from
   `is_active` or `is_verified`. Expose it in response schemas and importer;
   decide in API/UI policy whether unknown providers are hidden or shown with
   an explicit unknown label before any such records are published.

Migration impact: a new Alembic revision must drop the false defaults and
`NOT NULL` constraint for the two service flags, then add an
`operational_status` column with an allowed-value check. Existing service
flag values cannot be reliably classified as explicit or defaulted; avoid
bulk rewriting them without record-level evidence. Existing rows should get
`operational_status='unknown'` rather than a guessed operating state. A
downgrade would have to collapse null service values to false and discard
operational status, so it is lossy if unknowns/statuses have been stored and
must be treated accordingly. The manifest/importer remain separate from this
ledger; no schema, importer, manifest, or data changes were made in this
research update.
