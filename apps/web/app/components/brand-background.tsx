export function BrandBackground({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`ecare-brand-background ${className}`}>{children}</div>;
}
