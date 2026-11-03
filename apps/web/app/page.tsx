"use client";

import { HomeSearch } from "@/components/home-search";
import { PackageCard } from "@/components/package-card";
import { DEMO_PACKAGES } from "@/lib/mock-data";
import { HomeDirectoryHighlights } from "@/components/home-directory-highlights";
import { FeaturedDoctorsCarousel } from "@/components/featured-doctors-carousel";
import { BrandBackground } from "@/components/brand-background";
import { useDemoLocation } from "@/components/location-provider";

export default function Home() {
  const { locationId } = useDemoLocation();
  return (
    <div className="bg-background text-ink min-h-full">
      {/* Hero */}
      <BrandBackground className="px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <span className="inline-flex items-center gap-2 rounded bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700 mb-4">
              Fictional healthcare directory demo
            </span>
            <h1 className="text-4xl sm:text-5xl font-bold text-ink mb-4 leading-tight">
              Your Health, Closer to Home.
            </h1>
            <p className="text-lg text-ink-muted max-w-2xl mx-auto">Explore fictional sample hospitals, doctors, and diagnostic labs. Profiles, schedules, fees, and availability are illustrative and do not represent real providers.</p>
          </div>

          <HomeSearch />
        </div>
      </BrandBackground>

      <HomeDirectoryHighlights />
      <FeaturedDoctorsCarousel />

      {/* Featured packages */}
      <section className="px-4 sm:px-6 lg:px-8 py-12 bg-navy-50">
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
            <div>
              <h2 className="text-2xl font-bold text-ink">Featured health packages</h2>
              <p className="text-sm text-ink-muted">
                Sample packages â€” not real provider data.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {DEMO_PACKAGES.filter((pkg) => pkg.locationId === locationId).map((pkg) => (
              <PackageCard key={pkg.id} {...pkg} />
            ))}
          </div>
        </div>
      </section>

      {/* Trust info */}
      <section className="px-4 sm:px-6 lg:px-8 py-12">
        <div className="max-w-5xl mx-auto">
          <div className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-6 shadow-[var(--shadow-card)]">
            <h3 className="text-lg font-semibold text-ink mb-3">How eCare works</h3>
            <ul className="space-y-3 text-sm text-ink-muted">
              <li className="flex items-start gap-3">
                <span className="mt-0.5 flex shrink-0 rounded bg-teal-700 px-2 py-0.5 text-xs font-bold text-white">1</span>
                Search for hospitals, doctors, or labs by name, specialty, or locality.
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-0.5 flex shrink-0 rounded bg-teal-700 px-2 py-0.5 text-xs font-bold text-white">2</span>
                View provider details and contact information.
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-0.5 flex shrink-0 rounded bg-teal-700 px-2 py-0.5 text-xs font-bold text-white">3</span>
                Send an appointment request â€” a request is not a confirmed booking.
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-0.5 flex shrink-0 rounded bg-teal-700 px-2 py-0.5 text-xs font-bold text-white">4</span>
                All listings default to &quot;Not verified&quot; until confirmed by the provider.
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
