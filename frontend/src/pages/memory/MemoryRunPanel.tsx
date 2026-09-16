/**
 * 桌面同名件 1:1（复制自 DeepTutor 原仓 web/components/memory/MemoryRunPanel.tsx，942 行）。
 * 替换点：
 *  - 删除 "use client"；lucide → @ant-design/icons：AlertCircle→ExclamationCircleOutlined、
 *    Bot→RobotOutlined、CheckCircle2→CheckCircleOutlined、ChevronDown→DownOutlined、
 *    ChevronRight→RightOutlined、CircleSlash→MinusCircleOutlined、GitBranch→NodeIndexOutlined、
 *    Loader2→LoadingOutlined、Octagon→StopOutlined、PlayCircle→PlayCircleOutlined、
 *    RotateCcw→RollbackOutlined、ScanSearch→SearchOutlined、Send→SendOutlined、
 *    Sparkles→ThunderboltOutlined（先例）、Trash2→DeleteOutlined、Undo2→UndoOutlined；
 *  - react-i18next → 组内 zhT.t；i18n.language → 'zh'（登记，同 useMemoryRun）；
 *  - @/lib/llm-options → 组内 ./llm-options（fetch 直调 + client-cache 内联等价，登记）；
 *  - apiFetch(apiUrl(...)) → fetch('/api/v1/...')；window.confirm/window.alert 保留（中文逐字）；
 *  - Tailwind → 内联样式；hover:/dark: 伪类按先例省略并在此登记；amber/emerald/rose/red
 *    色系 → 对应 rgba/十六进制内联值。
 * 交互逐字未改。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DeleteOutlined,
  DownOutlined,
  ExclamationCircleOutlined,
  MinusCircleOutlined,
  NodeIndexOutlined,
  PlayCircleOutlined,
  RightOutlined,
  RollbackOutlined,
  RobotOutlined,
  SearchOutlined,
  SendOutlined,
  StopOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ThunderboltOutlined,
  UndoOutlined,
} from "@ant-design/icons";
import type { CSSProperties } from "react";

import {
  listLLMOptions,
  llmSelectionKey,
  sameLLMSelection,
  type LLMOption,
} from "./llm-options";
import type { LLMSelection } from "../tutor/admin/unified-ws";
import {
  useMemoryRun,
  type RunEvent,
  type RunMode,
} from "./useMemoryRun";
import { t } from "./zhT";

interface MemoryRunPanelProps {
  layer: "L2" | "L3";
  docKey: string;
  onRunComplete?: () => void;
  onDocUpdated?: () => void;
}

interface MemorySettingsDTO {
  update: { l2_budget: number; l3_budget: number };
  audit: { l2_budget: number; l3_budget: number };
  dedup: { iterations: number; auto_after_update: boolean };
}

const MODE_META: { key: RunMode; icon: typeof RobotOutlined; tKey: string }[] = [
  { key: "update", icon: ThunderboltOutlined, tKey: "Update memory" },
  { key: "audit", icon: SearchOutlined, tKey: "Audit memory" },
  { key: "dedup", icon: NodeIndexOutlined, tKey: "Dedup" },
];

const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";
const CARD = "var(--card, #ffffff)";
const MUTED = "var(--muted, #f5f5f5)";
const PRIMARY = "var(--primary, #1677ff)";
const PRIMARY_FG = "var(--primary-foreground, #ffffff)";
const BG = "var(--background, #ffffff)";

export function MemoryRunPanel({
  layer,
  docKey,
  onRunComplete,
  onDocUpdated,
}: MemoryRunPanelProps) {
  const { run, events, status, error, isRunning, start, cancel, undo, clear } =
    useMemoryRun(layer, docKey);

  const [mode, setMode] = useState<RunMode>("update");
  // Per-mode overrides keep typed values stable while the user flips between
  // modes — each mode has its own input value, defaulting to the settings
  // value when no override exists. Avoids setState-in-effect entirely.
  const [overrides, setOverrides] = useState<Record<RunMode, number | null>>({
    update: null,
    audit: null,
    dedup: null,
  });
  const budgetOverride = mode === "dedup" ? null : overrides[mode];
  const iterationsOverride = mode === "dedup" ? overrides.dedup : null;
  const setBudgetOverride = useCallback(
    (v: number | null) => setOverrides((prev) => ({ ...prev, [mode]: v })),
    [mode],
  );
  const setIterationsOverride = useCallback(
    (v: number | null) => setOverrides((prev) => ({ ...prev, dedup: v })),
    [],
  );
  const [selection, setSelection] = useState<LLMSelection | null>(null);
  const [activeDefault, setActiveDefault] = useState<LLMSelection | null>(null);
  const [modelOptions, setModelOptions] = useState<LLMOption[]>([]);
  const [modelLoading, setModelLoading] = useState(true);
  const [modelError, setModelError] = useState(false);
  const [settings, setSettings] = useState<MemorySettingsDTO | null>(null);

  // Load LLM options + memory settings once.
  useEffect(() => {
    setModelLoading(true);
    void (async () => {
      try {
        const data = await listLLMOptions();
        setModelOptions(data.options);
        setActiveDefault(data.active);
        setModelError(false);
      } catch {
        setModelOptions([]);
        setModelError(true);
      } finally {
        setModelLoading(false);
      }
    })();
    void (async () => {
      const res = await fetch("/api/v1/memory/settings");
      const data = (await res.json()) as MemorySettingsDTO;
      setSettings(data);
    })();
  }, []);

  const defaultBudget = useMemo(() => {
    if (!settings) return null;
    if (mode === "update") {
      return layer === "L2"
        ? settings.update.l2_budget
        : settings.update.l3_budget;
    }
    if (mode === "audit") {
      return layer === "L2"
        ? settings.audit.l2_budget
        : settings.audit.l3_budget;
    }
    return null;
  }, [settings, mode, layer]);
  const defaultIterations = settings?.dedup.iterations ?? null;
  const budget = budgetOverride ?? defaultBudget ?? ("" as const);
  const iterations = iterationsOverride ?? defaultIterations ?? ("" as const);

  const effectiveSelection = useMemo(
    () => selection ?? activeDefault ?? null,
    [selection, activeDefault],
  );
  const handleRun = useCallback(() => {
    if (isRunning) return;
    const llmSelection = effectiveSelection
      ? {
          profile_id: effectiveSelection.profile_id,
          model_id: effectiveSelection.model_id,
        }
      : null;
    if (mode === "dedup") {
      void start({
        mode,
        iterations: typeof iterations === "number" ? iterations : undefined,
        llmSelection,
        language: "zh",
      });
    } else {
      void start({
        mode,
        budget: typeof budget === "number" ? budget : undefined,
        llmSelection,
        language: "zh",
      });
    }
  }, [
    isRunning,
    mode,
    iterations,
    budget,
    effectiveSelection,
    start,
  ]);

  // Notify parent when a run finishes (success or otherwise) so the doc
  // preview can refresh.
  const lastCompleted = useRef<string | null>(null);
  useEffect(() => {
    if (!run || isRunning) return;
    if (
      run.status === "done" ||
      run.status === "cancelled" ||
      run.status === "error"
    ) {
      if (lastCompleted.current !== run.id) {
        lastCompleted.current = run.id;
        onRunComplete?.();
      }
    }
  }, [run, isRunning, onRunComplete]);

  const lastDocEvent = useRef<number | null>(null);
  useEffect(() => {
    if (!onDocUpdated) return;
    const latest = [...events]
      .reverse()
      .find(
        (ev) =>
          ev.payload.stage === "doc_updated" ||
          ev.payload.stage === "undo_applied",
      );
    if (!latest || lastDocEvent.current === latest.seq) return;
    lastDocEvent.current = latest.seq;
    onDocUpdated();
  }, [events, onDocUpdated]);

  const undoDepth = useMemo(() => {
    let depth = run?.undo_count ?? 0;
    for (const ev of events) {
      const value = ev.payload.undo_depth;
      if (
        (ev.payload.stage === "doc_updated" ||
          ev.payload.stage === "undo_applied") &&
        typeof value === "number"
      ) {
        depth = value;
      }
    }
    return depth;
  }, [events, run?.undo_count]);

  const handleUndo = useCallback(() => {
    if (isRunning || undoDepth <= 0) return;
    void undo();
  }, [isRunning, undo, undoDepth]);

  const handleReset = useCallback(async () => {
    if (isRunning) return;
    const ok =
      typeof window !== "undefined" &&
      window.confirm(
        t(
          "Reset will delete the current memory file AND its seen-id state. The next Update will re-ingest every L1 entity from scratch. Continue?",
        ),
      );
    if (!ok) return;
    try {
      const res = await fetch(
        `/api/v1/memory/doc/${layer}/${encodeURIComponent(docKey)}/reset`,
        { method: "POST" },
      );
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(
          detail || t("reset failed: {{status}}", { status: res.status }),
        );
      }
      // Clear local run trace + tell the parent workbench to re-fetch the
      // (now empty) doc, line view, and overview badge.
      clear();
      onDocUpdated?.();
    } catch (e) {
      if (typeof window !== "undefined") {
        window.alert(
          t("Reset failed: {{msg}}", {
            msg: e instanceof Error ? e.message : t("unknown error"),
          }),
        );
      }
    }
  }, [isRunning, layer, docKey, clear, onDocUpdated]);

  const turns = useMemo(() => groupByTurn(events), [events]);

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        minHeight: 0,
        flexDirection: "column",
        borderRadius: 16,
        border: `1px solid ${BORDER}`,
        background: CARD,
        boxSizing: "border-box",
      }}
    >
      {/* Header */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          borderBottom: `1px solid ${BORDER}`,
          padding: "8px 12px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 12.5,
            fontWeight: 600,
            color: FG,
          }}
        >
          <RobotOutlined style={{ fontSize: 14, color: MUTED_FG }} />
          {t("LLM workspace")}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {run && events.length > 0 && (
            <>
              <button
                type="button"
                onClick={handleUndo}
                disabled={isRunning || undoDepth <= 0}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  borderRadius: 6,
                  padding: "2px 6px",
                  fontSize: 11,
                  color: MUTED_FG,
                  border: "none",
                  background: "transparent",
                  cursor: isRunning || undoDepth <= 0 ? "not-allowed" : "pointer",
                  opacity: isRunning || undoDepth <= 0 ? 0.4 : 1,
                }}
                title={t("Undo last memory edit")}
              >
                <UndoOutlined style={{ fontSize: 12 }} />
                {undoDepth > 0 && <span>{undoDepth}</span>}
              </button>
              <button
                type="button"
                onClick={clear}
                disabled={isRunning}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  borderRadius: 6,
                  padding: "2px 6px",
                  fontSize: 11,
                  color: MUTED_FG,
                  border: "none",
                  background: "transparent",
                  cursor: isRunning ? "not-allowed" : "pointer",
                  opacity: isRunning ? 0.4 : 1,
                }}
                title={t("Clear trace")}
              >
                <DeleteOutlined style={{ fontSize: 12 }} />
              </button>
            </>
          )}
          <button
            type="button"
            onClick={() => void handleReset()}
            disabled={isRunning}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              borderRadius: 6,
              border: "1px solid rgba(245,158,11,0.4)",
              background: "rgba(245,158,11,0.1)",
              padding: "2px 8px",
              fontSize: 11,
              fontWeight: 500,
              color: "#b45309",
              cursor: isRunning ? "not-allowed" : "pointer",
              opacity: isRunning ? 0.4 : 1,
            }}
            title={t("Reset memory (delete md + seen-id state)")}
          >
            <RollbackOutlined style={{ fontSize: 12 }} />
            <span>{t("Reset")}</span>
          </button>
        </div>
      </header>

      {/* Composer — two evenly-distributed rows pinned at the top */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
          borderBottom: `1px solid ${BORDER}`,
          background: "color-mix(in srgb, var(--background, #ffffff) 40%, transparent)",
          padding: "10px 12px",
        }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 6 }}>
          {MODE_META.map(({ key, icon: Icon, tKey }) => (
            <button
              key={key}
              type="button"
              disabled={isRunning}
              onClick={() => setMode(key)}
              style={{
                display: "inline-flex",
                minWidth: 0,
                alignItems: "center",
                justifyContent: "center",
                gap: 4,
                borderRadius: 999,
                border: `1px solid ${BORDER}`,
                padding: "4px 8px",
                fontSize: 11.5,
                cursor: isRunning ? "not-allowed" : "pointer",
                opacity: isRunning ? 0.5 : 1,
                background: mode === key ? MUTED : BG,
                color: mode === key ? FG : MUTED_FG,
              }}
            >
              <Icon style={{ fontSize: 12, flexShrink: 0 }} />
              <span
                style={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {t(tKey)}
              </span>
            </button>
          ))}
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr) auto",
            alignItems: "center",
            gap: 6,
          }}
        >
          {mode === "dedup" ? (
            <NumberInput
              value={iterations}
              setValue={(v) => setIterationsOverride(v === "" ? null : v)}
              label={t("Iter")}
              min={1}
              max={20}
              disabled={isRunning}
              fullWidth
            />
          ) : (
            <NumberInput
              value={budget}
              setValue={(v) => setBudgetOverride(v === "" ? null : v)}
              label={t("Budget")}
              min={1}
              max={200}
              disabled={isRunning}
              fullWidth
            />
          )}
          <ModelPill
            options={modelOptions}
            value={selection ?? activeDefault}
            loading={modelLoading}
            error={modelError}
            disabled={isRunning}
            onChange={(next) => setSelection(next)}
          />
          {isRunning ? (
            <button
              type="button"
              onClick={() => void cancel()}
              style={{
                display: "inline-flex",
                height: 28,
                width: 36,
                alignItems: "center",
                justifyContent: "center",
                borderRadius: 999,
                background: MUTED,
                color: FG,
                border: "none",
                cursor: "pointer",
              }}
              title={t("Cancel")}
            >
              <StopOutlined style={{ fontSize: 14 }} />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleRun}
              style={{
                display: "inline-flex",
                height: 28,
                width: 36,
                alignItems: "center",
                justifyContent: "center",
                borderRadius: 999,
                background: PRIMARY,
                color: PRIMARY_FG,
                border: "none",
                cursor: "pointer",
              }}
              title={t("Run")}
            >
              <SendOutlined style={{ fontSize: 14 }} />
            </button>
          )}
        </div>
      </div>

      {/* Stream */}
      <div style={{ minHeight: 0, flex: 1, overflowY: "auto", padding: "12px 12px" }}>
        {events.length === 0 && status === "idle" ? (
          <EmptyTrace />
        ) : (
          <ol style={{ display: "flex", flexDirection: "column", gap: 8, listStyle: "none", margin: 0, padding: 0 }}>
            {turns.map((turn) => (
              <TurnCard key={`${turn.kind}-${turn.id}`} turn={turn} />
            ))}
            {isRunning && (
              <li
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  borderRadius: 6,
                  background: "color-mix(in srgb, var(--muted, #f5f5f5) 40%, transparent)",
                  padding: "6px 10px",
                  fontSize: 11.5,
                  color: MUTED_FG,
                  listStyle: "none",
                }}
              >
                <LoadingOutlined style={{ fontSize: 12 }} />
                {t("Working…")}
              </li>
            )}
            {error && (
              <li
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 8,
                  borderRadius: 6,
                  border: "1px solid rgba(239,68,68,0.3)",
                  background: "rgba(239,68,68,0.05)",
                  padding: "6px 10px",
                  fontSize: 11.5,
                  color: "#ef4444",
                  listStyle: "none",
                }}
              >
                <ExclamationCircleOutlined
                  style={{ marginTop: 2, fontSize: 14, flexShrink: 0 }}
                />
                {error}
              </li>
            )}
          </ol>
        )}
      </div>
    </div>
  );
}

// ── Trace pieces ─────────────────────────────────────────────────────

type Turn =
  | { kind: "system"; id: string; ts: string; payload: RunEvent["payload"] }
  | {
      kind: "llm";
      id: string;
      ts: string;
      turn: number;
      chunkIndex: number | null;
      system_prompt: string;
      user_prompt: string;
      response: string;
      error: string | null;
      label: string | null;
    };

function groupByTurn(events: RunEvent[]): Turn[] {
  const out: Turn[] = [];
  const pending: Record<string, Turn & { kind: "llm" }> = {};
  for (const ev of events) {
    const p = ev.payload as Record<string, unknown>;
    const stage = String(p.stage || "");
    if (stage === "llm_io_start") {
      const turn = typeof p.turn === "number" ? p.turn : 0;
      const chunkIndex =
        typeof p.chunk_index === "number" ? (p.chunk_index as number) : null;
      const key = `${turn}:${chunkIndex}:${ev.seq}`;
      const card: Turn & { kind: "llm" } = {
        kind: "llm",
        id: key,
        ts: ev.ts,
        turn,
        chunkIndex,
        system_prompt: String(p.system_prompt || ""),
        user_prompt: String(p.user_prompt || ""),
        response: "",
        error: null,
        label: typeof p.label === "string" ? p.label : null,
      };
      pending[`${turn}:${chunkIndex}`] = card;
      out.push(card);
      continue;
    }
    if (stage === "llm_io_end") {
      const turn = typeof p.turn === "number" ? p.turn : 0;
      const chunkIndex =
        typeof p.chunk_index === "number" ? (p.chunk_index as number) : null;
      const card = pending[`${turn}:${chunkIndex}`];
      if (card) {
        card.response = String(p.response || "");
        card.error = typeof p.error === "string" ? p.error : null;
        delete pending[`${turn}:${chunkIndex}`];
      }
      continue;
    }
    if (stage === "llm_io_delta") {
      const turn = typeof p.turn === "number" ? p.turn : 0;
      const chunkIndex =
        typeof p.chunk_index === "number" ? (p.chunk_index as number) : null;
      const card = pending[`${turn}:${chunkIndex}`];
      if (card) {
        card.response += String(p.delta || "");
      }
      continue;
    }
    out.push({
      kind: "system",
      id: `sys-${ev.seq}`,
      ts: ev.ts,
      payload: ev.payload,
    });
  }
  return out;
}

function TurnCard({ turn }: { turn: Turn }) {
  if (turn.kind === "system") {
    return <SystemEventRow event={turn.payload} />;
  }
  return <LLMTurnCard turn={turn} />;
}

function SystemEventRow({
  event,
}: {
  event: RunEvent["payload"];
}) {
  const stage = String(event.stage || "");
  const display = systemEventDisplay(stage, event);
  if (!display) return null;
  const toneStyle: CSSProperties =
    display.tone === "ok"
      ? {
          border: "1px solid rgba(16,185,129,0.3)",
          background: "rgba(16,185,129,0.05)",
          color: "#047857",
        }
      : display.tone === "warn"
        ? {
            border: "1px solid rgba(245,158,11,0.3)",
            background: "rgba(245,158,11,0.05)",
            color: "#b45309",
          }
        : {
            background: "color-mix(in srgb, var(--muted, #f5f5f5) 40%, transparent)",
            color: MUTED_FG,
          };
  const Icon = display.icon;
  return (
    <li
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 8,
        borderRadius: 6,
        padding: "6px 8px",
        fontSize: 11.5,
        listStyle: "none",
        ...toneStyle,
      }}
    >
      <Icon style={{ marginTop: 2, fontSize: 14, flexShrink: 0 }} />
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            fontFamily: "monospace",
            fontSize: 10.5,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          {display.title}
        </div>
        {display.detail && (
          <div style={{ marginTop: 2, wordBreak: "break-word", lineHeight: 1.375 }}>
            {display.detail}
          </div>
        )}
      </div>
    </li>
  );
}

function systemEventDisplay(
  stage: string,
  event: RunEvent["payload"],
): {
  icon: typeof RobotOutlined;
  title: string;
  detail: string;
  tone: "ok" | "warn" | "muted";
} | null {
  const num = (k: string) =>
    typeof event[k] === "number" ? String(event[k]) : null;
  const str = (k: string) =>
    typeof event[k] === "string" ? String(event[k]) : null;
  switch (stage) {
    case "run_started":
      return {
        icon: PlayCircleOutlined,
        title: t("Run started"),
        detail: `${event.mode}`,
        tone: "muted",
      };
    case "trace_loaded": {
      const total = num("total") ?? num("total_l2_entries");
      const fresh = num("new") ?? num("new_l2_entries");
      const parts = [
        total ? `total=${total}` : null,
        fresh ? `new=${fresh}` : null,
      ].filter(Boolean);
      return {
        icon: PlayCircleOutlined,
        title: t("Traces loaded"),
        detail: parts.join(" · "),
        tone: "muted",
      };
    }
    case "chunked":
      return {
        icon: PlayCircleOutlined,
        title: t("Chunked"),
        detail: [
          num("chunks") ? `chunks=${num("chunks")}` : null,
          num("budget") ? `budget=${num("budget")}` : null,
          num("chars") ? `chars=${num("chars")}` : null,
        ]
          .filter(Boolean)
          .join(" · "),
        tone: "muted",
      };
    case "progress": {
      const turn = num("turn");
      const total = num("total");
      return {
        icon: PlayCircleOutlined,
        title: t("Progress"),
        detail: turn && total ? `${turn}/${total}` : "",
        tone: "muted",
      };
    }
    case "facts_extracted":
      return {
        icon: CheckCircleOutlined,
        title: t("Facts extracted"),
        detail: [
          num("kept") ? `kept=${num("kept")}` : null,
          num("added") ? `added=${num("added")}` : null,
        ]
          .filter(Boolean)
          .join(" · "),
        tone: "ok",
      };
    case "refs_dropped":
      return {
        icon: MinusCircleOutlined,
        title: t("Ref dropped"),
        detail: `${str("reason") || "?"} :: ${str("text") || ""}`,
        tone: "warn",
      };
    case "op_applied":
      return {
        icon: CheckCircleOutlined,
        title: t("Edit applied"),
        detail: [str("op"), str("detail")].filter(Boolean).join(" · "),
        tone: "ok",
      };
    case "op_rejected":
      return {
        icon: MinusCircleOutlined,
        title: t("Edit rejected"),
        detail: [str("op"), str("detail")].filter(Boolean).join(" · "),
        tone: "warn",
      };
    case "doc_updated":
      return {
        icon: CheckCircleOutlined,
        title: t("Markdown updated"),
        detail: [
          str("action"),
          num("turn") ? `turn=${num("turn")}` : null,
          num("undo_depth") ? `undo=${num("undo_depth")}` : null,
        ]
          .filter(Boolean)
          .join(" · "),
        tone: "ok",
      };
    case "undo_applied":
      return {
        icon: UndoOutlined,
        title: t("Undo applied"),
        detail: [
          str("action"),
          num("undo_depth") ? `remaining=${num("undo_depth")}` : "remaining=0",
        ]
          .filter(Boolean)
          .join(" · "),
        tone: "warn",
      };
    case "done":
      return {
        icon: CheckCircleOutlined,
        title: t("Done"),
        detail: [
          num("facts_added") ? `+${num("facts_added")} facts` : null,
          num("edits_applied") ? `+${num("edits_applied")} edits` : null,
          num("refs_dropped") ? `dropped=${num("refs_dropped")}` : null,
        ]
          .filter(Boolean)
          .join(" · "),
        tone: "ok",
      };
    case "run_ended":
      return {
        icon: CheckCircleOutlined,
        title: t("Run ended"),
        detail: str("status") || "",
        tone: "muted",
      };
    case "cancelled":
      return {
        icon: MinusCircleOutlined,
        title: t("Cancelled"),
        detail: "",
        tone: "warn",
      };
    case "error":
      return {
        icon: ExclamationCircleOutlined,
        title: t("Error"),
        detail: str("message") || "",
        tone: "warn",
      };
    default:
      return null;
  }
}

function LLMTurnCard({
  turn,
}: {
  turn: Extract<Turn, { kind: "llm" }>;
}) {
  const [systemOpen, setSystemOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const tag =
    turn.chunkIndex !== null
      ? `t${turn.turn} · chunk ${turn.chunkIndex + 1}`
      : `t${turn.turn}`;
  return (
    <li
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 6,
        borderRadius: 6,
        border: `1px solid ${BORDER}`,
        background: BG,
        padding: "8px 10px",
        listStyle: "none",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 10.5,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          color: MUTED_FG,
        }}
      >
        <RobotOutlined style={{ fontSize: 12 }} />
        <span>{turn.label || "llm"}</span>
        <span>·</span>
        <span>{tag}</span>
      </div>

      <Disclosure
        open={systemOpen}
        setOpen={setSystemOpen}
        label={t("System prompt")}
        body={turn.system_prompt}
      />
      <Disclosure
        open={userOpen}
        setOpen={setUserOpen}
        label={t("User prompt")}
        body={turn.user_prompt}
      />

      <div style={{ fontSize: 12, color: FG }}>
        {turn.response ? (
          <pre
            style={{
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              fontFamily: "monospace",
              fontSize: 11.5,
              lineHeight: 1.625,
              margin: 0,
            }}
          >
            {turn.response}
          </pre>
        ) : turn.error ? (
          <div
            style={{
              borderRadius: 4,
              border: "1px solid rgba(239,68,68,0.3)",
              background: "rgba(239,68,68,0.05)",
              padding: "4px 8px",
              fontSize: 11,
              color: "#ef4444",
            }}
          >
            {turn.error}
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 11.5,
              color: MUTED_FG,
            }}
          >
            <LoadingOutlined style={{ fontSize: 12 }} />
            {t("Streaming…")}
          </div>
        )}
      </div>
    </li>
  );
}

function Disclosure({
  open,
  setOpen,
  label,
  body,
}: {
  open: boolean;
  setOpen: (v: boolean) => void;
  label: string;
  body: string;
}) {
  if (!body) return null;
  return (
    <div style={{ fontSize: 11, color: MUTED_FG }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
          borderRadius: 4,
          padding: "2px 4px",
          border: "none",
          background: "transparent",
          cursor: "pointer",
          color: "inherit",
        }}
      >
        {open ? (
          <DownOutlined style={{ fontSize: 12 }} />
        ) : (
          <RightOutlined style={{ fontSize: 12 }} />
        )}
        {label}
        <span style={{ opacity: 0.6 }}>·&nbsp;{body.length}</span>
      </button>
      {open && (
        <pre
          style={{
            marginTop: 4,
            maxHeight: 240,
            overflowY: "auto",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            borderRadius: 4,
            background: "color-mix(in srgb, var(--muted, #f5f5f5) 40%, transparent)",
            padding: "6px 8px",
            fontFamily: "monospace",
            fontSize: 10.5,
            color: FG,
            margin: "4px 0 0",
          }}
        >
          {body}
        </pre>
      )}
    </div>
  );
}

// ── Composer pieces ─────────────────────────────────────────────────

function NumberInput({
  value,
  setValue,
  label,
  min,
  max,
  disabled,
  fullWidth = false,
}: {
  value: number | "";
  setValue: (n: number | "") => void;
  label: string;
  min: number;
  max: number;
  disabled: boolean;
  fullWidth?: boolean;
}) {
  return (
    <label
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 4,
        borderRadius: 999,
        border: `1px solid ${BORDER}`,
        background: BG,
        padding: "4px 10px",
        fontSize: 11.5,
        color: MUTED_FG,
        width: fullWidth ? "100%" : undefined,
      }}
    >
      <span>{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        disabled={disabled}
        onChange={(e) => {
          const v = e.target.value;
          if (v === "") return setValue("");
          const n = parseInt(v, 10);
          if (!Number.isNaN(n)) setValue(Math.max(min, Math.min(max, n)));
        }}
        style={{
          width: 56,
          background: "transparent",
          textAlign: "right",
          fontSize: 11.5,
          color: FG,
          outline: "none",
          border: "none",
          padding: 0,
        }}
      />
    </label>
  );
}

interface ModelPillProps {
  options: LLMOption[];
  value: LLMSelection | null;
  loading: boolean;
  error: boolean;
  disabled: boolean;
  onChange: (next: LLMSelection | null) => void;
}

function ModelPill({
  options,
  value,
  loading,
  error,
  disabled,
  onChange,
}: ModelPillProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const selectedOption = useMemo(
    () => options.find((o) => sameLLMSelection(o, value)) ?? null,
    [options, value],
  );
  const label = loading
    ? t("Loading models")
    : error
      ? t("Models unavailable")
      : selectedOption?.model_name || t("Default model");
  const inactive = disabled || loading || error || options.length === 0;

  return (
    <div ref={rootRef} style={{ position: "relative", width: "100%", minWidth: 0 }}>
      <button
        type="button"
        disabled={inactive}
        onClick={() => setOpen(!open)}
        title={
          selectedOption
            ? `${selectedOption.profile_name} | ${selectedOption.provider}`
            : label
        }
        style={{
          display: "flex",
          width: "100%",
          minWidth: 0,
          alignItems: "center",
          gap: 4,
          borderRadius: 999,
          border: `1px solid ${open ? "color-mix(in srgb, var(--primary, #1677ff) 40%, transparent)" : BORDER}`,
          background: BG,
          padding: "4px 10px",
          fontSize: 11.5,
          color: FG,
          cursor: inactive ? "not-allowed" : "pointer",
          opacity: inactive ? 0.5 : 1,
        }}
      >
        <RobotOutlined
          style={{ fontSize: 12, flexShrink: 0, color: MUTED_FG }}
        />
        <span
          style={{
            flex: 1,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            textAlign: "left",
          }}
        >
          {label}
        </span>
        <DownOutlined style={{ fontSize: 12, flexShrink: 0, color: MUTED_FG }} />
      </button>

      {open && !inactive && (
        <div
          style={{
            position: "absolute",
            right: 0,
            top: "100%",
            zIndex: 30,
            marginTop: 4,
            maxHeight: 288,
            width: "min(320px, calc(100vw - 32px))",
            overflowY: "auto",
            borderRadius: 12,
            border: `1px solid ${BORDER}`,
            background: CARD,
            padding: 4,
            boxShadow: "0 10px 15px -3px rgba(0,0,0,0.1)",
          }}
        >
          {options.map((opt) => {
            const active = sameLLMSelection(opt, value);
            return (
              <button
                key={llmSelectionKey(opt)}
                type="button"
                onClick={() => {
                  onChange({
                    profile_id: opt.profile_id,
                    model_id: opt.model_id,
                  });
                  setOpen(false);
                }}
                style={{
                  display: "flex",
                  width: "100%",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 8,
                  borderRadius: 6,
                  padding: "6px 8px",
                  textAlign: "left",
                  fontSize: 11.5,
                  border: "none",
                  cursor: "pointer",
                  background: active ? MUTED : "transparent",
                  color: active ? FG : MUTED_FG,
                }}
              >
                <span
                  style={{
                    display: "flex",
                    minWidth: 0,
                    flex: 1,
                    alignItems: "baseline",
                    gap: 8,
                  }}
                >
                  <span
                    style={{
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      color: FG,
                    }}
                  >
                    {opt.model_name}
                  </span>
                  <span style={{ flexShrink: 0, fontSize: 10, opacity: 0.6 }}>
                    {opt.provider}
                  </span>
                </span>
                {opt.is_active_default && (
                  <span
                    style={{
                      flexShrink: 0,
                      borderRadius: 4,
                      background: "color-mix(in srgb, var(--primary, #1677ff) 10%, transparent)",
                      padding: "2px 4px",
                      fontSize: 9.5,
                      textTransform: "uppercase",
                      color: PRIMARY,
                    }}
                  >
                    {t("default")}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function EmptyTrace() {
  return (
    <div
      style={{
        display: "grid",
        height: "100%",
        placeItems: "center",
        textAlign: "center",
        fontSize: 12.5,
        color: MUTED_FG,
      }}
    >
      <div style={{ maxWidth: 320, display: "flex", flexDirection: "column", gap: 6 }}>
        <RobotOutlined style={{ margin: "0 auto", fontSize: 24, opacity: 0.6 }} />
        <p style={{ margin: 0 }}>
          {t(
            "Pick a mode and click Run. The LLM trace — system prompt, user prompt, response — appears here, turn by turn.",
          )}
        </p>
      </div>
    </div>
  );
}

export default MemoryRunPanel;
