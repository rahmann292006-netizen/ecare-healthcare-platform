/**
 * eCare API client — connects to the FastAPI backend at NEXT_PUBLIC_API_URL
 * (default http://localhost:8000). Only public read-only GET routes are used.
 * No secrets or credentials stored here.
 */

const API_BASE =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL
    : "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return res.json() as Promise<T>;
}

export interface HospitalListResponse {
  items: Hospital[];
  total: number;
  limit: number;
  offset: number;
}

export interface Hospital {
  id: number;
  name: string;
  slug: string;
  address: string;
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
