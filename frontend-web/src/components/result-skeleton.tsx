// pulsing placeholders mirroring the ResultCard layout, shown while a scrape runs
export function ResultSkeletons({ count = 3 }: { count?: number }) {
  return (
    <section className="space-y-2.5 animate-rise" aria-hidden>
      <div className="h-3 w-20 animate-pulse rounded bg-surface-high" />
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="flex gap-3 rounded-xl border border-border bg-surface p-3">
          <div className="h-[68px] w-[96px] shrink-0 animate-pulse rounded-lg bg-surface-high" />
          <div className="min-w-0 flex-1 space-y-2 py-0.5">
            <div className="h-4 w-2/3 animate-pulse rounded bg-surface-high" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-surface-high" />
            <div className="h-3 w-4/5 animate-pulse rounded bg-surface-high" />
          </div>
        </div>
      ))}
    </section>
  );
}
