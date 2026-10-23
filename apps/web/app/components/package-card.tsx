"use strict";

import { Badge } from "./ui/badge";
import { Button } from "./ui/button";

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
          <Button variant="primary" size="sm" className="flex-1">
            Subscribe
          </Button>
          <Button variant="outline" size="sm" className="flex-1">
            Request Booking
          </Button>
        </div>
        <p className="mt-3 text-xs text-ink-muted">
          Sample data — not real provider data.
        </p>
      </div>
    </Card>
  );
}

import { Card } from "./ui/card";
