"use client";

import Link from "next/link";
import { Suspense } from "react";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Home" },
  { href: "/find", label: "Find Healthcare" },
  { href: "/packages", label: "Health Packages" },
  { href: "/dashboard", label: "My Dashboard" },
  { href: "/reminders", label: "Reminders" },
  { href: "/notifications", label: "Notifications" },
  { href: "/provider", label: "Provider Dashboard" },
];

export function Navbar() {
  return (
    <Suspense fallback={<NavbarContent pathname={null} />}>
      <NavbarWithPathname />
    </Suspense>
  );
}

function NavbarWithPathname() {
  const pathname = usePathname();
  return <NavbarContent pathname={pathname} />;
}

function NavbarContent({ pathname }: { pathname: string | null }) {
  return (
    <nav
      className="sticky top-0 z-20 border-b border-solid border-border bg-background/95 backdrop-blur"
      aria-label="Main navigation"
    >
      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        <div className="flex flex-wrap items-center justify-between py-3 sm:py-4 gap-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-xl font-bold text-ink"
            aria-label="eCare home"
          >
            <span className="rounded bg-teal-700 px-2 py-0.5 text-white font-bold text-sm">
              eCare
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`px-4 py-2 rounded-[var(--radius-control)] text-sm font-medium transition-colors ${
                  pathname === link.href
                    ? "bg-navy-50 text-navy-900"
                    : "text-ink-muted hover:text-ink hover:bg-navy-50"
                }`}
                aria-current={pathname === link.href ? "page" : undefined}
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <ButtonAsLink href="/find" variant="secondary">
              Find a Provider
            </ButtonAsLink>
            <ButtonAsLink href="/dashboard" variant="primary">
              My Dashboard
            </ButtonAsLink>
          </div>
        </div>

        {/* Mobile menu */}
        <div className="md:hidden flex items-center justify-between py-3">
          <Link
            href="/"
            className="flex items-center gap-2 text-xl font-bold text-ink"
          >
            <span className="rounded bg-teal-700 px-2 py-0.5 text-white font-bold text-sm">
              eCare
            </span>
          </Link>
          <button
            className="rounded-[var(--radius-control)] border border-solid border-border bg-background px-3 py-2 text-ink"
            aria-label="Open menu"
            aria-expanded="false"
          >
            Menu
          </button>
        </div>
      </div>
    </nav>
  );
}

function ButtonAsLink({
  href,
  variant,
  children,
}: {
  href: string;
  variant: "primary" | "secondary";
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center justify-center rounded-[var(--radius-control)] text-sm font-medium transition-colors ${
        variant === "primary"
          ? "bg-navy-900 text-white px-4 py-2 hover:bg-navy-800"
          : "bg-teal-700 text-white px-4 py-2 hover:bg-teal-600"
      }`}
    >
      {children}
    </Link>
  );
}
