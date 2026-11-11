"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  createAdminPackage,
  listAdminPackages,
  updateAdminPackage,
  verifyAdminPackage,
  type PackageCreateRequest,
  type PackageRecord,
  type PackageUpdateRequest,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

type PlanForm = {
  name: string;
  provider_name: string;
  provider_type: "" | "hospital" | "diagnostic_lab";
  price: string;
  currency: string;
  city: string;
  state: string;
  locality: string;
  category: "checkup" | "dental" | "vaccination" | "other";
  description: string;
  min_age_years: string;
  max_age_years: string;
  validity_period: "" | "monthly" | "quarterly" | "yearly";
  validity_description: string;
  source: string;
  source_url: string;
  inclusions: string;
};

const EMPTY_FORM: PlanForm = {
  name: "",
  provider_name: "",
  provider_type: "",
  price: "",
  currency: "INR",
  city: "",
  state: "",
  locality: "",
  category: "checkup",
  description: "",
  min_age_years: "",
  max_age_years: "",
  validity_period: "",
  validity_description: "",
  source: "",
  source_url: "",
  inclusions: "",
};

function formFromPackage(plan: PackageRecord): PlanForm {
  const categories: PlanForm["category"][] = ["checkup", "dental", "vaccination", "other"];
  return {
    name: plan.name,
    provider_name: plan.provider_name,
    provider_type: plan.provider_type === "hospital" ? "hospital" : "diagnostic_lab",
    price: String(plan.price),
    currency: plan.currency,
    city: plan.city,
    state: plan.state,
    locality: plan.locality ?? "",
    category: categories.includes(plan.category as PlanForm["category"])
      ? plan.category as PlanForm["category"]
      : "checkup",
    description: plan.description ?? "",
    min_age_years: plan.min_age_years === null ? "" : String(plan.min_age_years),
    max_age_years: plan.max_age_years === null ? "" : String(plan.max_age_years),
    validity_period: plan.validity_period ?? "",
    validity_description: plan.validity_description ?? "",
    source: plan.source ?? "",
    source_url: plan.source_url ?? "",
    inclusions: plan.inclusions.map((item) => item.test_name).join("\n"),
  };
}

function optionalNumber(value: string) {
  return value.trim() ? Number(value) : null;
}

function packagePayload(form: PlanForm): PackageCreateRequest {
  const inclusions = form.inclusions
    .split(/\r?\n/)
    .map((testName) => testName.trim())
    .filter(Boolean)
    .map((test_name, display_order) => ({ test_name, display_order }));
  return {
    name: form.name.trim(),
    provider_name: form.provider_name.trim(),
    provider_type: form.provider_type,
    price: Number(form.price),
    currency: form.currency.trim(),
    city: form.city.trim(),
    state: form.state.trim(),
    locality: form.locality.trim() || null,
    category: form.category,
    description: form.description.trim() || null,
    min_age_years: optionalNumber(form.min_age_years),
    max_age_years: optionalNumber(form.max_age_years),
    validity_period: form.validity_period || null,
    validity_description: form.validity_description.trim() || null,
    source: form.source.trim() || null,
    source_url: form.source_url.trim() || null,
    inclusions,
  };
}

function formatDate(value: string | null) {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(value));
}

export function AdminPackagePlans() {
  const [plans, setPlans] = useState<PackageRecord[]>([]);
  const [form, setForm] = useState<PlanForm>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadPlans = useCallback(async () => {
    try {
      const loadedPlans = await listAdminPackages();
      setPlans(loadedPlans);
      setError("");
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Package plans could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    listAdminPackages()
      .then((loadedPlans) => {
        if (!active) return;
        setPlans(loadedPlans);
        setError("");
      })
      .catch((loadError: unknown) => {
        if (!active) return;
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Package plans could not be loaded.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function updateForm<K extends keyof PlanForm>(key: K, value: PlanForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function editPlan(plan: PackageRecord) {
    setEditingId(plan.id);
    setForm(formFromPackage(plan));
    setNotice("");
  }

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function savePlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const payload = packagePayload(form);
      if (editingId === null) {
        await createAdminPackage(payload);
        setNotice("Plan saved as unverified. Verify provider-supplied details before subscriptions are available.");
      } else {
        const update: PackageUpdateRequest = payload;
        const previous = plans.find((plan) => plan.id === editingId);
        const saved = await updateAdminPackage(editingId, update);
        setNotice(
          previous?.is_verified && !saved.is_verified
            ? "Plan updated. Provider verification was cleared and must be repeated."
            : "Plan updated.",
        );
      }
      resetForm();
      await loadPlans();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "The plan could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(plan: PackageRecord) {
    setSaving(true);
    setError("");
    try {
      await updateAdminPackage(plan.id, { is_active: !plan.is_active });
      await loadPlans();
    } catch (toggleError) {
      setError(toggleError instanceof Error ? toggleError.message : "The plan status could not be updated.");
    } finally {
      setSaving(false);
    }
  }

  async function verifyPlan(plan: PackageRecord) {
    setSaving(true);
    setError("");
    setNotice("");
    try {
      await verifyAdminPackage(plan.id, {
        source: plan.source ?? "",
        source_url: plan.source_url,
      });
      setNotice(`${plan.name} was marked verified with the recorded provider source and timestamp.`);
      await loadPlans();
    } catch (verificationError) {
      setError(
        verificationError instanceof Error
          ? verificationError.message
          : "The plan could not be verified.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="mt-8" aria-labelledby="admin-plans-title">
      <h2 id="admin-plans-title" className="mb-2 text-xl font-semibold">Health checkup plans</h2>
      <p className="mb-4 text-sm text-ink-muted">
        Enter only provider-supplied prices, validity, age range, and included tests. New or edited plans are unverified until reviewed.
      </p>
      {error && <p role="alert" className="mb-3 text-sm text-danger">{error}</p>}
      {notice && <p role="status" className="mb-3 text-sm text-success">{notice}</p>}

      <Card className="p-5">
        <h3 className="mb-4 text-lg font-semibold">
          {editingId === null ? "Create plan" : `Update plan ${editingId}`}
        </h3>
        <form className="grid gap-3 sm:grid-cols-2" onSubmit={(event) => void savePlan(event)}>
          <label className="grid gap-1 text-sm">Plan name
            <input required maxLength={255} value={form.name} onChange={(event) => updateForm("name", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm">Provider name
            <input required maxLength={255} value={form.provider_name} onChange={(event) => updateForm("provider_name", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm">Provider type
            <select required value={form.provider_type} onChange={(event) => updateForm("provider_type", event.target.value as PlanForm["provider_type"])} className="rounded border border-border px-3 py-2">
              <option value="">Select provider type</option>
              <option value="hospital">Hospital</option>
              <option value="diagnostic_lab">Diagnostic lab</option>
            </select>
          </label>
          <label className="grid gap-1 text-sm">Provider-supplied price
            <input required type="number" min="0" step="0.01" value={form.price} onChange={(event) => updateForm("price", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm">City
            <input required maxLength={100} value={form.city} onChange={(event) => updateForm("city", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm">State
            <input required maxLength={100} value={form.state} onChange={(event) => updateForm("state", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm">Locality
            <input maxLength={255} value={form.locality} onChange={(event) => updateForm("locality", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm">Category
            <select value={form.category} onChange={(event) => updateForm("category", event.target.value as PlanForm["category"])} className="rounded border border-border px-3 py-2">
              <option value="checkup">Checkup</option><option value="dental">Dental</option><option value="vaccination">Vaccination</option><option value="other">Other</option>
            </select>
          </label>
          <label className="grid gap-1 text-sm">Minimum age in years (optional)
            <input type="number" min="0" max="130" value={form.min_age_years} onChange={(event) => updateForm("min_age_years", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm">Maximum age in years (optional)
            <input type="number" min="0" max="130" value={form.max_age_years} onChange={(event) => updateForm("max_age_years", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm">Provider-supplied validity
            <select value={form.validity_period} onChange={(event) => updateForm("validity_period", event.target.value as PlanForm["validity_period"])} className="rounded border border-border px-3 py-2">
              <option value="">Not supplied</option><option value="monthly">Monthly</option><option value="quarterly">Quarterly</option><option value="yearly">Yearly</option>
            </select>
          </label>
          <label className="grid gap-1 text-sm">Validity details from provider
            <input value={form.validity_description} onChange={(event) => updateForm("validity_description", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm sm:col-span-2">Provider source
            <input value={form.source} onChange={(event) => updateForm("source", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm sm:col-span-2">Provider source URL
            <input type="url" value={form.source_url} onChange={(event) => updateForm("source_url", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm sm:col-span-2">Included tests (one provider-supplied test per line)
            <textarea rows={3} value={form.inclusions} onChange={(event) => updateForm("inclusions", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm sm:col-span-2">Description
            <textarea rows={3} value={form.description} onChange={(event) => updateForm("description", event.target.value)} className="rounded border border-border px-3 py-2" />
          </label>
          <div className="flex flex-wrap gap-2 sm:col-span-2">
            <Button type="submit" disabled={saving}>{saving ? "Saving…" : editingId === null ? "Create plan" : "Save plan"}</Button>
            {editingId !== null && <Button type="button" variant="outline" disabled={saving} onClick={resetForm}>Cancel edit</Button>}
          </div>
        </form>
      </Card>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {loading ? <p role="status">Loading plans…</p> : plans.length === 0 ? <Card className="p-5 text-sm text-ink-muted">No plans have been created.</Card> : plans.map((plan) => (
          <Card key={plan.id} className="p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div><h3 className="font-semibold">{plan.name}</h3><p className="text-sm text-ink-muted">{plan.provider_name} · {plan.city}, {plan.state}</p></div>
              <Badge variant={plan.is_verified ? "success" : "warning"}>{plan.is_verified ? `Verified · ${formatDate(plan.verified_at)}` : "Unverified"}</Badge>
            </div>
            <p className="mt-2 text-sm">₹{plan.price} {plan.currency} · {plan.validity_description || plan.validity_period || "Validity not supplied"}</p>
            <p className="text-sm text-ink-muted">Age range: {plan.min_age_years ?? "—"} to {plan.max_age_years ?? "—"} years · {plan.is_active ? "Active" : "Inactive"}</p>
            <p className="mt-1 text-xs text-ink-muted">Source: {plan.source || "Not recorded"}{plan.is_demo ? " · Sample only" : ""}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button type="button" variant="outline" disabled={saving} onClick={() => editPlan(plan)}>Edit</Button>
              <Button type="button" variant="outline" disabled={saving || plan.is_verified || plan.is_demo} onClick={() => void verifyPlan(plan)}>Verify source</Button>
              <Button type="button" variant="outline" disabled={saving} onClick={() => void toggleActive(plan)}>{plan.is_active ? "Deactivate" : "Activate"}</Button>
            </div>
          </Card>
        ))}
      </div>
    </section>
  );
}
