"use strict";

import * as React from "react";

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {}

export function Select({ className, ...props }: SelectProps) {
  return (
    <select
      className={`flex h-[var(--radius-control)] min-h-[var(--radius-control)] w-full rounded-[var(--radius-control)] border border-solid border-border bg-background px-3 py-2 text-ink shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-navy-700 disabled:cursor-not-allowed disabled:opacity-50 ${className || ""}`}
      {...props}
    />
  );
}
