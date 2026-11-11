"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import {
  cancelMyAppointment,
  listMyAppointments,
  listMyReminders,
  type AppointmentRecord,
  type ReminderRecord,
} from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const subscribeToDate = () => () => {};
const getToday = () => new Date().toLocaleDateString("en-CA");
const getServerToday = () => "";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [appointments, setAppointments] = useState<AppointmentRecord[]>([]);
  const [reminders, setReminders] = useState<ReminderRecord[]>([]);
  const [error, setError] = useState("");
  const [reminderError, setReminderError] = useState("");
  const [appointmentsLoading, setAppointmentsLoading] = useState(true);
  const today = useSyncExternalStore(subscribeToDate, getToday, getServerToday);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login?next=%2Fdashboard");
      return;
    }
    if (user?.role === "provider") {
      router.replace("/provider");
      return;
    }
    if (user?.role === "admin") {
      router.replace("/admin");
      return;
    }
    if (!user) return;

    let active = true;
    listMyAppointments()
      .then((records) => {
        if (active) {
          setAppointments(records);
          setAppointmentsLoading(false);
        }
      })
      .catch(() => {
        if (active) {
          setError("Could not load your appointments.");
          setAppointmentsLoading(false);
        }
      });
    listMyReminders()
      .then((records) => {
        if (active) setReminders(records);
      })
      .catch(() => {
        if (active) setReminderError("Could not load your in-app reminders.");
      });

    return () => {
      active = false;
    };
  }, [loading, user, router]);

  const upcoming = useMemo(
    () => appointments.filter(
      (item) => item.appointment_date >= today && !["cancelled", "completed"].includes(item.status),
    ),
    [appointments, today],
  );
  const upcomingReminders = useMemo(
    () => reminders.filter((reminder) => !reminder.completed && reminder.reminder_date >= today),
    [reminders, today],
  );
  const pending = appointments.filter((item) => item.status.includes("pending"));
  const completed = appointments.filter((item) => item.status === "completed");
  const cancelled = appointments.filter((item) => item.status === "cancelled");
  const next = upcoming[0];

  async function cancelAppointment(appointment: AppointmentRecord) {
    if (!window.confirm(`Cancel the demo appointment with ${appointment.doctor_name}?`)) return;
    setError("");
    try {
      const updated = await cancelMyAppointment(appointment.reference);
      setAppointments((current) =>
        current.map((item) => item.reference === updated.reference ? updated : item),
      );
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : "Could not cancel this appointment.");
    }
  }

  if (loading || !user) {
    return <section className="px-4 py-10">Loading your dashboard…</section>;
  }

  return (
    <section className="px-4 py-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-7">
          <Badge variant="warning">PATIENT · DEMO DASHBOARD</Badge>
          <h1 className="mt-2 text-3xl font-bold">Welcome, {user.full_name}</h1>
          <p className="text-sm text-ink-muted">
            Your account-linked appointments and in-app checkup reminders.
          </p>
        </header>

        {error && <p role="alert" className="mb-4 text-sm text-danger">{error}</p>}
        {reminderError && <p role="alert" className="mb-4 text-sm text-danger">{reminderError}</p>}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Upcoming appointments", upcoming.length],
            ["Pending requests", pending.length],
            ["Completed appointments", completed.length],
            ["Cancelled appointments", cancelled.length],
            ["Checkup reminders", upcomingReminders.length],
          ].map(([title, count]) => (
            <Card key={String(title)} className="bg-navy-900 p-4 text-white">
              <p className="text-sm">{title}</p>
              <p className="mt-1 text-3xl font-bold">{count}</p>
            </Card>
          ))}
        </div>

        {next && (
          <section className="mt-7">
            <h2 className="mb-3 text-xl font-bold">Next appointment</h2>
            <Card className="p-5">
              <p className="text-lg font-semibold">{next.doctor_name}</p>
              <p className="mt-1 text-sm text-ink-muted">
                {next.appointment_date} at {next.appointment_time} · {next.location}
              </p>
              <p className="text-sm">{next.package_name ?? "Consultation"} · Demo record</p>
              <Link
                href={`/profile/appointments/${next.reference}`}
                className="mt-3 inline-block text-sm text-teal-700 underline"
              >
                View appointment and invoice
              </Link>
            </Card>
          </section>
        )}

        <section id="appointments" className="mt-7">
          <h2 className="mb-3 text-xl font-bold">Appointments</h2>
          {appointmentsLoading ? (
            <Card className="p-5 text-sm text-ink-muted">Loading appointment history…</Card>
          ) : appointments.length ? (
            <div className="grid gap-3 md:grid-cols-2">
              {appointments.map((item) => (
                <Card key={item.reference} className="p-4">
                  <div className="flex items-center justify-between gap-2">
                    <strong>{item.doctor_name}</strong>
                    <Badge
                      variant={
                        item.status === "completed"
                          ? "success"
                          : item.status.includes("pending")
                            ? "warning"
                            : "info"
                      }
                    >
                      {item.status}
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm text-ink-muted">
                    {item.appointment_date} at {item.appointment_time} · {item.location}
                  </p>
                  <p className="text-sm">{item.package_name ?? "Consultation"} · ₹{item.total_amount}</p>
                  <p className="text-xs text-ink-muted">
                    Ref {item.reference} · Demo payment: {item.payment_status.replaceAll("_", " ")}
                  </p>
                  <Link
                    href={`/profile/appointments/${item.reference}`}
                    className="mt-2 inline-block text-sm text-teal-700 underline"
                  >
                    Details and invoice
                  </Link>
                  {["pending", "demo_confirmed"].includes(item.status) && (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="ml-3 mt-2"
                      onClick={() => void cancelAppointment(item)}
                    >
                      Cancel demo appointment
                    </Button>
                  )}
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-5 text-sm text-ink-muted">
              No linked appointments yet. Browse doctors to start a demo booking.
            </Card>
          )}
        </section>

        <section className="mt-7">
          <div className="mb-3 flex justify-between">
            <h2 className="text-xl font-bold">Health checkup reminders</h2>
            <Link className="text-sm text-teal-700 underline" href="/reminders">
              Manage in-app reminders
            </Link>
          </div>
          <p className="mb-3 text-xs text-ink-muted">
            Stored in your account only; reminders do not send email, SMS, or push notifications.
          </p>
          {reminders.length ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {reminders.map((reminder) => {
                const overdue = reminder.reminder_date < today && !reminder.completed;
                const status = reminder.completed ? "Completed" : overdue ? "Due" : "Upcoming";
                return (
                  <Card key={reminder.id} className="p-4">
                    <strong className="text-sm">{reminder.title}</strong>
                    <p className="text-xs text-ink-muted">
                      {reminder.category} · {reminder.reminder_date} · Repeats {reminder.repeat_interval}
                    </p>
                    <Badge variant={reminder.completed ? "success" : overdue ? "warning" : "info"}>
                      {status}
                    </Badge>
                  </Card>
                );
              })}
            </div>
          ) : (
            <Card className="p-5 text-sm text-ink-muted">
              No in-app reminders yet. Add one to track a future due date.
            </Card>
          )}
        </section>
      </div>
    </section>
  );
}
