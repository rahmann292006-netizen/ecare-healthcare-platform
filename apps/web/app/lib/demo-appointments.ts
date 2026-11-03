import { FICTIONAL_DOCTORS, getDoctorHospital, getDoctorSlots, type FictionalProvider } from "@/lib/fictional-directory";

export type DemoAppointmentStatus = "pending" | "confirmed" | "completed";
export interface DemoAppointment {
  id: string;
  doctorId: number;
  date: string;
  time: string;
  location: string;
  status: DemoAppointmentStatus;
  reference: string;
  isSample: true;
}

function localDate(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function findAppointmentSlot(doctor: FictionalProvider, direction: "future" | "past", offset: number) {
  const today = new Date("2026-11-03T12:00:00");
  for (let distance = direction === "future" ? 1 : 1; distance < 45; distance += 1) {
    const day = new Date(today);
    day.setDate(today.getDate() + (direction === "future" ? distance : -distance));
    const date = localDate(day);
    const slot = getDoctorSlots(doctor, date)[offset % 4];
    if (slot) return { date, ...slot };
  }
  return null;
}

const appointmentSeeds: Array<[number, DemoAppointmentStatus, "future" | "past", number]> = [
  [9001, "confirmed", "future", 0],
  [9002, "pending", "future", 1],
  [9004, "pending", "future", 0],
  [9006, "confirmed", "future", 2],
  [9005, "completed", "past", 0],
  [9003, "completed", "past", 1],
  [9010, "confirmed", "future", 1],
];

export const DEMO_APPOINTMENTS: DemoAppointment[] = appointmentSeeds.flatMap(([doctorId, status, direction, slotIndex], index) => {
  const doctor = FICTIONAL_DOCTORS.find((item) => item.id === doctorId);
  const slot = doctor && findAppointmentSlot(doctor, direction, slotIndex);
  if (!doctor || !slot) return [];
  return [{ id: `sample-appt-${index + 1}`, doctorId, date: slot.date, time: slot.time, location: slot.location, status, reference: `DEMO-${String(index + 1).padStart(3, "0")}`, isSample: true }];
});

export function getAppointmentDoctor(appointment: DemoAppointment) {
  return FICTIONAL_DOCTORS.find((doctor) => doctor.id === appointment.doctorId);
}

export function getAppointmentHospital(appointment: DemoAppointment) {
  const doctor = getAppointmentDoctor(appointment);
  return doctor ? getDoctorHospital(doctor) : undefined;
}

export function compareAppointmentDates(a: DemoAppointment, b: DemoAppointment) {
  return `${a.date}T${a.time}`.localeCompare(`${b.date}T${b.time}`);
}

