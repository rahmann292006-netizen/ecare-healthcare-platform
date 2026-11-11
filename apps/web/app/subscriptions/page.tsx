"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  cancelSubscription,
  createSubscription,
  getSubscriptionPaymentOptions,
  listFamilyMembers,
  listMySubscriptions,
  listPackages,
  renewSubscription,
  simulateSubscriptionPayment,
  type FamilyMemberRecord,
  type PackageRecord,
  type SubscriptionPaymentOptions,
  type SubscriptionRecord,
} from "@/lib/api";

function isSubscribable(plan: PackageRecord) {
  return (
    plan.is_active &&
    !plan.is_demo &&
    plan.is_verified &&
    Boolean(plan.source?.trim()) &&
    Boolean(plan.verified_at) &&
    Boolean(plan.validity_period)
  );
}

function statusLabel(subscription: SubscriptionRecord) {
  if (subscription.status === "active" && subscription.payment_status === "simulated") {
    return "Active · simulated payment";
  }
  return subscription.status.replaceAll("_", " ");
}

function statusVariant(status: SubscriptionRecord["status"]) {
  if (status === "active") return "success";
  if (status === "pending_payment" || status === "scheduled") return "warning";
  return "info";
}

function formatUtc(value: string) {
  return `${new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value))} UTC`;
}

function money(amount: number, currency: string) {
  return `${currency} ${amount.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export default function SubscriptionsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [plans, setPlans] = useState<PackageRecord[]>([]);
  const [familyMembers, setFamilyMembers] = useState<FamilyMemberRecord[]>([]);
  const [subscriptions, setSubscriptions] = useState<SubscriptionRecord[]>([]);
  const [paymentOptions, setPaymentOptions] = useState<SubscriptionPaymentOptions | null>(null);
  const [familyMemberId, setFamilyMemberId] = useState("");
  const [ageYears, setAgeYears] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [busyPlanId, setBusyPlanId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loadingData, setLoadingData] = useState(true);

  const subscribablePlans = useMemo(() => plans.filter(isSubscribable), [plans]);

  const loadData = useCallback(async () => {
    if (!user || user.role !== "patient") return;
    try {
      const [packageResponse, members, records, paymentMode] = await Promise.all([
        listPackages({ is_active: true, limit: 100 }),
        listFamilyMembers(),
        listMySubscriptions(),
        getSubscriptionPaymentOptions(),
      ]);
      setPlans(packageResponse.items);
      setFamilyMembers(members);
      setSubscriptions(records);
      setPaymentOptions(paymentMode);
      setError("");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Subscription data could not be loaded.");
    } finally {
      setLoadingData(false);
    }
  }, [user]);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login?next=%2Fsubscriptions");
      return;
    }
    if (user && user.role !== "patient") {
      router.replace(user.role === "admin" ? "/admin" : "/provider");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (user?.role !== "patient") return;
    let active = true;
    Promise.all([
      listPackages({ is_active: true, limit: 100 }),
      listFamilyMembers(),
      listMySubscriptions(),
      getSubscriptionPaymentOptions(),
    ])
      .then(([packageResponse, members, records, paymentMode]) => {
        if (!active) return;
        setPlans(packageResponse.items);
        setFamilyMembers(members);
        setSubscriptions(records);
        setPaymentOptions(paymentMode);
        setError("");
      })
      .catch((loadError: unknown) => {
        if (!active) return;
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Subscription data could not be loaded.",
        );
      })
      .finally(() => {
        if (active) setLoadingData(false);
      });
    return () => {
      active = false;
    };
  }, [user]);

  function subscriptionInput(planId: number, fallbackAge?: number | null) {
    const enteredAge = ageYears.trim() ? Number(ageYears) : fallbackAge;
    return {
      plan_id: planId,
      family_member_id: familyMemberId ? Number(familyMemberId) : null,
      age_years: enteredAge ?? null,
    };
  }

  async function subscribe(plan: PackageRecord) {
    setBusyPlanId(plan.id);
    setError("");
    setNotice("");
    try {
      await createSubscription(subscriptionInput(plan.id));
      setNotice(
        paymentOptions?.mode === "simulated"
          ? "Subscription recorded as Pending Payment. No charge has been made."
          : "Subscription recorded as Pending Payment. No gateway is configured, so no charge or entitlement was created.",
      );
      await loadData();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "The subscription could not be created.");
    } finally {
      setBusyPlanId(null);
    }
  }

  async function renew(subscription: SubscriptionRecord) {
    setBusyId(subscription.id);
    setError("");
    setNotice("");
    try {
      await renewSubscription(
        subscription.id,
        subscriptionInput(subscription.plan_id, subscription.age_years_at_start),
      );
      setNotice("Renewal recorded as Pending Payment. It does not activate until payment is recorded.");
      await loadData();
    } catch (renewError) {
      setError(renewError instanceof Error ? renewError.message : "The renewal could not be created.");
    } finally {
      setBusyId(null);
    }
  }

  async function simulatePayment(subscription: SubscriptionRecord) {
    setBusyId(subscription.id);
    setError("");
    setNotice("");
    try {
      const updated = await simulateSubscriptionPayment(subscription.id);
      setNotice(
        updated.status === "scheduled"
          ? "Demo payment recorded; no real charge was made. Access begins on the renewal start date."
          : "Demo payment recorded; no real charge was made. This is not a live payment.",
      );
      await loadData();
    } catch (paymentError) {
      setError(paymentError instanceof Error ? paymentError.message : "The simulated payment could not be recorded.");
    } finally {
      setBusyId(null);
    }
  }

  async function cancel(subscription: SubscriptionRecord) {
    setBusyId(subscription.id);
    setError("");
    setNotice("");
    try {
      await cancelSubscription(subscription.id);
      setNotice("Subscription cancelled. Its in-app expiry reminder was completed.");
      await loadData();
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : "The subscription could not be cancelled.");
    } finally {
      setBusyId(null);
    }
  }

  if (loading || !user || user.role !== "patient") {
    return <section className="px-4 py-10">Loading subscription access…</section>;
  }

  return (
    <section className="px-4 py-8">
      <div className="mx-auto max-w-5xl">
        <Badge variant="warning">HEALTH CHECKUP SUBSCRIPTIONS</Badge>
        <h1 className="mt-2 text-3xl font-bold">Plans and subscriptions</h1>
        <p className="mt-2 max-w-3xl text-sm text-ink-muted">
          Only active, provider-sourced, verified API plans can be subscribed to. Age is self-reported and is not medically verified. Dates are stored and displayed in UTC.
        </p>
        {paymentOptions && (
          <Card className="mt-4 p-4 text-sm">
            <strong>Payment status:</strong> {paymentOptions.message}
          </Card>
        )}
        {error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}
        {notice && <p role="status" className="mt-4 text-sm text-success">{notice}</p>}

        <section className="mt-7" aria-labelledby="available-plans-title">
          <h2 id="available-plans-title" className="mb-3 text-xl font-semibold">Available plans</h2>
          <Card className="mb-4 grid gap-3 p-4 sm:grid-cols-2">
            <label className="grid gap-1 text-sm">For family member (optional)
              <select value={familyMemberId} onChange={(event) => setFamilyMemberId(event.target.value)} className="rounded border border-border px-3 py-2">
                <option value="">My account</option>
                {familyMembers.map((member) => <option key={member.id} value={member.id}>{member.name} · {member.relationship_type}</option>)}
              </select>
            </label>
            <label className="grid gap-1 text-sm">Self-reported age in years (if the plan has an age range)
              <input type="number" min="0" max="130" value={ageYears} onChange={(event) => setAgeYears(event.target.value)} className="rounded border border-border px-3 py-2" />
            </label>
          </Card>
          {loadingData ? (
            <p role="status">Loading provider-supplied plans…</p>
          ) : subscribablePlans.length === 0 ? (
            <Card className="p-5 text-sm text-ink-muted">
              No verified provider plans with validity details are available yet. Sample and unverified plans are display-only and cannot be subscribed to.
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {subscribablePlans.map((plan) => (
                <Card key={plan.id} className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div><h3 className="text-lg font-semibold">{plan.name}</h3><p className="text-sm text-ink-muted">{plan.provider_name}</p></div>
                    <Badge variant="success">Provider verified</Badge>
                  </div>
                  <p className="mt-3 text-2xl font-bold">{money(plan.price, plan.currency)}</p>
                  <p className="text-sm text-ink-muted">{plan.validity_description || plan.validity_period}</p>
                  {(plan.min_age_years !== null || plan.max_age_years !== null) && (
                    <p className="mt-2 text-sm">Stated age range: {plan.min_age_years ?? "—"} to {plan.max_age_years ?? "—"} years</p>
                  )}
                  {plan.description && <p className="mt-3 text-sm text-ink-muted">{plan.description}</p>}
                  <h4 className="mt-3 text-sm font-semibold">Included tests supplied by provider</h4>
                  {plan.inclusions.length ? (
                    <ul className="mt-1 list-inside list-disc text-sm text-ink-muted">
                      {plan.inclusions.map((item) => <li key={item.id}>{item.test_name}</li>)}
                    </ul>
                  ) : (
                    <p className="mt-1 text-sm text-ink-muted">No included tests are recorded.</p>
                  )}
                  <p className="mt-3 text-xs text-ink-muted">Source: {plan.source} · Verified {formatUtc(plan.verified_at!)}</p>
                  <Button type="button" className="mt-4" disabled={busyPlanId === plan.id} onClick={() => void subscribe(plan)}>
                    {busyPlanId === plan.id ? "Saving…" : "Subscribe"}
                  </Button>
                </Card>
              ))}
            </div>
          )}
        </section>

        <section className="mt-9" aria-labelledby="my-subscriptions-title">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 id="my-subscriptions-title" className="text-xl font-semibold">My subscriptions</h2>
            <Link href="/reminders" className="text-sm text-teal-700 underline">View in-app reminders</Link>
          </div>
          <p className="mb-3 text-sm text-ink-muted">
            Expiry reminders are stored in the app; they do not send email, SMS, or push notifications.
          </p>
          {loadingData ? (
            <p role="status">Loading subscriptions…</p>
          ) : subscriptions.length === 0 ? (
            <Card className="p-5 text-sm text-ink-muted">No subscriptions yet.</Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {subscriptions.map((subscription) => (
                <Card key={subscription.id} className="p-5">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div><h3 className="font-semibold">{subscription.plan.name}</h3><p className="text-sm text-ink-muted">Plan #{subscription.plan_id}</p></div>
                    <Badge variant={statusVariant(subscription.status)}>{statusLabel(subscription)}</Badge>
                  </div>
                  <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                    <div><dt className="text-ink-muted">Price snapshot</dt><dd>{money(Number(subscription.amount), subscription.currency)}</dd></div>
                    <div><dt className="text-ink-muted">Payment status</dt><dd>{subscription.payment_status}{subscription.payment_status === "simulated" ? " · no real charge" : ""}</dd></div>
                    <div><dt className="text-ink-muted">Starts</dt><dd>{formatUtc(subscription.start_at)}</dd></div>
                    <div><dt className="text-ink-muted">Expires</dt><dd>{formatUtc(subscription.expires_at)}</dd></div>
                  </dl>
                  {subscription.reminder && (
                    <p className="mt-3 text-xs text-ink-muted">
                      In-app expiry reminder stored for {subscription.reminder.reminder_date}; no external notification is sent.
                    </p>
                  )}
                  <details className="mt-3 text-xs">
                    <summary className="cursor-pointer font-medium">Transaction and audit history ({subscription.events.length})</summary>
                    <ol className="mt-2 space-y-2">
                      {subscription.events.map((event) => (
                        <li key={event.id} className="border-l-2 border-border pl-3">
                          <strong>{event.event_type.replaceAll("_", " ")}</strong> · {event.payment_status} · {formatUtc(event.created_at)}
                          {event.details && <p className="text-ink-muted">{event.details}</p>}
                        </li>
                      ))}
                    </ol>
                  </details>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {subscription.status === "pending_payment" && paymentOptions?.mode === "simulated" && (
                      <Button type="button" disabled={busyId === subscription.id} onClick={() => void simulatePayment(subscription)}>
                        Record demo payment
                      </Button>
                    )}
                    {subscription.status !== "cancelled" && subscription.status !== "expired" && (
                      <Button type="button" variant="outline" disabled={busyId === subscription.id} onClick={() => void cancel(subscription)}>
                        Cancel
                      </Button>
                    )}
                    {(subscription.status === "active" || subscription.status === "expired") &&
                      subscription.renewal_subscription_id === null && (
                        <Button type="button" variant="outline" disabled={busyId === subscription.id} onClick={() => void renew(subscription)}>
                          Renew
                        </Button>
                      )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
