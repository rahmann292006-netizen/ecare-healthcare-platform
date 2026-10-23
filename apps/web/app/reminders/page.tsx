"use client";

import { useState } from "react";
import { DEMO_REMINDERS } from "@/lib/mock-data";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

export default function RemindersPage() {
  const [reminders, setReminders] = useState(
    DEMO_REMINDERS.map((r) => ({ ...r }))
  );
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    title: "",
    category: "checkup",
    date: "",
    repeatInterval: "none" as const,
    childProfile: "",
    vaccinationDate: "",
  });

  const active = reminders.filter((r) => !r.completed);
  const completed = reminders.filter((r) => r.completed);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title || !form.date) return;
    const newReminder = {
      id: `rem-${Date.now()}`,
      title: form.title,
      category: form.category,
      date: form.date,
      repeatInterval: form.repeatInterval,
      completed: false,
      childProfile: form.childProfile || undefined,
      vaccinationDate: form.vaccinationDate || undefined,
      isSample: true,
    };
    setReminders([...reminders, newReminder]);
    setForm({
      title: "",
      category: "checkup",
      date: "",
      repeatInterval: "none",
      childProfile: "",
      vaccinationDate: "",
    });
    setOpen(false);
  };

  const toggleComplete = (id: string) => {
    setReminders(
      reminders.map((r) =>
        r.id === id ? { ...r, completed: !r.completed } : r
      )
    );
  };

  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold text-ink mb-2">Reminders</h1>
        <p className="text-sm text-ink-muted mb-8">
          Manage your health checkup and vaccination reminders.
        </p>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-ink">All reminders</h2>
            <p className="text-sm text-ink-muted">
              {reminders.length} total &middot; {active.length} active
            </p>
          </div>
          <Button variant="primary" onClick={() => setOpen(true)}>
            Add reminder
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ReminderList title="Upcoming" reminders={active} onToggle={toggleComplete} />
          <ReminderList title="Completed" reminders={completed} onToggle={toggleComplete} />
        </div>

        <div
          className={`fixed inset-0 z-50 flex items-center justify-center ${open ? "" : "hidden"}`}
          aria-modal="true"
          role="dialog"
        >
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="relative bg-background rounded-[var(--radius-card)] border border-solid border-border p-6 shadow-xl w-full max-w-md m-4">
            <h2 className="text-xl font-bold text-ink mb-4">Add reminder</h2>
            <form onSubmit={handleAdd} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-ink mb-1">Title</label>
                <Input
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="e.g. Annual checkup"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-ink mb-1">Category</label>
                  <Select
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value as DemoReminder["category"] })}
                  >
                    <option value="checkup">Checkup</option>
                    <option value="vaccination">Vaccination</option>
                    <option value="dental">Dental</option>
                    <option value="other">Other</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink mb-1">Date</label>
                  <Input
                    type="date"
                    value={form.date}
                    onChange={(e) => setForm({ ...form, date: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-ink mb-1">Repeat interval</label>
                <Select
                  value={form.repeatInterval}
                  onChange={(e) => setForm({ ...form, repeatInterval: e.target.value as DemoReminder["repeatInterval"] })}
                >
                  <option value="none">None</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </Select>
              </div>
              <div className="bg-navy-50 rounded-[var(--radius-control)] p-3 border border-solid border-border">
                <p className="text-xs font-medium text-ink mb-2">Child profile & vaccination</p>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-ink mb-1">Child profile name</label>
                    <Input
                      value={form.childProfile}
                      onChange={(e) => setForm({ ...form, childProfile: e.target.value })}
                      placeholder="e.g. Aarav (age 4)"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-ink mb-1">Vaccination date</label>
                    <Input
                      type="date"
                      value={form.vaccinationDate}
                      onChange={(e) => setForm({ ...form, vaccinationDate: e.target.value })}
                    />
                    <p className="text-[10px] text-ink-muted mt-1">
                      Enter dates supplied by a qualified healthcare professional.
                    </p>
                  </div>
                </div>
              </div>
              <div className="flex gap-3 mt-2">
                <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary">Add reminder</Button>
              </div>
            </form>
            <p className="mt-4 text-xs text-ink-muted">
              Reminders are stored locally in this demo. No emails, SMS, or
              WhatsApp messages are sent.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function ReminderList({
  title,
  reminders,
  onToggle,
}: {
  title: string;
  reminders: (typeof DEMO_REMINDERS)[number][];
  onToggle: (id: string) => void;
}) {
  return (
    <Card className="rounded-[var(--radius-card)] p-4">
      <h3 className="text-sm font-semibold text-ink mb-4">{title}</h3>
      {reminders.length > 0 ? (
        <ul className="space-y-3">
          {reminders.map((r) => (
            <li
              key={r.id}
              className="flex items-center gap-3 p-3 rounded-[var(--radius-control)] border border-solid border-border hover:bg-navy-50"
            >
              <button
                onClick={() => onToggle(r.id)}
                className="shrink-0"
              >
                {r.completed ? (
                  <svg className="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5 text-ink-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M1 4.35A2 2 0 014.35 2h6.3a2 2 0 011.893 1.15L12.5 5H19a2 2 0 012 2v11a2 2 0 01-2 2H5a2 2 0 01-2-2V4.35z" />
                  </svg>
                )}
              </button>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-ink truncate">{r.title}</p>
                <p className="text-xs text-ink-muted">{r.category} &middot; {r.date}</p>
                {r.childProfile && (
                  <p className="text-xs text-teal-700 mt-0.5">Child: {r.childProfile}</p>
                )}
              </div>
              <Badge variant={r.completed ? "success" : "verified"} className="text-xs shrink-0">
                {r.completed ? "Done" : "Pending"}
              </Badge>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-ink-muted text-center">None.</p>
      )}
    </Card>
  );
}

import { Card } from "@/components/ui/card";
