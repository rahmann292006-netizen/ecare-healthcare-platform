"use strict";

import Link from "next/link";
import { Badge } from "./ui/badge";

export interface ProviderCardProps {
  id: number | string;
  name: string;
  type: string;
  location: string;
  phone: string | null;
  verificationStatus: string;
  services?: string[];
  onDetails?: () => void;
}

export function ProviderCard({
  id,
  name,
  type,
  location,
  phone,
  verificationStatus,
  services,
  onDetails,
}: ProviderCardProps) {
  const statusMap: Record<string, { label: string; variant: NonNullable<React.ComponentProps<typeof Badge>["variant"]> }> = {
    verified: { label: "Verified", variant: "verified" },
    pending: { label: "Pending", variant: "stale" },
    rejected: { label: "Rejected", variant: "unverified" },
    unverified: { label: "Not verified", variant: "unverified" },
  };
  const status = statusMap[verificationStatus] || statusMap.unverified;

  return (
    <Card className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-4 shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-card)] transition-shadow">
      <div className="flex flex-col md:flex-row md:items-center gap-4">
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <h3 className="text-lg font-semibold text-ink">{name}</h3>
            <Badge variant={status.variant}>{status.label}</Badge>
          </div>
          <p className="text-sm text-ink-muted">{type}</p>
          <p className="text-sm text-ink muted">{location}</p>
          {phone && (
            <p className="text-sm text-ink muted">📞 {phone}</p>
          )}
          {services && services.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {services.map((s) => (
                <span
                  key={s}
                  className="rounded-[var(--radius-control)] border border-solid border-border bg-navy-50 px-2.5 py-1 text-xs text-ink"
                >
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-end gap-2">
          {onDetails ? (
            <button
              onClick={onDetails}
              className="rounded-[var(--radius-control)] border border-solid border-border bg-background px-4 py-2 text-sm font-medium text-ink hover:bg-navy-50"
              aria-label={`View details for ${name}`}
            >
              Details
            </button>
          ) : (
            <Link
              href={`/find?provider=${id}`}
              className="rounded-[var(--radius-control)] bg-navy-900 px-4 py-2 text-sm font-medium text-white hover:bg-navy-800"
            >
              Details
            </Link>
          )}
        </div>
      </div>
    </Card>
  );
}

import { Card } from "./ui/card";
