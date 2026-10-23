"use strict";

import Link from "next/link";
import { DEMO_REMINDERS } from "@/lib/mock-data";
import { Badge } from "@/components/ui/badge";

const upcoming = DEMO_REMINDERS.filter((r) => !r.completed);
const completed = DEMO_REMINDERS.filter((r) => r.completed);

export default function DashboardPage() {
  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold text-ink mb-2">My Health Dashboard</h1>
        <p className="text-sm text-ink-muted mb-8">
          Your subscriptions, reminders, and quick actions.
        </p>

        {/* Summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <SummaryCard
            title="Active subscriptions"
            value="0"
            subtitle="No active subscriptions"
            variant="navy"
          />
          <SummaryCard
            title="Upcoming reminders"
            value={upcoming.length.toString()}
            subtitle="Reminders due soon"
            variant="teal"
          />
          <SummaryCard
            title="Completed reminders"
            value={completed.length.toString()}
            subtitle="Marked as done"
            variant="success"
          />
        </div>

        {/* Upcoming reminders */}
        <section className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-ink">Upcoming reminders</h2>
            <Link
              href="/reminders"
              className="text-sm font-medium text-teal-700 hover:underline"
            >
              View all
            </Link>
          </div>
          {upcoming.length > 0 ? (
            <div className="space-y-3">
              {upcoming.map((r) => (
                <ReminderRow key={r.id} reminder={r} />
              ))}
            </div>
          ) : (
            <div className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-6 text-center shadow-[var(--shadow-card)]">
              <p className="text-ink-muted">No upcoming reminders.</p>
            </div>
          )}
        </section>

        {/* Completed reminders */}
        <section className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-ink">Completed reminders</h2>
            <Link
              href="/reminders"
              className="text-sm font-medium text-teal-700 hover:underline"
            >
              View all
            </Link>
          </div>
          {completed.length > 0 ? (
            <div className="space-y-3">
              {completed.map((r) => (
                <ReminderRow key={r.id} reminder={r} completed />
              ))}
            </div>
          ) : (
            <div className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-6 text-center shadow-[var(--shadow-card)]">
              <p className="text-ink-muted">No completed reminders.</p>
            </div>
          )}
        </section>

        {/* Quick actions */}
        <section>
          <h2 className="text-xl font-bold text-ink mb-4">Quick actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <QuickAction
              title="Add reminder"
              description="Schedule a health checkup or vaccination reminder"
              href="/reminders"
              icon="+"
            />
            <QuickAction
              title="Browse packages"
              description="Explore health checkup packages"
              href="/packages"
              icon="📦"
            />
            <QuickAction
              title="Find providers"
              description="Search hospitals, doctors, and labs"
              href="/find"
              icon="🔍"
            />
          </div>
        </section>
      </div>
    </section>
  );
}

function SummaryCard({
  title,
  value,
  subtitle,
  variant,
}: {
  title: string;
  value: string;
  subtitle: string;
  variant: "navy" | "teal" | "success";
}) {
  const variants: Record<string, string> = {
    navy: "bg-navy-900 text-white",
    teal: "bg-teal-700 text-white",
    success: "bg-success text-white",
  };
  return (
    <Card className={`rounded-[var(--radius-card)] p-6 ${variants[variant]}`}>
      <p className="text-sm opacity-90 mb-1">{title}</p>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs opacity-80 mt-1">{subtitle}</p>
    </Card>
  );
}

function ReminderRow({
  reminder,
  completed,
}: {
  reminder: (typeof DEMO_REMINDERS)[number];
  completed?: boolean;
}) {
  return (
    <Card className="rounded-[var(--radius-card)] p-4 flex items-center gap-3">
      <div className="flex-1">
        <p className="text-sm font-medium text-ink">{reminder.title}</p>
        <p className="text-xs text-ink-muted">
          {reminder.category} &middot; {reminder.date}
        </p>
      </div>
      <Badge
        variant={completed ? "success" : "verified"}
        className="text-xs"
      >
        {completed ? "Completed" : "Upcoming"}
      </Badge>
    </Card>
  );
}

function QuickAction({
  title,
  description,
  href,
  icon,
}: {
  title: string;
  description: string;
  href: string;
  icon: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-4 shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-card)] transition-shadow"
    >
      <div className="text-2xl mb-2">{icon}</div>
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <p className="text-xs text-ink-muted">{description}</p>
    </Link>
  );
}

import { Card } from "@/components/ui/card";
