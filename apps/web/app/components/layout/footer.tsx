"use strict";

export function Footer() {
  return (
    <footer
      className="mt-auto border-t border-solid border-border bg-navy-50 py-8"
      aria-label="Footer"
    >
      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-ink-muted">
          <p>
            eCare — Independent healthcare directory for Raichur, Karnataka.
          </p>
          <p>
            Users send appointment requests only — a request is not a confirmed
            booking. eCare is not an official partner of any hospital or lab.
          </p>
          <p>
            No medical records and no AI diagnosis in the MVP. Patient data
            must never be publicly exposed.
          </p>
        </div>
      </div>
    </footer>
  );
}
