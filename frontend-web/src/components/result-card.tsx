"use client";

import { useState } from "react";
import { api, SearchResult } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Badge } from "./ui/badge";

function scoreColor(score: number | null): string {
  if (score == null) return "bg-surface-highest text-muted";
  if (score >= 8) return "bg-success/15 text-success ring-1 ring-success/30";
  if (score >= 6) return "bg-primary-container text-on-primary-container ring-1 ring-primary/30";
  return "bg-danger/15 text-danger ring-1 ring-danger/30";
}

export function ResultCard({
  rank,
  r,
  selected,
  onToggle,
}: {
  rank: number;
  r: SearchResult;
  selected?: boolean;
  onToggle?: () => void;
}) {
  const price = r.price_eur ? `${r.price_eur.toLocaleString("pt-PT")} €` : "n/a";
  const [saved, setSaved] = useState(r.status === "shortlist");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);

  const save = async () => {
    if (!r.external_id) return;
    setSaving(true);
    setError(false);
    const next = !saved;
    try {
      await api.patchDecision(r.source, r.external_id, next ? "shortlist" : null, "");
      setSaved(next);
    } catch {
      setError(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className={cn(
        "group flex gap-3 rounded-xl border bg-surface p-3 transition-colors",
        selected
          ? "border-primary/50 bg-primary-container/10"
          : "border-border hover:border-border-strong",
      )}
    >
      {onToggle && (
        <input
          type="checkbox"
          checked={!!selected}
          onChange={onToggle}
          className="mt-1 h-4 w-4 shrink-0 accent-[var(--primary)]"
          aria-label="select to compare"
        />
      )}

      {/* thumbnail with score overlay; missing photo is flagged as a risk */}
      <div className="relative h-[68px] w-[96px] shrink-0 overflow-hidden rounded-lg bg-surface-high">
        {r.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={r.image_url}
            alt={r.title ?? "listing"}
            loading="lazy"
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-0.5 text-center text-danger">
            <span className="text-base leading-none">⚠</span>
            <span className="text-[10px] leading-tight">no photos</span>
          </div>
        )}
        <span
          className={cn(
            "absolute left-1 top-1 flex h-7 min-w-7 items-center justify-center rounded-md px-1 text-sm font-semibold tabular-nums backdrop-blur-sm",
            scoreColor(r.score),
          )}
        >
          {r.score != null ? r.score.toFixed(1) : "—"}
        </span>
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <a
            href={r.url}
            target="_blank"
            rel="noreferrer"
            className="line-clamp-1 font-semibold leading-tight hover:text-primary"
          >
            {r.title ?? "(untitled)"}
          </a>
          <span className="ml-auto shrink-0 text-[11px] text-muted">#{rank}</span>
        </div>

        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted">
          <span className="font-semibold text-foreground">{price}</span>
          {r.year != null && <span>· {r.year}</span>}
          {r.km != null && <span>· {r.km.toLocaleString("pt-PT")} km</span>}
          <Badge className="ml-1">{r.source}</Badge>
          {r.has_photo === false && (
            <Badge className="border-danger/40 text-danger">no photos</Badge>
          )}
          {r.also_on?.map((d) => (
            <a key={d.url} href={d.url} target="_blank" rel="noreferrer">
              <Badge className="border-primary/40 text-primary hover:bg-primary/10">
                also on {d.source}
              </Badge>
            </a>
          ))}
        </div>

        {r.rationale && <p className="mt-1.5 text-sm leading-relaxed text-muted">{r.rationale}</p>}

        <div className="mt-2 flex items-center gap-2">
          <a
            href={r.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 rounded-md bg-surface-high px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-highest"
          >
            Open ad ↗
          </a>
          {r.external_id && (
            <button
              onClick={save}
              disabled={saving}
              className={cn(
                "inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50",
                saved
                  ? "bg-primary-container text-on-primary-container"
                  : "text-muted hover:bg-surface-high hover:text-foreground",
              )}
            >
              {saving ? "…" : saved ? "♥ Saved" : "♡ Save"}
            </button>
          )}
          {error && <span className="text-xs text-danger">save failed</span>}
        </div>
      </div>
    </div>
  );
}
