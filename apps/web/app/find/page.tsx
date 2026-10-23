"use client";

import { useState, useEffect, useCallback } from "react";
import { SearchBar } from "@/components/search-bar";
import { ProviderCard } from "@/components/provider-card";
import {
  listHospitals,
  listDoctors,
  listLabs,
  Hospital,
  Doctor,
  DiagnosticLab,
} from "@/lib/api";

type ProviderType = "hospitals" | "doctors" | "labs";

interface ProviderCardItem {
  id: number | string;
  name: string;
  type: string;
  location: string;
  phone: string | null;
  verificationStatus: string;
  services?: string[];
}

export default function FindPage() {
  const [providerType, setProviderType] = useState<ProviderType>("hospitals");
  const [search, setSearch] = useState("");
  const [locality, setLocality] = useState("");
  const [providers, setProviders] = useState<ProviderCardItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  const fetchProviders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (providerType === "hospitals") {
        const res = await listHospitals({
          search: search || undefined,
          locality: locality || undefined,
          limit: 20,
        });
        setProviders(
          res.items.map((h: Hospital) => ({
            id: h.id,
            name: h.name,
            type: h.hospital_type || "Hospital",
            location: [h.locality, h.city, h.state]
              .filter(Boolean)
              .join(", "),
            phone: h.phone,
            verificationStatus: h.verification_status,
          }))
        );
        setTotal(res.total);
      } else if (providerType === "doctors") {
        const res = await listDoctors({
          search: search || undefined,
          limit: 20,
        });
        setProviders(
          res.items.map((d: Doctor) => ({
            id: d.id,
            name: d.full_name,
            type: d.specializations || "Doctor",
            location: d.hospital_id ? "Affiliated hospital" : "Independent",
            phone: d.phone,
            verificationStatus: d.verification_status,
          }))
        );
        setTotal(res.total);
      } else {
        const res = await listLabs({
          search: search || undefined,
          locality: locality || undefined,
          limit: 20,
        });
        setProviders(
          res.items.map((l: DiagnosticLab) => ({
            id: l.id,
            name: l.name,
            type: "Diagnostic Lab",
            location: [l.locality, l.city, l.state]
              .filter(Boolean)
              .join(", "),
            phone: l.phone,
            verificationStatus: l.verification_status,
            services: l.home_sample_collection
              ? ["Home sample collection"]
              : undefined,
          }))
        );
        setTotal(res.total);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load providers. Is the backend running on port 8000?"
      );
      setProviders([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [providerType, search, locality]);

  useEffect(() => {
    void Promise.resolve().then(fetchProviders);
  }, [fetchProviders]);

  const typeLabels: Record<ProviderType, string> = {
    hospitals: "Hospitals",
    doctors: "Doctors",
    labs: "Diagnostic Labs",
  };

  if (loading && providers.length === 0) {
    return (
      <section className="px-4 py-12">
        <div className="max-w-5xl mx-auto">
          <SearchBar
            placeholder="Search hospitals, doctors, labs..."
            onSearch={(q) => setSearch(q)}
          />
          <div className="mt-8 flex justify-center">
            <div className="flex flex-col items-center gap-2 text-ink-muted">
              <p className="animate-pulse">Loading providers…</p>
            </div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-col lg:flex-row lg:items-start gap-6 mb-8">
          <SearchBar
            placeholder="Search hospitals, doctors, labs..."
            onSearch={(q) => setSearch(q)}
          />
          <div className="flex gap-2">
            {["hospitals", "doctors", "labs"].map((t) => (
              <button
                key={t}
                onClick={() => setProviderType(t as ProviderType)}
                className={`px-4 py-2 rounded-[var(--radius-control)] text-sm font-medium border border-solid transition-colors ${
                  providerType === t
                    ? "bg-navy-900 border-navy-900 text-white"
                    : "border-border bg-background text-ink hover:bg-navy-50 border-border"
                }`}
              >
                {typeLabels[t as ProviderType]}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="rounded bg-danger/10 border border-solid border-danger p-4 mb-6 text-danger">
            {error}
          </div>
        )}

        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-ink">
            {total} {typeLabels[providerType]} found
          </h2>
          <input
            type="text"
            value={locality}
            onChange={(e) => setLocality(e.target.value)}
            placeholder="Filter by locality"
            className="rounded-[var(--radius-control)] border border-solid border-border bg-background px-3 py-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-navy-700"
          />
        </div>

        {providers.length === 0 && !error && !loading ? (
          <div className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-12 text-center shadow-[var(--shadow-card)]">
            <p className="text-ink-muted">No providers found.</p>
            {search || locality ? (
              <button
                onClick={() => {
                  setSearch("");
                  setLocality("");
                }}
                className="mt-4 text-sm font-medium text-teal-700 hover:underline"
              >
                Clear filters
              </button>
            ) : null}
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {providers.map((p) => (
              <ProviderCard
                key={p.id}
                id={p.id}
                name={p.name}
                type={p.type}
                location={p.location}
                phone={p.phone}
                verificationStatus={p.verificationStatus}
                services={p.services}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
