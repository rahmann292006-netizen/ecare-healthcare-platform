"use client";

import { useCallback, useEffect, useState } from "react";
import {
  cancelAdminSubscription,
  listAdminSubscriptions,
  type SubscriptionRecord,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

function formatUtc(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value)) + " UTC";
}

function statusVariant(status: SubscriptionRecord["status"]) {
  if (status === "active") return "success";
  if (status === "pending_payment" || status === "scheduled") return "warning";
  return "info";
}

export function AdminSubscriptions() {
  const [subscriptions, setSubscriptions] = useState<SubscriptionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const records = await listAdminSubscriptions();
      setSubscriptions(records);
      setError("");
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Subscription records could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    listAdminSubscriptions()
      .then((records) => {
        if (!active) return;
        setSubscriptions(records);
        setError("");
      })
      .catch((loadError: unknown) => {
        if (!active) return;
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Subscription records could not be loaded.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function cancel(subscription: SubscriptionRecord) {
    setBusyId(subscription.id);
    setError("");
    try {
      await cancelAdminSubscription(subscription.id);
      await load();
    } catch (cancelError) {
      setError(
        cancelError instanceof Error
          ? cancelError.message
          : "The subscription could not be cancelled.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="mt-8" aria-labelledby="admin-subscriptions-title">
      <h2 id="admin-subscriptions-title" className="mb-3 text-xl font-semibold">
        Subscriptions ({subscriptions.length})
      </h2>
      {error && <p role="alert" className="mb-3 text-sm text-danger">{error}</p>}
      {loading ? (
        <p role="status">Loading subscriptions…</p>
      ) : subscriptions.length === 0 ? (
        <Card className="p-5 text-sm text-ink-muted">No subscriptions recorded.</Card>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {subscriptions.map((subscription) => (
            <Card key={subscription.id} className="p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong>{subscription.plan.name}</strong>
                <Badge variant={statusVariant(subscription.status)}>{subscription.status.replaceAll("_", " ")}</Badge>
              </div>
              <p className="mt-2 text-sm text-ink-muted">
                User {subscription.user_id} · ₹{subscription.amount} {subscription.currency} · {subscription.payment_status}
                {subscription.payment_status === "simulated" ? " (no real charge)" : ""}
              </p>
              <p className="text-sm text-ink-muted">
                Starts {formatUtc(subscription.start_at)} · Expires {formatUtc(subscription.expires_at)}
              </p>
              <p className="mt-1 text-xs text-ink-muted">
                {subscription.events.length} audit event{subscription.events.length === 1 ? "" : "s"}
                {subscription.reminder ? " · expiry reminder stored in-app" : ""}
              </p>
              {subscription.status !== "cancelled" && subscription.status !== "expired" && (
                <Button
                  type="button"
                  className="mt-3"
                  variant="outline"
                  disabled={busyId === subscription.id}
                  onClick={() => void cancel(subscription)}
                >
                  {busyId === subscription.id ? "Cancelling…" : "Cancel subscription"}
                </Button>
              )}
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}
