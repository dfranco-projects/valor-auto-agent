"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, SessionMeta } from "@/lib/api";
import { modelLabel } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";
import { Select } from "./ui/select";
import { Badge } from "./ui/badge";

export function Sidebar({
  sessions,
  activeThread,
  models,
  raterModel,
  onNewChat,
  onSelect,
  onModelChange,
}: {
  sessions: SessionMeta[];
  activeThread: string;
  models: string[];
  raterModel: string;
  onNewChat: () => void;
  onSelect: (threadId: string) => void;
  onModelChange: (model: string) => void;
}) {
  const [unread, setUnread] = useState(0);
  useEffect(() => {
    let active = true;
    api
      .getAlerts(true)
      .then((a) => {
        if (active) setUnread(a.length);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-surface-low">
      <div className="p-3">
        <div className="mb-3 flex items-center gap-2 px-1">
          <span className="text-primary">●</span>
          <span className="font-semibold">Valor-Auto</span>
        </div>
        <Button variant="outline" className="w-full" onClick={onNewChat}>
          ＋ New chat
        </Button>
      </div>

      <div className="px-3">
        <label className="text-xs text-muted">Model</label>
        <Select
          className="mt-1"
          value={raterModel}
          onChange={(e) => onModelChange(e.target.value)}
        >
          {models.map((m) => (
            <option key={m} value={m}>
              {modelLabel(m)}
            </option>
          ))}
        </Select>
      </div>

      <div className="mt-4 flex-1 overflow-y-auto px-3">
        <div className="mb-1 px-1 text-xs uppercase tracking-wide text-muted">Recent</div>
        {sessions.map((s) => (
          <button
            key={s.thread_id}
            onClick={() => onSelect(s.thread_id)}
            className={cn(
              "block w-full truncate rounded px-2 py-1.5 text-left text-sm hover:bg-surface-high",
              s.thread_id === activeThread && "bg-surface-high text-primary",
            )}
          >
            {s.title || "untitled"}
          </button>
        ))}
      </div>

      <div className="space-y-0.5 border-t border-border p-3">
        <Link
          href="/saved"
          className="flex items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-surface-high"
        >
          Saved &amp; alerts
          {unread > 0 && (
            <Badge className="ml-auto border-primary/40 bg-primary-container text-on-primary-container">
              {unread}
            </Badge>
          )}
        </Link>
        <Link
          href="/evaluations"
          className="block rounded px-2 py-1.5 text-sm hover:bg-surface-high"
        >
          Evaluations →
        </Link>
      </div>
    </aside>
  );
}
