"use client";

import { Suspense, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  cancelMyAppointment,
  getMyAppointment,
  type AppointmentDetail,
} from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function AppointmentPage() {
  return (
    <Suspense fallback={<p className="px-4 py-8">Loading appointment…</p>}>
      <AppointmentContent />
    </Suspense>
  );
}

function AppointmentContent() {
  const { reference } = useParams<{ reference: string }>();
  const { user, loading } = useAuth();
  const router = useRouter();
  const [record, setRecord] = useState<AppointmentDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.replace(`/login?next=${encodeURIComponent(`/profile/appointments/${reference}`)}`);
      return;
    }
    if (!user) return;

    let active = true;
    getMyAppointment(reference)
      .then((appointment) => {
        if (active) setRecord(appointment);
      })
      .catch(() => {
        if (active) setError("Appointment not found or unavailable.");
      });

    return () => {
      active = false;
    };
  }, [user, loading, router, reference]);

  async function cancelAppointment() {
    if (!record || !window.confirm("Cancel this demo appointment?")) return;
    setBusy(true);
    setError("");
    try {
      const updated = await cancelMyAppointment(record.reference);
      setRecord((current) => current ? { ...current, status: updated.status } : current);
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : "Could not cancel this appointment.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="px-4 py-10">
      <Card className="mx-auto max-w-2xl p-6">
        <Badge variant="warning">DEMO APPOINTMENT</Badge>
        <h1 className="mt-3 text-2xl font-bold">Appointment and invoice</h1>
        {error && <p role="alert" className="mt-3 text-danger">{error}</p>}
        {!record && !error && <p role="status" className="mt-3">Loading account record…</p>}
        {record && (
          <>
            <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
              {[
                ["Reference", record.reference],
                ["Doctor", record.doctor_name],
                ["Speciality", record.doctor_speciality ?? "Unavailable"],
                ["Hospital/clinic", record.hospital_name ?? record.location],
                ["Date", record.appointment_date],
                ["Time", record.appointment_time],
                ["Consultation fee", `₹${record.consultation_fee}`],
                ["Total", `₹${record.total_amount}`],
                ["Booking status", record.status],
                ["Payment method", record.invoice.payment_method ?? "DEMO PAYMENT"],
                ["Payment status", record.invoice.payment_status ?? record.payment_status],
                ["Invoice", record.invoice.invoice_number],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-ink-muted">{label}</dt>
                  <dd className="break-words font-medium">{value}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-5 text-xs text-ink-muted">
              DEMO PAYMENT only: no money was collected or transferred.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              {["pending", "demo_confirmed"].includes(record.status) && (
                <Button type="button" variant="outline" disabled={busy} onClick={() => void cancelAppointment()}>
                  {busy ? "Cancelling…" : "Cancel demo appointment"}
                </Button>
              )}
              <Link className="inline-flex items-center text-sm text-teal-700 underline" href="/dashboard">
                Back to appointment history
              </Link>
            </div>
          </>
        )}
      </Card>
    </section>
  );
}
