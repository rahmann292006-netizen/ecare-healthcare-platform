/**
 * eCare API client — connects to NEXT_PUBLIC_API_URL (development default:
 * http://localhost:8000). Public read-only GET routes plus
 * authentication helpers. No secrets or credentials stored here.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ||
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "");

const TOKEN_KEY = "ecare_access_token";
const API_REQUEST_TIMEOUT_MS = 10_000;

function apiUrl(path: string): string {
  if (!API_BASE) {
    throw new Error("NEXT_PUBLIC_API_URL must be configured for production.");
  }
  return `${API_BASE}${path}`;
}

function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(apiUrl(path), {
    cache: "no-store",
    ...init,
    signal: AbortSignal.timeout(API_REQUEST_TIMEOUT_MS),
  });
}

async function responseError(res: Response, action: string): Promise<Error> {
  try {
    const body = await res.json() as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) {
      return new Error(body.detail);
    }
  } catch {
    // Keep the HTTP status when the server response is not JSON.
  }
  return new Error(`API ${res.status} ${action}`);
}

async function get<T>(path: string): Promise<T> {
  const res = await apiFetch(path, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return res.json() as Promise<T>;
}

function authHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
  return token ? { "Content-Type": "application/json", Authorization: `Bearer ${token}` } : { "Content-Type": "application/json" };
}

async function authedGet<T>(path: string): Promise<T> {
  const res = await apiFetch(path, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return res.json() as Promise<T>;
}

function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export interface HospitalListResponse {
  items: Hospital[];
  total: number;
  limit: number;
  offset: number;
}

export type ProviderType = "hospital" | "doctor" | "lab" | "opd";
export type ProviderSort = "name_asc" | "name_desc";

export interface Speciality {
  id: number;
  name: string;
  slug: string;
}

export interface ProviderDirectoryItem {
  id: number;
  provider_type: ProviderType;
  name: string;
  slug: string;
  description: string | null;
  address: string | null;
  locality: string | null;
  city: string | null;
  state: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  hospital_type: string | null;
  opd_type: string | null;
  operating_hours?: string | null;
  hospital_id: number | null;
  hospital_name: string | null;
  qualifications: string | null;
  experience_years: number | null;
  consultation_fee: number | null;
  schedule: DoctorSchedule | null;
  specialities: Speciality[];
  source: string | null;
  source_url: string | null;
  verified_at: string | null;
  is_verified: boolean;
  is_demo: boolean;
  verification_status: string;
  operational_status?: "unknown" | "operational" | "not_operational";
  emergency_services?: boolean | null;
  home_sample_collection?: boolean | null;
}

export interface ProviderDirectoryResponse {
  items: ProviderDirectoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProviderDirectoryParams {
  provider_type?: ProviderType;
  city?: string;
  speciality_id?: number;
  locality?: string;
  search?: string;
  sort?: ProviderSort;
  limit?: number;
  offset?: number;
}

export interface DoctorScheduleSession { start: string; end: string; breakStart?: string; breakEnd?: string; location: string; }
export interface DoctorSchedule { governmentDuty: Record<string, DoctorScheduleSession>; privateOpd: Record<string, DoctorScheduleSession>; durationMinutes: number; unavailableDays: number[]; }

export function hasBookableDoctorSchedule(schedule: DoctorSchedule | null): boolean {
  if (
    !schedule ||
    !Number.isInteger(schedule.durationMinutes) ||
    schedule.durationMinutes < 1 ||
    schedule.durationMinutes > 1440 ||
    !Array.isArray(schedule.unavailableDays)
  ) return false;
  const validClock = (value: string) => /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value);
  return Object.entries(schedule.privateOpd ?? {}).some(([day, session]) => {
    const weekday = Number(day);
    if (!session || typeof session !== "object") return false;
    return (
      Number.isInteger(weekday) &&
      weekday >= 0 &&
      weekday <= 6 &&
      !schedule.unavailableDays.includes(weekday) &&
      typeof session.start === "string" &&
      typeof session.end === "string" &&
      validClock(session.start) &&
      validClock(session.end) &&
      session.end > session.start &&
      typeof session.location === "string" &&
      Boolean(session.location.trim())
    );
  });
}

export async function listSpecialities(): Promise<Speciality[]> {
  return get<Speciality[]>("/api/v1/specialities");
}

export async function listProviders(
  params: ProviderDirectoryParams = {}
): Promise<ProviderDirectoryResponse> {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") qs.set(key, String(value));
  }
  return get<ProviderDirectoryResponse>(`/api/v1/providers?${qs.toString()}`);
}

export async function getProvider(
  providerType: ProviderType,
  id: number
): Promise<ProviderDirectoryItem> {
  return get<ProviderDirectoryItem>(`/api/v1/providers/${providerType}/${id}`);
}

export interface Hospital {
  id: number;
  name: string;
  slug: string;
  address: string;
  hospital_type: string | null;
  locality: string | null;
  city: string;
  state: string;
  phone: string | null;
  verification_status: string;
  is_active: boolean;
}

export async function listHospitals(params: Record<string, string | number | boolean | undefined> = {}): Promise<HospitalListResponse> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return get<HospitalListResponse>(`/api/v1/hospitals?${qs.toString()}`);
}

export async function getHospital(id: number): Promise<Hospital> {
  return get<Hospital>(`/api/v1/hospitals/${id}`);
}

export interface DoctorListResponse {
  items: Doctor[];
  total: number;
  limit: number;
  offset: number;
}

export async function listDoctors(params: Record<string, string | number | boolean | undefined> = {}): Promise<DoctorListResponse> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return get<DoctorListResponse>(`/api/v1/doctors?${qs.toString()}`);
}

export interface Doctor {
  id: number;
  full_name: string;
  slug: string;
  specializations: string | null;
  consultation_fee: number | null;
  phone: string | null;
  hospital_id: number | null;
  verification_status: string;
}

export async function getDoctor(id: number): Promise<Doctor> {
  return get<Doctor>(`/api/v1/doctors/${id}`);
}

export interface LabListResponse {
  items: DiagnosticLab[];
  total: number;
  limit: number;
  offset: number;
}

export async function listLabs(params: Record<string, string | number | boolean | undefined> = {}): Promise<LabListResponse> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return get<LabListResponse>(`/api/v1/labs?${qs.toString()}`);
}

export interface DiagnosticLab {
  id: number;
  name: string;
  slug: string;
  address: string;
  locality: string | null;
  city: string;
  state: string;
  phone: string | null;
  home_sample_collection: boolean;
  verification_status: string;
}

export async function getLab(id: number): Promise<DiagnosticLab> {
  return get<DiagnosticLab>(`/api/v1/labs/${id}`);
}

export interface TestListResponse {
  items: DiagnosticTest[];
  total: number;
  limit: number;
  offset: number;
}

export async function listTestsForLab(labId: number): Promise<TestListResponse> {
  return get<TestListResponse>(`/api/v1/labs/${labId}/tests`);
}

export interface DiagnosticTest {
  id: number;
  lab_id: number;
  name: string;
  price: number | null;
  availability_status: string;
}

export async function getTest(id: number): Promise<DiagnosticTest> {
  return get<DiagnosticTest>(`/api/v1/tests/${id}`);
}

export async function listHospitalDoctors(hospitalId: number): Promise<DoctorListResponse> {
  return get<DoctorListResponse>(`/api/v1/hospitals/${hospitalId}/doctors`);
}

// ---------------------------------------------------------------------------
// Authentication API support
// ---------------------------------------------------------------------------

export interface UserRegisterRequest {
  email: string;
  full_name: string;
  phone: string;
  password: string;
  role?: "patient" | "provider" | "admin";
}

export interface UserRegisterResponse {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserLoginRequest {
  email: string;
  password: string;
}

export interface UserLoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserRead {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
  provider_doctor_id: number | null;
}

export async function register(user: UserRegisterRequest): Promise<UserRegisterResponse> {
  return post<UserRegisterResponse>("/api/v1/auth/register", user);
}

export async function login(credentials: UserLoginRequest): Promise<UserLoginResponse> {
  const data = await post<UserLoginResponse>("/api/v1/auth/login", credentials);
  if (data.access_token) {
    setToken(data.access_token);
  }
  return data;
}

export async function logout(): Promise<void> {
  setToken(null);
}

export function hasSessionToken(): boolean { return getToken() !== null; }

export async function getMe(): Promise<UserRead> {
  return authedGet<UserRead>("/api/v1/auth/me");
}

export async function updateMe(input: { full_name?: string; phone?: string | null }): Promise<UserRead> {
  const res = await apiFetch("/api/v1/auth/me", { method: "PATCH", headers: authHeaders(), body: JSON.stringify(input) });
  if (!res.ok) throw new Error(`API ${res.status} updating profile`);
  return res.json() as Promise<UserRead>;
}

export async function changePassword(current_password: string, new_password: string): Promise<void> {
  const res = await apiFetch("/api/v1/auth/change-password", { method: "POST", headers: authHeaders(), body: JSON.stringify({ current_password, new_password }) });
  if (!res.ok) throw new Error(`API ${res.status} changing password`);
}

export interface AppointmentRecord {
  id: number; reference: string; user_id: number; patient_name: string | null; doctor_id: number; doctor_name: string;
  doctor_qualification: string | null; doctor_speciality: string | null; hospital_id: number | null;
  hospital_name: string | null; appointment_date: string; appointment_time: string; location: string;
  city: string; state: string; package_id: number | null; package_name: string | null;
  package_amount: number; consultation_fee: number; service_charge: number; total_amount: number;
  advance_paid: number; remaining_balance: number; status: string; payment_status: string;
  is_demo: boolean; created_at: string;
}

export interface PaymentRecord { id: number; amount: number; method_label: string; status: string; created_at: string; }
export interface InvoiceRecord {
  invoice_number: string; appointment_id: number; package_amount: number; consultation_fee: number;
  service_charge: number; total_amount: number; advance_paid: number; outstanding_balance: number;
  is_demo: boolean; created_at: string; payments: PaymentRecord[];
  payment_method?: string | null; payment_status?: string | null;
}
export interface AppointmentDetail extends AppointmentRecord { invoice: InvoiceRecord; }
export interface AppointmentCreateRequest {
  doctor_id: number; appointment_date: string; appointment_time: string; location_id?: string;
  package_id?: number; payment_method: "demo";
}

export interface AppointmentAvailabilitySlot {
  time: string;
  status: "available" | "unavailable";
  reason: string | null;
}

export interface DoctorAppointmentAvailability {
  doctor_id: number;
  appointment_date: string;
  consultation_days: string[];
  opd_start: string | null;
  opd_end: string | null;
  clinic_location: string | null;
  consultation_fee: number | null;
  duration_minutes: number | null;
  slots: AppointmentAvailabilitySlot[];
  fully_booked: boolean;
  message: string | null;
}

export async function getDoctorAppointmentAvailability(
  doctorId: number,
  appointmentDate: string
): Promise<DoctorAppointmentAvailability> {
  const query = new URLSearchParams({ appointment_date: appointmentDate });
  return get<DoctorAppointmentAvailability>(
    `/api/v1/appointments/availability/${doctorId}?${query.toString()}`
  );
}

export async function createDemoAppointment(input: AppointmentCreateRequest): Promise<AppointmentDetail> {
  const res = await apiFetch("/api/v1/appointments/", { method: "POST", headers: authHeaders(), body: JSON.stringify(input) });
  if (!res.ok) {
    let message = `API ${res.status} creating appointment request`;
    try {
      const body = await res.json() as { detail?: unknown };
      if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
    } catch {
      // Keep the HTTP status message when the server does not return JSON.
    }
    throw new Error(message);
  }
  return res.json() as Promise<AppointmentDetail>;
}
export async function listMyAppointments(): Promise<AppointmentRecord[]> { return authedGet<AppointmentRecord[]>("/api/v1/appointments/me"); }
export async function getMyAppointment(reference: string): Promise<AppointmentDetail> { return authedGet<AppointmentDetail>(`/api/v1/appointments/me/${encodeURIComponent(reference)}`); }
export async function listMyInvoices(): Promise<InvoiceRecord[]> { return authedGet<InvoiceRecord[]>("/api/v1/appointments/me/invoices"); }
export async function cancelMyAppointment(reference: string): Promise<AppointmentRecord> {
  const res = await apiFetch(`/api/v1/appointments/me/${encodeURIComponent(reference)}/cancel`, {
    method: "PATCH",
    headers: authHeaders(),
  });
  if (!res.ok) throw await responseError(res, "cancelling appointment");
  return res.json() as Promise<AppointmentRecord>;
}
export async function listDoctorAppointments(): Promise<AppointmentRecord[]> { return authedGet<AppointmentRecord[]>("/api/v1/appointments/doctor/me"); }
export async function updateDoctorAppointmentStatus(
  appointmentId: number,
  status: "demo_confirmed" | "cancelled"
): Promise<AppointmentRecord> {
  const res = await apiFetch(`/api/v1/appointments/doctor/me/${appointmentId}/status`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error(`API ${res.status} updating appointment status`);
  return res.json() as Promise<AppointmentRecord>;
}
export async function listAdminAppointments(): Promise<AppointmentRecord[]> { return authedGet<AppointmentRecord[]>("/api/v1/appointments/admin/all"); }
export async function getDoctorSchedule(): Promise<{ doctor_id: number; schedule: Record<string, unknown> | null }> { return authedGet("/api/v1/appointments/doctor/me/schedule"); }

export interface DoctorApplicationRecord { id: number; user_id: number; doctor_id: number; status: string; created_at: string; reviewed_at: string | null; applicant_name: string | null; applicant_email: string | null; doctor_name: string | null; }
export async function createDoctorApplication(doctor_id: number): Promise<DoctorApplicationRecord> { return post<DoctorApplicationRecord>("/api/v1/auth/doctor-applications", { doctor_id }); }
export async function listDoctorApplications(): Promise<DoctorApplicationRecord[]> { return authedGet<DoctorApplicationRecord[]>("/api/v1/auth/admin/doctor-applications"); }
export async function reviewDoctorApplication(id: number, action: "approve" | "reject"): Promise<DoctorApplicationRecord> { const res = await apiFetch(`/api/v1/auth/admin/doctor-applications/${id}/${action}`, { method: "POST", headers: authHeaders() }); if (!res.ok) throw new Error(`API ${res.status} reviewing doctor application`); return res.json() as Promise<DoctorApplicationRecord>; }

// ---------------------------------------------------------------------------
// Health checkup package API support
// ---------------------------------------------------------------------------

export interface PackageInclusion {
  id: number;
  package_id: number;
  test_name: string;
  display_order: number;
}

export interface PackageRecord {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  provider_name: string;
  provider_type: string;
  price: number;
  currency: string;
  city: string;
  state: string;
  locality: string | null;
  category: string;
  source: string | null;
  source_url: string | null;
  min_age_years: number | null;
  max_age_years: number | null;
  validity_period: "monthly" | "quarterly" | "yearly" | null;
  validity_description: string | null;
  verified_at: string | null;
  is_verified: boolean;
  is_demo: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  inclusions: PackageInclusion[];
}

export interface PackageListResponse {
  items: PackageRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface PackageCreateRequest {
  name: string;
  slug?: string;
  description?: string | null;
  provider_name: string;
  provider_type?: string;
  price: number;
  currency?: string;
  city?: string;
  state?: string;
  locality?: string | null;
  category?: string;
  source?: string | null;
  source_url?: string | null;
  min_age_years?: number | null;
  max_age_years?: number | null;
  validity_period?: "monthly" | "quarterly" | "yearly" | null;
  validity_description?: string | null;
  inclusions?: Array<{ test_name: string; display_order?: number }>;
}

export type PackageUpdateRequest = Partial<PackageCreateRequest> & {
  is_active?: boolean;
};

export interface PackageVerificationRequest {
  source: string;
  source_url?: string | null;
}

export async function listPackages(
  params: Record<string, string | number | boolean | undefined> = {}
): Promise<PackageListResponse> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return get<PackageListResponse>(`/api/v1/packages?${qs.toString()}`);
}

export async function getPackage(id: number): Promise<PackageRecord> {
  return get<PackageRecord>(`/api/v1/packages/${id}`);
}

export async function listAdminPackages(): Promise<PackageRecord[]> {
  return authedGet<PackageRecord[]>("/api/v1/packages/admin");
}

export async function createAdminPackage(input: PackageCreateRequest): Promise<PackageRecord> {
  const res = await apiFetch("/api/v1/packages", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await responseError(res, "creating package plan");
  return res.json() as Promise<PackageRecord>;
}

export async function updateAdminPackage(id: number, input: PackageUpdateRequest): Promise<PackageRecord> {
  const res = await apiFetch(`/api/v1/packages/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await responseError(res, "updating package plan");
  return res.json() as Promise<PackageRecord>;
}

export async function verifyAdminPackage(id: number, input: PackageVerificationRequest): Promise<PackageRecord> {
  const res = await apiFetch(`/api/v1/packages/${id}/verify`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await responseError(res, "verifying package plan");
  return res.json() as Promise<PackageRecord>;
}

export interface SubscriptionEventRecord {
  id: number;
  actor_user_id: number | null;
  event_type: string;
  previous_status: string | null;
  new_status: string;
  payment_status: string;
  amount: number;
  details: string | null;
  created_at: string;
}

export interface SubscriptionRecord {
  id: number;
  user_id: number;
  plan_id: number;
  family_member_id: number | null;
  age_years_at_start: number | null;
  amount: number;
  currency: string;
  start_at: string;
  expires_at: string;
  status: "pending_payment" | "scheduled" | "active" | "expired" | "cancelled";
  payment_status: "pending" | "simulated" | "paid" | "failed" | "refunded";
  renewal_of_id: number | null;
  renewal_subscription_id: number | null;
  created_at: string;
  updated_at: string;
  plan: PackageRecord;
  reminder: ReminderRecord | null;
  events: SubscriptionEventRecord[];
}

export interface SubscriptionCreateRequest {
  plan_id: number;
  family_member_id?: number | null;
  age_years?: number | null;
}

export interface SubscriptionPaymentOptions {
  mode: "simulated" | "unavailable";
  message: string;
}

export async function getSubscriptionPaymentOptions(): Promise<SubscriptionPaymentOptions> {
  return get<SubscriptionPaymentOptions>("/api/v1/subscriptions/payment-options");
}

export async function listMySubscriptions(): Promise<SubscriptionRecord[]> {
  return authedGet<SubscriptionRecord[]>("/api/v1/subscriptions/me");
}

export async function listAdminSubscriptions(): Promise<SubscriptionRecord[]> {
  return authedGet<SubscriptionRecord[]>("/api/v1/subscriptions/admin");
}

export async function listMyEntitlements(): Promise<number[]> {
  return authedGet<number[]>("/api/v1/subscriptions/me/entitlements");
}

export async function createSubscription(input: SubscriptionCreateRequest): Promise<SubscriptionRecord> {
  const res = await apiFetch("/api/v1/subscriptions", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await responseError(res, "creating subscription");
  return res.json() as Promise<SubscriptionRecord>;
}

export async function renewSubscription(id: number, input: SubscriptionCreateRequest): Promise<SubscriptionRecord> {
  const res = await apiFetch(`/api/v1/subscriptions/${id}/renew`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await responseError(res, "renewing subscription");
  return res.json() as Promise<SubscriptionRecord>;
}

export async function cancelSubscription(id: number, reason?: string): Promise<SubscriptionRecord> {
  const res = await apiFetch(`/api/v1/subscriptions/${id}/cancel`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) throw await responseError(res, "cancelling subscription");
  return res.json() as Promise<SubscriptionRecord>;
}

export async function simulateSubscriptionPayment(id: number): Promise<SubscriptionRecord> {
  const res = await apiFetch(`/api/v1/subscriptions/${id}/simulate-payment`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw await responseError(res, "recording simulated subscription payment");
  return res.json() as Promise<SubscriptionRecord>;
}

export async function cancelAdminSubscription(id: number, reason?: string): Promise<SubscriptionRecord> {
  const res = await apiFetch(`/api/v1/subscriptions/admin/${id}/cancel`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) throw await responseError(res, "cancelling subscription as admin");
  return res.json() as Promise<SubscriptionRecord>;
}

// ---------------------------------------------------------------------------
// Family Members API support
// ---------------------------------------------------------------------------

export interface FamilyMemberRecord {
  id: number;
  user_id: number;
  name: string;
  relationship_type: "self" | "father" | "mother" | "child" | "other";
  created_at: string;
}

export interface FamilyMemberCreateRequest {
  name: string;
  relationship_type: "self" | "father" | "mother" | "child" | "other";
}

export async function createFamilyMember(input: FamilyMemberCreateRequest): Promise<FamilyMemberRecord> {
  const res = await apiFetch("/api/v1/family-members/", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await responseError(res, "creating family member");
  return res.json() as Promise<FamilyMemberRecord>;
}

export async function listFamilyMembers(): Promise<FamilyMemberRecord[]> {
  return authedGet<FamilyMemberRecord[]>("/api/v1/family-members/me");
}

export async function deleteFamilyMember(memberId: number): Promise<void> {
  const res = await apiFetch(`/api/v1/family-members/${memberId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw await responseError(res, "deleting family member");
}

// ---------------------------------------------------------------------------
// Reminders API support
// ---------------------------------------------------------------------------

export interface ReminderRecord {
  id: number;
  user_id: number;
  family_member_id: number | null;
  subscription_id: number | null;
  title: string;
  category: "checkup" | "dental" | "vaccination" | "other";
  reminder_date: string;
  repeat_interval: "none" | "daily" | "weekly" | "monthly" | "yearly" | "half-yearly";
  completed: boolean;
  created_at: string;
}

export interface ReminderCreateRequest {
  family_member_id: number;
  title: string;
  category: "checkup" | "dental" | "vaccination" | "other";
  reminder_date: string;
  repeat_interval: "none" | "daily" | "weekly" | "monthly" | "yearly" | "half-yearly";
}

export interface ReminderUpdateRequest {
  title?: string;
  category?: "checkup" | "dental" | "vaccination" | "other";
  reminder_date?: string;
  repeat_interval?: "none" | "daily" | "weekly" | "monthly" | "yearly" | "half-yearly";
  completed?: boolean;
}

export async function createReminder(input: ReminderCreateRequest): Promise<ReminderRecord> {
  const res = await apiFetch("/api/v1/reminders/", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await responseError(res, "creating reminder");
  return res.json() as Promise<ReminderRecord>;
}

export async function listMyReminders(): Promise<ReminderRecord[]> {
  return authedGet<ReminderRecord[]>("/api/v1/reminders/me");
}

export async function updateReminder(reminderId: number, input: ReminderUpdateRequest): Promise<ReminderRecord> {
  const res = await apiFetch(`/api/v1/reminders/${reminderId}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await responseError(res, "updating reminder");
  return res.json() as Promise<ReminderRecord>;
}

export async function deleteReminder(reminderId: number): Promise<void> {
  const res = await apiFetch(`/api/v1/reminders/${reminderId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw await responseError(res, "deleting reminder");
}
