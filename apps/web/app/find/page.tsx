"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ProviderCard } from "@/components/provider-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  listProviders,
  listSpecialities,
  type ProviderDirectoryItem,
  type ProviderSort,
  type ProviderType,
  type Speciality,
} from "@/lib/api";
import { FICTIONAL_PROVIDERS, FICTIONAL_SPECIALITIES, type FictionalProvider } from "@/lib/fictional-directory";
import { useDemoLocation } from "@/components/location-provider";
import { DEMO_LOCATIONS } from "@/lib/locations";

const PAGE_SIZE = 20;

const providerLabels: Record<ProviderType, string> = {
  hospital: "Hospitals",
  doctor: "Doctors",
  lab: "Diagnostic labs",
  opd: "OPDs",
};

const providerTypes: Array<{ value: ProviderType | ""; label: string }> = [
  { value: "", label: "All provider types" },
  { value: "hospital", label: "Hospitals" },
  { value: "doctor", label: "Doctors" },
  { value: "lab", label: "Diagnostic labs" },
  { value: "opd", label: "OPDs" },
];

export default function FindPage() {
  return (
    <Suspense fallback={<p role="status" className="px-4 py-8 text-sm text-ink-muted">Loading provider directory...</p>}>
      <FindDirectory />
    </Suspense>
  );
}

function FindDirectory() {
  const searchParams = useSearchParams();
  const { setLocationId } = useDemoLocation();
  const requestedLocation = searchParams.get("location");
  const requestedType = searchParams.get("provider_type") ?? searchParams.get("category");
  const typeAliases: Record<string, ProviderType> = {
    hospitals: "hospital",
    doctors: "doctor",
    labs: "lab",
    opds: "opd",
  };
  const normalizedType = requestedType
    ? typeAliases[requestedType] ?? requestedType
    : "";
  const initialProviderType = ["hospital", "doctor", "lab", "opd"].includes(normalizedType)
    ? (normalizedType as ProviderType)
    : "";
  const initialSearch = searchParams.get("search") ?? "";
  const [providerType, setProviderType] = useState<ProviderType | "">(initialProviderType);
  const [specialityId, setSpecialityId] = useState(searchParams.get("speciality") ?? searchParams.get("speciality_id") ?? "");
  const [locality, setLocality] = useState(searchParams.get("locality") ?? "");
  const [cityFilter, setCityFilter] = useState(requestedLocation && DEMO_LOCATIONS.some((item) => item.id === requestedLocation) ? requestedLocation : "");
  const [searchInput, setSearchInput] = useState(initialSearch);
  const [search, setSearch] = useState(initialSearch);
  const [sort, setSort] = useState<ProviderSort>("name_asc");
  const [offset, setOffset] = useState(0);
  const [providers, setProviders] = useState<Array<ProviderDirectoryItem | FictionalProvider>>([]);
  const [specialities, setSpecialities] = useState<Speciality[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [specialityError, setSpecialityError] = useState(false);
  const requestNumber = useRef(0);

  useEffect(() => {
    if (requestedLocation && DEMO_LOCATIONS.some((item) => item.id === requestedLocation)) setLocationId(requestedLocation);
  }, [requestedLocation, setLocationId]);

  useEffect(() => {
    let active = true;
    setSpecialities(FICTIONAL_SPECIALITIES);
    listSpecialities()
      .then((items) => {
        if (active) setSpecialities([...FICTIONAL_SPECIALITIES, ...items.filter((item) => !FICTIONAL_SPECIALITIES.some((demo) => demo.name.toLowerCase() === item.name.toLowerCase()))]);
      })
      .catch(() => {
        if (active) setSpecialityError(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const fetchProviders = useCallback(async () => {
    const requestId = ++requestNumber.current;
    setLoading(true);
    setError(null);
    try {
      let liveProviders: ProviderDirectoryItem[] = [];
      try {
        const selectedLocation = DEMO_LOCATIONS.find((item) => item.id === cityFilter);
        const response = await listProviders({ provider_type: providerType || undefined, city: selectedLocation?.city, locality: locality.trim() || undefined, limit: 100 });
        liveProviders = response.items;
      } catch {
        // Fictional sample directory remains usable without a running API.
      }
      const localProviders = FICTIONAL_PROVIDERS.filter((item) => (!cityFilter || item.locationId === cityFilter) && (!locality.trim() || `${item.locality ?? ""} ${item.city ?? ""}`.toLowerCase().includes(locality.trim().toLowerCase())));
      let combined: Array<ProviderDirectoryItem | FictionalProvider> = [...localProviders, ...liveProviders];
      if (providerType) combined = combined.filter((item) => item.provider_type === providerType);
      if (specialityId) combined = combined.filter((item) => item.specialities.some((value) => value.id === Number(specialityId)));
      if (locality.trim()) combined = combined.filter((item) => `${item.locality ?? ""} ${item.city ?? ""}`.toLowerCase().includes(locality.trim().toLowerCase()));
      if (search) combined = combined.filter((item) => `${item.name} ${item.description ?? ""} ${item.specialities.map((value) => value.name).join(" ")}`.toLowerCase().includes(search.toLowerCase()));
      combined.sort((a, b) => sort === "name_asc" ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name));
      if (requestId !== requestNumber.current) return;
      setProviders(combined.slice(offset, offset + PAGE_SIZE));
      setTotal(combined.length);
    } catch {
      if (requestId !== requestNumber.current) return;
      setError("We couldn't load the provider directory. Please try again.");
    } finally {
      if (requestId === requestNumber.current) setLoading(false);
    }
  }, [cityFilter, locality, offset, providerType, search, sort, specialityId]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => void fetchProviders(), 0);
    return () => {
      window.clearTimeout(timeoutId);
      requestNumber.current += 1;
    };
  }, [fetchProviders]);

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOffset(0);
    setSearch(searchInput.trim());
  }

  function clearFilters() {
    setProviderType("");
    setSpecialityId("");
    setLocality("");
    setCityFilter("");
    setSearchInput("");
    setSearch("");
    setSort("name_asc");
    setOffset(0);
  }

  function updateProviderType(value: string) {
    setProviderType(value as ProviderType | "");
    if (value === "lab" || value === "opd") setSpecialityId("");
    setOffset(0);
  }

  const specialityFilterSupported = providerType !== "lab" && providerType !== "opd";
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + providers.length, total);
  const hasFilters = Boolean(providerType || specialityId || locality || search);

  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8">
          <p className="mb-2 text-sm font-medium text-teal-700">Provider directory</p>
          <h1 className="text-3xl font-bold text-ink">Find healthcare near you</h1>
          <p className="mt-2 max-w-2xl text-sm text-ink-muted">
              Search hospitals, doctors, diagnostic labs, and OPDs. Fictional sample
              listings are marked; live API records are included when available.
          </p>
        </header>

        <form
          onSubmit={handleSearchSubmit}
          className="mb-6 rounded-[var(--radius-card)] border border-solid border-border bg-background p-4 shadow-[var(--shadow-card)] sm:p-6"
        >
          <div className="mb-5 flex flex-col gap-2 sm:flex-row">
            <div className="flex-1">
              <label htmlFor="provider-search" className="mb-1 block text-sm font-medium text-ink">
                Search by provider name
              </label>
              <Input
                id="provider-search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="For example, a hospital or lab name"
                autoComplete="off"
              />
            </div>
            <div className="flex items-end">
              <Button type="submit" variant="primary" className="w-full sm:w-auto">
                Search
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <div>
              <label htmlFor="provider-location" className="mb-1 block text-sm font-medium text-ink">City filter (optional)</label>
              <Select id="provider-location" value={cityFilter} onChange={(event) => { setCityFilter(event.target.value); if(event.target.value) setLocationId(event.target.value); setOffset(0); }}>
                <option value="">All locations</option>{DEMO_LOCATIONS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </Select>
            </div>
            <div>
              <label htmlFor="provider-type" className="mb-1 block text-sm font-medium text-ink">
                Provider type
              </label>
              <Select
                id="provider-type"
                value={providerType}
                onChange={(event) => updateProviderType(event.target.value)}
              >
                {providerTypes.map((item) => (
                  <option key={item.value || "all"} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <label htmlFor="provider-speciality" className="mb-1 block text-sm font-medium text-ink">
                Speciality
              </label>
              <Select
                id="provider-speciality"
                value={specialityId}
                disabled={!specialityFilterSupported || specialities.length === 0}
                onChange={(event) => {
                  setSpecialityId(event.target.value);
                  setOffset(0);
                }}
                aria-describedby="speciality-help"
              >
                <option value="">All specialities</option>
                {specialities.map((speciality) => (
                  <option key={speciality.id} value={speciality.id}>
                    {speciality.name}
                  </option>
                ))}
              </Select>
              <p id="speciality-help" className="mt-1 text-xs text-ink-muted">
                  {!specialityFilterSupported
                    ? "Speciality filtering is available for hospitals and doctors."
                      : specialityError
                        ? "Showing fictional sample specialities; API specialities could not be loaded."
                        : "Fictional sample specialities and API records are available."}
              </p>
            </div>

            <div>
              <label htmlFor="provider-locality" className="mb-1 block text-sm font-medium text-ink">
                Locality
              </label>
              <Input
                id="provider-locality"
                value={locality}
                onChange={(event) => {
                  setLocality(event.target.value);
                  setOffset(0);
                }}
                placeholder="Any city or locality"
                autoComplete="address-level3"
              />
            </div>

            <div>
              <label htmlFor="provider-sort" className="mb-1 block text-sm font-medium text-ink">
                Sort by name
              </label>
              <Select
                id="provider-sort"
                value={sort}
                onChange={(event) => {
                  setSort(event.target.value as ProviderSort);
                  setOffset(0);
                }}
              >
                <option value="name_asc">A to Z</option>
                <option value="name_desc">Z to A</option>
              </Select>
            </div>
          </div>

          {hasFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="mt-4 rounded text-sm font-medium text-teal-700 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700"
            >
              Clear filters
            </button>
          )}
        </form>

        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-xl font-bold text-ink" aria-live="polite">
            {total} {total === 1 ? "provider" : "providers"} found
          </h2>
          {total > 0 && (
            <p className="text-sm text-ink-muted">
              Showing {pageStart}–{pageEnd} of {total}
            </p>
          )}
        </div>

        {loading && (
          <p role="status" aria-live="polite" className="mb-4 text-sm text-ink-muted">
            Loading providers…
          </p>
        )}

        {error ? (
          <div role="alert" className="rounded-[var(--radius-card)] border border-solid border-danger bg-danger/5 p-6">
            <p className="font-medium text-danger">{error}</p>
            <button
              type="button"
              onClick={() => void fetchProviders()}
              className="mt-3 rounded text-sm font-medium text-navy-900 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700"
            >
              Try again
            </button>
          </div>
        ) : !loading && providers.length === 0 ? (
          <div className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-8 text-center shadow-[var(--shadow-card)] sm:p-12">
            <h3 className="text-lg font-semibold text-ink">
              {hasFilters ? "No matching demo providers found in this location." : "No provider listings available yet"}
            </h3>
            <p className="mx-auto mt-2 max-w-xl text-sm text-ink-muted">
              {hasFilters
                ? "Try another speciality or search term in the selected location."
                : "The directory currently has no provider records. Listings will appear here when source-backed provider information is added."}
            </p>
            {hasFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="mt-4 rounded text-sm font-medium text-teal-700 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <div aria-busy={loading} className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {providers.map((provider) => (
              <ProviderCard
                key={`${provider.provider_type}-${provider.id}`}
                provider={provider}
                typeLabel={providerLabels[provider.provider_type]}
              />
            ))}
          </div>
        )}

        {!error && total > PAGE_SIZE && (
          <nav aria-label="Provider result pages" className="mt-6 flex items-center justify-between">
            <Button
              type="button"
              variant="secondary"
              disabled={offset === 0 || loading}
              onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
            >
              Previous
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={offset + PAGE_SIZE >= total || loading}
              onClick={() => setOffset((current) => current + PAGE_SIZE)}
            >
              Next
            </Button>
          </nav>
        )}
      </div>
    </section>
  );
}
