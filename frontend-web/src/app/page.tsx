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
import { isGemini } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { Sidebar } from "@/components/sidebar";
import { FilterForm } from "@/components/filter-form";
import { ResultCard } from "@/components/result-card";
import { CompareTable } from "@/components/compare-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface Msg {
  role: Role;
  content: string;
}

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

      <main className="flex flex-1 flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
            {history.map((m, i) => (
              <MessageBubble key={i} msg={m} />
            ))}

            {busy && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-lg bg-surface px-3 py-2 text-sm text-muted">
                  <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
                  {pendingFilters ? "scraping olx + standvirtual, then rating…" : "working…"}
                </div>
              </div>
            )}

            {pendingFilters && (
              <FilterForm prefill={prefill} busy={busy} onSubmit={resume} />
            )}

            {selected.size >= 2 && (
              <CompareTable
                items={[...selected].sort((a, b) => a - b).map((i) => top[i])}
                onClear={() => setSelected(new Set())}
              />
            )}

            {top.length > 0 && (
              <section className="space-y-2">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
                  Top picks
                  {selected.size === 1 && (
                    <span className="ml-2 font-normal normal-case text-muted">
                      select one more to compare
                    </span>
                  )}
                </h2>
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
        </div>

        <div className="border-t border-border bg-surface-low p-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const p = input;
              setInput("");
              submit(p);
            }}
            className="mx-auto flex max-w-3xl gap-2"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask the agent — e.g. find me a bmw 320d under 10k"
              disabled={busy || !threadId}
            />
            <Button type="submit" disabled={busy || !threadId}>
              {busy ? "…" : "Send"}
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
}

function MessageBubble({ msg }: { msg: Msg }) {
  if (msg.role === "error") {
    return (
      <div className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
        {msg.content}
      </div>
    );
  }
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm",
          isUser ? "bg-primary-container text-on-primary-container" : "bg-surface",
        )}
      >
        {msg.content}
      </div>
    </div>
  );
}
