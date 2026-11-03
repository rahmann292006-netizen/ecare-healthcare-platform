import type { ProviderDirectoryItem, ProviderType, Speciality } from "@/lib/api";
import { DEMO_LOCATIONS } from "@/lib/locations";

export interface DemoSession {
  start: string;
  end: string;
  breakStart?: string;
  breakEnd?: string;
  location: string;
}

export interface FictionalProvider extends ProviderDirectoryItem {
  locationId: string;
  qualification?: string;
  experienceYears?: number;
  biography?: string;
  consultationFee?: number;
  schedule?: {
    governmentDuty: Partial<Record<number, DemoSession>>;
    privateOpd: Partial<Record<number, DemoSession>>;
    durationMinutes: number;
    unavailableDays: number[];
  };
  addedDaysAgo?: number;
}

const specialityCatalog = [
  [1, "General Medicine", "general-medicine"], [2, "Cardiology", "cardiology"],
  [3, "Paediatrics", "paediatrics"], [4, "Obstetrics and Gynaecology", "obstetrics-gynaecology"],
  [5, "Orthopaedics", "orthopaedics"], [6, "Dermatology", "dermatology"],
  [7, "Ophthalmology", "ophthalmology"], [8, "ENT", "ent"],
  [9, "Dentistry", "dentistry"], [10, "Diabetology", "diabetology"],
  [11, "Neurology", "neurology"], [12, "Pulmonology", "pulmonology"],
  [13, "Nephrology", "nephrology"], [14, "Psychiatry", "psychiatry"],
  [15, "Urology", "urology"], [16, "General Surgery", "general-surgery"],
  [17, "Radiology", "radiology"], [18, "Pathology", "pathology"],
  [19, "Physiotherapy", "physiotherapy"], [20, "Nutrition", "nutrition"],
] as const;

export const FICTIONAL_SPECIALITIES: Speciality[] = specialityCatalog.map(([id, name, slug]) => ({ id: id + 1000, name, slug }));

const localities = ["Vidya Nagar", "Ashok Nagar", "Green Park Demo Zone", "Station Road Demo Zone", "College Road Demo Zone", "Market Area Demo Zone", "Extension Demo Zone", "Shakti Nagar", "Basava Nagar", "Teachers Colony"];
const facilityNames = [
  "Sanjeevani Community Hospital", "Aarogya Multispeciality Hospital", "Nirmala Women and Child Centre",
  "Sushruta Orthopaedic Hospital", "Prerana Eye and ENT Hospital", "Jeevanrekha Community Hospital",
  "Vaatsalya Heart and Medical Centre", "Anugraha General Hospital", "Sparsha Family Hospital", "Navachetana Teaching Hospital",
];

const hospitals: FictionalProvider[] = facilityNames.map((name, index) => {
  const location = DEMO_LOCATIONS[index % DEMO_LOCATIONS.length];
  return {
  id: 9101 + index,
  provider_type: "hospital",
  name,
  slug: `fictional-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-$/, "")}`,
  description: "Fictional sample facility created for the eCare college demonstration. Not a real healthcare provider.",
  address: `Fictional demo address, ${localities[index]}, ${location.label}`,
  locality: localities[index], city: location.city, state: location.state, locationId: location.id,
  phone: "Fictional contact only — not a real phone number", email: `hospital${index + 1}@example.com`,
  website: null, hospital_type: "Fictional sample hospital", opd_type: null, hospital_id: null,
  specialities: [FICTIONAL_SPECIALITIES[index % 10]], source: "Fictional sample data", source_url: null,
  verified_at: null, is_verified: false, is_demo: true, verification_status: "Fictional sample — unverified",
  };
});

const labs: FictionalProvider[] = [
  "Asterix Diagnostic Laboratory", "Bluebell Pathology Centre", "CarePoint Imaging and Diagnostics",
  "Lifeline Clinical Laboratory", "Medisphere Diagnostics", "Nova Health Testing Centre",
  "WellSpring Diagnostic Hub", "ClearView Imaging Studio", "Orchid Clinical Lab", "Sampurna Health Diagnostics",
].map((name, index) => {
  const location = DEMO_LOCATIONS[index % DEMO_LOCATIONS.length];
  return {
  id: 9201 + index, provider_type: "lab", name,
  slug: `fictional-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-$/, "")}`,
  description: "Fictional sample laboratory created for the eCare college demonstration. Not a real facility.",
  address: `Fictional demo address, ${localities[index]}, ${location.label}`,
  locality: localities[index], city: location.city, state: location.state, locationId: location.id,
  phone: "Fictional contact only — not a real phone number", email: `lab${index + 1}@example.com`,
  website: null, hospital_type: null, opd_type: null, hospital_id: null, specialities: [],
  source: "Fictional sample data", source_url: null, verified_at: null, is_verified: false,
  is_demo: true, verification_status: "Fictional sample — unverified",
  };
});

type DoctorSeed = [string, string, number, number, number, number];
const doctorSeeds: DoctorSeed[] = [
  ["Aarav Kulkarni", "MBBS, MD (General Medicine)", 12, 1, 1, 525],
  ["Nandita Rao", "MBBS, MD (Paediatrics)", 9, 3, 2, 450],
  ["Kabir Deshmukh", "MBBS, MS (Orthopaedics)", 15, 5, 3, 650],
  ["Mira Iyer", "MBBS, MS (Obstetrics and Gynaecology)", 11, 4, 4, 600],
  ["Rohan Bhat", "MBBS, DM (Cardiology)", 14, 2, 5, 750],
  ["Sana Qureshi", "MBBS, MD (Dermatology)", 8, 6, 6, 500],
  ["Devika Shetty", "MBBS, MS (Ophthalmology)", 10, 7, 7, 500],
  ["Ishaan Naik", "MBBS, DLO (ENT)", 7, 8, 8, 425],
  ["Tara Menon", "BDS, MDS (Dentistry)", 13, 9, 9, 400],
  ["Neel Patil", "MBBS, fellowship in Diabetology", 6, 10, 10, 450],
  ["Ananya Hegde", "MBBS, MD (General Medicine)", 16, 1, 1, 575],
  ["Vikram Sood", "MBBS, DM (Neurology)", 18, 11, 2, 800],
  ["Leela Krishnan", "MBBS, MD (Pulmonology)", 9, 12, 3, 550],
  ["Arjun Nayak", "MBBS, MD (Nephrology)", 12, 13, 4, 700],
  ["Farah Siddiqui", "MBBS, DPM (Psychiatry)", 7, 14, 5, 500],
  ["Kiran Joshi", "MBBS, MS (General Surgery)", 20, 16, 6, 650],
  ["Meera Prabhu", "MBBS, MS (Urology)", 11, 15, 7, 650],
  ["Aditya Rao", "MBBS, MD (Radiology)", 8, 17, 8, 475],
  ["Pooja Fernandes", "MPT (Musculoskeletal Physiotherapy)", 10, 19, 9, 350],
  ["Rahul Anand", "MSc (Clinical Nutrition)", 5, 20, 10, 300],
];

const weekday = (days: number[], start: string, end: string, location: string, breakStart?: string, breakEnd?: string) =>
  Object.fromEntries(days.map((day) => [day, { start, end, location, breakStart, breakEnd }])) as Partial<Record<number, DemoSession>>;

const scheduleTemplates = [
  { governmentDuty: weekday([1, 2, 3, 4, 5], "09:00", "13:00", "Fictional District Teaching Hospital"), privateOpd: weekday([1, 2, 3, 4, 5], "17:00", "19:00", "Fictional Aarogya Clinic", "18:00", "18:15") },
  { governmentDuty: weekday([1, 2, 3, 4, 5, 6], "10:00", "14:00", "Fictional Community Hospital"), privateOpd: weekday([2, 4], "17:00", "20:00", "Fictional Rao Family Clinic", "18:30", "19:00") },
  { governmentDuty: weekday([3, 4, 5], "09:00", "13:00", "Fictional Taluk Hospital"), privateOpd: weekday([1, 2, 3, 4, 5, 6], "16:00", "19:00", "Fictional Sushruta Clinic", "17:30", "17:45") },
  { governmentDuty: {}, privateOpd: weekday([1, 2, 3, 4, 5, 6], "10:00", "13:00", "Fictional Independent Practice", "11:30", "12:00") },
  { governmentDuty: weekday([1, 2, 3, 4, 5], "08:30", "12:30", "Fictional City Hospital"), privateOpd: weekday([1, 3, 5, 6], "16:30", "19:30", "Fictional Specialist Clinic", "18:00", "18:20") },
  { governmentDuty: weekday([2, 3, 4, 5, 6], "09:30", "13:30", "Fictional General Hospital"), privateOpd: weekday([1, 2, 4, 6], "15:30", "18:30", "Fictional Nirmala Clinic", "17:00", "17:15") },
  { governmentDuty: weekday([1, 2, 3, 4], "09:00", "12:00", "Fictional Medical College"), privateOpd: weekday([1, 2, 3, 4, 5], "14:30", "17:30", "Fictional College Road Clinic", "16:00", "16:15") },
  { governmentDuty: weekday([1, 3, 5, 6], "10:00", "14:00", "Fictional District Hospital"), privateOpd: weekday([2, 3, 5, 6], "16:00", "19:00", "Fictional Prerana Clinic", "17:30", "17:45") },
  { governmentDuty: weekday([1, 2, 3, 4, 5], "08:00", "12:00", "Fictional Urban Health Centre"), privateOpd: weekday([1, 2, 3, 4, 5, 6], "15:00", "18:00", "Fictional Bluebell Practice", "16:30", "16:45") },
  { governmentDuty: weekday([2, 3, 4, 5], "09:00", "13:00", "Fictional Regional Hospital"), privateOpd: weekday([1, 2, 4, 5, 6], "17:00", "20:00", "Fictional Green Park Clinic", "18:30", "18:45") },
];

function rotateAndLabelSessions(sessions: Partial<Record<number, DemoSession>>, rotation: number, doctorName: string): Partial<Record<number, DemoSession>> {
  return Object.fromEntries(Object.entries(sessions).flatMap(([day, session]) => {
    if (!session) return [];
    const sourceDay = Number(day);
    const targetDay = rotation === 0 ? sourceDay : ((sourceDay - 1 + rotation) % 6) + 1;
    return [[targetDay, { ...session, location: `${session.location} · ${doctorName.split(" ")[0]} sample room` }]];
  })) as Partial<Record<number, DemoSession>>;
}

export const FICTIONAL_DOCTORS: FictionalProvider[] = doctorSeeds.map(([name, qualification, experienceYears, specialityId, hospitalIndex, consultationFee], index) => {
  const hospital = hospitals[hospitalIndex - 1];
  const baseSchedule = scheduleTemplates[index % scheduleTemplates.length];
  const rotation = index < 10 ? 0 : 1 + ((index - 10) % 5);
  const schedule = {
    governmentDuty: rotateAndLabelSessions(baseSchedule.governmentDuty, rotation, name),
    privateOpd: rotateAndLabelSessions(baseSchedule.privateOpd, rotation, name),
  };
  const special = FICTIONAL_SPECIALITIES.find((item) => item.id === specialityId + 1000)!;
  return {
    id: 9001 + index, provider_type: "doctor", name: `Dr. ${name}`,
    slug: `fictional-dr-${name.toLowerCase().replace(/\s+/g, "-")}`,
    description: `Fictional sample profile for a ${special.name.toLowerCase()} demonstration. Biography and credentials are invented for this college project.`,
    qualification, experienceYears, biography: `Fictional ${special.name.toLowerCase()} clinician with ${experienceYears} years of invented sample experience. This profile is not a real person or professional history.`,
    address: hospital.address, locality: hospital.locality, city: hospital.city, state: hospital.state, locationId: hospital.locationId,
    phone: "Fictional contact only — not a real phone number", email: `doctor${String(index + 1).padStart(2, "0")}@example.com`,
    website: null, hospital_type: null, opd_type: "Fictional private OPD", hospital_id: hospital.id,
    specialities: [special], source: "Fictional sample data", source_url: null, verified_at: null,
    is_verified: false, is_demo: true, verification_status: "Fictional sample — unverified",
    consultationFee, schedule: { ...schedule, durationMinutes: index % 3 === 0 ? 30 : 20, unavailableDays: [0] },
    addedDaysAgo: doctorSeeds.length - index,
  };
});

export const FICTIONAL_PROVIDERS: FictionalProvider[] = [...hospitals, ...FICTIONAL_DOCTORS, ...labs];

export const FICTIONAL_HOSPITALS = hospitals;
export const FICTIONAL_LABS = labs;

export function getFictionalProvider(type: ProviderType, id: number): FictionalProvider | undefined {
  return FICTIONAL_PROVIDERS.find((provider) => provider.provider_type === type && provider.id === id);
}

function toMinutes(value: string): number {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

function fromMinutes(value: number): string {
  return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
}

export interface DemoAppointmentSlot { time: string; location: string; }

/** Slots are generated only inside this doctor's sample private OPD session. */
export function getDoctorSlots(doctor: FictionalProvider, date: string): DemoAppointmentSlot[] {
  if (!doctor.schedule || !date) return [];
  const day = new Date(`${date}T12:00:00`).getDay();
  const schedule = doctor.schedule;
  const session = schedule.privateOpd[day];
  if (!session || schedule.unavailableDays.includes(day)) return [];
  const duty = schedule.governmentDuty[day];
  const start = toMinutes(session.start);
  const end = toMinutes(session.end);
  const duration = schedule.durationMinutes;
  const slots: DemoAppointmentSlot[] = [];
  for (let time = start; time + duration <= end; time += duration) {
    const slotEnd = time + duration;
    const overlapsDuty = duty && time < toMinutes(duty.end) && slotEnd > toMinutes(duty.start);
    const overlapsBreak = session.breakStart && session.breakEnd && time < toMinutes(session.breakEnd) && slotEnd > toMinutes(session.breakStart);
    if (!overlapsDuty && !overlapsBreak) {
      slots.push({ time: fromMinutes(time), location: session.location });
    }
  }
  return slots;
}

export function getDoctorHospital(doctor: FictionalProvider): FictionalProvider | undefined {
  return doctor.hospital_id ? getFictionalProvider("hospital", doctor.hospital_id) : undefined;
}

