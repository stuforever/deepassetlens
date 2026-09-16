/**
 * 桌面同名件 1:1（复制自 DeepTutor 原仓 web/components/memory/useMemoryRun.ts，389 行）。
 * 替换点：
 *  - 删除 "use client"；i18next 直用（i18n.t）→ 组内 zhT.t 中文直出（登记）；
 *  - start 缺省 language 原为 i18n.language || "en" → tupu 无 i18n，改为 "zh"（登记）；
 *  - apiFetch(apiUrl(...)) → fetch('/api/v1/...')（同源 cookie 等价，先例）；
 *  - LLMSelection 类型 → 批8已移植 ../tutor/admin/unified-ws.ts（同源同名）。
 * SSE 流读取、localStorage 运行恢复（key "dt:memory:active-run:{layer}:{key}"）、
 * AbortController 语义逐字未改。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { LLMSelection } from "../tutor/admin/unified-ws";
import { t } from "./zhT";

export type RunMode = "update" | "audit" | "dedup";
export type RunStatus = "queued" | "running" | "cancelled" | "done" | "error";

export interface RunHandle {
  id: string;
  layer: "L2" | "L3";
  key: string;
  mode: RunMode;
  status: RunStatus;
  started_at: string;
  ended_at: string | null;
  error: string | null;
  event_count: number;
  undo_count: number;
}

export interface RunEventPayload {
  stage: string;
  [key: string]: unknown;
}

export interface RunEvent {
  seq: number;
  ts: string;
  payload: RunEventPayload;
}

export interface StartArgs {
  mode: RunMode;
  budget?: number;
  iterations?: number;
  llmSelection?: LLMSelection | null;
  language?: string;
}

interface State {
  run: RunHandle | null;
  events: RunEvent[];
  status: RunStatus | "idle";
  error: string | null;
  reconnecting: boolean;
}

// One row per `(layer, key)` survives a page refresh by persisting the
// active run_id in localStorage. The hook reads this on mount and tries
// to re-attach to a still-running run on the server.
const STORAGE_PREFIX = "dt:memory:active-run";

function storageKey(layer: string, key: string) {
  return `${STORAGE_PREFIX}:${layer}:${key}`;
}

function readPersistedRunId(layer: string, key: string): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(storageKey(layer, key));
}

function writePersistedRunId(layer: string, key: string, runId: string | null) {
  if (typeof window === "undefined") return;
  if (runId) {
    window.localStorage.setItem(storageKey(layer, key), runId);
  } else {
    window.localStorage.removeItem(storageKey(layer, key));
  }
}

export function useMemoryRun(layer: "L2" | "L3", key: string) {
  const [state, setState] = useState<State>({
    run: null,
    events: [],
    status: "idle",
    error: null,
    reconnecting: false,
  });
  const abortRef = useRef<AbortController | null>(null);
  const cursorRef = useRef<number>(0);
  // Track if we've initialised for this (layer, key) so a parent re-render
  // doesn't trigger duplicate reconnects.
  const initialisedFor = useRef<string>("");

  const close = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  // Reset when the doc changes; re-attach to that doc's persisted run if any.
  useEffect(() => {
    const tag = `${layer}:${key}`;
    if (initialisedFor.current === tag) return;
    initialisedFor.current = tag;
    close();
    cursorRef.current = 0;
    setState({
      run: null,
      events: [],
      status: "idle",
      error: null,
      reconnecting: false,
    });

    void (async () => {
      const persistedId = readPersistedRunId(layer, key);
      let runId: string | null = persistedId;
      // Verify the persisted run exists; otherwise see if the server thinks
      // this doc has an active run.
      try {
        if (runId) {
          const res = await fetch(`/api/v1/memory/runs/${runId}`);
          if (!res.ok) runId = null;
        }
        if (!runId) {
          const res = await fetch(
            `/api/v1/memory/runs?layer=${layer}&key=${encodeURIComponent(key)}`,
          );
          if (res.ok) {
            const data = (await res.json()) as { runs: RunHandle[] };
            const active = data.runs.find(
              (r) => r.status === "running" || r.status === "queued",
            );
            if (active) {
              runId = active.id;
              writePersistedRunId(layer, key, runId);
            }
          }
        }
      } catch {
        // best-effort recovery — if the API is unreachable we'll just start
        // a new run when the user clicks Run.
      }
      if (runId) {
        await attach(runId);
      }
    })();

    return () => {
      close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layer, key]);

  const attach = useCallback(
    async (runId: string, since = 0): Promise<void> => {
      // Pull the run handle first.
      try {
        const res = await fetch(`/api/v1/memory/runs/${runId}`);
        if (!res.ok) {
          writePersistedRunId(layer, key, null);
          return;
        }
        const run = (await res.json()) as RunHandle;
        setState((s) => ({
          ...s,
          run,
          status: run.status,
          reconnecting: false,
        }));
      } catch {
        return;
      }

      abortRef.current?.abort();
      const ctl = new AbortController();
      abortRef.current = ctl;
      cursorRef.current = since;

      try {
        const res = await fetch(`/api/v1/memory/runs/${runId}/events?since=${since}`, {
          signal: ctl.signal,
          cache: "no-store",
        });
        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (reader) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let nl = buffer.indexOf("\n\n");
          while (nl !== -1) {
            const chunk = buffer.slice(0, nl);
            buffer = buffer.slice(nl + 2);
            const line = chunk
              .split("\n")
              .find((l) => l.startsWith("data:"))
              ?.replace(/^data:\s?/, "");
            if (line) {
              try {
                const parsed = JSON.parse(line);
                const seq =
                  typeof parsed.seq === "number"
                    ? parsed.seq
                    : cursorRef.current;
                const ts =
                  typeof parsed.ts === "string"
                    ? parsed.ts
                    : new Date().toISOString();
                const payload = Object.assign({}, parsed);
                delete payload.seq;
                delete payload.ts;
                cursorRef.current = seq + 1;
                setState((s) => {
                  const undoDepth =
                    typeof payload.undo_depth === "number"
                      ? payload.undo_depth
                      : null;
                  const endedStatus =
                    payload.stage === "run_ended" &&
                    typeof payload.status === "string"
                      ? (payload.status as RunStatus)
                      : null;
                  return {
                    ...s,
                    status: endedStatus ?? s.status,
                    run: s.run
                      ? {
                          ...s.run,
                          status: endedStatus ?? s.run.status,
                          undo_count: undoDepth ?? s.run.undo_count,
                        }
                      : s.run,
                    events: s.events.some((ev) => ev.seq === seq)
                      ? s.events
                      : [
                          ...s.events,
                          { seq, ts, payload: payload as RunEventPayload },
                        ],
                  };
                });
                if (
                  payload.stage === "run_ended" &&
                  typeof payload.status === "string"
                ) {
                  writePersistedRunId(layer, key, null);
                }
              } catch {
                // ignore malformed chunks
              }
            }
            nl = buffer.indexOf("\n\n");
          }
        }
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        setState((s) => ({
          ...s,
          error: e instanceof Error ? e.message : t("stream failed"),
        }));
      }
    },
    [layer, key],
  );

  const start = useCallback(
    async (args: StartArgs): Promise<void> => {
      setState((s) => ({ ...s, error: null, events: [], status: "queued" }));
      try {
        const res = await fetch("/api/v1/memory/runs/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            layer,
            key,
            mode: args.mode,
            budget: args.budget ?? null,
            iterations: args.iterations ?? null,
            llm_selection: args.llmSelection ?? null,
            language: args.language ?? "zh",
          }),
        });
        if (!res.ok) {
          const detail = await res.text();
          throw new Error(
            detail ||
              t("start failed: {{status}}", { status: res.status }),
          );
        }
        const run = (await res.json()) as RunHandle;
        writePersistedRunId(layer, key, run.id);
        await attach(run.id, 0);
      } catch (e) {
        setState((s) => ({
          ...s,
          status: "error",
          error: e instanceof Error ? e.message : t("start failed"),
        }));
      }
    },
    [layer, key, attach],
  );

  const cancel = useCallback(async (): Promise<void> => {
    if (!state.run) return;
    try {
      await fetch(`/api/v1/memory/runs/${state.run.id}/cancel`, {
        method: "POST",
      });
    } catch {
      // ignore: the server may already have terminated naturally.
    }
  }, [state.run]);

  const undo = useCallback(async (): Promise<boolean> => {
    if (!state.run) return false;
    try {
      const res = await fetch(`/api/v1/memory/runs/${state.run.id}/undo`, {
        method: "POST",
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(
          detail || t("undo failed: {{status}}", { status: res.status }),
        );
      }
      const data = (await res.json()) as {
        undo_count?: number;
        event?: { seq: number; ts: string; [key: string]: unknown };
      };
      const ev = data.event;
      setState((s) => {
        const nextRun = s.run
          ? { ...s.run, undo_count: data.undo_count ?? s.run.undo_count }
          : s.run;
        if (!ev || typeof ev.seq !== "number") return { ...s, run: nextRun };
        const payload = Object.assign({}, ev);
        delete (payload as Record<string, unknown>).seq;
        delete (payload as Record<string, unknown>).ts;
        const seq = ev.seq;
        const ts = ev.ts;
        return {
          ...s,
          run: nextRun,
          events: s.events.some((item) => item.seq === seq)
            ? s.events
            : [
                ...s.events,
                {
                  seq,
                  ts: typeof ts === "string" ? ts : new Date().toISOString(),
                  payload: payload as unknown as RunEventPayload,
                },
              ],
        };
      });
      return true;
    } catch (e) {
      setState((s) => ({
        ...s,
        error: e instanceof Error ? e.message : t("undo failed"),
      }));
      return false;
    }
  }, [state.run]);

  const clear = useCallback(() => {
    setState({
      run: null,
      events: [],
      status: "idle",
      error: null,
      reconnecting: false,
    });
    writePersistedRunId(layer, key, null);
    close();
  }, [layer, key, close]);

  const isRunning = useMemo(
    () => state.status === "queued" || state.status === "running",
    [state.status],
  );

  return {
    run: state.run,
    events: state.events,
    status: state.status,
    error: state.error,
    isRunning,
    start,
    cancel,
    undo,
    clear,
  };
}
