"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/components/auth-provider";
import {
  createDemoAppointment,
  getDoctorAppointmentAvailability,
  getProvider,
  hasBookableDoctorSchedule,
  type AppointmentCreateRequest,
  type AppointmentDetail,
  type DoctorAppointmentAvailability,
  type ProviderDirectoryItem,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCurrentTime } from "@/lib/use-current-time";

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export default function BookingPage() {
  return (
    <Suspense fallback={<section className="px-4 py-12"><p className="text-ink-muted">Loading booking…</p></section>}>
      <BookingForm />
    </Suspense>
  );
}

function BookingForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading } = useAuth();
  const nowTimestamp = useCurrentTime();
  const doctorIdParam = searchParams.get("doctor_id");
  const doctorId = doctorIdParam && /^\d+$/.test(doctorIdParam) ? Number(doctorIdParam) : null;
  const bookingPath = searchParams.toString() ? `/booking?${searchParams.toString()}` : "/booking";
  const [doctorResult, setDoctorResult] = useState<{
    id: number;
    doctor: ProviderDirectoryItem | null;
    error: string | null;
  } | null>(null);
  const [appointmentDate, setAppointmentDate] = useState("");
  const [appointmentTime, setAppointmentTime] = useState("");
  const [availabilityResult, setAvailabilityResult] = useState<{
    key: string;
    availability: DoctorAppointmentAvailability | null;
    error: string | null;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState<AppointmentDetail | null>(null);
  const [demoPaymentAccepted, setDemoPaymentAccepted] = useState(false);
  const doctor = doctorResult?.id === doctorId ? doctorResult.doctor : null;
  const doctorError = doctorId === null
    ? "Open Book Appointment from a doctor's profile so the doctor is selected automatically."
    : doctorResult?.id === doctorId
      ? doctorResult.error
      : null;
  const doctorLoading = doctorId !== null && doctorResult?.id !== doctorId;
  const availabilityKey = `${doctor?.id ?? ""}:${appointmentDate}`;
  const currentAvailability = availabilityResult?.key === availabilityKey ? availabilityResult : null;
  const availability = currentAvailability?.availability ?? null;
  const availabilityError = currentAvailability?.error ?? "";
  const availabilityLoading = Boolean(doctor && appointmentDate && !currentAvailability);

  useEffect(() => {
    if (!loading && !user) {
      router.replace(`/login?next=${encodeURIComponent(bookingPath)}`);
    }
  }, [bookingPath, loading, router, user]);

  useEffect(() => {
    if (!user) return;
    let active = true;
    if (doctorId === null || !Number.isSafeInteger(doctorId) || doctorId < 1) {
      return;
    }

    getProvider("doctor", doctorId)
      .then((record) => {
        if (active) setDoctorResult({
          id: doctorId,
          doctor: record.is_demo ? null : record,
          error: record.is_demo ? "Demo/sample doctors are fictional and cannot be booked." : null,
        });
      })
      .catch(() => {
        if (active) {
          setDoctorResult({
            id: doctorId,
            doctor: null,
            error: "This doctor could not be loaded from the provider directory.",
          });
        }
      });

    return () => { active = false; };
  }, [doctorId, user]);

  useEffect(() => {
    if (!doctor || !appointmentDate) {
      return;
    }

    let active = true;
    getDoctorAppointmentAvailability(doctor.id, appointmentDate)
      .then((result) => {
        if (active) {
          setAvailabilityResult({
            key: availabilityKey,
            availability: result,
            error: null,
          });
        }
      })
      .catch(() => {
        if (active) {
          setAvailabilityResult({
            key: availabilityKey,
            availability: null,
            error: "Could not check this doctor's live availability. Please try again.",
          });
        }
      });

    return () => { active = false; };
  }, [appointmentDate, availabilityKey, doctor]);

  const consultationDays = useMemo(() => {
    const schedule = doctor?.schedule;
    if (
      !schedule ||
      !Number.isInteger(schedule.durationMinutes) ||
      schedule.durationMinutes < 1 ||
      schedule.durationMinutes > 1440
    ) return [];
    return WEEKDAYS.flatMap((day, index) => {
      const session = schedule.privateOpd?.[String(index)];
      if (!session || typeof session !== "object" || schedule.unavailableDays?.includes(index)) return [];
      const validClock = (value: string) => /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value);
      if (
        typeof session.start !== "string" ||
        typeof session.end !== "string" ||
        !validClock(session.start) ||
        !validClock(session.end) ||
        session.end <= session.start ||
        typeof session.location !== "string" ||
        !session.location.trim()
      ) return [];
      return [{ day, session }];
    });
  }, [doctor]);

  const hasBookingPrerequisites = Boolean(
    doctor?.provider_type === "doctor" &&
    !doctor.is_demo &&
    hasBookableDoctorSchedule(doctor.schedule) &&
    consultationDays.length > 0 &&
    doctor.consultation_fee !== null &&
    doctor.consultation_fee !== undefined &&
    doctor.hospital_id &&
    doctor.hospital_name &&
    doctor.city &&
    doctor.state
  );
  const unavailableMessage = doctor && !hasBookingPrerequisites
    ? "Currently unavailable for online appointment booking."
    : "";

  const minDate = useMemo(() => {
    if (nowTimestamp === 0) return "";
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Kolkata",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).formatToParts(new Date(nowTimestamp));
    const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
    const tomorrow = new Date(`${part("year")}-${part("month")}-${part("day")}T12:00:00`);
    tomorrow.setDate(tomorrow.getDate() + 1);
    return `${tomorrow.getFullYear()}-${String(tomorrow.getMonth() + 1).padStart(2, "0")}-${String(tomorrow.getDate()).padStart(2, "0")}`;
  }, [nowTimestamp]);

  const selectedSlot = availability?.slots.find((slot) => slot.time.slice(0, 5) === appointmentTime);
  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (!user) {
      setError("You must be signed in to request an appointment.");
      return;
    }
    if (!doctor || doctor.is_demo || !hasBookingPrerequisites) {
      setError("Currently unavailable for online appointment booking.");
      return;
    }
    if (!appointmentDate || !appointmentTime || selectedSlot?.status !== "available") {
      setError("Select an available date and time slot before submitting.");
      return;
    }
    if (!demoPaymentAccepted) {
      setError("Confirm that you understand this is a simulated demo payment.");
      return;
    }

    setBusy(true);
    try {
      const input: AppointmentCreateRequest = {
        doctor_id: doctor.id,
        appointment_date: appointmentDate,
        appointment_time: appointmentTime,
        payment_method: "demo",
      };
      setSuccess(await createDemoAppointment(input));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Booking failed. Please try again.");
      if (requestError instanceof Error && /already been reserved|already been saved/i.test(requestError.message)) {
        setAppointmentTime("");
      }
    } finally {
      setBusy(false);
    }
  };

  if (loading || !user) {
    return <section className="px-4 py-12"><p className="text-ink-muted">Loading booking…</p></section>;
  }

  if (success) {
    return (
      <section className="px-4 py-8 sm:py-12">
        <Card className="mx-auto max-w-2xl p-5 sm:p-8">
          <Badge variant="warning">DEMO APPOINTMENT · DEMO PAYMENT</Badge>
          <h1 className="mt-3 text-2xl font-bold">Demo appointment confirmed</h1>
          <p className="mt-2 text-sm text-ink-muted">
            Booking and payment are simulated for this demonstration. No money was collected or transferred.
          </p>
          <BookingSummary
            doctorName={success.doctor_name}
            speciality={success.doctor_speciality}
            hospital={success.hospital_name}
            location={success.location}
            appointmentDate={success.appointment_date}
            appointmentTime={success.appointment_time}
            consultationFee={success.consultation_fee}
            status={success.status}
            paymentStatus={success.invoice.payment_status ?? success.payment_status}
            reference={success.reference}
          />
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Button onClick={() => router.push(`/profile/appointments/${success.reference}`)}>
              View appointment history
            </Button>
            <Button variant="outline" onClick={() => router.replace("/profile")}>
              Return to profile
            </Button>
          </div>
        </Card>
      </section>
    );
  }

  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="mx-auto max-w-2xl">
        <header className="mb-6">
          <Badge variant="warning">DEMO APPOINTMENT</Badge>
          <h1 className="mt-2 text-3xl font-bold text-ink">Book an Appointment</h1>
          <p className="text-sm text-ink-muted">
            Choose a date and an available slot for the doctor whose profile you selected.
          </p>
        </header>

        {error && <p role="alert" className="mb-4 rounded border border-danger bg-danger/5 p-4 text-sm text-danger">{error}</p>}
        {doctorError && <p role="alert" className="mb-4 rounded border border-warning bg-warning/5 p-4 text-sm text-ink">{doctorError}</p>}

        {doctorLoading ? (
          <p role="status" className="py-6 text-sm text-ink-muted">Loading selected doctor…</p>
        ) : !doctor ? (
          <Card className="p-5">
            <p className="text-sm text-ink-muted">No doctor has been selected for this appointment request.</p>
            <Link href="/find?provider_type=doctor" className="mt-3 inline-block text-sm text-teal-700 underline">
              Find a Doctor
            </Link>
          </Card>
        ) : (
          <Card className="p-5 sm:p-8">
            <section aria-labelledby="selected-doctor-heading" className="mb-6 rounded border border-border bg-navy-50 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <h2 id="selected-doctor-heading" className="text-lg font-semibold">{doctor.name}</h2>
                {doctor.is_demo && <Badge variant="info">Sample data</Badge>}
                {!doctor.is_verified && <Badge variant="unverified">Unverified</Badge>}
              </div>
              <p className="mt-1 text-sm text-ink-muted">
                {doctor.specialities.map((speciality) => speciality.name).join(", ") || "Speciality unavailable"}
              </p>
              <p className="mt-1 text-sm text-ink-muted">
                {doctor.hospital_name || "Hospital/clinic unavailable"}
                {doctor.city ? ` · ${doctor.city}` : ""}
              </p>
              <p className="mt-1 text-sm text-ink-muted">
                Consultation fee: {doctor.consultation_fee == null ? "Unavailable" : `₹${doctor.consultation_fee}`}
              </p>
              <Link
                href={`/find/doctor/${doctor.id}`}
                className="mt-2 inline-block text-sm text-teal-700 underline"
              >
                View doctor profile
              </Link>
            </section>

            {unavailableMessage ? (
              <p role="status" className="rounded border border-warning bg-warning/5 p-4 text-sm text-ink">
                {unavailableMessage}
              </p>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5">
                <section aria-labelledby="doctor-hours-heading" className="rounded border border-border p-4">
                  <h2 id="doctor-hours-heading" className="font-semibold">Consultation days and OPD timings</h2>
                  <ul className="mt-2 space-y-2 text-sm">
                    {consultationDays.map(({ day, session }) => (
                      <li key={day}>
                        <strong>{day}:</strong> {session.start}–{session.end} · {session.location}
                      </li>
                    ))}
                  </ul>
                  <p className="mt-2 text-xs text-ink-muted">
                    Availability is based on the directory schedule and live appointment records. Sample listings are illustrative and unverified.
                  </p>
                </section>

                <div>
                  <label htmlFor="appointment-date" className="mb-1 block text-sm font-medium">
                    Appointment date
                  </label>
                  <Input
                    id="appointment-date"
                    type="date"
                    min={minDate}
                    value={appointmentDate}
                    onChange={(event) => {
                      setAppointmentDate(event.target.value);
                      setAppointmentTime("");
                    }}
                    required
                    className="w-full"
                  />
                </div>

                {appointmentDate && (
                  <section aria-live="polite" aria-busy={availabilityLoading} className="rounded border border-border p-4">
                    <h2 className="font-semibold">Available appointment slots</h2>
                    {availabilityLoading && <p role="status" className="mt-2 text-sm text-ink-muted">Checking availability…</p>}
                    {availabilityError && <p role="alert" className="mt-2 text-sm text-danger">{availabilityError}</p>}
                    {!availabilityLoading && availability?.message && (
                      <p role="status" className="mt-2 text-sm text-ink-muted">{availability.message}</p>
                    )}
                    {availability && (
                      <>
                        {availability.opd_start && availability.opd_end && (
                          <p className="mt-1 text-sm text-ink-muted">
                            OPD {availability.opd_start.slice(0, 5)}–{availability.opd_end.slice(0, 5)}
                            {availability.clinic_location ? ` · ${availability.clinic_location}` : ""}
                          </p>
                        )}
                        {availability.fully_booked && (
                          <p className="mt-2 rounded bg-warning/10 p-2 text-sm text-ink">
                            This date is fully booked. Choose another date.
                          </p>
                        )}
                        {availability.slots.length > 0 && (
                          <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                            {availability.slots.map((slot) => {
                              const value = slot.time.slice(0, 5);
                              const available = slot.status === "available";
                              const selected = appointmentTime === value;
                              return (
                                <li key={value}>
                                  <button
                                    type="button"
                                    disabled={!available || availabilityLoading}
                                    aria-pressed={selected}
                                    title={slot.reason ?? "Available"}
                                    onClick={() => setAppointmentTime(value)}
                                    className={`w-full rounded border px-3 py-2 text-sm ${
                                      selected
                                        ? "border-teal-700 bg-teal-700 text-white"
                                        : available
                                          ? "border-teal-700 text-teal-800 hover:bg-teal-50"
                                          : "cursor-not-allowed border-border bg-navy-50 text-ink-muted line-through"
                                    }`}
                                  >
                                    {value} · {available ? "Available" : "Unavailable"}
                                  </button>
                                  {!available && slot.reason && (
                                    <span className="sr-only">{slot.reason}</span>
                                  )}
                                </li>
                              );
                            })}
                          </ul>
                        )}
                      </>
                    )}
                  </section>
                )}

                <BookingSummary
                  doctorName={doctor.name}
                  speciality={doctor.specialities.map((speciality) => speciality.name).join(", ") || "Unavailable"}
                  hospital={doctor.hospital_name}
                  location={availability?.clinic_location ?? doctor.address}
                  appointmentDate={appointmentDate || "Select a date"}
                  appointmentTime={appointmentTime || "Select an available slot"}
                  consultationFee={availability?.consultation_fee ?? doctor.consultation_fee}
                  status="Pending — not submitted"
                />

                <section className="rounded border border-warning bg-warning/5 p-4 text-sm">
                  <h2 className="font-semibold">DEMO PAYMENT · NOT A REAL TRANSACTION</h2>
                  <p className="mt-1">
                    Confirming simulates payment of the displayed consultation fee for this local demo only. No real payment service is contacted, and no money is collected or transferred.
                  </p>
                  <label className="mt-3 flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={demoPaymentAccepted}
                      onChange={(event) => setDemoPaymentAccepted(event.target.checked)}
                      required
                      className="mt-1"
                    />
                    <span>I understand this is a simulated demo payment and not a real transaction.</span>
                  </label>
                </section>

                <Button
                  type="submit"
                  disabled={
                    busy ||
                    !hasBookingPrerequisites ||
                    !appointmentDate ||
                    selectedSlot?.status !== "available" ||
                    availabilityLoading ||
                    !demoPaymentAccepted
                  }
                  className="w-full"
                >
                  {busy ? "Confirming demo booking…" : "Confirm DEMO PAYMENT & Book"}
                </Button>
                <p className="text-center text-xs text-ink-muted">
                  The booking and payment status are simulated; no money changes hands.
                </p>
              </form>
            )}
          </Card>
        )}
      </div>
    </section>
  );
}

function BookingSummary({
  doctorName,
  speciality,
  hospital,
  location,
  appointmentDate,
  appointmentTime,
  consultationFee,
  status,
  paymentStatus,
  reference,
}: {
  doctorName: string;
  speciality: string | null;
  hospital: string | null;
  location: string | null;
  appointmentDate: string;
  appointmentTime: string;
  consultationFee: number | null;
  status: string;
  paymentStatus?: string | null;
  reference?: string;
}) {
  return (
    <section aria-labelledby="booking-summary-heading" className="mt-5 rounded border border-border p-4">
      <h2 id="booking-summary-heading" className="font-semibold">Booking summary</h2>
      <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <SummaryItem label="Doctor" value={doctorName} />
        <SummaryItem label="Speciality" value={speciality || "Unavailable"} />
        <SummaryItem label="Hospital/clinic" value={hospital || location || "Unavailable"} />
        <SummaryItem label="OPD location" value={location || "Unavailable"} />
        <SummaryItem label="Date" value={appointmentDate} />
        <SummaryItem label="Time" value={appointmentTime} />
        <SummaryItem
          label="Consultation fee"
          value={consultationFee == null ? "Unavailable" : `₹${consultationFee}`}
        />
        <SummaryItem label="Payment method" value="DEMO PAYMENT — NOT A REAL TRANSACTION" />
        {paymentStatus && <SummaryItem label="Payment status" value={paymentStatus} />}
        <SummaryItem label="Booking status" value={status} />
        {reference && <SummaryItem label="Reference" value={reference} />}
      </dl>
    </section>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd className="break-words font-medium">{value}</dd>
    </div>
  );
}
