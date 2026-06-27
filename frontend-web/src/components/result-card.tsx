"use client";

import { useState } from "react";
import { api, SearchResult } from "@/lib/api";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";

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
      // "favourite" == shortlist in the evaluations store, keyed by (source, external_id)
      await api.patchDecision(r.source, r.external_id, next ? "shortlist" : null, "");
      setSaved(next);
    } catch {
      setError(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="flex gap-3">
      {onToggle && (
        <input
          type="checkbox"
          checked={!!selected}
          onChange={onToggle}
          className="mt-1 h-4 w-4 accent-[var(--primary)]"
          aria-label="select to compare"
        />
      )}
      <div className="w-7 shrink-0 font-mono text-lg text-primary">{rank}</div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="rounded bg-primary-container px-1.5 py-0.5 text-xs font-semibold text-on-primary-container">
            {r.score != null ? r.score.toFixed(1) : "—"}
          </span>
          <a
            href={r.url}
            target="_blank"
            rel="noreferrer"
            className="truncate font-medium text-primary hover:underline"
          >
            {r.title ?? "(untitled)"}
          </a>
        </div>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          <Badge>{price}</Badge>
          {r.year != null && <Badge>{r.year}</Badge>}
          {r.km != null && <Badge>{r.km.toLocaleString("pt-PT")} km</Badge>}
          <Badge>{r.source}</Badge>
          {r.also_on?.map((d) => (
            <a key={d.url} href={d.url} target="_blank" rel="noreferrer">
              <Badge className="border-primary/40 text-primary">also on {d.source}</Badge>
            </a>
          ))}
        </div>
        {r.rationale && <p className="mt-2 text-sm text-muted">{r.rationale}</p>}
        <div className="mt-2 flex items-center gap-3">
          <a
            href={r.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
          >
            Open ad ↗
          </a>
          {r.external_id && (
            <Button size="sm" variant={saved ? "outline" : "ghost"} onClick={save} disabled={saving}>
              {saving ? "…" : saved ? "♥ Saved" : "♡ Save"}
            </Button>
          )}
          {error && <span className="text-xs text-danger">save failed</span>}
        </div>
      </div>
    </Card>
  );
}
