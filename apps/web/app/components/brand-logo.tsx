import Link from "next/link";

export function BrandLogo({ compact = false }: { compact?: boolean }) {
  return <Link href="/" aria-label="eCare home" className="inline-flex items-center gap-2 text-xl font-bold tracking-tight text-navy-900">
    <svg aria-hidden="true" viewBox="0 0 40 40" className="h-9 w-9 shrink-0">
      <path d="M20 3.5c-7 0-12.5 5.5-12.5 12.3 0 8.6 12.5 20.7 12.5 20.7s12.5-12.1 12.5-20.7C32.5 9 27 3.5 20 3.5Z" fill="#0B7285" />
      <path d="M17 9h6v6h6v6h-6v6h-6v-6h-6v-6h6z" fill="#fff" />
      <circle cx="20" cy="17.8" r="1.1" fill="#0B7285" />
    </svg>
    {!compact && <span>eCare</span>}
  </Link>;
}
