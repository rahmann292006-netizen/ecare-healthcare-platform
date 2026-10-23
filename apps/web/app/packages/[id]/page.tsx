"use strict";

import { notFound } from "next/navigation";
import { DEMO_PACKAGES } from "@/lib/mock-data";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default async function PackageDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const pkg = DEMO_PACKAGES.find((p) => p.id === id);

  if (!pkg) {
    notFound();
  }

  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col lg:flex-row lg:items-start gap-8">
          <div className="flex-1">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <span className="inline-flex items-center gap-1 rounded bg-teal-50 px-2.5 py-0.5 text-xs font-medium text-teal-700 mb-2">
                  Sample data
                </span>
                <h1 className="text-3xl font-bold text-ink">{pkg.title}</h1>
                <p className="text-sm text-ink-muted">
                  {pkg.provider} &middot; {pkg.providerType.replace(
                    "_",
                    " "
                  )}
                </p>
              </div>
              {pkg.offerBadge && (
                <Badge variant="verified">{pkg.offerBadge}</Badge>
              )}
            </div>
            <p className="text-ink-muted mb-6">{pkg.description}</p>

            <div className="mb-6">
              <h3 className="text-lg font-semibold text-ink mb-3">
                Price
              </h3>
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
                {pkg.includedTests.map((test) => (
                  <span
                    key={test}
                    className="rounded-[var(--radius-control)] border border-solid border-border bg-navy-50 px-3 py-1.5 text-sm text-ink"
                  >
                    {test}
                  </span>
                ))}
              </div>
            </div>

            <div className="mb-6 p-4 rounded bg-teal-50 border border-solid border-teal-100">
              <h3 className="text-sm font-semibold text-teal-700 mb-2">
                Important notice
              </h3>
              <p className="text-sm text-teal-700">
                This is sample data for demonstration purposes. It does not
                represent real provider data, pricing, or availability. Contact
                the provider directly to confirm details and book.
              </p>
            </div>
          </div>

          <div className="lg:w-80 flex-shrink-0">
            <Card className="sticky top-8">
              <CardHeader>
                <CardTitle>Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <Button variant="primary" className="w-full mb-3">
                  Subscribe to package
                </Button>
                <Button variant="outline" className="w-full">
                  Request booking
                </Button>
              </CardContent>
              <CardContent className="pt-4">
                <p className="text-xs text-ink-muted">
                  Booking and subscription requests are demo interactions only.
                  No actual booking, payment, or confirmation occurs.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
}

import { Card } from "@/components/ui/card";
import { CardHeader } from "@/components/ui/card";
import { CardTitle } from "@/components/ui/card";
import { CardContent } from "@/components/ui/card";
