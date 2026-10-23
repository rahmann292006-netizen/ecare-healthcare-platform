"use strict";

import * as React from "react";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "verified" | "stale" | "unverified" | "contact" | "success" | "warning" | "info";
}

export function Badge({ className, variant = "verified", ...props }: BadgeProps) {
  const variants: Record<string, string> = {
    verified:
      "rounded-[var(--radius-control)] border border-solid border-teal-700 bg-teal-700 px-3 py-1 text-xs font-medium text-white",
    stale:
      "rounded-[var(--radius-control)] border border-solid border-warning bg-warning px-3 py-1 text-xs font-medium text-white",
    unverified:
      "rounded-[var(--radius-control)] border border-solid border-danger bg-danger px-3 py-1 text-xs font-medium text-white",
    contact:
      "rounded-[var(--radius-control)] border border-solid border-info bg-info px-3 py-1 text-xs font-medium text-white",
    success:
      "rounded-[var(--radius-control)] border border-solid border-success bg-success px-3 py-1 text-xs font-medium text-white",
    warning:
      "rounded-[var(--radius-control)] border border-solid border-warning bg-warning px-3 py-1 text-xs font-medium text-white",
    info:
      "rounded-[var(--radius-control)] border border-solid border-info bg-info px-3 py-1 text-xs font-medium text-white",
  };

  return (
    <span
      className={`${variants[variant]} ${className || ""}`}
      {...props}
    />
  );
}
