"use strict";

import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function ProviderPage() {
  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold text-ink mb-2">Provider Dashboard</h1>
        <p className="text-sm text-ink-muted mb-8">
          Demo view for healthcare providers. Manage your package listings.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard title="Active listings" value="0" subtitle="No listings published" />
          <StatCard title="Subscriptions" value="0" subtitle="No active subscriptions" />
          <StatCard title="Pending requests" value="0" subtitle="No pending bookings" />
          <StatCard title="Verified" value="No" subtitle="Listing verification status" />
        </div>

        <div className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-6 shadow-[var(--shadow-card)]">
          <h2 className="text-xl font-bold text-ink mb-4">Manage package listings</h2>
          <p className="text-sm text-ink-muted mb-6">
            Package management is demo functionality. No real listings are
            created or modified.
          </p>
          <div className="rounded bg-teal-50 border border-solid border-teal-100 p-4">
            <h3 className="text-sm font-semibold text-teal-700 mb-2">How to add packages</h3>
            <p className="text-sm text-teal-700 mb-3">
              Providers can add or edit package listings through the backend
              API (write endpoints require development-mode authorization).
            </p>
            <Button variant="outline" size="sm" asChild>
              <Link href="/packages">Browse packages</Link>
            </Button>
          </div>
        </div>

        <p className="mt-8 text-xs text-ink-muted">
          This is a demo provider view. No actual provider accounts,
          authentication, or data modification exists.
        </p>
      </div>
    </section>
  );
}

function StatCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string | number;
  subtitle: string;
}) {
  return (
    <Card className="rounded-[var(--radius-card)] p-4">
      <p className="text-sm font-medium text-ink">{title}</p>
      <p className="text-2xl font-bold text-ink mt-1">{value}</p>
      <p className="text-xs text-ink-muted">{subtitle}</p>
    </Card>
  );
}
