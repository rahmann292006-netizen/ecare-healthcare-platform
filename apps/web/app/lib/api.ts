/**
 * eCare API client — connects to the FastAPI backend at NEXT_PUBLIC_API_URL
 * (default http://localhost:8000). Public read-only GET routes plus
 * authentication helpers. No secrets or credentials stored here.
 */

const API_BASE =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL
    : "http://localhost:8000";

const TOKEN_KEY = "ecare_access_token";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
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
  const res = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders(),
    cache: "no-store",
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
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, { method: "PATCH", headers: authHeaders(), cache: "no-store", body: JSON.stringify(input) });
  if (!res.ok) throw new Error(`API ${res.status} updating profile`);
  return res.json() as Promise<UserRead>;
}

export async function changePassword(current_password: string, new_password: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/auth/change-password`, { method: "POST", headers: authHeaders(), cache: "no-store", body: JSON.stringify({ current_password, new_password }) });
  if (!res.ok) throw new Error(`API ${res.status} changing password`);
}

export interface AppointmentRecord {
  id: number; reference: string; user_id: number; doctor_id: number; doctor_name: string;
  doctor_qualification: string | null; doctor_speciality: string | null; hospital_id: number | null;
  hospital_name: string | null; appointment_date: string; appointment_time: string; location: string;
  city: string; state: string; package_id: string | null; package_name: string | null;
  package_amount: number; consultation_fee: number; service_charge: number; total_amount: number;
  advance_paid: number; remaining_balance: number; status: string; payment_status: string;
  is_demo: boolean; created_at: string;
}

export interface PaymentRecord { id: number; amount: number; method_label: string; status: string; created_at: string; }
export interface InvoiceRecord {
  invoice_number: string; appointment_id: number; package_amount: number; consultation_fee: number;
  service_charge: number; total_amount: number; advance_paid: number; outstanding_balance: number;
  is_demo: boolean; created_at: string; payments: PaymentRecord[];
}
export interface AppointmentDetail extends AppointmentRecord { invoice: InvoiceRecord; }
export interface AppointmentCreateRequest {
  doctor_id: number; appointment_date: string; appointment_time: string; location_id?: string;
  package_id?: string; package_name?: string; package_amount?: number;
  payment_method: "demo-card" | "demo-upi" | "demo-cash";
}

export async function createDemoAppointment(input: AppointmentCreateRequest): Promise<AppointmentDetail> {
  const res = await fetch(`${API_BASE}/api/v1/appointments/`, { method: "POST", headers: authHeaders(), cache: "no-store", body: JSON.stringify(input) });
  if (!res.ok) throw new Error(`API ${res.status} creating demo appointment`);
  return res.json() as Promise<AppointmentDetail>;
}
export async function listMyAppointments(): Promise<AppointmentRecord[]> { return authedGet<AppointmentRecord[]>("/api/v1/appointments/me"); }
export async function getMyAppointment(reference: string): Promise<AppointmentDetail> { return authedGet<AppointmentDetail>(`/api/v1/appointments/me/${encodeURIComponent(reference)}`); }
export async function listMyInvoices(): Promise<InvoiceRecord[]> { return authedGet<InvoiceRecord[]>("/api/v1/appointments/me/invoices"); }
export async function listDoctorAppointments(): Promise<AppointmentRecord[]> { return authedGet<AppointmentRecord[]>("/api/v1/appointments/doctor/me"); }
export async function listAdminAppointments(): Promise<AppointmentRecord[]> { return authedGet<AppointmentRecord[]>("/api/v1/appointments/admin/all"); }
export async function getDoctorSchedule(): Promise<{ doctor_id: number; schedule: Record<string, unknown> | null }> { return authedGet("/api/v1/appointments/doctor/me/schedule"); }

export interface DoctorApplicationRecord { id: number; user_id: number; doctor_id: number; status: string; created_at: string; reviewed_at: string | null; applicant_name: string | null; applicant_email: string | null; doctor_name: string | null; }
export async function createDoctorApplication(doctor_id: number): Promise<DoctorApplicationRecord> { return post<DoctorApplicationRecord>("/api/v1/auth/doctor-applications", { doctor_id }); }
export async function listDoctorApplications(): Promise<DoctorApplicationRecord[]> { return authedGet<DoctorApplicationRecord[]>("/api/v1/auth/admin/doctor-applications"); }
export async function reviewDoctorApplication(id: number, action: "approve" | "reject"): Promise<DoctorApplicationRecord> { const res = await fetch(`${API_BASE}/api/v1/auth/admin/doctor-applications/${id}/${action}`, { method: "POST", headers: authHeaders(), cache: "no-store" }); if (!res.ok) throw new Error(`API ${res.status} reviewing doctor application`); return res.json() as Promise<DoctorApplicationRecord>; }
