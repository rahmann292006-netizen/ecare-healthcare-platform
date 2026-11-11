"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import {
  createFamilyMember,
  listFamilyMembers,
  createReminder,
  listMyReminders,
  updateReminder,
  deleteReminder,
  type FamilyMemberRecord,
  type ReminderRecord,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { useCurrentTime } from "@/lib/use-current-time";

export default function RemindersPage() {
  const { user, loading } = useAuth();
  const [familyMembers, setFamilyMembers] = useState<FamilyMemberRecord[]>([]);
  const [reminders, setReminders] = useState<ReminderRecord[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(true);
  const [loadingReminders, setLoadingReminders] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [memberOpen, setMemberOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [busyReminderId, setBusyReminderId] = useState<number | null>(null);
  const [editingReminderId, setEditingReminderId] = useState<number | null>(null);
  const [form, setForm] = useState<{
    title: string;
    category: ReminderRecord["category"];
    date: string;
    repeat_interval: ReminderRecord["repeat_interval"];
    family_member_id: number;
  }>({
    title: "",
    category: "checkup",
    date: "",
    repeat_interval: "none",
    family_member_id: 0,
  });
  const [memberForm, setMemberForm] = useState<{
    name: string;
    relationship_type: FamilyMemberRecord["relationship_type"];
  }>({
    name: "",
    relationship_type: "self",
  });

  const loadFamilyMembers = useCallback(async () => {
    setLoadingMembers(true);
    try {
      const members = await listFamilyMembers();
      setFamilyMembers(members);
    } catch {
      setError("Could not load family members.");
    } finally {
      setLoadingMembers(false);
    }
  }, []);

  const loadReminders = useCallback(async () => {
    setLoadingReminders(true);
    try {
      const rs = await listMyReminders();
      setReminders(rs);
    } catch {
      setError("Could not load reminders.");
    } finally {
      setLoadingReminders(false);
    }
  }, []);

  useEffect(() => {
    if (loading || !user) return;
    let active = true;
    listFamilyMembers()
      .then((members) => {
        if (active) setFamilyMembers(members);
      })
      .catch(() => {
        if (active) setError("Could not load family members.");
      })
      .finally(() => {
        if (active) setLoadingMembers(false);
      });
    listMyReminders()
      .then((nextReminders) => {
        if (active) setReminders(nextReminders);
      })
      .catch(() => {
        if (active) setError("Could not load reminders.");
      })
      .finally(() => {
        if (active) setLoadingReminders(false);
      });
    return () => {
      active = false;
    };
  }, [loading, user]);

  const active = reminders.filter((r) => !r.completed);
  const completed = reminders.filter((r) => r.completed);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = memberForm.name.trim();
    if (!name) {
      setError("Enter a name for the family member.");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await createFamilyMember({
        name,
        relationship_type: memberForm.relationship_type,
      });
      setMemberForm({ name: "", relationship_type: "self" });
      setMemberOpen(false);
      await loadFamilyMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add family member.");
    } finally {
      setSaving(false);
    }
  };

  const handleEditReminder = (reminder: ReminderRecord) => {
    if (reminder.family_member_id === null || reminder.subscription_id !== null) return;
    setEditingReminderId(reminder.id);
    setForm({
      title: reminder.title,
      category: reminder.category,
      date: reminder.reminder_date,
      repeat_interval: reminder.repeat_interval,
      family_member_id: reminder.family_member_id,
    });
    setOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const title = form.title.trim();
    if (!title || !form.date || !form.family_member_id) {
      setError("Choose a family member, enter a title, and select a date.");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      if (editingReminderId !== null) {
        await updateReminder(editingReminderId, {
          title,
          category: form.category,
          reminder_date: form.date,
          repeat_interval: form.repeat_interval,
        });
      } else {
        await createReminder({
          family_member_id: form.family_member_id,
          title,
          category: form.category,
          reminder_date: form.date,
          repeat_interval: form.repeat_interval,
        });
      }
      setForm({
        title: "",
        category: "checkup",
        date: "",
        repeat_interval: "none",
        family_member_id: 0,
      });
      setEditingReminderId(null);
      setOpen(false);
      await loadReminders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save reminder.");
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (id: number, completed: boolean) => {
    setError(null);
    setBusyReminderId(id);
    try {
      await updateReminder(id, { completed: !completed });
      await loadReminders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update reminder.");
    } finally {
      setBusyReminderId(null);
    }
  };

  const handleDeleteReminder = async (id: number) => {
    setError(null);
    setBusyReminderId(id);
    try {
      await deleteReminder(id);
      await loadReminders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete reminder.");
    } finally {
      setBusyReminderId(null);
    }
  };

  if (loading || (!user && !loading)) {
    return (
      <section className="px-4 py-12">
        <p className="text-ink-muted">Please sign in to manage reminders.</p>
      </section>
    );
  }

  if (loadingMembers || loadingReminders) {
    return (
      <section className="px-4 py-12">
        <p role="status" className="text-ink-muted">Loading your reminders…</p>
      </section>
    );
  }

  return (
    <section className="px-4 py-8 sm:py-12">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold text-ink mb-2">Reminders</h1>
        <p className="text-sm text-ink-muted mb-8">
          Track due dates and completion for health checkups and other reminders. These are stored in your eCare account; they do not trigger scheduled notifications.
        </p>
        {error && (
          <div role="alert" className="mb-4 rounded border border-danger bg-danger/5 p-4 text-sm text-danger">
            {error}
          </div>
        )}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-ink">Family Members</h2>
            <p className="text-sm text-ink-muted">
              {familyMembers.length} member(s)
            </p>
          </div>
          <Button variant="primary" onClick={() => setMemberOpen(true)} disabled={loadingMembers}>
            Add family member
          </Button>
        </div>

        {familyMembers.length === 0 && (
          <div className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-8 text-center shadow-[var(--shadow-card)]">
            <p className="text-ink-muted">
              No family members added yet. Add a family member to create reminders for them.
            </p>
          </div>
        )}

        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-ink">All reminders</h2>
            <p className="text-sm text-ink-muted">
              {reminders.length} total \u00b7 {active.length} active
            </p>
          </div>
          <Button
            variant="primary"
            onClick={() => {
              setEditingReminderId(null);
              setForm({
                title: "",
                category: "checkup",
                date: "",
                repeat_interval: "none",
                family_member_id: familyMembers[0]?.id ?? 0,
              });
              setOpen(true);
            }}
            disabled={familyMembers.length === 0}
          >
            Add reminder
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ReminderList
            title="Upcoming"
            reminders={active}
            onToggle={handleToggle}
            onDelete={handleDeleteReminder}
            onEdit={handleEditReminder}
            familyMembers={familyMembers}
            busyReminderId={busyReminderId}
          />
          <ReminderList
            title="Completed"
            reminders={completed}
            onToggle={handleToggle}
            onDelete={handleDeleteReminder}
            onEdit={handleEditReminder}
            familyMembers={familyMembers}
            busyReminderId={busyReminderId}
          />
        </div>

        {open && familyMembers.length > 0 && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center"
            aria-modal="true"
            role="dialog"
          >
            <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setOpen(false)} />
            <div className="relative bg-background rounded-[var(--radius-card)] border border-solid border-border p-6 shadow-xl w-full max-w-md m-4">
              <h2 className="text-xl font-bold text-ink mb-4">
                {editingReminderId === null ? "Add reminder" : "Edit reminder"}
              </h2>
              <form onSubmit={handleSave} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-ink mb-1">Family member</label>
                  <Select
                    value={form.family_member_id?.toString() ?? ""}
                    onChange={(e) => setForm({ ...form, family_member_id: Number(e.target.value) })}
                    required
                    disabled={editingReminderId !== null}
                    className="mt-1 w-full"
                  >
                    <option value="">Select a family member</option>
                    {familyMembers.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.relationship_type})
                      </option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink mb-1">Title</label>
                  <Input
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    maxLength={255}
                    placeholder="e.g. Annual checkup"
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-ink mb-1">Category</label>
                    <Select
                      value={form.category}
                      onChange={(e) => setForm({ ...form, category: e.target.value as ReminderRecord["category"] })}
                      className="mt-1 w-full"
                    >
                      <option value="checkup">Checkup</option>
                      <option value="dental">Dental</option>
                      <option value="vaccination">Vaccination</option>
                      <option value="other">Other</option>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-ink mb-1">Repeat interval</label>
                    <Select
                      value={form.repeat_interval}
                      onChange={(e) => setForm({ ...form, repeat_interval: e.target.value as ReminderRecord["repeat_interval"] })}
                      className="mt-1 w-full"
                    >
                      <option value="none">None</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                      <option value="half-yearly">Half-yearly</option>
                      <option value="yearly">Yearly</option>
                    </Select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink mb-1">Reminder date</label>
                  <Input
                    type="date"
                    value={form.date}
                    onChange={(e) => setForm({ ...form, date: e.target.value })}
                    required
                  />
                </div>
                <div className="flex gap-3 mt-2">
                  <Button type="button" variant="outline" onClick={() => { setOpen(false); setEditingReminderId(null); }}>
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" disabled={saving}>
                    {saving ? "Saving…" : editingReminderId === null ? "Add reminder" : "Save changes"}
                  </Button>
                </div>
              </form>
              <p className="mt-4 text-xs text-ink-muted">
                Reminders are stored records for in-app tracking only. No
                email, SMS, push, or other scheduled notifications are sent.
              </p>
            </div>
          </div>
        )}

        {memberOpen && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center"
            aria-modal="true"
            role="dialog"
          >
            <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setMemberOpen(false)} />
            <div className="relative bg-background rounded-[var(--radius-card)] border border-solid border-border p-6 shadow-xl w-full max-w-md m-4">
              <h2 className="text-xl font-bold text-ink mb-4">Add family member</h2>
              <form onSubmit={handleAddMember} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-ink mb-1">Name</label>
                  <Input
                    value={memberForm.name}
                    onChange={(e) => setMemberForm({ ...memberForm, name: e.target.value })}
                    maxLength={255}
                    placeholder="e.g. Aarav"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink mb-1">Relationship</label>
                  <Select
                    value={memberForm.relationship_type}
                    onChange={(e) => setMemberForm({ ...memberForm, relationship_type: e.target.value as FamilyMemberRecord["relationship_type"] })}
                    className="mt-1 w-full"
                  >
                    <option value="self">Self</option>
                    <option value="father">Father</option>
                    <option value="mother">Mother</option>
                    <option value="child">Child</option>
                    <option value="other">Other</option>
                  </Select>
                </div>
                <div className="flex gap-3 mt-2">
                  <Button type="button" variant="outline" onClick={() => setMemberOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" disabled={saving}>
                    {saving ? "Adding…" : "Add member"}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function ReminderList({
  title,
  reminders,
  onToggle,
  onDelete,
  onEdit,
  familyMembers,
  busyReminderId,
}: {
  title: string;
  reminders: ReminderRecord[];
  onToggle: (id: number, completed: boolean) => void;
  onDelete: (id: number) => void;
  onEdit: (reminder: ReminderRecord) => void;
  familyMembers: FamilyMemberRecord[];
  busyReminderId: number | null;
}) {
  const nowTimestamp = useCurrentTime();
  const today = nowTimestamp === 0 ? null : localDate(new Date(nowTimestamp));
  return (
    <Card className="rounded-[var(--radius-card)] p-4">
      <h3 className="text-sm font-semibold text-ink mb-4">{title}</h3>
      {reminders.length > 0 ? (
        <ul className="space-y-3">
          {reminders.map((r) => {
            const isOverdue = !r.completed && today !== null && r.reminder_date < today;
            const isSubscriptionReminder = r.subscription_id !== null;
            return (
              <li
                key={r.id}
                className="flex items-center gap-3 p-3 rounded-[var(--radius-control)] border border-solid border-border hover:bg-navy-50"
              >
                <button
                  onClick={() => onToggle(r.id, r.completed)}
                  disabled={busyReminderId === r.id}
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
                  <p className="text-xs text-ink-muted">
                    {r.category} \u00b7 {r.reminder_date}
                    {isOverdue && " \u00b7 Overdue"}
                  </p>
                  <p className="text-xs text-ink-muted">
                    For {r.family_member_id
                      ? familyMembers.find((member) => member.id === r.family_member_id)?.name ?? "family member"
                      : isSubscriptionReminder ? "subscription" : "account"} · Repeats {r.repeat_interval}
                  </p>
                </div>
                <Badge variant={r.completed ? "success" : isOverdue ? "warning" : "info"} className="text-xs shrink-0">
                  {r.completed ? "Done" : isOverdue ? "Overdue" : "Pending"}
                </Badge>
                {isSubscriptionReminder ? (
                  <Link href="/subscriptions" className="shrink-0 text-xs text-teal-700 underline">Manage</Link>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => onEdit(r)}
                      disabled={busyReminderId === r.id}
                      className="shrink-0 text-xs text-teal-700 underline"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(r.id)}
                      disabled={busyReminderId === r.id}
                      className="shrink-0 text-ink-muted hover:text-danger"
                    >
                      \u00d7
                    </button>
                  </>
                )}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="text-xs text-ink-muted text-center">None.</p>
      )}
    </Card>
  );
}

function localDate(date: Date) { return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`; }
