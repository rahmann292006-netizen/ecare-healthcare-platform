"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { BrandLogo } from "@/components/brand-logo";
import { useAuth } from "@/components/auth-provider";

const publicLinks = [
  { href: "/", label: "Home" }, { href: "/find", label: "Find Healthcare" },
  { href: "/specialities", label: "Specialities" }, { href: "/packages", label: "Health Packages" },
  { href: "/join-doctor", label: "Join as Doctor" },
];

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, signOut } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const roleLinks = user?.role === "admin"
    ? [{ href: "/admin", label: "Admin Panel" }]
    : user?.role === "provider"
      ? [{ href: "/provider", label: "Doctor Dashboard" }, { href: "/provider#schedule", label: "My Schedule" }, { href: "/profile", label: "My Profile" }]
      : user
        ? [{ href: "/dashboard", label: "Dashboard" }, { href: "/dashboard#appointments", label: "My Appointments" }, { href: "/profile", label: "My Profile" }]
        : [];

  async function handleLogout() {
    await signOut();
    setMenuOpen(false);
    router.push("/");
  }

  const links = [...publicLinks, ...roleLinks];
  return <nav className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur" aria-label="Main navigation">
    <div className="mx-auto max-w-6xl px-4 sm:px-6"><div className="flex min-h-16 items-center justify-between gap-4">
      <BrandLogo />
      <div className="hidden items-center gap-1 lg:flex">{links.map((item) => <Link key={item.href} href={item.href} aria-current={pathname === item.href ? "page" : undefined} className={`rounded-[var(--radius-control)] px-3 py-2 text-sm font-medium ${pathname === item.href ? "bg-navy-50 text-navy-900" : "text-ink-muted hover:bg-navy-50 hover:text-ink"}`}>{item.label}</Link>)}</div>
      <div className="hidden items-center gap-2 sm:flex">{loading ? <span className="text-xs text-ink-muted">Checking session…</span> : user ? <><span className="max-w-36 truncate text-sm text-ink-muted">{user.full_name}</span><button type="button" onClick={() => void handleLogout()} className="rounded-[var(--radius-control)] bg-navy-900 px-4 py-2 text-sm font-medium text-white hover:bg-navy-800">Logout</button></> : <><Link href="/login" className="rounded-[var(--radius-control)] px-3 py-2 text-sm font-medium text-ink hover:bg-navy-50">Login</Link><Link href="/register" className="rounded-[var(--radius-control)] bg-navy-900 px-4 py-2 text-sm font-medium text-white hover:bg-navy-800">Create Account</Link></>}</div>
      <button type="button" className="rounded-[var(--radius-control)] border border-border px-3 py-2 text-sm text-ink lg:hidden" aria-expanded={menuOpen} aria-controls="mobile-navigation" onClick={() => setMenuOpen((value) => !value)}>{menuOpen ? "Close" : "Menu"}</button>
    </div>
    {menuOpen && <div id="mobile-navigation" className="border-t border-border py-3 lg:hidden"><div className="grid gap-1">{links.map((item) => <Link key={item.href} href={item.href} onClick={() => setMenuOpen(false)} className="rounded px-3 py-2 text-sm font-medium text-ink hover:bg-navy-50">{item.label}</Link>)}{!loading && (user ? <button type="button" onClick={() => void handleLogout()} className="rounded px-3 py-2 text-left text-sm font-medium text-danger">Logout</button> : <><Link href="/login" onClick={() => setMenuOpen(false)} className="rounded px-3 py-2 text-sm font-medium text-ink">Login</Link><Link href="/register" onClick={() => setMenuOpen(false)} className="rounded px-3 py-2 text-sm font-medium text-ink">Create Account</Link></>)}</div></div>}
    </div>
  </nav>;
}
