"use client";

import { Suspense, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getPackage, type PackageRecord } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { CardHeader } from "@/components/ui/card";
import { CardTitle } from "@/components/ui/card";
import { CardContent } from "@/components/ui/card";
import { buildPackageBookingHref, isBookableApiPackage, parsePackageId } from "@/lib/package-booking.mjs";

export default function PackageDetailPage() {
  return (
    <Suspense fallback={<section className="px-4 py-8 sm:py-12"><p role="status" className="text-sm text-ink-muted">Loading package details…</p></section>}>
      <PackageDetail />
    </Suspense>
  );
}

function PackageDetail() {
  const params = useParams<{ id: string }>();
  const parsedPackageId = parsePackageId(params.id);
  const packageId = parsedPackageId.kind === "valid" ? parsedPackageId.id : null;
  const [pkg, setPkg] = useState<PackageRecord | null>(null);
  const [loading, setLoading] = useState(packageId !== null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (packageId === null) return;
    let active = true;
    getPackage(packageId)
      .then((result) => {
        if (active) setPkg(result);
      })
      .catch(() => {
        if (active) setError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [packageId]);

  if (loading) {
    return (
      <section className="px-4 py-8 sm:py-12">
        <p role="status" className="text-sm text-ink-muted">Loading package details…</p>
      </section>
    );
  }

  if (error || !pkg) {
    return (
      <section className="px-4 py-8 sm:py-12">
        <div className="max-w-4xl mx-auto">
          <Link
            href="/packages"
            className="text-sm font-medium text-teal-700 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700"
          >
            Back to health packages
          </Link>
          <div className="mt-6 rounded-[var(--radius-card)] border border-solid border-border bg-background p-8 text-center shadow-[var(--shadow-card)]">
            <h1 className="text-xl font-bold text-ink">Package details unavailable</h1>
            <p className="mt-2 text-sm text-ink-muted">
              This package could not be loaded from the eCare API.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col lg:flex-row lg:items-start gap-8">
          <div className="flex-1">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <span className="mb-2 inline-flex items-center gap-1 rounded bg-navy-50 px-2.5 py-0.5 text-xs font-medium text-navy-700">
                  {pkg.is_demo ? "Demo/sample data" : !pkg.is_active ? "Inactive package" : pkg.is_verified ? "Verified" : "Unverified API data"}
                </span>
                <h1 className="text-3xl font-bold text-ink">{pkg.name}</h1>
                <p className="text-sm text-ink-muted">
                  {pkg.provider_name} \u00b7 {pkg.provider_type.replace("_", " ")}
                </p>
              </div>
              {pkg.is_verified && <Badge variant="verified">Verified</Badge>}
              {pkg.is_demo && <Badge variant="info">Demo data</Badge>}
            </div>
            <p className="text-ink-muted mb-6">{pkg.description ?? "No description provided."}</p>

            <div className="mb-6">
              <h3 className="text-lg font-semibold text-ink mb-3">Price</h3>
              <div className="text-2xl font-bold text-ink">
                {pkg.currency} {pkg.price}
              </div>
              <p className="text-xs text-ink-muted mt-1">
                One-time screening package price.
              </p>
            </div>

            <div className="mb-6">
              <h3 className="text-lg font-semibold text-ink mb-3">
                Included tests
              </h3>
              <div className="flex flex-wrap gap-2">
                {pkg.inclusions.map((inc) => (
                  <span
                    key={inc.id}
                    className="rounded-[var(--radius-control)] border border-solid border-border bg-navy-50 px-3 py-1.5 text-sm text-ink"
                  >
                    {inc.test_name}
                  </span>
                ))}
                {pkg.inclusions.length === 0 && (
                  <p className="text-xs text-ink-muted">No tests listed.</p>
                )}
              </div>
            </div>

            <div className="mb-6 p-4 rounded bg-teal-50 border border-solid border-teal-100">
              <h3 className="text-sm font-semibold text-teal-700 mb-2">
                Important notice
              </h3>
              <p className="text-sm text-teal-700">
                This package data is loaded from the eCare API. Pricing and
                availability must be confirmed directly with the provider.
                Demo records do not represent real transactions.
              </p>
            </div>

            <div className="mb-6">
              <h3 className="text-lg font-semibold text-ink mb-3">Details</h3>
              <dl className="grid grid-cols-1 gap-y-2 sm:grid-cols-2 text-sm">
                <dt className="text-ink-muted">Category</dt>
                <dd className="text-ink">{pkg.category}</dd>
                <dt className="text-ink-muted">Location</dt>
                <dd className="text-ink">{pkg.city}, {pkg.state}{pkg.locality ? ", " + pkg.locality : ""}</dd>
                <dt className="text-ink-muted">Provider type</dt>
                <dd className="text-ink">{pkg.provider_type}</dd>
                <dt className="text-ink-muted">Source</dt>
                <dd className="text-ink">{pkg.source ?? "Not specified"}</dd>
                {pkg.source_url && (
                  <>
                    <dt className="text-ink-muted">Source URL</dt>
                    <dd className="text-ink">
                      <a href={pkg.source_url} target="_blank" rel="noopener noreferrer" className="text-teal-700 underline">
                        View source
                      </a>
                    </dd>
                  </>
                )}
                <dt className="text-ink-muted">Verified</dt>
                <dd className="text-ink">
                  {pkg.is_verified && pkg.verified_at ? `Yes · ${new Date(pkg.verified_at).toLocaleDateString()}` : "No"}
                </dd>
              </dl>
            </div>
          </div>

          <div className="lg:w-80 flex-shrink-0">
            <Card className="sticky top-8">
              <CardHeader>
                <CardTitle>Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <Link href="/find?provider_type=doctor" className="mb-3 inline-flex w-full items-center justify-center rounded-[var(--radius-control)] bg-navy-900 px-5 py-2.5 text-base font-medium text-white hover:bg-navy-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700">
                  Explore Doctors
                </Link>
                {!isBookableApiPackage(pkg) ? (
                  <p role="status" className="rounded border border-warning bg-warning/5 p-3 text-sm text-ink">
                    {pkg.is_demo
                      ? "This demo/sample package is for display only. Online booking is unavailable."
                      : !pkg.is_active
                        ? "This package is currently inactive. Online booking is unavailable."
                        : "This package has not been verified with provider-supplied source details. Online booking is unavailable."}
                  </p>
                ) : (
                  <Link href={buildPackageBookingHref(pkg.id, pkg.city, pkg.locality)} className="inline-flex w-full items-center justify-center rounded-[var(--radius-control)] border border-solid border-border bg-background px-5 py-2.5 text-base font-medium hover:bg-navy-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700">
                    Book Now
                  </Link>
                )}
              </CardContent>
              <CardContent className="pt-4">
                <p className="text-xs text-ink-muted">
                  Booking requests are demo interactions only. A request is not
                  a confirmed booking until accepted by the provider. No real
                  payment is processed.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
}
