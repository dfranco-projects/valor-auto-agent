"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Alert, api, Filters, SavedSearch } from "@/lib/api";
import { brandLabel } from "@/lib/labels";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FilterForm } from "@/components/filter-form";

const summarize = (f: Filters) =>
  Object.entries(f)
    .map(([k, v]) => (k === "brand" ? brandLabel(String(v)) : `${k}=${v}`))
    .join(" · ") || "any car";

export default function SavedPage() {
  const [saved, setSaved] = useState<SavedSearch[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [name, setName] = useState("");
  const [cadence, setCadence] = useState("360");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = async () => {
    try {
      const [s, a] = await Promise.all([api.getSaved(), api.getAlerts()]);
      setSaved(s);
      setAlerts(a);
      setError("");
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [s, a] = await Promise.all([api.getSaved(), api.getAlerts()]);
        if (active) {
          setSaved(s);
          setAlerts(a);
        }
      } catch (e) {
        if (active) setError(String(e));
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const create = async (filters: Filters) => {
    if (!name.trim()) {
      setError("Give the saved search a name first.");
      return;
    }
    setBusy(true);
    try {
      await api.createSaved(name.trim(), filters, Number(cadence) || 360);
      setName("");
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const runNow = async (id: number) => {
    setBusy(true);
    try {
      await api.runSaved(id);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: number) => {
    await api.deleteSaved(id);
    refresh();
  };

  const markRead = async (id: number) => {
    await api.readAlert(id);
    refresh();
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Saved searches &amp; alerts</h1>
        <Link href="/" className="text-sm text-primary hover:underline">
          ← Chat
        </Link>
      </div>

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}

      <Card className="mb-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
          New saved search
        </h2>
        <div className="mb-3 flex flex-wrap gap-3">
          <label className="flex flex-col gap-1 text-xs text-muted">
            name
            <Input
              className="w-56"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. cheap diesel BMWs"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted">
            re-run every (minutes)
            <Input
              className="w-40"
              type="number"
              value={cadence}
              onChange={(e) => setCadence(e.target.value)}
            />
          </label>
        </div>
        <FilterForm
          prefill={{}}
          busy={busy}
          onSubmit={create}
          note="Set the filters to watch, then save."
          submitLabel="Add saved search"
          busyLabel="Saving…"
        />
      </Card>

      <section className="mb-6 space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Watching</h2>
        {saved.length === 0 && <p className="text-sm text-muted">No saved searches yet.</p>}
        {saved.map((s) => (
          <Card key={s.id} className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium">{s.name}</span>
                {s.new_count > 0 && (
                  <Badge className="border-primary/40 bg-primary-container text-on-primary-container">
                    {s.new_count} new
                  </Badge>
                )}
              </div>
              <p className="truncate text-xs text-muted">{summarize(s.filters)}</p>
              <p className="text-xs text-muted">
                every {s.cadence_minutes}m ·{" "}
                {s.last_run_at ? `last run ${new Date(s.last_run_at).toLocaleString()}` : "never run"}
              </p>
            </div>
            <div className="flex shrink-0 gap-2">
              <Button size="sm" variant="outline" onClick={() => runNow(s.id)} disabled={busy}>
                Run now
              </Button>
              <Button size="sm" variant="danger" onClick={() => remove(s.id)}>
                Delete
              </Button>
            </div>
          </Card>
        ))}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Alerts</h2>
        {alerts.length === 0 && <p className="text-sm text-muted">No alerts yet.</p>}
        {alerts.map((a) => (
          <Card key={a.id} className={a.read ? "opacity-60" : "border-primary/30"}>
            <div className="flex items-center gap-2">
              {a.score != null && (
                <span className="rounded bg-primary-container px-1.5 py-0.5 text-xs font-semibold text-on-primary-container">
                  {a.score.toFixed(1)}
                </span>
              )}
              <a
                href={a.url}
                target="_blank"
                rel="noreferrer"
                className="truncate font-medium hover:text-primary"
              >
                {a.title}
              </a>
              <Badge className="ml-auto">{a.source}</Badge>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              {a.price_eur && <Badge>{a.price_eur.toLocaleString("pt-PT")} €</Badge>}
              {a.year != null && <Badge>{a.year}</Badge>}
              {a.km != null && <Badge>{a.km.toLocaleString("pt-PT")} km</Badge>}
              {!a.read && (
                <Button size="sm" variant="ghost" className="ml-auto" onClick={() => markRead(a.id)}>
                  Mark read
                </Button>
              )}
            </div>
            {a.rationale && <p className="mt-1 text-sm text-muted">{a.rationale}</p>}
          </Card>
        ))}
      </section>
    </div>
  );
}
