"use strict";

import { Badge } from "./ui/badge";
import Link from "next/link";

export interface PackageCardProps {
  id: string;
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
  title,
  provider,
  providerType,
  price,
  currency,
  includedTests,
  offerBadge,
  description,
}: PackageCardProps) {
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
          <Link href={`/booking?package_id=${encodeURIComponent(id)}`} className="inline-flex flex-1 items-center justify-center rounded-[var(--radius-control)] border border-solid border-border bg-background px-3 py-1.5 text-sm font-medium transition-colors hover:bg-navy-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700">
            Book Now
          </Link>
        </div>
        <p className="mt-3 text-xs text-ink-muted">
          Sample data — not real provider data.
        </p>
      </div>
    </Card>
  );
}

import { Card } from "./ui/card";
