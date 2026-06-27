"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Evaluation } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

const STATUS_OPTIONS = ["", "shortlist", "rejected"];

export default function EvaluationsPage() {
  const [rows, setRows] = useState<Evaluation[]>([]);
  const [search, setSearch] = useState("");
  const [minScore, setMinScore] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState("");

  // honor ?status=shortlist (the sidebar "Favorites" link) without an SSR hydration mismatch
  useEffect(() => {
    const s = new URLSearchParams(window.location.search).get("status");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (s) setStatusFilter(s);
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const statuses = statusFilter === "all" ? undefined : [statusFilter];
        const data = await api.getEvaluations({
          search: search || undefined,
          min_score: minScore ? Number(minScore) : undefined,
          statuses,
        });
        if (active) {
          setRows(data);
          setError("");
        }
      } catch (e) {
        if (active) setError(String(e));
      }
    })();
    return () => {
      active = false;
    };
  }, [search, minScore, statusFilter]);

  const setDecision = async (r: Evaluation, status: string, notes: string) => {
    setRows((rs) =>
      rs.map((x) =>
        x.source === r.source && x.external_id === r.external_id ? { ...x, status: status || null, notes } : x,
      ),
    );
    try {
      await api.patchDecision(r.source, r.external_id, status || null, notes);
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Evaluations</h1>
        <Link href="/" className="text-sm text-primary hover:underline">
          ← Chat
        </Link>
      </div>

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs text-muted">
          search
          <Input
            className="w-56"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="title contains…"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted">
          min score
          <Input
            className="w-24"
            type="number"
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted">
          status
          <Select
            className="w-36"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">all</option>
            <option value="shortlist">shortlist</option>
            <option value="rejected">rejected</option>
            <option value="unset">unset</option>
          </Select>
        </label>
      </div>

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-surface-high text-left text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="p-2">score</th>
              <th className="p-2">title</th>
              <th className="p-2">year</th>
              <th className="p-2">km</th>
              <th className="p-2">price</th>
              <th className="p-2">source</th>
              <th className="p-2">status</th>
              <th className="p-2">notes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${r.source}-${r.external_id}`} className="border-t border-border">
                <td className="p-2 font-mono text-primary">{r.score.toFixed(1)}</td>
                <td className="max-w-xs truncate p-2">
                  <a href={r.url} target="_blank" rel="noreferrer" className="hover:text-primary">
                    {r.title}
                  </a>
                </td>
                <td className="p-2">{r.year ?? "—"}</td>
                <td className="p-2">{r.km != null ? r.km.toLocaleString("pt-PT") : "—"}</td>
                <td className="p-2">{r.price_eur ? `${r.price_eur.toLocaleString("pt-PT")} €` : "—"}</td>
                <td className="p-2">
                  <Badge>{r.source}</Badge>
                </td>
                <td className="p-2">
                  <Select
                    className="w-28"
                    value={r.status ?? ""}
                    onChange={(e) => setDecision(r, e.target.value, r.notes)}
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>
                        {s || "—"}
                      </option>
                    ))}
                  </Select>
                </td>
                <td className="p-2">
                  <Input
                    className="w-48"
                    defaultValue={r.notes}
                    onBlur={(e) => setDecision(r, r.status ?? "", e.target.value)}
                  />
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={8} className="p-6 text-center text-muted">
                  No evaluations match.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
