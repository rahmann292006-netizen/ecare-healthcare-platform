"use client";

const backgrounds = ["#0b7285", "#1d4478", "#557a46", "#76558c", "#9a5d38", "#3f6d78", "#866b26", "#6b5471"];

export function DoctorAvatar({ id, name, size = "md" }: { id: number; name: string; size?: "sm" | "md" | "lg" }) {
  const initials = name.replace(/^Dr\.?\s*/i, "").split(/\s+/).filter(Boolean).map((part) => part[0]).slice(0, 2).join("").toUpperCase();
  const dimensions = size === "lg" ? "h-16 w-16 text-lg" : size === "sm" ? "h-9 w-9 text-xs" : "h-12 w-12 text-sm";
  return <span role="img" aria-label={`Illustrative avatar for ${name}`} className={`inline-flex shrink-0 items-center justify-center rounded-full font-bold text-white ring-2 ring-white ${dimensions}`} style={{ backgroundColor: backgrounds[Math.abs(id) % backgrounds.length] }}>{initials}</span>;
}
