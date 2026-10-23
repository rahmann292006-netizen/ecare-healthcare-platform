"use strict";

import * as React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={`rounded-[var(--radius-card)] border border-solid border-border bg-background shadow-[var(--shadow-card)] ${className || ""}`}
      {...props}
    />
  );
}

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {}
export function CardHeader({ className, ...props }: CardHeaderProps) {
  return (
    <div
      className={`flex flex-col space-y-1.5 pb-2 ${className || ""}`}
      {...props}
    />
  );
}

export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}
export function CardTitle({ className, ...props }: CardTitleProps) {
  return (
    <h3
      className={`text-lg font-semibold text-ink ${className || ""}`}
      {...props}
    />
  );
}

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {}
export function CardContent({ className, ...props }: CardContentProps) {
  return (
    <div className={`pb-2 ${className || ""}`} {...props} />
  );
}

export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {}
export function CardFooter({ className, ...props }: CardFooterProps) {
  return (
    <div
      className={`flex items-center pt-2 ${className || ""}`}
      {...props}
    />
  );
}
