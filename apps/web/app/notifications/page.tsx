"use strict";

import Link from "next/link";
import { DEMO_NOTIFICATIONS } from "@/lib/mock-data";
import { Badge } from "@/components/ui/badge";

export default function NotificationsPage() {
  const unread = DEMO_NOTIFICATIONS.filter((n) => !n.read);

  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold text-ink mb-2">Notifications</h1>
        <p className="text-sm text-ink-muted mb-8">
          In-app notifications for reminders, package updates, and more.
        </p>

        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-ink">All notifications</h2>
          {unread.length > 0 && (
            <span className="rounded bg-danger px-2 py-0.5 text-xs font-bold text-danger">
              {unread.length} unread
            </span>
          )}
        </div>

        <div className="space-y-3">
          {DEMO_NOTIFICATIONS.map((n) => (
            <NotificationItem key={n.id} notification={n} />
          ))}
        </div>

        {DEMO_NOTIFICATIONS.length === 0 && (
          <div className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-12 text-center shadow-[var(--shadow-card)]">
            <p className="text-ink-muted">No notifications.</p>
          </div>
        )}

        <p className="mt-8 text-xs text-ink-muted">
          Notifications below are sample/demo data. eCare does not send emails,
          SMS, or WhatsApp messages.
        </p>
      </div>
    </section>
  );
}

function NotificationItem({
  notification,
}: {
  notification: (typeof DEMO_NOTIFICATIONS)[number];
}) {
  const typeIcons: Record<string, string> = {
    reminder: "🔔",
    package: "📦",
    completed: "✅",
  };
  const typeLabels: Record<string, string> = {
    reminder: "Reminder",
    package: "Package update",
    completed: "Completed",
  };

  return (
    <Link
      href="#"
      className={`rounded-[var(--radius-card)] border border-solid border-border bg-background p-4 flex items-start gap-3 transition-colors hover:bg-navy-50 ${!notification.read ? "border-teal-700/50 bg-teal-50/50" : ""}`}
    >
      <span className="shrink-0 text-lg">{typeIcons[notification.type]}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-ink">{typeLabels[notification.type]}</span>
          {!notification.read && (
            <Badge variant="verified" className="text-[10px]">
              New
            </Badge>
          )}
        </div>
        <h3 className="text-sm font-semibold text-ink mb-1">{notification.title}</h3>
        <p className="text-sm text-ink-muted">{notification.body}</p>
        <p className="text-xs text-ink-muted mt-1">{new Date(notification.createdAt).toLocaleDateString()}</p>
      </div>
    </Link>
  );
}

import { Card } from "@/components/ui/card";
