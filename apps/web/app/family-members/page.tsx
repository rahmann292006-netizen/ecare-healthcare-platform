"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import {
  createFamilyMember,
  listFamilyMembers,
  deleteFamilyMember,
  type FamilyMemberRecord,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

export default function FamilyMembersPage() {
  const { user, loading } = useAuth();
  const [members, setMembers] = useState<FamilyMemberRecord[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [form, setForm] = useState<{
    name: string;
    relationship_type: FamilyMemberRecord["relationship_type"];
  }>({
    name: "",
    relationship_type: "self",
  });

  const loadMembers = useCallback(async () => {
    setLoadingMembers(true);
    try {
      const ms = await listFamilyMembers();
      setMembers(ms);
    } catch {
      setError("Could not load family members.");
    } finally {
      setLoadingMembers(false);
    }
  }, []);

  useEffect(() => {
    if (loading || !user) return;
    let active = true;
    listFamilyMembers()
      .then((nextMembers) => {
        if (active) setMembers(nextMembers);
      })
      .catch(() => {
        if (active) setError("Could not load family members.");
      })
      .finally(() => {
        if (active) setLoadingMembers(false);
      });
    return () => {
      active = false;
    };
  }, [loading, user]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = form.name.trim();
    if (!name) {
      setError("Enter a name for the family member.");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await createFamilyMember({
        name,
        relationship_type: form.relationship_type,
      });
      setForm({ name: "", relationship_type: "self" });
      setOpen(false);
      await loadMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add family member.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this family member? Their reminders will also be removed.")) return;
    setError(null);
    setDeletingId(id);
    try {
      await deleteFamilyMember(id);
      await loadMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete family member.");
    } finally {
      setDeletingId(null);
    }
  };

  if (loading || (!user && !loading)) {
    return (
      <section className="px-4 py-12">
        <p className="text-ink-muted">Please sign in to manage family members.</p>
      </section>
    );
  }

  if (loadingMembers) {
    return (
      <section className="px-4 py-12">
        <p role="status" className="text-ink-muted">Loading your family members…</p>
      </section>
    );
  }

  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold text-ink mb-2">Family Members</h1>
        <p className="text-sm text-ink-muted mb-8">
          Manage family members for your in-app health reminders.
        </p>
        {error && (
          <div role="alert" className="mb-4 rounded border border-danger bg-danger/5 p-4 text-sm text-danger">
            {error}
          </div>
        )}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-ink">Your family members</h2>
            <p className="text-sm text-ink-muted">
              {members.length} member(s)
            </p>
          </div>
          <Button variant="primary" onClick={() => setOpen(true)} disabled={loadingMembers}>
            Add family member
          </Button>
        </div>

        {members.length === 0 && (
          <div className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-12 text-center shadow-[var(--shadow-card)]">
            <p className="text-ink-muted">
              No family members added yet. Add a family member to get started.
            </p>
          </div>
        )}

        {members.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {members.map((m) => (
              <Card key={m.id} className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-semibold text-ink">{m.name}</h3>
                  <Badge variant="info">{m.relationship_type}</Badge>
                </div>
                <p className="text-xs text-ink-muted">
                  Added {m.created_at.slice(0, 10)}
                </p>
                <button
                  type="button"
                  onClick={() => handleDelete(m.id)}
                  disabled={deletingId !== null}
                  className="mt-3 inline-block text-xs text-danger underline underline-offset-2 hover:text-danger/80"
                >
                  {deletingId === m.id ? "Deleting…" : "Delete family member"}
                </button>
              </Card>
            ))}
          </div>
        )}

        {open && <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          aria-modal="true"
          role="dialog"
        >
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="relative bg-background rounded-[var(--radius-card)] border border-solid border-border p-6 shadow-xl w-full max-w-md m-4">
            <h2 className="text-xl font-bold text-ink mb-4">Add family member</h2>
            <form onSubmit={handleAdd} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-ink mb-1">Name</label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  maxLength={255}
                  placeholder="e.g. Aarav"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink mb-1">Relationship</label>
                <SelectPlaceholder
                  value={form.relationship_type}
                  onChange={(e) => setForm({ ...form, relationship_type: e.target.value as FamilyMemberRecord["relationship_type"] })}
                  className="mt-1 w-full"
                >
                  <option value="self">Self</option>
                  <option value="father">Father</option>
                  <option value="mother">Mother</option>
                  <option value="child">Child</option>
                  <option value="other">Other</option>
                </SelectPlaceholder>
              </div>
              <div className="flex gap-3 mt-2">
                <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" disabled={saving}>
                  {saving ? "Adding…" : "Add member"}
                </Button>
              </div>
            </form>
          </div>
        </div>}
      </div>
    </section>
  );
}

function SelectPlaceholder({
  value,
  onChange,
  className,
  children,
}: {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <select value={value} onChange={onChange} className={className}>
      {children}
    </select>
  );
}
