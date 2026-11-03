import Link from "next/link";
import { BrandLogo } from "@/components/brand-logo";

export function Footer() {
  return <footer className="mt-auto border-t border-border bg-navy-50 py-8" aria-label="Footer"><div className="mx-auto max-w-6xl space-y-5 px-4 sm:px-6">
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><BrandLogo /><div className="flex flex-wrap gap-x-4 gap-y-2 text-sm"><Link href="/find" className="text-teal-700 hover:underline">Find healthcare</Link><Link href="/specialities" className="text-teal-700 hover:underline">Specialities</Link><Link href="/packages" className="text-teal-700 hover:underline">Checkup packages</Link></div></div>
    <p className="max-w-5xl text-xs leading-5 text-ink-muted">eCare currently includes illustrative healthcare listings and demonstration booking information. Provider details, availability, and charges must not be treated as verified real-world information.</p>
    <p className="text-xs text-ink-muted">Demo authentication and billing are for classroom presentation only. eCare does not process real payments or send external notifications.</p>
  </div></footer>;
}
