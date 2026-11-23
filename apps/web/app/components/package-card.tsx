"use client";

import { Badge } from "./ui/badge";
import Link from "next/link";
import { Card } from "./ui/card";
import { buildPackageBookingHref } from "@/lib/package-booking.mjs";

export interface PackageCardProps {
  id: number | string;
  city?: string;
  locality?: string | null;
  isDemo?: boolean;
  isSample?: boolean;
  isVerified?: boolean;
  isActive?: boolean;
  source?: string | null;
  verifiedAt?: string | null;
  locationId?: string;
  title: string;
  provider: string;
  providerType: string;
  price: number;
  currency: string;
  includedTests: string[];
  offerBadge: string | null;
  description: string;
}

export function PackageCard({
  id,
  city,
  locality,
  isDemo,
  isSample,
  isVerified = false,
  isActive = true,
  source,
  verifiedAt,
  title,
  provider,
  providerType,
  price,
  currency,
  includedTests,
  offerBadge,
  description,
}: PackageCardProps) {
  const demoPackage = isDemo ?? isSample ?? false;
  const bookable = !demoPackage && isActive && isVerified && Boolean(source?.trim()) && Boolean(verifiedAt?.trim());

  return (
    <Card className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-4 shadow-[var(--shadow-card)]">
      <div className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-lg font-semibold text-ink">{title}</h3>
            <p className="text-sm text-ink-muted">{provider} · {providerType.replace("_", " ")}</p>
          </div>
          {offerBadge && (
            <Badge variant="verified">{offerBadge}</Badge>
          )}
          {!offerBadge && (demoPackage ? (
            <Badge variant="info">Demo only - not a real offer</Badge>
          ) : isVerified ? (
            <Badge variant="verified">Verified</Badge>
          ) : (
            <Badge variant="unverified">Unverified</Badge>
          ))}
        </div>
        <p className="text-sm text-ink-muted line-clamp-2">{description}</p>
        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {includedTests.slice(0, 4).map((test) => (
              <span
                key={test}
                className="rounded-[var(--radius-control)] border border-solid border-border bg-navy-50 px-2.5 py-1 text-xs text-ink"
              >
                {test}
              </span>
            ))}
            {includedTests.length > 4 && (
              <span className="rounded-[var(--radius-control)] border border-solid border-border bg-navy-50 px-2.5 py-1 text-xs text-ink-muted">
                +{includedTests.length - 4} more
              </span>
            )}
          </div>
          <span className="text-lg font-bold text-ink">{currency} {price}</span>
        </div>
        <div className="mt-4 flex gap-2">
          <Link href="/find?provider_type=doctor" className="inline-flex flex-1 items-center justify-center rounded-[var(--radius-control)] bg-navy-900 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-navy-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700">
            Explore
          </Link>
          {!bookable ? (
            <span className="inline-flex flex-1 items-center justify-center rounded-[var(--radius-control)] border border-solid border-border bg-navy-50 px-3 py-1.5 text-center text-xs text-ink-muted">
              Online booking unavailable
            </span>
          ) : (
            <Link href={buildPackageBookingHref(id, city ?? null, locality ?? null)} className="inline-flex flex-1 items-center justify-center rounded-[var(--radius-control)] border border-solid border-border bg-background px-3 py-1.5 text-sm font-medium transition-colors hover:bg-navy-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700">
              Book Now
            </Link>
          )}
        </div>
        <p className="mt-3 text-xs text-ink-muted">
          {demoPackage
            ? "Demo/sample package — not bookable online."
            : bookable
              ? "Provider-sourced and verified package data."
              : "Unverified or incomplete provider data — not bookable online."}
        </p>
      </div>
    </Card>
  );
}
