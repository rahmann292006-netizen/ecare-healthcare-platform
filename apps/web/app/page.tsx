"use strict";

import Link from "next/link";
import { SearchBar } from "@/components/search-bar";
import { CategoryCard } from "@/components/category-card";
import { PackageCard } from "@/components/package-card";
import { DEMO_PACKAGES } from "@/lib/mock-data";

const categories = [
  {
    title: "Hospitals",
    description: "Discover hospitals and healthcare facilities near you.",
    count: "0",
    href: "/find?category=hospitals",
    icon: "H",
  },
  {
    title: "Doctors",
    description: "Find specialists and general practitioners.",
    count: "0",
    href: "/find?category=doctors",
    icon: "D",
  },
  {
    title: "Diagnostic Labs",
    description: "Book tests and health screenings.",
    count: "0",
    href: "/find?category=labs",
    icon: "L",
  },
  {
    title: "Health Checkups",
    description: "Explore preventive health packages.",
    count: "4",
    href: "/packages",
    icon: "+",
  },
];

export default function Home() {
  return (
    <div className="bg-background text-ink min-h-full">
      {/* Hero */}
      <section className="px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <span className="inline-flex items-center gap-2 rounded bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700 mb-4">
              Independent healthcare directory for Raichur
            </span>
            <h1 className="text-4xl sm:text-5xl font-bold text-ink mb-4 leading-tight">
              Your Health, Closer to Home.
            </h1>
            <p className="text-lg text-ink-muted max-w-2xl mx-auto">
              Discover hospitals, doctors, specialists, and diagnostic labs in
              Raichur. Users send appointment requests only — a request is not a
              confirmed booking.
            </p>
          </div>

          <SearchBar
            placeholder="Search hospitals, doctors, diagnostic labs..."
            onSearch={(query) => {
              if (typeof window !== "undefined") {
                window.location.href = `/find?search=${encodeURIComponent(query)}`;
              }
            }}
          />
        </div>
      </section>

      {/* Category cards */}
      <section className="px-4 sm:px-6 lg:px-8 py-12">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-ink mb-8">Explore by category</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {categories.map((cat) => (
              <CategoryCard key={cat.title} {...cat} />
            ))}
          </div>
        </div>
      </section>

      {/* Featured packages */}
      <section className="px-4 sm:px-6 lg:px-8 py-12 bg-navy-50">
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
            <div>
              <h2 className="text-2xl font-bold text-ink">Featured health packages</h2>
              <p className="text-sm text-ink-muted">
                Sample packages — not real provider data.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {DEMO_PACKAGES.map((pkg) => (
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
                Send an appointment request — a request is not a confirmed booking.
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-0.5 flex shrink-0 rounded bg-teal-700 px-2 py-0.5 text-xs font-bold text-white">4</span>
                All listings default to "Not verified" until confirmed by the provider.
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
