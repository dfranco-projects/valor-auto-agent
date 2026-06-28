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
  geminiKey,
  anthropicKey,
  onNewChat,
  onSelect,
  onModelChange,
}: {
  sessions: SessionMeta[];
  activeThread: string;
  models: string[];
  raterModel: string;
  geminiKey: boolean;
  anthropicKey: boolean;
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
    <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-surface-low/60">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-on-primary">
          <span className="text-lg leading-none">◈</span>
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">Valor-Auto</div>
          <div className="text-[11px] text-muted">used-car agent</div>
        </div>
      </div>

      <div className="px-3">
        <Button variant="outline" className="w-full justify-start" onClick={onNewChat}>
          <span className="text-base leading-none">＋</span> New chat
        </Button>
      </div>

      <div className="px-3 pt-4">
        <label className="px-1 text-[11px] font-medium uppercase tracking-wide text-muted">
          Rater model
        </label>
        <Select className="mt-1.5" value={raterModel} onChange={(e) => onModelChange(e.target.value)}>
          {models.map((m) => (
            <option key={m} value={m}>
              {modelLabel(m)}
            </option>
          ))}
        </Select>
      </div>

      <div className="mt-5 flex min-h-0 flex-1 flex-col px-3">
        <div className="mb-1 px-1 text-[11px] font-medium uppercase tracking-wide text-muted">
          Recent
        </div>
        <div className="-mx-1 min-h-0 flex-1 overflow-y-auto px-1">
          {sessions.length === 0 && (
            <p className="px-1 py-2 text-xs text-muted">No chats yet.</p>
          )}
          {sessions.map((s) => (
            <button
              key={s.thread_id}
              onClick={() => onSelect(s.thread_id)}
              className={cn(
                "mb-0.5 block w-full truncate rounded-lg px-2.5 py-1.5 text-left text-sm transition-colors",
                s.thread_id === activeThread
                  ? "bg-surface-high font-medium text-foreground"
                  : "text-muted hover:bg-surface-high hover:text-foreground",
              )}
            >
              {s.title || "untitled"}
            </button>
          ))}
        </div>
      </div>

      <nav className="mt-2 space-y-0.5 border-t border-border p-3">
        <NavLink href="/evaluations?status=shortlist" icon="♥">
          Favorites
        </NavLink>
        <NavLink href="/saved" icon="🔔" badge={unread}>
          Saved &amp; alerts
        </NavLink>
        <NavLink href="/evaluations" icon="☰">
          Evaluations
        </NavLink>
      </nav>

      <div className="border-t border-border px-3 py-3">
        <div className="flex items-center gap-2 rounded-lg bg-surface px-2.5 py-2">
          <span className="text-sm text-muted">⚙</span>
          <span className="text-xs font-medium">Settings</span>
          <div className="ml-auto flex items-center gap-2.5 text-[11px] text-muted">
            <span
              className="flex items-center gap-1"
              title={geminiKey ? "Gemini key configured" : "no Gemini key"}
            >
              <span
                className={cn("h-1.5 w-1.5 rounded-full", geminiKey ? "bg-success" : "bg-border-strong")}
              />
              Gemini
            </span>
            <span
              className="flex items-center gap-1"
              title={anthropicKey ? "Claude key configured" : "no Claude key"}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  anthropicKey ? "bg-success" : "bg-border-strong",
                )}
              />
              Claude
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}

function NavLink({
  href,
  icon,
  badge,
  children,
}: {
  href: string;
  icon: string;
  badge?: number;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm text-muted transition-colors hover:bg-surface-high hover:text-foreground"
    >
      <span className="w-4 text-center text-xs opacity-80">{icon}</span>
      {children}
      {badge != null && badge > 0 && (
        <Badge className="ml-auto border-primary/40 bg-primary-container text-on-primary-container">
          {badge}
        </Badge>
      )}
    </Link>
  );
}
