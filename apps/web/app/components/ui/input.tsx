"use strict";

import * as React from "react";

type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={`flex h-[var(--radius-control)] min-h-[var(--radius-control)] w-full rounded-[var(--radius-control)] border border-solid border-border bg-background px-3 py-2 text-ink shadow-sm placeholder:text-ink-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-navy-700 disabled:cursor-not-allowed disabled:opacity-50 ${className || ""}`}
      {...props}
    />
  );
}
