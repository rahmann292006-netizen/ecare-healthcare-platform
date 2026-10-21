export default function Home() {
  return (
    <div className="bg-background text-ink min-h-full">
      <main className="max-w-5xl mx-auto p-6 sm:p-10">
        <h1 className="text-3xl font-semibold text-ink">
          ecare design token preview
        </h1>
        <p className="mt-2 text-ink-muted">
          Temporary preview page for the ecare design tokens. Placeholder
          content only.
        </p>

        <div className="mt-10 flex flex-wrap gap-3">
          <button
            className="rounded-[var(--radius-control)] bg-navy-900 px-5 py-2.5 text-white font-medium"
          >
            Primary button
          </button>
          <button
            className="rounded-[var(--radius-control)] border-2 border-solid border-teal-700 bg-transparent px-5 py-2 text-teal-700 font-medium"
          >
            Secondary button
          </button>
        </div>

        <section className="mt-10">
          <div
            className="rounded-[var(--radius-card)] border border-solid border-border bg-background p-6 shadow-[var(--shadow-card)]"
          >
            <h3 className="text-lg font-medium text-ink">Sample card</h3>
            <p className="mt-2 text-ink-muted">
              This is a sample card with placeholder text.
            </p>
          </div>
        </section>

        <div className="mt-10 flex flex-wrap gap-3">
          <span
            className="rounded-[var(--radius-control)] border border-solid border-teal-700 bg-teal-700 px-3 py-1 text-xs font-medium text-white"
          >
            Verified
          </span>
          <span
            className="rounded-[var(--radius-control)] border border-solid border-warning bg-warning px-3 py-1 text-xs font-medium text-white"
          >
            Stale
          </span>
          <span
            className="rounded-[var(--radius-control)] border border-solid border-danger bg-danger px-3 py-1 text-xs font-medium text-white"
          >
            Not verified
          </span>
          <span
            className="rounded-[var(--radius-control)] border border-solid border-info bg-info px-3 py-1 text-xs font-medium text-white"
          >
            Contact provider
          </span>
        </div>
      </main>
    </div>
  );
}
