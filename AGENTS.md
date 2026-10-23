# Project rules

- Keep work within two features only:
  1. Hospital and speciality finder, including locations, contact details, specialities, and explicit OPD information where available.
  2. Age-based health checkup packages and in-app reminders, including included tests, provider-supplied prices and validity, subscriptions, due dates, and upcoming/completed tracking.
- Do not add unrelated product modules.
- Never invent provider, package, test, price, validity, speciality, or OPD data. Clearly label sample or unverified records. Real provider/package data must retain its source, verification timestamp, and verification status.
- Never read or print `.env` files or secret values.
- Inspect the relevant code and make a short plan before coding.
- Ask before commands that change Git state or database state.
- Do not claim email, SMS, or push notifications; reminders are in-app only.
- Treat every package page as sample-only until real data is loaded from the API.
