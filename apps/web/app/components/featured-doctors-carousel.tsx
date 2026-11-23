"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import { DoctorAvatar } from "@/components/doctor-avatar";
import { useDemoLocation } from "@/components/location-provider";
import { FICTIONAL_DOCTORS, getDoctorHospital, getDoctorSlots } from "@/lib/fictional-directory";
import { DEMO_LOCATIONS } from "@/lib/locations";
import { useCurrentTime } from "@/lib/use-current-time";

export function FeaturedDoctorsCarousel() {
  const { locationId } = useDemoLocation();
  const track = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(false);
  const doctors = useMemo(() => FICTIONAL_DOCTORS.filter((doctor) => doctor.locationId === locationId).slice(0, 5), [locationId]);
  const location = DEMO_LOCATIONS.find((item) => item.id === locationId) ?? DEMO_LOCATIONS[0];
  const nowTimestamp = useCurrentTime();

  const nextSlots = useMemo(() => {
    if (nowTimestamp === 0) return {};
    const now = new Date(nowTimestamp);
    const timeNow = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    const next: Record<number, { date: string; time: string } | null> = {};
    for (const doctor of doctors) {
      next[doctor.id] = null;
      for (let offset = 0; offset < 8; offset += 1) {
        const date = new Date(now);
        date.setDate(now.getDate() + offset);
        const dateKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
        const slot = getDoctorSlots(doctor, dateKey).find((item) => offset > 0 || item.time > timeNow);
        if (slot) { next[doctor.id] = { date: dateKey, time: slot.time }; break; }
      }
    }
    return next;
  }, [doctors, nowTimestamp]);

  useEffect(() => {
    if (paused || doctors.length < 2 || !track.current) return;
    const timer = window.setInterval(() => {
      const element = track.current;
      if (!element) return;
      const nextPosition = element.scrollLeft + element.clientWidth;
      if (nextPosition >= element.scrollWidth - 8) element.scrollTo({ left: 0, behavior: "smooth" });
      else element.scrollBy({ left: element.clientWidth * 0.8, behavior: "smooth" });
    }, 6500);
    return () => window.clearInterval(timer);
  }, [doctors.length, paused]);

  function move(direction: -1 | 1) { track.current?.scrollBy({ left: direction * (track.current.clientWidth * 0.8), behavior: "smooth" }); }

  return <section className="px-4 py-10 sm:px-6 lg:px-8"><div className="mx-auto max-w-5xl" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocusCapture={() => setPaused(true)} onBlurCapture={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setPaused(false); }}>
    <div className="mb-4 flex items-end justify-between gap-3"><div><p className="text-sm font-medium text-teal-700">Demo listings · {location.label}</p><h2 className="text-2xl font-bold text-ink">Sample Doctors</h2><p className="mt-1 text-sm text-ink-muted">Fictional profiles, not real providers. Booking is unavailable.</p></div><div className="flex gap-2"><button type="button" aria-label="Previous featured doctors" onClick={() => move(-1)} className="rounded-full border border-border bg-background px-3 py-2 text-ink hover:bg-navy-50">←</button><button type="button" aria-label="Next featured doctors" onClick={() => move(1)} className="rounded-full border border-border bg-background px-3 py-2 text-ink hover:bg-navy-50">→</button></div></div>
    {doctors.length ? <div ref={track} role="region" aria-roledescription="carousel" aria-label="Featured demo doctors; fictional and not bookable" className="flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-smooth pb-3">{doctors.map((doctor) => { const hospital = getDoctorHospital(doctor); const next = nextSlots[doctor.id]; return <Card key={doctor.id} className="w-[88%] shrink-0 snap-start p-5 sm:w-[48%] lg:w-[32%]"><div className="flex items-center gap-3"><DoctorAvatar id={doctor.id} name={doctor.name} /><div><h3 className="font-semibold text-ink">{doctor.name}</h3><p className="text-xs font-medium text-amber-800">Fictional demo · not a real provider</p></div></div><p className="mt-4 text-sm text-ink">{doctor.qualification}</p><p className="mt-1 text-sm text-ink-muted">{doctor.specialities[0].name} · {doctor.experienceYears} sample years</p><p className="mt-2 text-sm text-ink-muted">{hospital?.name}</p><p className="mt-1 text-sm text-ink-muted">Example consultation fee: ₹{doctor.consultationFee}</p><p className="mt-1 text-sm text-ink-muted">Next demo OPD: {next ? `${next.date} at ${next.time}` : "No slot in the next week"}</p><div className="mt-4 flex gap-2"><Link href={`/find/doctor/${doctor.id}?location=${encodeURIComponent(locationId)}&source=sample`} className="rounded-[var(--radius-control)] border border-border px-3 py-2 text-sm font-medium hover:bg-navy-50">View Demo Profile</Link><span className="rounded-[var(--radius-control)] bg-navy-50 px-3 py-2 text-sm font-medium text-ink-muted">Not bookable</span></div></Card>; })}</div> : <p className="rounded-xl bg-navy-50 p-6 text-sm text-ink-muted">No matching demo providers found in this location.</p>}
  </div></section>;
}
