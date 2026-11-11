"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import {
  listAdminAppointments,
  listDoctorApplications,
  reviewDoctorApplication,
  type AppointmentRecord,
  type DoctorApplicationRecord,
} from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AdminPackagePlans } from "@/components/admin-package-plans";
import { AdminSubscriptions } from "@/components/admin-subscriptions";

export default function AdminPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [applications, setApplications] = useState<DoctorApplicationRecord[]>([]);
  const [appointments, setAppointments] = useState<AppointmentRecord[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(async () => {
    const [nextApplications, nextAppointments] = await Promise.all([
      listDoctorApplications(),
      listAdminAppointments(),
    ]);
    setApplications(nextApplications);
    setAppointments(nextAppointments);
  }, []);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login?next=%2Fadmin");
      return;
    }
    if (user && user.role !== "admin") {
      router.replace("/profile");
      return;
    }
    if (user?.role === "admin") {
      let active = true;
      Promise.all([listDoctorApplications(), listAdminAppointments()])
        .then(([nextApplications, nextAppointments]) => {
          if (!active) return;
          setApplications(nextApplications);
          setAppointments(nextAppointments);
        })
        .catch(() => {
          if (active) setError("Admin data unavailable. Confirm your account has admin role and the API is running.");
        });
      return () => {
        active = false;
      };
    }
  }, [loading, user, router, load]);

  async function review(id: number, action: "approve" | "reject") {
    setBusy(id);
    setError("");
    try {
      await reviewDoctorApplication(id, action);
      await load();
    } catch {
      setError("Application review failed.");
    } finally {
      setBusy(null);
    }
  }

  if (loading || !user || user.role !== "admin") {
    return <section className="px-4 py-10">Loading admin access…</section>;
  }

  return (
    <section className="px-4 py-8">
      <div className="mx-auto max-w-5xl">
        <Badge variant="warning">ADMIN · DEMO</Badge>
        <h1 className="mt-2 text-3xl font-bold">Admin dashboard</h1>
        {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
        <section className="mt-6">
          <h2 className="mb-3 text-xl font-semibold">
            Provider applications ({applications.filter((application) => application.status === "pending").length} pending)
          </h2>
          {applications.length ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {applications.map((application) => (
                <Card key={application.id} className="p-4">
                  <strong>{application.applicant_name ?? "Applicant"}</strong>
                  <p className="text-sm text-ink-muted">
                    {application.applicant_email} · {application.doctor_name ?? `Listing ${application.doctor_id}`}
                  </p>
                  <Badge variant="info">{application.status}</Badge>
                  {application.status === "pending" && (
                    <div className="mt-3 flex gap-2">
                      <Button disabled={busy === application.id} onClick={() => void review(application.id, "approve")}>
                        Approve
                      </Button>
                      <Button
                        disabled={busy === application.id}
                        variant="outline"
                        onClick={() => void review(application.id, "reject")}
                      >
                        Reject
                      </Button>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-5 text-sm text-ink-muted">No applications.</Card>
          )}
        </section>
        <section className="mt-8">
          <h2 className="mb-3 text-xl font-semibold">Appointments ({appointments.length})</h2>
          {appointments.length ? (
            <div className="grid gap-3 md:grid-cols-2">
              {appointments.map((appointment) => (
                <Card key={appointment.reference} className="p-4">
                  <strong>{appointment.doctor_name}</strong>
                  <p className="text-sm text-ink-muted">
                    {appointment.appointment_date} {appointment.appointment_time} · {appointment.location}
                  </p>
                  <p className="text-sm">
                    {appointment.status} · {appointment.payment_status} · demo
                  </p>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-5 text-sm text-ink-muted">No appointment records.</Card>
          )}
        </section>
        <AdminPackagePlans />
        <AdminSubscriptions />
      </div>
    </section>
  );
}
