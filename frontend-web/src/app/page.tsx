"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  ConfigOut,
  Filters,
  Role,
  SearchResponse,
  SearchResult,
  SessionMeta,
  SessionOut,
} from "@/lib/api";
import { isGemini, modelLabel } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { Sidebar } from "@/components/sidebar";
import { FilterForm } from "@/components/filter-form";
import { ResultCard } from "@/components/result-card";
import { CompareTable } from "@/components/compare-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface Msg {
  role: Role;
  content: string;
}

const EXAMPLES = [
  "find me a bmw 320d under 10k",
  "audi a4 avant diesel automatic",
  "cheap toyota with low km",
  "volkswagen golf gti under 15k",
];

export default function Page() {
  const [threadId, setThreadId] = useState("");
  const [history, setHistory] = useState<Msg[]>([]);
  const [top, setTop] = useState<SearchResult[]>([]);
  const [pendingFilters, setPendingFilters] = useState(false);
  const [prefill, setPrefill] = useState<Filters>({});
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [cfg, setCfg] = useState<ConfigOut | null>(null);
  const [raterModel, setRaterModel] = useState("");
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  const toggleSelect = (i: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  const push = (role: Role, content: string) =>
    setHistory((h) => [...h, { role, content }]);

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await api.getSessions());
    } catch {
      /* sidebar list is best-effort */
    }
  }, []);

  const applySession = useCallback((s: SessionOut) => {
    setThreadId(s.thread_id);
    setHistory(s.history.map(([role, content]) => ({ role, content })));
    setTop(s.top ?? []);
    setSelected(new Set());
    setPendingFilters(false);
    if (s.rater_model) setRaterModel(s.rater_model);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const c = await api.getConfig();
        setCfg(c);
        setRaterModel(c.default_model);
        applySession(await api.getActiveSession());
        await refreshSessions();
      } catch (e) {
        push("error", String(e));
      }
    })();
  }, [applySession, refreshSessions]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [history, top, pendingFilters]);

  const apply = (res: SearchResponse) => {
    if (res.status === "need_filters") {
      setPendingFilters(true);
      setPrefill(res.prefill ?? {});
      push("assistant", res.reply ?? "filters needed");
    } else {
      setPendingFilters(false);
      push("assistant", res.reply ?? "done");
      if (res.top?.length) {
        setTop(res.top);
        setSelected(new Set());
      }
    }
  };

  const providerOk = (model: string) => {
    if (!cfg) return true;
    return isGemini(model) ? cfg.gemini_key : cfg.anthropic_key;
  };

  const submit = async (prompt: string) => {
    prompt = prompt.trim();
    if (!prompt || !threadId) return;
    push("user", prompt);
    if (!providerOk(raterModel)) {
      push(
        "error",
        "No API key configured for the selected model. Add it to .env and restart the backend.",
      );
      return;
    }
    setBusy(true);
    try {
      const res = await api.postSearch(threadId, prompt, raterModel);
      apply(res);
      refreshSessions();
    } catch (e) {
      push("error", `Something went wrong: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  const resume = async (filters: Filters) => {
    setBusy(true);
    try {
      const res = await api.postResume(threadId, filters);
      if (res.status === "done" && !res.top?.length) {
        push("error", "No listings matched these filters — adjust them and try again.");
        return; // keep the pre-filled form up
      }
      apply(res);
    } catch (e) {
      push("error", `Scrape failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  const newChat = async () => {
    try {
      applySession(await api.newSession());
      setTop([]);
      refreshSessions();
    } catch (e) {
      push("error", String(e));
    }
  };

  const selectSession = async (id: string) => {
    try {
      applySession(await api.getSession(id));
    } catch (e) {
      push("error", String(e));
    }
  };

  const changeModel = (m: string) => {
    setRaterModel(m);
    api.patchConfig(m).catch(() => {});
  };

  const sessionTitle = sessions.find((s) => s.thread_id === threadId)?.title;
  const send = (text: string) => {
    setInput("");
    submit(text);
  };
  const empty = history.length === 0 && top.length === 0 && !pendingFilters && !busy;

  return (
    <div className="flex h-screen">
      <Sidebar
        sessions={sessions}
        activeThread={threadId}
        models={cfg?.models ?? []}
        raterModel={raterModel}
        onNewChat={newChat}
        onSelect={selectSession}
        onModelChange={changeModel}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-5">
          <div className="truncate text-sm font-medium">{sessionTitle || "New chat"}</div>
          {raterModel && (
            <Badge className="shrink-0 gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-success" />
              {modelLabel(raterModel)}
            </Badge>
          )}
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {empty ? (
            <Welcome onPick={send} />
          ) : (
            <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
              {history.map((m, i) => (
                <MessageBubble key={i} msg={m} />
              ))}

              {busy && (
                <div className="flex items-center gap-2.5 px-1 text-sm text-muted animate-rise">
                  <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
                  {pendingFilters ? "scraping olx + standvirtual, then rating…" : "working…"}
                </div>
              )}

              {pendingFilters && <FilterForm prefill={prefill} busy={busy} onSubmit={resume} />}

              {selected.size >= 2 && (
                <CompareTable
                  items={[...selected].sort((a, b) => a - b).map((i) => top[i])}
                  onClear={() => setSelected(new Set())}
                />
              )}

              {top.length > 0 && (
                <section className="space-y-2.5">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">
                      Top picks
                    </h2>
                    {selected.size === 1 && (
                      <span className="text-xs text-muted">select one more to compare</span>
                    )}
                  </div>
                  {top.map((r, i) => (
                    <ResultCard
                      key={`${r.source}-${i}`}
                      rank={i + 1}
                      r={r}
                      selected={selected.has(i)}
                      onToggle={() => toggleSelect(i)}
                    />
                  ))}
                </section>
              )}
            </div>
          )}
        </div>

        <div className="shrink-0 border-t border-border bg-surface-low/60 px-4 py-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (input.trim()) send(input);
            }}
            className="mx-auto flex max-w-3xl items-center gap-2 rounded-2xl border border-border bg-surface px-2 py-1.5 shadow-sm transition-colors focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask the agent — e.g. find me a bmw 320d under 10k"
              disabled={busy || !threadId}
              className="h-9 flex-1 bg-transparent px-2.5 text-sm outline-none placeholder:text-muted disabled:opacity-60"
            />
            <Button type="submit" size="sm" disabled={busy || !threadId || !input.trim()}>
              {busy ? "…" : "Send"}
            </Button>
          </form>
          <p className="mx-auto mt-1.5 max-w-3xl px-2 text-[11px] text-muted">
            searches OLX + StandVirtual, then rates every listing for value.
          </p>
        </div>
      </main>
    </div>
  );
}

function Welcome({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center px-6 text-center animate-rise">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-2xl text-on-primary shadow-lg">
        ◈
      </div>
      <h1 className="text-2xl font-semibold tracking-tight">Find your next car</h1>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-muted">
        Describe what you want in plain language. I&apos;ll search OLX and StandVirtual, rate every
        listing for value, and surface the best picks — then you confirm the filters.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => onPick(ex)}
            className="rounded-full border border-border bg-surface px-3.5 py-1.5 text-sm text-foreground transition-colors hover:border-primary/50 hover:bg-surface-high"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ msg }: { msg: Msg }) {
  if (msg.role === "error") {
    return (
      <div className="flex items-start gap-2 rounded-xl border border-danger/40 bg-danger/10 px-3.5 py-2.5 text-sm text-danger animate-rise">
        <span className="mt-0.5 shrink-0">⚠</span>
        <span>{msg.content}</span>
      </div>
    );
  }
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex gap-2.5 animate-rise", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary text-sm text-on-primary">
          ◈
        </div>
      )}
      <div
        className={cn(
          "max-w-[80%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
          isUser
            ? "rounded-br-sm bg-primary-container text-on-primary-container"
            : "rounded-bl-sm border border-border bg-surface",
        )}
      >
        {msg.content}
      </div>
    </div>
  );
}
