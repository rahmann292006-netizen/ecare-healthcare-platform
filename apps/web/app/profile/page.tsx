"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import {
  updateMe,
  changePassword,
  listMyAppointments,
  listMyInvoices,
  type AppointmentRecord,
  type InvoiceRecord,
} from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function ProfilePage() {
  const { user, loading, refreshUser, signOut } = useAuth();
  const router = useRouter();
  const [nameDraft, setNameDraft] = useState<string | null>(null);
  const [phoneDraft, setPhoneDraft] = useState<string | null>(null);
  const [appointments, setAppointments] = useState<AppointmentRecord[]>([]);
  const [invoices, setInvoices] = useState<InvoiceRecord[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [passwords, setPasswords] = useState({ current: "", next: "" });
  const name = nameDraft ?? user?.full_name ?? "";
  const phone = phoneDraft ?? user?.phone ?? "";

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login?next=%2Fprofile");
    }
    if (!user) return;

    let active = true;
    Promise.all([listMyAppointments(), listMyInvoices()])
      .then(([nextAppointments, nextInvoices]) => {
        if (!active) return;
        setAppointments(nextAppointments);
        setInvoices(nextInvoices);
      })
      .catch(() => {
        if (active) setError("Could not load account records. Check API availability.");
      });

    return () => {
      active = false;
    };
  }, [loading, user, router]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await updateMe({ full_name: name, phone: phone || null });
      const refreshedUser = await refreshUser();
      if (refreshedUser) {
        setNameDraft(refreshedUser.full_name);
        setPhoneDraft(refreshedUser.phone ?? "");
      }
      setMessage("Profile updated.");
    } catch {
      setError("Profile could not be updated.");
    }
  }

  async function changeUserPassword(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await changePassword(passwords.current, passwords.next);
      setPasswords({ current: "", next: "" });
      setMessage("Password changed.");
    } catch {
      setError("Password could not be changed. Check current password and API availability.");
    }
  }

  if (loading || !user) {
    return <section className="px-4 py-10"><p>Loading account…</p></section>;
  }

  return (
    <section className="px-4 py-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-6">
          <Badge variant="warning">DEMO ACCOUNT</Badge>
          <h1 className="mt-2 text-3xl font-bold text-ink">My Profile</h1>
          <p className="text-sm text-ink-muted">Signed in as {user.role} · {user.email}</p>
        </header>
        {message && <p role="status" className="mb-3 text-sm text-success">{message}</p>}
        {error && <p role="alert" className="mb-3 text-sm text-danger">{error}</p>}
        <div className="grid gap-5 lg:grid-cols-2">
          <Card className="p-5">
            <h2 className="text-lg font-semibold">Account details</h2>
            <form onSubmit={save} className="mt-4 space-y-3">
              <label className="block text-sm">
                Full name
                <input
                  required
                  value={name}
                  onChange={(event) => setNameDraft(event.target.value)}
                  className="mt-1 w-full rounded border border-border bg-background px-3 py-2"
                />
              </label>
              <label className="block text-sm">
                Phone
                <input
                  value={phone}
                  onChange={(event) => setPhoneDraft(event.target.value)}
                  className="mt-1 w-full rounded border border-border bg-background px-3 py-2"
                />
              </label>
              <Button>Save profile</Button>
            </form>
          </Card>
          <Card className="p-5">
            <h2 className="text-lg font-semibold">Change password</h2>
            <form onSubmit={changeUserPassword} className="mt-4 space-y-3">
              <label className="block text-sm">
                Current password
                <input
                  required
                  type="password"
                  value={passwords.current}
                  onChange={(event) => setPasswords((current) => ({ ...current, current: event.target.value }))}
                  className="mt-1 w-full rounded border border-border bg-background px-3 py-2"
                />
              </label>
              <label className="block text-sm">
                New password
                <input
                  required
                  minLength={8}
                  type="password"
                  value={passwords.next}
                  onChange={(event) => setPasswords((current) => ({ ...current, next: event.target.value }))}
                  className="mt-1 w-full rounded border border-border bg-background px-3 py-2"
                />
              </label>
              <Button variant="outline">Update password</Button>
            </form>
            <Button
              className="mt-4"
              variant="outline"
              onClick={async () => {
                await signOut();
                router.push("/");
              }}
            >
              Log out
            </Button>
          </Card>
        </div>
        <section className="mt-8">
          <div className="mb-3 flex justify-between">
            <h2 className="text-xl font-bold">Your appointments</h2>
            <span className="text-sm text-ink-muted">{appointments.length} records</span>
          </div>
          {appointments.length ? (
            <div className="grid gap-3 md:grid-cols-2">
              {appointments.map((appointment) => (
                <Card key={appointment.reference} className="p-4">
                  <div className="flex justify-between gap-2">
                    <strong>{appointment.doctor_name}</strong>
                    <Badge variant="info">{appointment.status}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-ink-muted">
                    {appointment.appointment_date} at {appointment.appointment_time} · {appointment.location}
                  </p>
                  <p className="mt-1 text-sm">
                    {appointment.package_name ?? "Consultation"} · ₹{appointment.total_amount}
                  </p>
                  <Link
                    className="mt-2 inline-block text-sm text-teal-700 underline"
                    href={`/profile/appointments/${appointment.reference}`}
                  >
                    View invoice and details
                  </Link>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-5 text-sm text-ink-muted">
              No account-linked appointments yet.{" "}
              <Link href="/find?provider_type=doctor" className="text-teal-700 underline">Browse doctors</Link>
            </Card>
          )}
        </section>
        <section className="mt-8">
          <h2 className="mb-3 text-xl font-bold">Payment history</h2>
          {invoices.length ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {invoices.map((invoice) => (
                <Card key={invoice.invoice_number} className="p-4">
                  <p className="font-semibold">{invoice.invoice_number}</p>
                  <p className="text-sm text-ink-muted">
                    Demo invoice · Total ₹{invoice.total_amount} · Balance ₹{invoice.outstanding_balance}
                  </p>
                  {invoice.payments.map((payment) => (
                    <p key={payment.id} className="mt-1 text-xs text-ink-muted">
                      {payment.method_label}: {payment.status} (₹{payment.amount})
                    </p>
                  ))}
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-5 text-sm text-ink-muted">No invoice records.</Card>
          )}
        </section>
      </div>
    </section>
  );
}
