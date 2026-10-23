"use strict";

import Link from "next/link";

export interface CategoryCardProps {
  title: string;
  description: string;
  count: string;
  href: string;
  icon: string;
}

export function CategoryCard({ title, description, count, href, icon }: CategoryCardProps) {
  return (
    <Link
      href={href}
      className="group block rounded-[var(--radius-card)] border border-solid border-border bg-background p-6 shadow-[var(--shadow-card)] transition-colors hover:bg-navy-50"
      aria-label={title}
    >
      <div className="flex items-center gap-3">
        <span className="rounded bg-teal-50 p-2 text-teal-700 font-bold">{icon}</span>
        <div>
          <h3 className="text-lg font-semibold text-ink group-hover:text-navy-700">{title}</h3>
          <p className="text-sm text-ink-muted">{description}</p>
          <span className="mt-1 inline-block text-xs font-medium text-teal-700">
            {count} available
          </span>
        </div>
      </div>
    </Link>
  );
}
