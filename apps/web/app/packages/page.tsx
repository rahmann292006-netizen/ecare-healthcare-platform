"use client";

import { useEffect, useState } from "react";
import { PackageCard } from "@/components/package-card";
import { useDemoLocation } from "@/components/location-provider";
import { DEMO_LOCATIONS } from "@/lib/locations";
import {
  listPackages,
  type PackageRecord,
} from "@/lib/api";

export default function PackagesPage() {
  const { locationId } = useDemoLocation();
  const location = DEMO_LOCATIONS.find((item) => item.id === locationId) ?? DEMO_LOCATIONS[0];
  const [packages, setPackages] = useState<PackageRecord[]>([]);
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const [error, setError] = useState<{ key: string; message: string } | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [retry, setRetry] = useState(0);
  const requestKey = JSON.stringify([categoryFilter, location.city, retry]);

  useEffect(() => {
    let active = true;
    const params: Record<string, string | number | boolean | undefined> = {
      is_active: "true",
      limit: 100,
    };
    if (categoryFilter) params.category = categoryFilter;
    if (location.city) params.city = location.city;

    listPackages(params)
      .then((response) => {
        if (!active) return;
        setPackages(response.items);
        setLoadedKey(requestKey);
        setError(null);
      })
      .catch(() => {
        if (!active) return;
        setError({ key: requestKey, message: "Could not load packages. Is the API running?" });
        setLoadedKey(requestKey);
      });

    return () => {
      active = false;
    };
  }, [categoryFilter, location.city, requestKey]);

  const loading = loadedKey !== requestKey;
  const visibleError = error?.key === requestKey ? error.message : null;

  const categories = ["checkup", "dental", "vaccination", "other"];
  const apiPackages = packages.filter((pkg) => !pkg.is_demo);
  const demoPackages = packages.filter((pkg) => pkg.is_demo);

  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-ink">Health Packages</h1>
            <p className="text-sm text-ink-muted">
              Preventive health checkup packages for {location.label}. Data is loaded from the eCare API.
            </p>
          </div>
          <span className="inline-flex items-center gap-1 rounded bg-teal-50 px-2.5 py-0.5 text-xs font-medium text-teal-700">
            {loading ? "Loading from API" : visibleError ? "API unavailable" : "Loaded from API"}
          </span>
        </div>

        <div className="mb-6 flex flex-wrap gap-2">
          <button
            onClick={() => setCategoryFilter("")}
            className={`rounded-[var(--radius-control)] border border-solid border-border px-3 py-1 text-xs font-medium ${!categoryFilter ? "bg-navy-900 text-white" : "bg-background text-ink hover:bg-navy-50"}`}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`rounded-[var(--radius-control)] border border-solid border-border px-3 py-1 text-xs font-medium ${categoryFilter === cat ? "bg-navy-900 text-white" : "bg-background text-ink hover:bg-navy-50"}`}
            >
              {cat}
            </button>
          ))}
        </div>

        {visibleError && (
          <div role="alert" className="rounded-[var(--radius-card)] border border-solid border-danger bg-danger/5 p-6">
            <p className="font-medium text-danger">{visibleError}</p>
            <button
              type="button"
              onClick={() => {
                setLoadedKey(null);
                setRetry((current) => current + 1);
              }}
              className="mt-3 rounded text-sm font-medium text-navy-900 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700"
            >
              Try again
            </button>
          </div>
        )}

        {!visibleError && loading ? (
          <p role="status" className="mb-4 text-sm text-ink-muted">Loading packages…</p>
        ) : !visibleError && !loading && packages.length === 0 ? (
          <div className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-12 text-center shadow-[var(--shadow-card)] sm:p-16">
            <h3 className="text-lg font-semibold text-ink">No packages available.</h3>
            <p className="mx-auto mt-2 max-w-xl text-sm text-ink-muted">
              No health checkup packages are currently listed for {location.city}.
            </p>
          </div>
        ) : !visibleError && !loading ? (
          <div className="space-y-8">
            {apiPackages.length > 0 && (
              <section aria-labelledby="api-packages">
                <h2 id="api-packages" className="mb-1 text-lg font-semibold text-ink">API-backed packages</h2>
                <p className="mb-3 text-sm text-ink-muted">Provider source and verification status are shown on each package. API-backed does not mean verified.</p>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {apiPackages.map((pkg) => <PackageCard key={pkg.id} id={pkg.id} city={pkg.city} locality={pkg.locality} isDemo={pkg.is_demo} isVerified={pkg.is_verified} isActive={pkg.is_active} source={pkg.source} verifiedAt={pkg.verified_at} title={pkg.name} provider={pkg.provider_name} providerType={pkg.provider_type} price={pkg.price} currency={pkg.currency} includedTests={pkg.inclusions.map((inc) => inc.test_name)} offerBadge={null} description={pkg.description ?? "No description provided."} />)}
                </div>
              </section>
            )}
            {demoPackages.length > 0 && (
              <section aria-labelledby="demo-packages">
                <h2 id="demo-packages" className="mb-1 text-lg font-semibold text-ink">Demo/sample packages — not real provider offers</h2>
                <p className="mb-3 text-sm text-ink-muted">Fictional display data only; these packages cannot be booked or subscribed to.</p>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {demoPackages.map((pkg) => <PackageCard key={pkg.id} id={pkg.id} city={pkg.city} locality={pkg.locality} isDemo={pkg.is_demo} isVerified={pkg.is_verified} isActive={pkg.is_active} source={pkg.source} verifiedAt={pkg.verified_at} title={pkg.name} provider={pkg.provider_name} providerType={pkg.provider_type} price={pkg.price} currency={pkg.currency} includedTests={pkg.inclusions.map((inc) => inc.test_name)} offerBadge={null} description={pkg.description ?? "No description provided."} />)}
                </div>
              </section>
            )}
          </div>
        ) : null}
      </div>
    </section>
  );
}
