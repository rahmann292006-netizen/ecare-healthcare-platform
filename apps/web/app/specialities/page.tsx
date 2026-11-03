"use client";

import Link from "next/link";
import { Card } from "@/components/ui/card";
import { useDemoLocation } from "@/components/location-provider";
import { FICTIONAL_DOCTORS, FICTIONAL_SPECIALITIES } from "@/lib/fictional-directory";
import { DEMO_LOCATIONS } from "@/lib/locations";

const descriptions: Record<string, string> = {
  Cardiology: "Illustrative profiles focused on heart and circulation care.",
  Dermatology: "Sample profiles for skin, hair, and nail care.",
  "General Medicine": "Demonstration listings for common adult health concerns.",
  Orthopaedics: "Illustrative profiles for bones, joints, and mobility.",
  Paediatrics: "Sample listings for children's health and development.",
  Neurology: "Demonstration profiles for the brain and nervous system.",
  Dentistry: "Illustrative profiles for oral and dental care.",
  "Obstetrics and Gynaecology": "Sample profiles for reproductive and maternal health.",
  ENT: "Demonstration listings for ear, nose, and throat care.",
  Ophthalmology: "Illustrative profiles for eye health and vision care.",
};

export default function SpecialitiesPage() {
  const { locationId } = useDemoLocation();
  const location = DEMO_LOCATIONS.find((item) => item.id === locationId) ?? DEMO_LOCATIONS[0];
  return <section className="px-4 py-8 sm:py-12"><div className="mx-auto max-w-6xl"><header className="mb-8"><p className="text-sm font-medium text-teal-700">Illustrative healthcare directory</p><h1 className="mt-2 text-3xl font-bold text-ink">Explore Specialities</h1><p className="mt-2 text-sm text-ink-muted">Browse the sample doctors listed in {location.label}. Counts are based on the current fictional directory.</p></header>
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{FICTIONAL_SPECIALITIES.map((speciality) => { const count = FICTIONAL_DOCTORS.filter((doctor) => doctor.locationId === locationId && doctor.specialities.some((item) => item.id === speciality.id)).length; return <Card key={speciality.id} className="flex flex-col p-5"><span className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-lg font-bold text-teal-700">✚</span><h2 className="text-lg font-semibold text-ink">{speciality.name}</h2><p className="mt-2 flex-1 text-sm text-ink-muted">{descriptions[speciality.name] ?? `Illustrative ${speciality.name.toLowerCase()} provider listings.`}</p><p className="mt-4 text-sm font-medium text-ink">{count} demo doctor{count === 1 ? "" : "s"} in {location.city}</p><Link href={`/find?provider_type=doctor&speciality=${speciality.id}&location=${encodeURIComponent(locationId)}`} className="mt-4 inline-flex items-center justify-center rounded-[var(--radius-control)] bg-navy-900 px-4 py-2 text-sm font-medium text-white hover:bg-navy-800">Explore</Link></Card>; })}</div>
  </div></section>;
}
