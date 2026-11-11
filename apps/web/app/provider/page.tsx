"use client";

import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import {
  getDoctorSchedule,
  listDoctorAppointments,
  updateDoctorAppointmentStatus,
  type AppointmentRecord,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const subscribeToDate = () => () => {};
const getToday = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
};
const getServerToday = () => "";

export default function ProviderPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [appointments, setAppointments] = useState<AppointmentRecord[]>([]);
  const [schedule, setSchedule] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const today = useSyncExternalStore(subscribeToDate, getToday, getServerToday);

  const loadProviderData = useCallback(async () => {
    return Promise.all([
      listDoctorAppointments(),
      getDoctorSchedule(),
    ]);
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login?next=%2Fprovider");
      return;
    }
    if (user.role !== "provider") {
      router.replace(user.role === "admin" ? "/admin" : "/profile");
      return;
    }
    let active = true;
    loadProviderData()
      .then(([records, doctorSchedule]) => {
        if (!active) return;
        setAppointments(records);
        setSchedule(doctorSchedule.schedule);
      })
      .catch(() => {
        if (active) setError("Provider records unavailable. Confirm the account is linked to a doctor listing and the API is running.");
      });
    return () => { active = false; };
  }, [loading, user, router, loadProviderData]);

  const upcoming = useMemo(
    () => appointments.filter((appointment) => appointment.appointment_date >= today && appointment.status !== "cancelled"),
    [appointments, today],
  );
  const todaysAppointments = appointments.filter((appointment) => appointment.appointment_date === today);
  const pending = appointments.filter((appointment) => appointment.status === "pending");
  const completed = appointments.filter((appointment) => appointment.status === "completed");

  async function reviewAppointment(appointmentId: number, status: "demo_confirmed" | "cancelled") {
    setBusyId(appointmentId);
    setError("");
    try {
      await updateDoctorAppointmentStatus(appointmentId, status);
      const [records, doctorSchedule] = await loadProviderData();
      setAppointments(records);
      setSchedule(doctorSchedule.schedule);
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "Appointment request could not be updated.");
    } finally {
      setBusyId(null);
    }
  }

  if (loading || !user || user.role !== "provider") {
    return <section className="px-4 py-10">Checking provider access…</section>;
  }

  return (
    <section className="px-4 py-8">
      <div className="mx-auto max-w-5xl">
        <Badge variant="warning">PROVIDER · DEMO DASHBOARD</Badge>
        <h1 className="mt-2 text-3xl font-bold">Doctor dashboard</h1>
        <p className="text-sm text-ink-muted">
          Appointment requests and schedule associated with your approved doctor account.
        </p>
        {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}

        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Today's appointments", todaysAppointments.length],
            ["Total appointments", appointments.length],
            ["Pending requests", pending.length],
            ["Upcoming appointments", upcoming.length],
            ["Completed appointments", completed.length],
          ].map(([label, value]) => (
            <Card key={String(label)} className="bg-navy-900 p-4 text-white">
              <p className="text-sm">{label}</p>
              <p className="mt-1 text-3xl font-bold">{value}</p>
            </Card>
          ))}
        </div>

        <section className="mt-7">
          <h2 className="mb-3 text-xl font-bold">Pending appointment requests</h2>
          {pending.length ? (
            <div className="grid gap-3 md:grid-cols-2">
              {pending.map((appointment) => (
                <Appointment
                  key={appointment.reference}
                  item={appointment}
                  busy={busyId === appointment.id}
                  onAccept={() => void reviewAppointment(appointment.id, "demo_confirmed")}
                  onDecline={() => void reviewAppointment(appointment.id, "cancelled")}
                />
              ))}
            </div>
          ) : (
            <Card className="p-5 text-sm text-ink-muted">No pending requests.</Card>
          )}
        </section>

        <section className="mt-7">
          <h2 className="mb-3 text-xl font-bold">Upcoming appointments</h2>
          {upcoming.length ? (
            <div className="grid gap-3 md:grid-cols-2">
              {upcoming.map((appointment) => (
                <Appointment key={appointment.reference} item={appointment} />
              ))}
            </div>
          ) : (
            <Card className="p-5 text-sm text-ink-muted">No upcoming appointments.</Card>
          )}
        </section>

        <section id="schedule" className="mt-7">
          <h2 className="mb-3 text-xl font-bold">Weekly schedule and availability</h2>
          {schedule ? (
            <Card className="overflow-x-auto p-4">
              <pre className="whitespace-pre-wrap text-xs text-ink">{JSON.stringify(schedule, null, 2)}</pre>
              <p className="mt-3 text-xs text-ink-muted">
                Schedule supplied by the linked doctor directory record. Availability changes are managed outside this demonstration page.
              </p>
            </Card>
          ) : (
            <Card className="p-5 text-sm text-ink-muted">No schedule has been supplied for this provider record.</Card>
          )}
        </section>
      </div>
    </section>
  );
}

function Appointment({
  item,
  busy = false,
  onAccept,
  onDecline,
}: {
  item: AppointmentRecord;
  busy?: boolean;
  onAccept?: () => void;
  onDecline?: () => void;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-3">
        <strong>{item.appointment_date} · {item.appointment_time}</strong>
        <Badge variant={item.status === "pending" ? "warning" : "info"}>{item.status}</Badge>
      </div>
      <p className="mt-1 text-sm text-ink-muted">Patient: {item.patient_name ?? "Patient"}</p>
      <p className="text-sm text-ink-muted">{item.location} · Demo reference {item.reference}</p>
      {onAccept && onDecline && (
        <div className="mt-3 flex gap-2">
          <Button disabled={busy} onClick={onAccept}>Accept request</Button>
          <Button disabled={busy} variant="outline" onClick={onDecline}>Decline request</Button>
        </div>
      )}
    </Card>
  );
}
