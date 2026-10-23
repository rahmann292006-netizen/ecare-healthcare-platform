"use strict";

import { DEMO_PACKAGES } from "@/lib/mock-data";
import { PackageCard } from "@/components/package-card";

export default function PackagesPage() {
  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-ink">Health Packages</h1>
            <p className="text-sm text-ink-muted">
              Preventive health checkup packages and screening offers.
            </p>
          </div>
          <span className="inline-flex items-center gap-1 rounded bg-teal-50 px-2.5 py-0.5 text-xs font-medium text-teal-700">
            Sample data
          </span>
        </div>

        <p className="text-sm text-ink-muted mb-6">
          Packages below are sample/demo data for illustration only. Real
          provider pricing and availability must be confirmed directly with the
          provider.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {DEMO_PACKAGES.map((pkg) => (
            <PackageCard key={pkg.id} {...pkg} />
          ))}
        </div>

        {DEMO_PACKAGES.length === 0 && (
          <div className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-12 text-center shadow-[var(--shadow-card)]">
            <p className="text-ink-muted">No packages available.</p>
          </div>
        )}
      </div>
    </section>
  );
}
