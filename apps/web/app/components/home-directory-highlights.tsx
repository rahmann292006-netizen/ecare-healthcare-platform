"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { CategoryCard } from "@/components/category-card";
import { Card } from "@/components/ui/card";
import { listProviders } from "@/lib/api";
import { FICTIONAL_DOCTORS, FICTIONAL_HOSPITALS, FICTIONAL_LABS, getDoctorHospital, getDoctorSlots, type FictionalProvider } from "@/lib/fictional-directory";
import { useDemoLocation } from "@/components/location-provider";
import { DEMO_LOCATIONS } from "@/lib/locations";
import { DEMO_PACKAGES } from "@/lib/mock-data";
import { DoctorAvatar } from "@/components/doctor-avatar";
import { useCurrentTime } from "@/lib/use-current-time";

const providerTypesWithSamples = [
  { type: "hospital" as const },
  { type: "doctor" as const },
  { type: "lab" as const },
];
const categories = [
  { title: "Hospitals", description: "Discover hospitals and healthcare facilities near you.", href: "/find?category=hospitals", icon: "H", type: "hospital" as const, sampleCount: FICTIONAL_HOSPITALS.length },
  { title: "Doctors", description: "Find specialists and general practitioners.", href: "/find?category=doctors", icon: "D", type: "doctor" as const, sampleCount: FICTIONAL_DOCTORS.length },
  { title: "Diagnostic Labs", description: "Browse sample laboratory listings.", href: "/find?category=labs", icon: "L", type: "lab" as const, sampleCount: FICTIONAL_LABS.length },
  { title: "Health Checkups", description: "Explore preventive health packages.", href: "/packages", icon: "+", count: "4" },
];

export function HomeDirectoryHighlights() {
  const { locationId } = useDemoLocation();
  const location = DEMO_LOCATIONS.find((item) => item.id === locationId) ?? DEMO_LOCATIONS[0];
  const [counts, setCounts] = useState<Record<string, number | null>>({});
  const nowTimestamp = useCurrentTime();
  useEffect(() => {
    let active = true;
    Promise.all(providerTypesWithSamples.map(async (item) => {
      try {
        const response = await listProviders({ provider_type: item.type, city: location.city, limit: 100 });
        return [item.type, response.items.filter((provider) => !provider.is_demo).length] as const;
      } catch {
        return [item.type, null] as const;
      }
    })).then((results) => { if (active) setCounts(Object.fromEntries(results)); });
    return () => { active = false; };
  }, [location.city]);

  const availability = useMemo(() => {
    if (nowTimestamp === 0) return null;
    const now = new Date(nowTimestamp);
    const today = localDate(now);
    const timeNow = currentTime(now);
    const next: Record<number, { date: string; time: string; location: string } | null> = {};
    for (const doctor of FICTIONAL_DOCTORS) {
      next[doctor.id] = null;
      for (let offset = 0; offset < 8; offset += 1) {
        const day = new Date(now);
        day.setDate(now.getDate() + offset);
        const date = localDate(day);
        const slot = getDoctorSlots(doctor, date).find((item) => offset > 0 || item.time > timeNow);
        if (slot) { next[doctor.id] = { date, ...slot }; break; }
      }
    }
    return {
      today: FICTIONAL_DOCTORS.filter((doctor) => Boolean(next[doctor.id]?.date === today)),
      next,
    };
  }, [nowTimestamp]);

  const locationDoctors = useMemo(
    () => FICTIONAL_DOCTORS.filter((doctor) => doctor.locationId === locationId),
    [locationId],
  );
  const locationHospitals = FICTIONAL_HOSPITALS.filter((provider) => provider.locationId === locationId);
  const locationLabs = FICTIONAL_LABS.filter((provider) => provider.locationId === locationId);
  const packageCount = DEMO_PACKAGES.filter((item) => item.locationId === locationId).length;
  const recommended = locationDoctors.slice(0, 4);
  const recent = [...locationDoctors].sort((a, b) => (a.addedDaysAgo ?? 0) - (b.addedDaysAgo ?? 0)).slice(0, 4);
  const popular = useMemo(() => {
    const totals = new Map<string, number>();
    locationDoctors.forEach((doctor) => doctor.specialities.forEach((speciality) => totals.set(speciality.name, (totals.get(speciality.name) ?? 0) + 1)));
    return [...totals.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 5);
  }, [locationDoctors]);

  return <>
    <section className="px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl"><h2 className="mb-2 text-2xl font-bold text-ink">Explore by category</h2><p className="mb-6 text-sm text-ink-muted">Active API listings and fictional sample records are counted separately.</p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">{categories.map((item) => { const sampleCount = item.type === "hospital" ? locationHospitals.length : item.type === "doctor" ? locationDoctors.length : item.type === "lab" ? locationLabs.length : packageCount; const count = "count" in item ? String(sampleCount) : counts[item.type] === null || counts[item.type] === undefined ? `${sampleCount} sample` : `${counts[item.type]} active · ${sampleCount} sample`; const href = `${item.href}${item.href.includes("?") ? "&" : "?"}location=${encodeURIComponent(locationId)}`; return <CategoryCard key={item.title} title={item.title} description={item.description} icon={item.icon} href={href} count={count} />; })}</div>
      </div>
    </section>

    <section className="bg-navy-50 px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-sm font-medium text-teal-700">Illustrative healthcare listings · {location.label}</p><h2 className="text-2xl font-bold text-ink">Suggested Doctors</h2></div><Link href={`/find?provider_type=doctor&location=${encodeURIComponent(locationId)}`} className="text-sm font-semibold text-teal-700 underline underline-offset-2">View All Doctors</Link></div>
        <DoctorGroup title="Recommended Doctors" doctors={recommended} nextSlots={availability?.next ?? {}} />
        <section className="mt-8"><h3 className="mb-3 text-lg font-semibold text-ink">Available Today · demo availability</h3>{availability ? availability.today.filter((doctor) => doctor.locationId === locationId).length ? <DoctorGrid doctors={availability.today.filter((doctor) => doctor.locationId === locationId).slice(0, 4)} nextSlots={availability.next} /> : <p className="text-sm text-ink-muted">No matching demo providers found in this location for today.</p> : <p role="status" className="text-sm text-ink-muted">Checking illustrative availability…</p>}</section>
        <section className="mt-8"><div className="mb-3 flex items-center justify-between"><h3 className="text-lg font-semibold text-ink">Popular Specialities · {location.city}</h3><Link href={`/specialities?location=${encodeURIComponent(locationId)}`} className="text-sm font-medium text-teal-700 underline">View All Specialities</Link></div><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{popular.slice(0, 4).map(([name, count]) => { const speciality = FICTIONAL_DOCTORS.flatMap((doctor) => doctor.specialities).find((item) => item.name === name); return <Card key={name} className="p-4"><h4 className="font-semibold text-ink">{name}</h4><p className="mt-1 text-xs text-ink-muted">{count} illustrative profile{count === 1 ? "" : "s"} in {location.city}</p><Link href={`/find?provider_type=doctor&speciality=${speciality?.id}&location=${encodeURIComponent(locationId)}`} className="mt-3 inline-block text-sm font-medium text-teal-700 underline">Explore</Link></Card>; })}</div></section>
        <DoctorGroup title="Recently Added Doctors" doctors={recent} nextSlots={availability?.next ?? {}} className="mt-8" />
        <div className="mt-6"><Link href={`/find?provider_type=doctor&location=${encodeURIComponent(locationId)}`} className="inline-flex w-full items-center justify-center rounded-[var(--radius-control)] bg-navy-900 px-5 py-3 text-sm font-medium text-white hover:bg-navy-800 sm:w-auto">View All Doctors</Link></div>
      </div>
    </section>
  </>;
}

function DoctorGroup({ title, doctors, nextSlots, className = "" }: { title: string; doctors: FictionalProvider[]; nextSlots: Record<number, { date: string; time: string; location: string } | null>; className?: string }) {
  return <section className={className}><h3 className="mb-3 text-lg font-semibold text-ink">{title}</h3><DoctorGrid doctors={doctors} nextSlots={nextSlots} /></section>;
}

function DoctorGrid({ doctors, nextSlots }: { doctors: FictionalProvider[]; nextSlots: Record<number, { date: string; time: string; location: string } | null> }) {
  return <div className="grid gap-4 sm:grid-cols-2">{doctors.map((doctor) => <DoctorSuggestion key={doctor.id} doctor={doctor} next={nextSlots[doctor.id] ?? null} />)}</div>;
}

function DoctorSuggestion({ doctor, next }: { doctor: FictionalProvider; next: { date: string; time: string; location: string } | null }) {
  const hospital = getDoctorHospital(doctor);
  return <Card className="p-4">
    <div className="flex gap-3"><DoctorAvatar id={doctor.id} name={doctor.name} /><div className="min-w-0"><h4 className="font-semibold text-ink">{doctor.name}</h4><p className="text-xs text-ink-muted">Illustrative profile · not a real provider</p></div></div>
    <dl className="mt-3 space-y-1 text-sm"><div><dt className="inline text-ink-muted">Qualification: </dt><dd className="inline text-ink">{doctor.qualification}</dd></div><div><dt className="inline text-ink-muted">Speciality: </dt><dd className="inline text-ink">{doctor.specialities[0].name}</dd></div><div><dt className="inline text-ink-muted">Experience: </dt><dd className="inline text-ink">{doctor.experienceYears} fictional years</dd></div><div><dt className="inline text-ink-muted">Hospital: </dt><dd className="inline text-ink">{hospital?.name}</dd></div><div><dt className="inline text-ink-muted">Sample fee: </dt><dd className="inline text-ink">₹{doctor.consultationFee}</dd></div><div><dt className="inline text-ink-muted">Next sample slot: </dt><dd className="inline text-ink">{next ? `${next.date} · ${next.time}` : "No slot in the next week"}</dd></div></dl>
    <div className="mt-4 flex flex-col gap-2 sm:flex-row"><Link href={`/find/doctor/${doctor.id}?location=${encodeURIComponent(doctor.locationId)}`} className="inline-flex flex-1 items-center justify-center rounded-[var(--radius-control)] border border-border px-3 py-2 text-sm font-medium hover:bg-navy-50">View Profile</Link><Link href={`/booking?doctor_id=${doctor.id}&location=${encodeURIComponent(doctor.locationId)}`} className="inline-flex flex-1 items-center justify-center rounded-[var(--radius-control)] bg-navy-900 px-3 py-2 text-sm font-medium text-white hover:bg-navy-800">Book Appointment</Link></div>
  </Card>;
}

function localDate(date: Date) { return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`; }
function currentTime(date: Date) { return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`; }
