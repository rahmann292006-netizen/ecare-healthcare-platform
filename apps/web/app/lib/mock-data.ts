/**
 * eCare demo / mock data
 *
 * WARNING: All data in this file is SAMPLE / DEMO data only. It does NOT come
 * from the backend and does NOT represent real provider data. It is used only
 * for screens that have no backend support (packages, dashboard, reminders,
 * notifications, provider dashboard).
 *
 * Real provider data (hospitals, doctors, labs, tests) is fetched from the
 * FastAPI backend via app/lib/api.ts.
 */

export interface DemoPackage {
  id: string;
  title: string;
  provider: string;
  providerType: "hospital" | "diagnostic_lab";
  price: number;
  currency: string;
  includedTests: string[];
  offerBadge: string | null;
  description: string;
  isSample: true;
}

export interface DemoReminder {
  id: string;
  title: string;
  category: string;
  date: string;
  repeatInterval: "none" | "daily" | "weekly" | "monthly";
  completed: boolean;
  childProfile?: string;
  vaccinationDate?: string;
  isSample: true;
}

export interface DemoNotification {
  id: string;
  title: string;
  body: string;
  type: "reminder" | "package" | "completed";
  read: boolean;
  createdAt: string;
  isSample: true;
}

/** Sample health packages — clearly demo data, not real provider data. */
export const DEMO_PACKAGES: DemoPackage[] = [
  {
    id: "pkg-1",
    title: "Full Body Checkup",
    provider: "City Diagnostic Lab",
    providerType: "diagnostic_lab",
    price: 2499,
    currency: "INR",
    includedTests: ["Blood glucose", "Lipid profile", "Liver function", "Kidney function", "Complete blood count"],
    offerBadge: "20% off",
    description: "Comprehensive health screening package.",
    isSample: true,
  },
  {
    id: "pkg-2",
    title: "Heart Health Screening",
    provider: "Raichur General Hospital",
    providerType: "hospital",
    price: 3999,
    currency: "INR",
    includedTests: ["ECG", "Echocardiogram", "Lipid profile", "Blood pressure", "Consultation"],
    offerBadge: null,
    description: "Cardiac evaluation and consultation.",
    isSample: true,
  },
  {
    id: "pkg-3",
    title: "Diabetes Care Package",
    provider: "City Diagnostic Lab",
    providerType: "diagnostic_lab",
    price: 1499,
    currency: "INR",
    includedTests: ["HbA1c", "Fasting glucose", "Post-prandial glucose", "Urine microalbumin"],
    offerBadge: "Free consultation",
    description: "Diabetes monitoring and management.",
    isSample: true,
  },
  {
    id: "pkg-4",
    title: "Women's Wellness",
    provider: "Raichur General Hospital",
    providerType: "hospital",
    price: 2999,
    currency: "INR",
    includedTests: ["Pap smear", "Mammogram", "Bone density", "Gynecologist consultation"],
    offerBadge: "15% off",
    description: "Women's preventive health screening.",
    isSample: true,
  },
];

/** Sample reminders — clearly demo data, not real user data. */
export const DEMO_REMINDERS: DemoReminder[] = [
  {
    id: "rem-1",
    title: "Annual Full Body Checkup",
    category: "checkup",
    date: "2026-11-15",
    repeatInterval: "yearly",
    completed: false,
    isSample: true,
  },
  {
    id: "rem-2",
    title: "Dental Cleaning",
    category: "dental",
    date: "2026-10-25",
    repeatInterval: "half-yearly",
    completed: false,
    isSample: true,
  },
  {
    id: "rem-3",
    title: "Child Vaccination – MMR",
    category: "vaccination",
    date: "2026-10-20",
    repeatInterval: "none",
    completed: true,
    childProfile: "Aarav (age 4)",
    vaccinationDate: "2026-10-20",
    isSample: true,
  },
];

/** Sample notifications — clearly demo data, not real user data. */
export const DEMO_NOTIFICATIONS: DemoNotification[] = [
  {
    id: "not-1",
    title: "Upcoming checkup",
    body: "Your Annual Full Body Checkup is due on 15 Nov 2026.",
    type: "reminder",
    read: false,
    createdAt: "2026-10-20T09:00:00Z",
    isSample: true,
  },
  {
    id: "not-2",
    title: "Package updated",
    body: "Heart Health Screening now includes a free ECG.",
    type: "package",
    read: false,
    createdAt: "2026-10-18T14:30:00Z",
    isSample: true,
  },
  {
    id: "not-3",
    title: "Reminder completed",
    body: "Child Vaccination – MMR marked as completed.",
    type: "completed",
    read: true,
    createdAt: "2026-10-20T10:00:00Z",
    isSample: true,
  },
];
