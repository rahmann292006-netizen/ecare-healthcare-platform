"use client";

import { useEffect, useMemo, useState } from "react";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { useDemoLocation } from "@/components/location-provider";
import { DEMO_LOCATIONS } from "@/lib/locations";
import { FICTIONAL_DOCTORS, FICTIONAL_HOSPITALS, FICTIONAL_LABS } from "@/lib/fictional-directory";
import { DEMO_PACKAGES } from "@/lib/mock-data";

export interface SearchBarProps { placeholder?: string; onSearch: (query: string, locality: string) => void; }
const HISTORY_KEY = "ecare_search_history";
const popularSearches = ["Cardiology", "Diabetes", "Blood test", "Paediatrics"];

export function SearchBar({ placeholder = "Search doctors, specialities, hospitals or diagnostic tests...", onSearch }: SearchBarProps) {
  const { locationId } = useDemoLocation();
  const [query, setQuery] = useState("");
  const [locality, setLocality] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const location = DEMO_LOCATIONS.find((item) => item.id === locationId) ?? DEMO_LOCATIONS[0];
  const suggestions = useMemo(() => {
    const text = query.trim().toLowerCase();
    if (text.length < 2) return [];
    const matches = [
      ...FICTIONAL_DOCTORS.filter((item) => item.locationId === locationId && `${item.name} ${item.specialities.map((s) => s.name).join(" ")}`.toLowerCase().includes(text)).map((item) => ({ label: item.name, hint: `${item.specialities[0].name} · sample` })),
      ...FICTIONAL_HOSPITALS.filter((item) => item.locationId === locationId && item.name.toLowerCase().includes(text)).map((item) => ({ label: item.name, hint: `Hospital · ${location.city} sample` })),
      ...FICTIONAL_LABS.filter((item) => item.locationId === locationId && item.name.toLowerCase().includes(text)).map((item) => ({ label: item.name, hint: `Laboratory · ${location.city} sample` })),
      ...DEMO_PACKAGES.filter((item) => item.locationId === locationId && item.title.toLowerCase().includes(text)).map((item) => ({ label: item.title, hint: "Sample package" })),
      ...["Cardiology", "Dermatology", "General Medicine", "Orthopaedics", "Paediatrics", "Neurology", "Dentistry", "Gynaecology", "ENT", "Ophthalmology"].filter((name) => name.toLowerCase().includes(text)).map((name) => ({ label: name, hint: "Speciality" })),
    ];
    return [...new Map(matches.map((item) => [item.label.toLowerCase(), item])).values()].slice(0, 7);
  }, [location.city, locationId, query]);

  useEffect(() => { try { const value: unknown = JSON.parse(window.localStorage.getItem(HISTORY_KEY) ?? "[]"); setHistory(Array.isArray(value) ? value.filter((item): item is string => typeof item === "string").slice(0, 5) : []); } catch { setHistory([]); } }, []);
  function remember(value: string) { const next = [value, ...history.filter((item) => item.toLowerCase() !== value.toLowerCase())].slice(0, 5); setHistory(next); window.localStorage.setItem(HISTORY_KEY, JSON.stringify(next)); }
  function submit(e: React.FormEvent) { e.preventDefault(); const value = query.trim(); if (!value && !locality.trim()) return; if (value) remember(value); setOpen(false); onSearch(value, locality.trim()); }
  function choose(value: string) { setQuery(value); remember(value); setOpen(false); onSearch(value, locality.trim()); }

  return <div className="relative mx-auto w-full max-w-5xl">
    <form onSubmit={submit} className="rounded-2xl border border-border bg-background p-3 shadow-[var(--shadow-card)] sm:p-4">
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(12rem,0.42fr)_auto] sm:items-end">
        <div className="min-w-0"><label htmlFor="home-search" className="mb-1 block text-xs font-medium text-ink-muted">What are you looking for?</label><Input id="home-search" className="h-14 text-base sm:text-lg" placeholder={placeholder} value={query} onFocus={() => setOpen(true)} onChange={(e) => { setQuery(e.target.value); setOpen(true); }} aria-label="Search doctors, specialities, hospitals or tests" aria-expanded={open && suggestions.length > 0} aria-controls="search-suggestions" autoComplete="off" /></div>
        <div><label htmlFor="search-locality" className="mb-1 block text-xs font-medium text-ink-muted">City or locality <span className="font-normal">(optional)</span></label><Input id="search-locality" className="h-14" value={locality} onChange={(event) => setLocality(event.target.value)} placeholder="Any location" autoComplete="address-level3" /></div>
        <div className="flex gap-2"><Button type="submit" variant="primary" size="lg" className="h-14 flex-1 sm:flex-none">Search</Button>{(query || locality) && <Button type="button" variant="outline" size="lg" className="h-14" onClick={() => { setQuery(""); setLocality(""); setOpen(false); }}>Clear</Button>}</div>
      </div>
    </form>
    {open && suggestions.length > 0 && <div id="search-suggestions" role="listbox" aria-label="Search suggestions" className="absolute z-30 mt-2 w-full overflow-hidden rounded-xl border border-border bg-background shadow-xl">{suggestions.map((item) => <button key={item.label} type="button" role="option" aria-selected="false" onMouseDown={(event) => event.preventDefault()} onClick={() => choose(item.label)} className="flex w-full items-center justify-between gap-3 border-b border-border px-4 py-3 text-left last:border-0 hover:bg-navy-50"><span className="font-medium text-ink">{item.label}</span><span className="text-xs text-ink-muted">{item.hint}</span></button>)}</div>}
    {!query && !locality && <div className="mt-3 flex flex-wrap items-center gap-2 text-xs"><span className="font-medium text-ink-muted">Popular:</span>{popularSearches.map((item) => <button key={item} type="button" onClick={() => choose(item)} className="rounded-full border border-border bg-background px-3 py-1.5 text-ink-muted hover:bg-teal-50">{item}</button>)}{history.length > 0 && <><span className="ml-1 font-medium text-ink-muted">Recent:</span>{history.slice(0, 3).map((item) => <button key={item} type="button" onClick={() => choose(item)} className="rounded-full bg-navy-50 px-3 py-1.5 text-ink-muted">{item}</button>)}<button type="button" onClick={() => { setHistory([]); window.localStorage.removeItem(HISTORY_KEY); }} className="underline underline-offset-2 text-ink-muted">Clear history</button></>}</div>}
  </div>;
}
