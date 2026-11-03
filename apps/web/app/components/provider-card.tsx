import Link from "next/link";
import type { ProviderDirectoryItem } from "@/lib/api";
import { getDoctorHospital, type FictionalProvider } from "@/lib/fictional-directory";
import { Badge } from "./ui/badge";
import { Card } from "./ui/card";
import { DoctorAvatar } from "@/components/doctor-avatar";
import { locationIdFor } from "@/lib/locations";

export interface ProviderCardProps {
  provider: FictionalProvider | ProviderDirectoryItem;
  typeLabel: string;
}

export function ProviderCard({ provider, typeLabel }: ProviderCardProps) {
  const providerSubType =
    provider.provider_type === "hospital"
      ? provider.hospital_type
      : provider.provider_type === "opd"
        ? provider.opd_type
        : null;
  const location = [provider.locality, provider.city, provider.state]
    .filter(Boolean)
    .join(", ");
  const fictional = provider as FictionalProvider;
  const providerLocationId = fictional.locationId ?? locationIdFor(provider.city, provider.state);
  const associatedHospital = provider.provider_type === "doctor" ? getDoctorHospital(fictional) : undefined;
  const privateSessions = fictional.schedule ? Object.values(fictional.schedule.privateOpd).filter(Boolean) : [];

  return (
    <Card className="p-4 transition-shadow hover:shadow-[var(--shadow-card)]">
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-3">
            {provider.provider_type === "doctor" && <DoctorAvatar id={provider.id} name={provider.name} size="sm" />}
            <h3 className="text-lg font-semibold text-ink">{provider.name}</h3>
          </div>
            <Badge variant={provider.is_verified ? "verified" : "unverified"}>
              {provider.is_verified ? "Verified" : "Unverified"}
            </Badge>
            {provider.is_demo && <Badge variant="info">Sample data</Badge>}
          </div>
          <p className="text-sm text-ink-muted">{providerSubType || typeLabel}</p>
          <p className="text-sm text-ink-muted">
            {location || "Location unavailable"}
          </p>
            {provider.provider_type === "doctor" && (
              <div className="mt-2 space-y-1 text-sm text-ink-muted">
                {fictional.qualification && <p>{fictional.qualification}</p>}
                {fictional.experienceYears !== undefined && <p>{fictional.experienceYears} years of fictional sample experience</p>}
                <p>Hospital: {associatedHospital?.name ?? (provider.hospital_id ? `Hospital record #${provider.hospital_id}` : "Not provided")}</p>
                {fictional.consultationFee !== undefined && <p>Sample consultation fee: ₹{fictional.consultationFee}</p>}
                {privateSessions.length > 0 && <p>Sample OPD: {privateSessions.length} weekly sessions · {privateSessions[0]?.start}–{privateSessions[0]?.end} at {privateSessions[0]?.location}</p>}
              </div>
            )}
          <p className="text-sm text-ink-muted">
            {provider.phone || "Phone unavailable"}
          </p>
          {(provider.provider_type === "hospital" ||
            provider.provider_type === "doctor") && (
            <div className="mt-3 flex flex-wrap gap-2" aria-label="Specialities">
              {provider.specialities.length > 0 ? (
                provider.specialities.map((speciality) => (
                  <span
                    key={speciality.id}
                    className="rounded-[var(--radius-control)] border border-solid border-border bg-navy-50 px-2.5 py-1 text-xs text-ink"
                  >
                    {speciality.name}
                  </span>
                ))
              ) : (
                <span className="text-xs text-ink-muted">
                  Speciality information unavailable
                </span>
              )}
            </div>
          )}
        </div>
        <div className="flex items-end gap-2">
          <Link
            href={`/find/${provider.provider_type}/${provider.id}?location=${encodeURIComponent(providerLocationId)}`}
            className="rounded-[var(--radius-control)] bg-navy-900 px-4 py-2 text-sm font-medium text-white hover:bg-navy-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700"
          >
            View Profile
          </Link>
          {provider.provider_type === "doctor" && fictional.schedule && (
            <Link href={`/booking?doctor_id=${provider.id}&location=${encodeURIComponent(providerLocationId)}`} className="rounded-[var(--radius-control)] bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-600">
              Book Appointment
            </Link>
          )}
        </div>
      </div>
    </Card>
  );
}
