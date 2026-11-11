"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense } from "react";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  getProvider,
  hasBookableDoctorSchedule,
  type DoctorSchedule,
  type ProviderDirectoryItem,
  type ProviderType,
} from "@/lib/api";
import { getDoctorHospital, getFictionalProvider, type FictionalProvider } from "@/lib/fictional-directory";

const providerLabels: Record<ProviderType, string> = {
  hospital: "Hospital",
  doctor: "Doctor",
  lab: "Diagnostic lab",
  opd: "OPD",
};

function available(value: string | null | undefined) {
  return value?.trim() || "Unavailable";
}

export default function ProviderDetailPage() {
  return (
    <Suspense fallback={<p role="status" className="px-4 py-8 text-sm text-ink-muted">Loading provider details...</p>}>
      <ProviderDetail />
    </Suspense>
  );
}

function ProviderDetail() {
  const params = useParams<{ providerType: string; id: string }>();
  const providerType = params.providerType as ProviderType;
  const id = Number(params.id);
  const invalidParams =
    !["hospital", "doctor", "lab", "opd"].includes(providerType) ||
    !Number.isInteger(id) ||
    id < 1;
  const requestKey = `${providerType}:${id}`;
  const fictionalProvider = invalidParams ? null : getFictionalProvider(providerType, id);
  const [apiResult, setApiResult] = useState<{
    key: string;
    provider: ProviderDirectoryItem | null;
    error: boolean;
  } | null>(null);

  useEffect(() => {
    if (invalidParams) return;
    let active = true;
    getProvider(providerType, id)
      .then((result) => {
        if (active) setApiResult({ key: requestKey, provider: result, error: false });
      })
      .catch(() => {
        if (active) setApiResult({ key: requestKey, provider: null, error: true });
      });

    return () => {
      active = false;
    };
  }, [id, invalidParams, fictionalProvider, params.id, params.providerType, providerType, requestKey]);

  const liveProvider = apiResult?.key === requestKey ? apiResult.provider : null;
  const provider = liveProvider ?? fictionalProvider;
  const loading = !invalidParams && apiResult?.key !== requestKey;
  const error = apiResult?.key === requestKey && apiResult.error && !fictionalProvider;

  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="mx-auto max-w-3xl">
        <Link
          href="/find"
          className="text-sm font-medium text-teal-700 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700"
        >
          Back to provider search
        </Link>

        {loading ? (
          <p role="status" aria-live="polite" className="mt-8 text-sm text-ink-muted">
            Loading provider details…
          </p>
        ) : invalidParams || error || !provider ? (
          <div role="alert" className="mt-6 rounded-[var(--radius-card)] border border-solid border-border bg-background p-8 text-center shadow-[var(--shadow-card)]">
            <h1 className="text-xl font-bold text-ink">Provider details unavailable</h1>
            <p className="mt-2 text-sm text-ink-muted">
              This listing could not be loaded from the provider directory.
            </p>
          </div>
        ) : (
          <Card className="mt-6 p-5 sm:p-8">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium text-teal-700">
                {providerLabels[provider.provider_type]}
              </p>
              <Badge variant={provider.is_verified ? "verified" : "unverified"}>
                {provider.is_verified ? "Verified" : "Unverified"}
              </Badge>
              {provider.is_demo && <Badge variant="info">Sample data</Badge>}
            </div>
            <h1 className="mt-2 break-words text-3xl font-bold text-ink">
              {provider.name}
            </h1>
            {provider.is_demo && <p className="mt-2 text-sm font-medium text-teal-700">Fictional sample profile · not a real healthcare provider</p>}
            <p className="mt-3 whitespace-pre-line text-sm text-ink-muted">
              {provider.provider_type === "doctor" && (provider as FictionalProvider).biography
                ? (provider as FictionalProvider).biography
                : available(provider.description)}
            </p>
            {provider.provider_type === "doctor" && (
              <div className="mt-4">
                {liveProvider?.provider_type === "doctor" &&
                hasBookableDoctorSchedule(liveProvider.schedule) &&
                liveProvider.consultation_fee != null &&
                liveProvider.hospital_id &&
                liveProvider.hospital_name &&
                liveProvider.city &&
                liveProvider.state ? (
                  <Link
                    href={`/booking?doctor_id=${liveProvider.id}`}
                    className="inline-flex rounded-[var(--radius-control)] bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-700"
                  >
                    Book Appointment
                  </Link>
                ) : (
                  <p role="status" className="text-sm text-ink-muted">
                    Currently unavailable for online appointment booking.
                  </p>
                )}
              </div>
            )}

            {liveProvider?.provider_type === "doctor" && liveProvider.is_demo && (
              <section className="mt-6 rounded-[var(--radius-card)] bg-navy-50 p-4">
                <h2 className="text-lg font-semibold text-ink">Doctor profile</h2>
                <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                  <Detail label="Qualification (fictional)" value={liveProvider.qualifications} />
                  <Detail label="Experience (fictional)" value={liveProvider.experience_years != null ? `${liveProvider.experience_years} years` : null} />
                  <Detail label="Hospital association" value={liveProvider.hospital_name} />
                  <Detail label="Sample consultation fee" value={liveProvider.consultation_fee != null ? `₹${liveProvider.consultation_fee}` : null} />
                  <Detail label="Fictional contact email" value={liveProvider.email} />
                  <Detail label="Fictional contact phone" value={liveProvider.phone} />
                </dl>
                {liveProvider.schedule && (
                  <DoctorScheduleDisplay
                    schedule={liveProvider.schedule}
                    verified={liveProvider.is_verified}
                  />
                )}
              </section>
            )}
            {!liveProvider && provider.provider_type === "doctor" && provider.is_demo && (() => {
              const fictional = provider as FictionalProvider;
              const hospital = getDoctorHospital(fictional);
              return <section className="mt-6 rounded-[var(--radius-card)] bg-navy-50 p-4">
                <h2 className="text-lg font-semibold text-ink">Doctor profile</h2>
                <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                  <Detail label="Qualification (fictional)" value={fictional.qualification} />
                  <Detail label="Experience (fictional)" value={fictional.experienceYears !== undefined ? `${fictional.experienceYears} years` : null} />
                  <Detail label="Hospital association" value={hospital?.name ?? null} />
                  <Detail label="Sample consultation fee" value={fictional.consultationFee !== undefined ? `₹${fictional.consultationFee}` : null} />
                  <Detail label="Fictional contact email" value={fictional.email} />
                  <Detail label="Fictional contact phone" value={fictional.phone} />
                </dl>
                {fictional.schedule && <div className="mt-4 border-t border-border pt-4"><h3 className="font-semibold text-ink">Illustrative weekly schedule</h3><p className="mt-1 text-xs text-ink-muted">Sample hours only. Confirm directly with a real provider before seeking care.</p><ul className="mt-3 space-y-2 text-sm">{[0,1,2,3,4,5,6].map((day) => {
                  const duty = fictional.schedule!.governmentDuty[day];
                  const opd = fictional.schedule!.privateOpd[day];
                  if (!duty && !opd) return null;
                  return <li key={day}><strong>{["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][day]}:</strong> {duty ? `Government duty ${duty.start}–${duty.end} at ${duty.location}` : ""}{duty && opd ? " · " : ""}{opd ? `Private OPD ${opd.start}–${opd.end} at ${opd.location}${opd.breakStart ? ` (break ${opd.breakStart}–${opd.breakEnd})` : ""}` : ""}</li>;
                })}</ul><p className="mt-3 text-xs text-ink-muted">Appointments are {fictional.schedule.durationMinutes} minutes. Sunday is unavailable.</p></div>}
              </section>;
            })()}
            {provider.provider_type === "doctor" && !provider.is_demo && (
              <section className="mt-6 rounded-[var(--radius-card)] bg-navy-50 p-4">
                <h2 className="text-lg font-semibold text-ink">Doctor profile</h2>
                <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                  <Detail label="Qualifications" value={provider.qualifications} />
                  <Detail label="Experience" value={provider.experience_years != null ? `${provider.experience_years} years` : null} />
                  <Detail label="Hospital association" value={provider.hospital_name} />
                  <Detail label="Consultation fee" value={provider.consultation_fee != null ? `₹${provider.consultation_fee}` : null} />
                </dl>
                {provider.schedule && (
                  <DoctorScheduleDisplay
                    schedule={provider.schedule}
                    verified={provider.is_verified}
                  />
                )}
              </section>
            )}

            <dl className="mt-8 grid grid-cols-1 gap-x-8 gap-y-5 sm:grid-cols-2">
              <Detail label="Address" value={provider.address} />
              <Detail label="Locality" value={provider.locality} />
              <Detail label="City" value={provider.city} />
              <Detail label="State" value={provider.state} />
              <Detail label={provider.is_demo ? "Fictional contact phone" : "Phone"} value={provider.phone} />
              <Detail label={provider.is_demo ? "Fictional contact email" : "Email"} value={provider.email} />
              <Detail label="Website" value={provider.website} />
              <Detail label="Operating hours" value={provider.operating_hours} />
              <Detail
                label="Operational status"
                value={provider.operational_status?.replaceAll("_", " ")}
              />
              <Detail
                label="Emergency services"
                value={provider.emergency_services == null ? null : provider.emergency_services ? "Reported available" : "Reported unavailable"}
              />
              <Detail
                label="Home sample collection"
                value={provider.home_sample_collection == null ? null : provider.home_sample_collection ? "Reported available" : "Reported unavailable"}
              />
              <Detail
                label={provider.provider_type === "opd" ? "OPD type" : "Provider type details"}
                value={provider.opd_type || provider.hospital_type}
              />
              {provider.provider_type === "opd" && (
                <Detail
                  label="Hospital association"
                  value={provider.hospital_id ? `Hospital record #${provider.hospital_id}` : null}
                />
              )}
              <Detail label="Data source" value={provider.source} />
              <Detail
                label="Verified at"
                value={provider.verified_at ? new Date(provider.verified_at).toLocaleString() : null}
              />
            </dl>

            {(provider.provider_type === "hospital" ||
              provider.provider_type === "doctor") && (
              <section className="mt-8 border-t border-solid border-border pt-6">
                <h2 className="text-lg font-semibold text-ink">Specialities</h2>
                {provider.specialities.length > 0 ? (
                  <ul className="mt-3 flex flex-wrap gap-2">
                    {provider.specialities.map((speciality) => (
                      <li
                        key={speciality.id}
                        className="rounded-[var(--radius-control)] border border-solid border-border bg-navy-50 px-3 py-1 text-sm text-ink"
                      >
                        {speciality.name}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-ink-muted">
                    Speciality information unavailable.
                  </p>
                )}
              </section>
            )}
          </Card>
        )}
      </div>
    </section>
  );
}

function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium uppercase tracking-wide text-ink-muted">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm text-ink">{available(value)}</dd>
    </div>
  );
}

function DoctorScheduleDisplay({
  schedule,
  verified,
}: {
  schedule: DoctorSchedule;
  verified: boolean;
}) {
  const weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const rows = weekdays.map((day, index) => ({
    day,
    duty: schedule.governmentDuty?.[String(index)],
    opd: schedule.privateOpd?.[String(index)],
  })).filter((row) => row.duty || row.opd);

  return (
    <div className="mt-4 border-t border-border pt-4">
      <h3 className="font-semibold text-ink">
        {verified ? "Provider-supplied OPD schedule" : "Unverified API schedule"}
      </h3>
      {!verified && (
        <p className="mt-1 text-xs text-ink-muted">
          This schedule has not been independently verified. Confirm it with the provider.
        </p>
      )}
      {rows.length ? (
        <ul className="mt-3 space-y-2 text-sm">
          {rows.map(({ day, duty, opd }) => (
            <li key={day}>
              <strong>{day}:</strong>{" "}
              {duty ? `Government duty ${duty.start}–${duty.end} at ${duty.location}` : ""}
              {duty && opd ? " · " : ""}
              {opd ? `Private OPD ${opd.start}–${opd.end} at ${opd.location}` : ""}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-ink-muted">No OPD hours supplied.</p>
      )}
      <p className="mt-3 text-xs text-ink-muted">
        Appointment duration: {schedule.durationMinutes} minutes.
      </p>
    </div>
  );
}
