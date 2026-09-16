/**
 * 桌面同名件 1:1（复制自 DeepTutor 原仓 web/components/memory/MemorySection.tsx，1522 行）。
 * 随 MemoryL1Workbench 随行移植（其消费本文件 named 导出 L1View；default 导出 MemorySection
 * 一并保留，tupu 内暂无第二消费者——原仓 SkillsSection/notifications 仅注释提及，无真实 import）。
 * 替换点：
 *  - 删除 "use client"；next/dynamic(MarkdownRenderer) → 直接 import 批8 已移植的
 *    ../tutor/admin/MarkdownRenderer stub（props 契约兼容；stub 的 allowHtml/富渲染不生效，
 *    【降级登记】linkifyEntityRefs 的 #entity-锚点点击在本 stub 下无 <a id> 目标可跳，L1View
 *    侧 scrollIntoView 定位不受影响——anchor 渲染恢复点=Rich 渲染链并入时）；
 *  - next/link Link → 跨应用 deep-link（entityDeepLinkUrl 产物）保留原 URL 形状、渲染为原生
 *    <a href>（tupu 无 /space/notebooks、/book、/partners、/co-writer、/knowledge 对应路由，
 *    /home 存在；跳转语义登记：目标页缺失时落到 tupu 404 兜底路由）；
 *  - lucide → @ant-design/icons：Archive→ContainerOutlined、Bot→RobotOutlined、
 *    BookOpen→ReadOutlined、Brain→BulbOutlined（先例 MemoryPicker）、ClipboardList→
 *    SnippetsOutlined、ExternalLink→ExportOutlined、GitCommit→BranchesOutlined、
 *    Library→DatabaseOutlined、Loader2→LoadingOutlined、MessageSquare→MessageOutlined、
 *    NotebookPen→FormOutlined、Pencil/PenLine→EditOutlined、RefreshCw→ReloadOutlined、
 *    Save→SaveOutlined、X→CloseOutlined；
 *  - react-i18next → 组内 zhT.t 中文直出（i18n.language → 'zh'，登记）；
 *  - Tailwind → 内联样式；hover:/group-hover: 伪类按先例省略并在此登记；
 *    line-clamp-2 → WebkitLineClamp。
 * 交互逐字未改。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BranchesOutlined,
  BulbOutlined,
  CloseOutlined,
  ContainerOutlined,
  DatabaseOutlined,
  EditOutlined,
  ExportOutlined,
  FormOutlined,
  LoadingOutlined,
  MessageOutlined,
  ReadOutlined,
  ReloadOutlined,
  RobotOutlined,
  SaveOutlined,
  SnippetsOutlined,
} from "@ant-design/icons";
import type { CSSProperties } from "react";

import { t } from "./zhT";
import SpaceSectionHeader from "./SpaceSectionHeader";
import MarkdownRenderer from "../tutor/admin/MarkdownRenderer";

// ── Types ────────────────────────────────────────────────────────────

type Layer = "L2" | "L3";

type Surface =
  | "chat"
  | "notebook"
  | "quiz"
  | "kb"
  | "book"
  | "partner"
  | "cowriter";

const SURFACES: readonly Surface[] = [
  "chat",
  "notebook",
  "quiz",
  "kb",
  "book",
  "partner",
  "cowriter",
] as const;

type Tab = "L1" | "L2" | "L3";

interface Entity {
  id: string;
  label: string;
  ts: string;
  content: string;
  metadata: Record<string, unknown>;
  fingerprint: string;
}

interface SnapshotResponse {
  surface: Surface;
  entities: Entity[];
  last_refresh: string | null;
  pending_changes: ChangeEntryDTO[];
}

interface ChangeEntryDTO {
  ts: string;
  kind: "added" | "modified" | "removed";
  entity_id: string;
  label: string;
  prev_fingerprint: string | null;
  new_fingerprint: string | null;
}

interface ChangesResponse {
  surface: Surface;
  changes: ChangeEntryDTO[];
}

interface KbQueryDTO {
  id: string;
  ts: string;
  surface: Surface;
  kind: string;
  payload: Record<string, unknown>;
  session_id: string | null;
  turn_id: string | null;
}

interface KbQueriesResponse {
  surface: Surface;
  events: KbQueryDTO[];
}

interface DocOverview {
  layer: Layer;
  key: string;
  exists: boolean;
  updated_at: string | null;
  entry_count: number;
  backlog: number;
}

interface OverviewResponse {
  docs: DocOverview[];
  backups: string[];
}

interface StreamStage {
  stage: string;
  count?: number;
  delta?: string;
  ops?: unknown[];
  report?: { accepted: boolean; reason?: string; results?: unknown[] };
  message?: string;
  // Agentic-loop fields (tool_called / tool_observed / step_done / loop_summary)
  turn?: number;
  name?: string;
  args?: Record<string, unknown>;
  brief?: string;
  action?: string;
  turns_used?: number;
  tools_used?: Record<string, number>;
  ops_emitted?: number;
  summary?: string;
}

// ── Surface metadata + helpers ───────────────────────────────────────

interface SurfaceMeta {
  icon: typeof MessageOutlined;
  label: string;
}

const SURFACE_META: Record<Surface, SurfaceMeta> = {
  chat: { icon: MessageOutlined, label: "Chat" },
  notebook: { icon: FormOutlined, label: "Notebook" },
  quiz: { icon: SnippetsOutlined, label: "题库" },
  kb: { icon: ReadOutlined, label: "Knowledge base" },
  book: { icon: DatabaseOutlined, label: "Book" },
  partner: { icon: RobotOutlined, label: "Partner" },
  cowriter: { icon: EditOutlined, label: "Co-writer" },
};

const L3_LABELS: Record<string, string> = {
  recent: "近期总结",
  profile: "用户画像",
  scope: "知识 Scope",
  preferences: "偏好",
};

// Entity refs in L2/L3 docs are written as `<surface>:<entity_id>`.
// The id portion is intentionally permissive (notebook record_id, doc_id,
// book_id, bot name, session_id, "session:question" composites, kb_name).
const ENTITY_REF_RE =
  /\b(chat|notebook|quiz|kb|book|partner|cowriter):[A-Za-z0-9_.\-:]+/g;

function entityAnchorId(ref: string): string {
  // Anchor IDs can't contain ':' cleanly across CSS selectors — flatten
  // it. We never round-trip from anchor back to ref, so the encoding
  // can be lossy.
  return `entity-${ref.replace(/:/g, "__")}`;
}

function parseEntityAnchor(anchor: string): {
  surface: Surface;
  ref: string;
} | null {
  if (!anchor.startsWith("entity-")) return null;
  const body = anchor.slice("entity-".length);
  const sep = body.indexOf("__");
  if (sep <= 0) return null;
  const surface = body.slice(0, sep);
  const rest = body.slice(sep + 2).replace(/__/g, ":");
  if (!(SURFACES as readonly string[]).includes(surface)) return null;
  return { surface: surface as Surface, ref: `${surface}:${rest}` };
}

function linkifyEntityRefs(content: string): string {
  return content.replace(
    ENTITY_REF_RE,
    (ref) => `[${ref}](#${entityAnchorId(ref)})`,
  );
}

function labelFor(doc: DocOverview): string {
  if (doc.layer === "L2")
    return SURFACE_META[doc.key as Surface]?.label ?? doc.key;
  return L3_LABELS[doc.key] ?? doc.key;
}

function formatTimestamp(value: string | null, fallback: string): string {
  if (!value) return fallback;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function shorten(s: string, n: number): string {
  const trimmed = (s || "").replace(/\s+/g, " ").trim();
  return trimmed.length > n ? trimmed.slice(0, n - 1) + "…" : trimmed;
}

function asString(v: unknown): string {
  if (typeof v === "string") return v;
  if (typeof v === "number") return String(v);
  return "";
}

function entityDeepLinkUrl(surface: Surface, ent: Entity): string | null {
  const m = ent.metadata || {};
  switch (surface) {
    case "chat":
      return `/home/${encodeURIComponent(ent.id)}`;
    case "cowriter":
      return `/co-writer/${encodeURIComponent(ent.id)}`;
    case "notebook": {
      const nbId = asString(m.notebook_id);
      return nbId
        ? `/space/notebooks?notebook=${encodeURIComponent(nbId)}`
        : "/space/notebooks";
    }
    case "book":
      return `/book?book=${encodeURIComponent(ent.id)}`;
    case "partner": {
      // Partner entity.id is `partnerId:sessionKey`. Deep-link to the partner.
      const partnerId = asString(m.partner_id) || ent.id.split(":")[0];
      return partnerId
        ? `/partners/${encodeURIComponent(partnerId)}`
        : "/partners";
    }
    case "quiz": {
      // Quiz entity.id is `session:question`. Deep-link to the session.
      const sessionId = asString(m.session_id) || ent.id.split(":")[0];
      return sessionId
        ? `/?session=${encodeURIComponent(sessionId)}`
        : "/space/questions";
    }
    case "kb":
      return `/knowledge?kb=${encodeURIComponent(ent.id)}`;
  }
  return null;
}

// ── Main component ──────────────────────────────────────────────────

interface MemorySectionProps {
  forcedTab?: Tab; // when provided, hides the TabStrip and locks the active tab
  hideHeader?: boolean; // when true, skips the SpaceSectionHeader (parent page renders its own)
}

export function MemorySection({
  forcedTab,
  hideHeader = false,
}: MemorySectionProps = {}) {
  const [tab, setTab] = useState<Tab>(forcedTab ?? "L2");
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [selected, setSelected] = useState<{
    layer: Layer;
    key: string;
  } | null>(null);
  const [content, setContent] = useState("");
  const [editing, setEditing] = useState(false);
  const [editorValue, setEditorValue] = useState("");
  const [stream, setStream] = useState<StreamStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");
  const [l1Surface, setL1Surface] = useState<Surface>("notebook");
  const [l1FocusRef, setL1FocusRef] = useState<string | null>(null);
  const [dismissedBackup, setDismissedBackup] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setDismissedBackup(
      window.localStorage.getItem("dt:memory:banner-dismissed") || null,
    );
  }, []);

  const latestBackup = overview?.backups?.[overview.backups.length - 1] ?? null;
  const showArchivedBanner = !!latestBackup && latestBackup !== dismissedBackup;

  const dismissArchivedBanner = useCallback(() => {
    if (!latestBackup) return;
    if (typeof window !== "undefined") {
      window.localStorage.setItem("dt:memory:banner-dismissed", latestBackup);
    }
    setDismissedBackup(latestBackup);
  }, [latestBackup]);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/memory/overview");
      const data = (await res.json()) as OverviewResponse;
      setOverview(data);
    } catch (e) {
      setToast(e instanceof Error ? e.message : t("Failed to load overview"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(id);
  }, [toast]);

  const loadDoc = useCallback(async (layer: Layer, key: string) => {
    setSelected({ layer, key });
    setEditing(false);
    setStream([]);
    try {
      const res = await fetch(`/api/v1/memory/doc/${layer}/${key}`);
      const data = await res.json();
      const md = String(data?.content || "");
      setContent(md);
      setEditorValue(md);
    } catch (e) {
      setToast(e instanceof Error ? e.message : t("Failed to load document"));
    }
  }, []);

  const saveDoc = useCallback(async () => {
    if (!selected) return;
    setBusy(true);
    try {
      await fetch(`/api/v1/memory/doc/${selected.layer}/${selected.key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: editorValue }),
      });
      setContent(editorValue);
      setEditing(false);
      setToast(t("Saved"));
      void loadOverview();
    } catch (e) {
      setToast(e instanceof Error ? e.message : t("Failed to save"));
    } finally {
      setBusy(false);
    }
  }, [editorValue, loadOverview, selected]);

  const runUpdate = useCallback(async () => {
    if (!selected) return;
    if (selected.layer === "L3" && selected.key === "preferences") {
      setToast(
        t("Preferences is written by the chat assistant, not consolidated."),
      );
      return;
    }
    setBusy(true);
    setStream([]);
    try {
      const res = await fetch(
        `/api/v1/memory/doc/${selected.layer}/${selected.key}/update`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ language: "zh" }),
        },
      );
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
              const evt = JSON.parse(line) as StreamStage;
              setStream((prev) => [...prev, evt]);
            } catch {
              // ignore malformed chunk
            }
          }
          nl = buffer.indexOf("\n\n");
        }
      }
      void loadDoc(selected.layer, selected.key);
      void loadOverview();
    } catch (e) {
      setToast(e instanceof Error ? e.message : t("Update failed"));
    } finally {
      setBusy(false);
    }
  }, [loadDoc, loadOverview, selected]);

  // Clicking a `<surface>:<entity_id>` ref inside an L2/L3 doc opens
  // the L1 tab focused on that entity.
  const handleEntityLinkClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const link = (e.target as HTMLElement | null)?.closest("a");
      if (!link) return;
      const href = link.getAttribute("href") || "";
      if (!href.startsWith("#entity-")) return;
      const parsed = parseEntityAnchor(href.slice(1));
      if (!parsed) return;
      setTab("L1");
      setL1Surface(parsed.surface);
      setL1FocusRef(parsed.ref);
    },
    [],
  );

  const l2Rows = useMemo(
    () => (overview?.docs || []).filter((d) => d.layer === "L2"),
    [overview],
  );
  const l3Rows = useMemo(
    () => (overview?.docs || []).filter((d) => d.layer === "L3"),
    [overview],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {!hideHeader && (
        <SpaceSectionHeader
          icon={BulbOutlined}
          title={t("Memory")}
          description={t(
            "L1 mirrors your workspace, L2 summarises per-surface content, L3 is cross-surface knowledge.",
          )}
          meta={
            toast ? (
              <span
                style={{
                  borderRadius: 999,
                  border: "1px solid color-mix(in srgb, var(--primary, #1677ff) 30%, transparent)",
                  background: "color-mix(in srgb, var(--primary, #1677ff) 10%, transparent)",
                  padding: "2px 8px",
                  fontSize: 10.5,
                  fontWeight: 500,
                  color: "var(--primary, #1677ff)",
                }}
              >
                {toast}
              </span>
            ) : null
          }
        />
      )}

      {!forcedTab && showArchivedBanner && latestBackup && (
        <div
          style={{
            position: "relative",
            display: "flex",
            alignItems: "flex-start",
            gap: 8,
            borderRadius: 12,
            border: "1px solid var(--border, #d9d9d9)",
            background: "var(--muted, #f5f5f5)",
            padding: "12px 40px 12px 16px",
            fontSize: 13,
          }}
        >
          <ContainerOutlined
            style={{
              marginTop: 2,
              fontSize: 16,
              flexShrink: 0,
              color: "var(--muted-foreground, rgba(0,0,0,0.45))",
            }}
          />
          <div>
            <p
              style={{
                fontWeight: 500,
                color: "var(--foreground, rgba(0,0,0,0.88))",
                margin: 0,
              }}
            >
              {t("Your v1 memory was archived")}
            </p>
            <p
              style={{
                marginTop: 2,
                color: "var(--muted-foreground, rgba(0,0,0,0.45))",
                marginBottom: 0,
              }}
            >
              {t(
                "Stored at memory/backup/{{name}}. v2 starts fresh — interact with DeepTutor and click Update on each doc to build memory.",
                { name: latestBackup },
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={dismissArchivedBanner}
            aria-label={t("Dismiss")}
            style={{
              position: "absolute",
              right: 8,
              top: 8,
              borderRadius: 6,
              padding: 6,
              color: "var(--muted-foreground, rgba(0,0,0,0.45))",
              border: "none",
              background: "transparent",
              cursor: "pointer",
              lineHeight: 0,
            }}
          >
            <CloseOutlined style={{ fontSize: 14 }} />
          </button>
        </div>
      )}

      {!forcedTab && (
        <TabStrip
          tab={tab}
          onChange={setTab}
          l2Count={l2Rows.length}
          l3Count={l3Rows.length}
        />
      )}

      {tab === "L1" && (
        <L1View
          surface={l1Surface}
          onSurfaceChange={(s) => {
            setL1Surface(s);
            setL1FocusRef(null);
          }}
          focusRef={l1FocusRef}
          onClearFocus={() => setL1FocusRef(null)}
          onToast={setToast}
        />
      )}

      {tab !== "L1" && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1fr)",
            gap: 24,
          }}
          className="memory-section-grid"
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <DocList
              title={t(
                tab === "L2" ? "L2 · Per-surface" : "L3 · Cross-surface",
              )}
              rows={tab === "L2" ? l2Rows : l3Rows}
              selected={selected}
              onSelect={loadDoc}
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {loading ? (
              <div
                style={{
                  display: "flex",
                  minHeight: 300,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <LoadingOutlined
                  style={{
                    fontSize: 20,
                    color: "var(--muted-foreground, rgba(0,0,0,0.45))",
                  }}
                />
              </div>
            ) : !selected || selected.layer !== tab ? (
              <div
                style={{
                  display: "flex",
                  minHeight: 300,
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: 12,
                  border: `1px dashed var(--border, #d9d9d9)`,
                  textAlign: "center",
                }}
              >
                <BulbOutlined
                  style={{
                    marginBottom: 12,
                    fontSize: 20,
                    color: "var(--muted-foreground, rgba(0,0,0,0.45))",
                  }}
                />
                <p
                  style={{
                    fontSize: 14,
                    color: "var(--foreground, rgba(0,0,0,0.88))",
                    margin: 0,
                  }}
                >
                  {t("Pick a document to view or update")}
                </p>
              </div>
            ) : (
              <DocPane
                selected={selected}
                content={content}
                editing={editing}
                editorValue={editorValue}
                busy={busy}
                onEditValue={setEditorValue}
                onEditToggle={() => {
                  setEditing((v) => !v);
                  setEditorValue(content);
                }}
                onSave={saveDoc}
                onUpdate={runUpdate}
                onEntityLinkClick={handleEntityLinkClick}
              />
            )}

            {stream.length > 0 && (
              <StreamPanel
                stages={stream}
                onDismiss={() => setStream([])}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── TabStrip ────────────────────────────────────────────────────────

interface TabStripProps {
  tab: Tab;
  onChange: (tab: Tab) => void;
  l2Count: number;
  l3Count: number;
}

function TabStrip({ tab, onChange, l2Count, l3Count }: TabStripProps) {
  const tabs: Array<{ key: Tab; label: string; count?: number; hint: string }> =
    [
      {
        key: "L1",
        label: t("L1 · Workspace"),
        hint: t(
          "Live snapshot of your workspace — one entry per real artifact.",
        ),
      },
      {
        key: "L2",
        label: t("L2 · Per-surface"),
        count: l2Count,
        hint: t("Per-surface summaries consolidated from L1 content."),
      },
      {
        key: "L3",
        label: t("L3 · Cross-surface"),
        count: l3Count,
        hint: t("Cross-surface knowledge consolidated from L2."),
      },
    ];
  return (
    <div style={{ borderBottom: "1px solid var(--border, #d9d9d9)" }}>
      <div style={{ display: "flex", gap: 4 }}>
        {tabs.map(({ key, label, count, hint }) => {
          const active = tab === key;
          return (
            <button
              key={key}
              onClick={() => onChange(key)}
              title={hint}
              style={{
                position: "relative",
                padding: "8px 16px",
                fontSize: 13,
                fontWeight: 500,
                background: "transparent",
                border: "none",
                cursor: "pointer",
                color: active
                  ? "var(--foreground, rgba(0,0,0,0.88))"
                  : "var(--muted-foreground, rgba(0,0,0,0.45))",
              }}
            >
              {label}
              {typeof count === "number" && (
                <span
                  style={{
                    marginLeft: 8,
                    borderRadius: 999,
                    background: "var(--muted, #f5f5f5)",
                    padding: "2px 6px",
                    fontSize: 10,
                    fontWeight: 400,
                    color: "var(--muted-foreground, rgba(0,0,0,0.45))",
                  }}
                >
                  {count}
                </span>
              )}
              {active && (
                <span
                  aria-hidden
                  style={{
                    position: "absolute",
                    bottom: -1,
                    left: 0,
                    right: 0,
                    height: 2,
                    background: "var(--foreground, rgba(0,0,0,0.88))",
                  }}
                />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── L1View (snapshot + changes per surface) ─────────────────────────

type L1Mode = "snapshot" | "changes" | "queries";

export interface L1ViewProps {
  surface: Surface;
  onSurfaceChange: (s: Surface) => void;
  focusRef: string | null;
  onClearFocus: () => void;
  onToast: (msg: string) => void;
  // When true, the surface pill bar is hidden — the parent renders its own
  // surface picker (e.g. a left rail in the workbench layout).
  compact?: boolean;
}

export function L1View({
  surface,
  onSurfaceChange,
  focusRef,
  onClearFocus,
  onToast,
  compact = false,
}: L1ViewProps) {
  const [mode, setMode] = useState<L1Mode>("snapshot");
  const [snapshot, setSnapshot] = useState<SnapshotResponse | null>(null);
  const [changes, setChanges] = useState<ChangeEntryDTO[]>([]);
  const [kbQueries, setKbQueries] = useState<KbQueryDTO[]>([]);
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  const [loadingChanges, setLoadingChanges] = useState(false);
  const [loadingQueries, setLoadingQueries] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Default mode when switching surfaces:
  //  - kb: prefer "snapshot" but kb-only "queries" mode is accessible.
  //  - others: snapshot.
  useEffect(() => {
    if (mode === "queries" && surface !== "kb") {
      setMode("snapshot");
    }
  }, [surface, mode]);

  const loadSnapshot = useCallback(async () => {
    setLoadingSnapshot(true);
    try {
      const res = await fetch(`/api/v1/memory/snapshot/${surface}`);
      const data = (await res.json()) as SnapshotResponse;
      setSnapshot(data);
    } catch (e) {
      onToast(e instanceof Error ? e.message : t("Failed to load snapshot"));
    } finally {
      setLoadingSnapshot(false);
    }
  }, [surface, onToast]);

  const loadChanges = useCallback(async () => {
    setLoadingChanges(true);
    try {
      const res = await fetch(`/api/v1/memory/snapshot/${surface}/changes`);
      const data = (await res.json()) as ChangesResponse;
      setChanges(data.changes);
    } catch (e) {
      onToast(e instanceof Error ? e.message : t("Failed to load changes"));
    } finally {
      setLoadingChanges(false);
    }
  }, [surface, onToast]);

  const loadKbQueries = useCallback(async () => {
    if (surface !== "kb") return;
    setLoadingQueries(true);
    try {
      const res = await fetch("/api/v1/memory/trace/kb?limit=200");
      const data = (await res.json()) as KbQueriesResponse;
      setKbQueries(data.events);
    } catch (e) {
      onToast(e instanceof Error ? e.message : t("Failed to load queries"));
    } finally {
      setLoadingQueries(false);
    }
  }, [surface, onToast]);

  useEffect(() => {
    setSnapshot(null);
    setChanges([]);
    setKbQueries([]);
    void loadSnapshot();
    void loadChanges();
    if (surface === "kb") void loadKbQueries();
  }, [surface, loadSnapshot, loadChanges, loadKbQueries]);

  // Auto-refetch snapshot when the tab regains focus or becomes visible —
  // workspace can mutate while the user is in another tab (notebook write,
  // co-writer edit, etc.) so the snapshot must reflect that without a click.
  useEffect(() => {
    const refetch = () => {
      if (typeof document !== "undefined" && document.hidden) return;
      void loadSnapshot();
    };
    window.addEventListener("focus", refetch);
    document.addEventListener("visibilitychange", refetch);
    return () => {
      window.removeEventListener("focus", refetch);
      document.removeEventListener("visibilitychange", refetch);
    };
  }, [loadSnapshot]);

  // Auto-scroll to focused entity when snapshot finishes loading.
  useEffect(() => {
    if (!focusRef || !containerRef.current) return;
    if (!snapshot) return;
    const el = containerRef.current.querySelector(
      `[data-entity-ref="${focusRef}"]`,
    ) as HTMLElement | null;
    if (el) {
      el.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [focusRef, snapshot]);

  const pendingByEntity = useMemo(() => {
    const m = new Map<string, ChangeEntryDTO["kind"]>();
    for (const c of snapshot?.pending_changes ?? []) {
      m.set(c.entity_id, c.kind);
    }
    return m;
  }, [snapshot?.pending_changes]);
  const pendingCount = snapshot?.pending_changes?.length ?? 0;

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const res = await fetch(`/api/v1/memory/snapshot/${surface}/refresh`, {
        method: "POST",
      });
      const data = await res.json();
      const newChanges: ChangeEntryDTO[] = data?.changes || [];
      onToast(
        newChanges.length > 0
          ? t("Refreshed: {{n}} changes", { n: newChanges.length })
          : t("Refreshed: no changes"),
      );
      await loadSnapshot();
      await loadChanges();
    } catch (e) {
      onToast(e instanceof Error ? e.message : t("Refresh failed"));
    } finally {
      setRefreshing(false);
    }
  }, [surface, loadSnapshot, loadChanges, onToast]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }} ref={containerRef}>
      {!compact && (
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8 }}>
          {SURFACES.map((s) => {
            const meta = SURFACE_META[s];
            return (
              <SurfacePill
                key={s}
                active={surface === s}
                onClick={() => onSurfaceChange(s)}
                icon={meta.icon}
                label={meta.label}
              />
            );
          })}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            {pendingCount > 0 && (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  borderRadius: 999,
                  border: "1px solid rgba(245,158,11,0.4)",
                  background: "rgba(245,158,11,0.1)",
                  padding: "2px 8px",
                  fontSize: 11,
                  fontWeight: 500,
                  color: "#b45309",
                }}
                title={t(
                  "Workspace changed since last refresh. Click Refresh to commit these to the changes log.",
                )}
              >
                {t("{{n}} pending", { n: pendingCount })}
              </span>
            )}
            <button
              onClick={() => void onRefresh()}
              disabled={refreshing}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                borderRadius: 6,
                border: "1px solid var(--border, #d9d9d9)",
                background: "var(--card, #ffffff)",
                padding: "4px 10px",
                fontSize: 12,
                color: "var(--muted-foreground, rgba(0,0,0,0.45))",
                cursor: refreshing ? "not-allowed" : "pointer",
                opacity: refreshing ? 0.5 : 1,
              }}
              title={t("Re-scan workspace and record any changes")}
            >
              {refreshing ? (
                <LoadingOutlined style={{ fontSize: 12 }} />
              ) : (
                <ReloadOutlined style={{ fontSize: 12 }} />
              )}
              {t("Refresh")}
            </button>
          </div>
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
        <ModeStrip mode={mode} setMode={setMode} surface={surface} />
        {compact && (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {pendingCount > 0 && (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  borderRadius: 999,
                  border: "1px solid rgba(245,158,11,0.4)",
                  background: "rgba(245,158,11,0.1)",
                  padding: "2px 8px",
                  fontSize: 11,
                  fontWeight: 500,
                  color: "#b45309",
                }}
                title={t(
                  "Workspace changed since last refresh. Click Refresh to commit these to the changes log.",
                )}
              >
                {t("{{n}} pending", { n: pendingCount })}
              </span>
            )}
            <button
              onClick={() => void onRefresh()}
              disabled={refreshing}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                borderRadius: 6,
                border: "1px solid var(--border, #d9d9d9)",
                background: "var(--card, #ffffff)",
                padding: "4px 10px",
                fontSize: 12,
                color: "var(--muted-foreground, rgba(0,0,0,0.45))",
                cursor: refreshing ? "not-allowed" : "pointer",
                opacity: refreshing ? 0.5 : 1,
              }}
              title={t("Re-scan workspace and record any changes")}
            >
              {refreshing ? (
                <LoadingOutlined style={{ fontSize: 12 }} />
              ) : (
                <ReloadOutlined style={{ fontSize: 12 }} />
              )}
              {t("Refresh")}
            </button>
          </div>
        )}
      </div>

      {mode === "snapshot" && (
        <SnapshotList
          surface={surface}
          loading={loadingSnapshot}
          snapshot={snapshot}
          pendingByEntity={pendingByEntity}
          focusRef={focusRef}
          onClearFocus={onClearFocus}
        />
      )}

      {mode === "changes" && (
        <ChangesList
          loading={loadingChanges}
          changes={changes}
          pending={snapshot?.pending_changes ?? []}
        />
      )}

      {mode === "queries" && surface === "kb" && (
        <KbQueriesList loading={loadingQueries} queries={kbQueries} />
      )}
    </div>
  );
}

// ── SurfacePill ─────────────────────────────────────────────────────

interface SurfacePillProps {
  active: boolean;
  onClick: () => void;
  icon: typeof MessageOutlined;
  label: string;
}

function SurfacePill({ active, onClick, icon: Icon, label }: SurfacePillProps) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        borderRadius: 999,
        border: active
          ? "1px solid color-mix(in srgb, var(--primary, #1677ff) 40%, transparent)"
          : "1px solid var(--border, #d9d9d9)",
        padding: "4px 12px",
        fontSize: 12,
        background: active
          ? "color-mix(in srgb, var(--primary, #1677ff) 10%, transparent)"
          : "transparent",
        color: active
          ? "var(--primary, #1677ff)"
          : "var(--muted-foreground, rgba(0,0,0,0.45))",
        cursor: "pointer",
      }}
    >
      <Icon style={{ fontSize: 12 }} />
      <span>{label}</span>
    </button>
  );
}

// ── ModeStrip (snapshot / changes / [kb queries]) ───────────────────

interface ModeStripProps {
  mode: L1Mode;
  setMode: (m: L1Mode) => void;
  surface: Surface;
}

function ModeStrip({ mode, setMode, surface }: ModeStripProps) {
  const tabs: Array<{ key: L1Mode; label: string; hidden?: boolean }> = [
    { key: "snapshot", label: t("Snapshot") },
    { key: "changes", label: t("Changes") },
    { key: "queries", label: t("Queries"), hidden: surface !== "kb" },
  ];
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 2,
        borderRadius: 6,
        border: "1px solid var(--border, #d9d9d9)",
        background: "var(--card, #ffffff)",
        padding: 2,
        fontSize: 12,
      }}
    >
      {tabs
        .filter((x) => !x.hidden)
        .map(({ key, label }) => {
          const active = mode === key;
          return (
            <button
              key={key}
              onClick={() => setMode(key)}
              style={{
                borderRadius: 4,
                padding: "4px 10px",
                background: active ? "var(--muted, #f5f5f5)" : "transparent",
                border: "none",
                cursor: "pointer",
                color: active
                  ? "var(--foreground, rgba(0,0,0,0.88))"
                  : "var(--muted-foreground, rgba(0,0,0,0.45))",
              }}
            >
              {label}
            </button>
          );
        })}
    </div>
  );
}

// ── SnapshotList ─────────────────────────────────────────────────────

interface SnapshotListProps {
  surface: Surface;
  loading: boolean;
  snapshot: SnapshotResponse | null;
  pendingByEntity: Map<string, ChangeEntryDTO["kind"]>;
  focusRef: string | null;
  onClearFocus: () => void;
}

function SnapshotList({
  surface,
  loading,
  snapshot,
  pendingByEntity,
  focusRef,
  onClearFocus,
}: SnapshotListProps) {
  const entities = snapshot?.entities ?? [];
  return (
    <>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          fontSize: 11.5,
          color: "var(--muted-foreground, rgba(0,0,0,0.45))",
        }}
      >
        <span>
          {t("{{n}} entities", { n: entities.length })}
          {snapshot?.last_refresh && (
            <>
              {" · "}
              {t("last refresh {{ts}}", {
                ts: formatTimestamp(snapshot.last_refresh, ""),
              })}
            </>
          )}
        </span>
        {focusRef && (
          <button
            onClick={onClearFocus}
            style={{
              color: "var(--primary, #1677ff)",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              textDecoration: "underline",
            }}
          >
            {t("Clear focus")}
          </button>
        )}
      </div>
      {loading && entities.length === 0 ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 12,
            border: "1px solid var(--border, #d9d9d9)",
            padding: "48px 0",
          }}
        >
          <LoadingOutlined
            style={{ fontSize: 16, color: "var(--muted-foreground, rgba(0,0,0,0.45))" }}
          />
        </div>
      ) : entities.length === 0 ? (
        <p
          style={{
            borderRadius: 12,
            border: "1px solid var(--border, #d9d9d9)",
            padding: "40px 16px",
            textAlign: "center",
            fontSize: 13,
            color: "var(--muted-foreground, rgba(0,0,0,0.45))",
          }}
        >
          {t("Nothing in workspace yet.")}
        </p>
      ) : (
        <ol
          style={{
            borderRadius: 12,
            border: "1px solid var(--border, #d9d9d9)",
            listStyle: "none",
            margin: 0,
            padding: 0,
            overflow: "hidden",
          }}
        >
          {entities.map((ent, idx) => (
            <EntityRow
              key={`${ent.id}#${idx}`}
              surface={surface}
              ent={ent}
              focused={focusRef === `${surface}:${ent.id}`}
              pendingKind={pendingByEntity.get(ent.id) ?? null}
            />
          ))}
        </ol>
      )}
    </>
  );
}

// ── EntityRow ───────────────────────────────────────────────────────

interface EntityRowProps {
  surface: Surface;
  ent: Entity;
  focused: boolean;
  pendingKind: ChangeEntryDTO["kind"] | null;
}

function EntityRow({ surface, ent, focused, pendingKind }: EntityRowProps) {
  const url = entityDeepLinkUrl(surface, ent);
  const ref = `${surface}:${ent.id}`;
  const meta = SURFACE_META[surface];
  const Icon = meta.icon;
  const preview = shorten(ent.content, 220);

  const inner = (
    <>
      <span
        style={{
          marginTop: 2,
          display: "inline-flex",
          height: 20,
          width: 20,
          flexShrink: 0,
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 4,
          background: focused
            ? "color-mix(in srgb, var(--primary, #1677ff) 25%, transparent)"
            : "var(--muted, #f5f5f5)",
          color: focused
            ? "var(--primary, #1677ff)"
            : "var(--muted-foreground, rgba(0,0,0,0.45))",
        }}
      >
        <Icon style={{ fontSize: 12 }} />
      </span>
      <div style={{ minWidth: 0, flex: 1 }}>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "baseline",
            columnGap: 8,
            fontSize: 11,
            color: "var(--muted-foreground, rgba(0,0,0,0.45))",
          }}
        >
          <span
            style={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              fontSize: 13,
              fontWeight: 500,
              color: "var(--foreground, rgba(0,0,0,0.88))",
            }}
          >
            {ent.label}
          </span>
          <span style={{ fontFamily: "monospace", opacity: 0.7 }}>{ent.id}</span>
          {ent.ts && <span>{formatTimestamp(ent.ts, "")}</span>}
          {pendingKind && <PendingBadge kind={pendingKind} />}
        </div>
        {preview && (
          <p
            style={{
              marginTop: 4,
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              fontSize: 12,
              color: "color-mix(in srgb, var(--muted-foreground, rgba(0,0,0,0.45)) 90%, transparent)",
              marginBottom: 0,
            }}
          >
            {preview}
          </p>
        )}
      </div>
      {url && (
        <ExportOutlined
          style={{
            marginTop: 4,
            fontSize: 14,
            flexShrink: 0,
            color: "var(--muted-foreground, rgba(0,0,0,0.45))",
          }}
        />
      )}
    </>
  );

  const focusedRing: CSSProperties = focused
    ? {
        borderLeft: "3px solid var(--primary, #1677ff)",
        background: "color-mix(in srgb, var(--primary, #1677ff) 12%, transparent)",
        boxShadow: "0 0 0 1px color-mix(in srgb, var(--primary, #1677ff) 30%, transparent)",
      }
    : pendingKind === "added"
      ? { borderLeft: "3px solid #10b981", background: "rgba(16,185,129,0.05)" }
      : pendingKind === "modified"
        ? { borderLeft: "3px solid #f59e0b", background: "rgba(245,158,11,0.05)" }
        : { borderLeft: "3px solid transparent" };
  const rowStyle: CSSProperties = {
    display: "flex",
    alignItems: "flex-start",
    gap: 12,
    borderBottom: "1px solid color-mix(in srgb, var(--border, #d9d9d9) 50%, transparent)",
    padding: "10px 16px",
    color: "inherit",
    textDecoration: "none",
    ...focusedRing,
  };

  return (
    <li
      id={entityAnchorId(ref)}
      data-entity-ref={ref}
      title={t("Open in {{label}}", { label: meta.label })}
      style={{ listStyle: "none" }}
    >
      {/* 跨应用 deep-link（原 next/link → 原生 <a>，保留 URL 形状；登记见头注） */}
      {url ? (
        <a href={url} style={rowStyle}>
          {inner}
        </a>
      ) : (
        <div style={rowStyle}>{inner}</div>
      )}
    </li>
  );
}

// ── PendingBadge (row-level pending marker) ─────────────────────────

function PendingBadge({ kind }: { kind: ChangeEntryDTO["kind"] }) {
  const map = {
    added: {
      label: t("new"),
      cls:
        "1px solid rgba(16,185,129,0.4)|rgba(16,185,129,0.1)|#047857",
    },
    modified: {
      label: t("modified"),
      cls:
        "1px solid rgba(245,158,11,0.4)|rgba(245,158,11,0.1)|#b45309",
    },
    removed: {
      label: t("removed"),
      cls:
        "1px solid rgba(244,63,94,0.4)|rgba(244,63,94,0.1)|#be123c",
    },
  } as const;
  const cfg = map[kind];
  const [border, bg, fg] = cfg.cls.split("|");
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        borderRadius: 999,
        border: border,
        padding: "0 6px",
        fontSize: 10,
        fontWeight: 500,
        background: bg,
        color: fg,
      }}
      title={t("Pending — not yet committed to changes log")}
    >
      {cfg.label}
    </span>
  );
}

// ── ChangesList (git-log style) ─────────────────────────────────────

interface ChangesListProps {
  loading: boolean;
  changes: ChangeEntryDTO[];
  pending: ChangeEntryDTO[];
}

function ChangesList({ loading, changes, pending }: ChangesListProps) {
  if (loading && changes.length === 0 && pending.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 12,
          border: "1px solid var(--border, #d9d9d9)",
          padding: "48px 0",
        }}
      >
        <LoadingOutlined
          style={{ fontSize: 16, color: "var(--muted-foreground, rgba(0,0,0,0.45))" }}
        />
      </div>
    );
  }
  const hasAny = changes.length > 0 || pending.length > 0;
  if (!hasAny) {
    return (
      <p
        style={{
          borderRadius: 12,
          border: "1px solid var(--border, #d9d9d9)",
          padding: "40px 16px",
          textAlign: "center",
          fontSize: 13,
          color: "var(--muted-foreground, rgba(0,0,0,0.45))",
        }}
      >
        {t("No changes recorded yet. Run Refresh to capture the baseline.")}
      </p>
    );
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {pending.length > 0 && (
        <div
          style={{
            borderRadius: 12,
            border: "1px solid rgba(245,158,11,0.4)",
            background: "rgba(245,158,11,0.05)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              borderBottom: "1px solid rgba(245,158,11,0.3)",
              padding: "6px 16px",
              fontSize: 11,
              fontWeight: 500,
              color: "#b45309",
            }}
          >
            <span>
              {t("Pending — {{n}} change(s) since last refresh", {
                n: pending.length,
              })}
            </span>
            <span style={{ opacity: 0.7 }}>{t("Click Refresh to commit")}</span>
          </div>
          <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {pending.map((c, i) => (
              <ChangeRow key={`pending-${c.entity_id}-${i}`} c={c} />
            ))}
          </ol>
        </div>
      )}
      {changes.length > 0 && (
        <ol
          style={{
            borderRadius: 12,
            border: "1px solid var(--border, #d9d9d9)",
            listStyle: "none",
            margin: 0,
            padding: 0,
            overflow: "hidden",
          }}
        >
          {changes.map((c, i) => (
            <ChangeRow key={`${c.ts}-${c.entity_id}-${i}`} c={c} />
          ))}
        </ol>
      )}
    </div>
  );
}

function ChangeRow({ c }: { c: ChangeEntryDTO }) {
  return (
    <li
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        borderBottom: "1px solid color-mix(in srgb, var(--border, #d9d9d9) 50%, transparent)",
        padding: "8px 16px",
        listStyle: "none",
      }}
    >
      <ChangeGlyph kind={c.kind} />
      <div style={{ minWidth: 0, flex: 1 }}>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "baseline",
            columnGap: 8,
            fontSize: 11,
            color: "var(--muted-foreground, rgba(0,0,0,0.45))",
          }}
        >
          <span style={{ fontWeight: 500, color: "var(--foreground, rgba(0,0,0,0.88))" }}>
            {c.label || c.entity_id}
          </span>
          <span style={{ fontFamily: "monospace", opacity: 0.7 }}>{c.entity_id}</span>
          <span>{formatTimestamp(c.ts, "")}</span>
        </div>
      </div>
    </li>
  );
}

function ChangeGlyph({ kind }: { kind: ChangeEntryDTO["kind"] }) {
  const map = {
    added: { ch: "+", bg: "rgba(16,185,129,0.15)", fg: "#059669" },
    modified: { ch: "~", bg: "rgba(245,158,11,0.15)", fg: "#d97706" },
    removed: { ch: "−", bg: "rgba(244,63,94,0.15)", fg: "#e11d48" },
  } as const;
  const cfg = map[kind];
  return (
    <span
      style={{
        marginTop: 2,
        display: "inline-flex",
        height: 20,
        width: 20,
        flexShrink: 0,
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 4,
        fontFamily: "monospace",
        fontSize: 12,
        fontWeight: 700,
        background: cfg.bg,
        color: cfg.fg,
      }}
    >
      {cfg.ch}
    </span>
  );
}

// ── KbQueriesList (event-driven, only for KB) ───────────────────────

interface KbQueriesListProps {
  loading: boolean;
  queries: KbQueryDTO[];
}

function KbQueriesList({ loading, queries }: KbQueriesListProps) {
  if (loading && queries.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 12,
          border: "1px solid var(--border, #d9d9d9)",
          padding: "48px 0",
        }}
      >
        <LoadingOutlined
          style={{ fontSize: 16, color: "var(--muted-foreground, rgba(0,0,0,0.45))" }}
        />
      </div>
    );
  }
  if (queries.length === 0) {
    return (
      <p
        style={{
          borderRadius: 12,
          border: "1px solid var(--border, #d9d9d9)",
          padding: "40px 16px",
          textAlign: "center",
          fontSize: 13,
          color: "var(--muted-foreground, rgba(0,0,0,0.45))",
        }}
      >
        {t("No RAG queries recorded yet.")}
      </p>
    );
  }
  return (
    <ol
      style={{
        borderRadius: 12,
        border: "1px solid var(--border, #d9d9d9)",
        listStyle: "none",
        margin: 0,
        padding: 0,
        overflow: "hidden",
      }}
    >
      {queries.map((q) => {
        const kb = asString(q.payload?.kb_name) || "?";
        const query = asString(q.payload?.query);
        return (
          <li
            key={q.id}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 12,
              borderBottom: "1px solid color-mix(in srgb, var(--border, #d9d9d9) 50%, transparent)",
              padding: "8px 16px",
              listStyle: "none",
            }}
          >
            <BranchesOutlined
              style={{
                marginTop: 2,
                fontSize: 14,
                flexShrink: 0,
                color: "var(--muted-foreground, rgba(0,0,0,0.45))",
              }}
            />
            <div style={{ minWidth: 0, flex: 1 }}>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "baseline",
                  columnGap: 8,
                  fontSize: 11,
                  color: "var(--muted-foreground, rgba(0,0,0,0.45))",
                }}
              >
                <span style={{ fontWeight: 500, color: "var(--foreground, rgba(0,0,0,0.88))" }}>
                  {kb}
                </span>
                <span>{formatTimestamp(q.ts, "")}</span>
              </div>
              <p
                style={{
                  marginTop: 2,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  fontSize: 12.5,
                  color: "var(--foreground, rgba(0,0,0,0.88))",
                  marginBottom: 0,
                }}
              >
                {query}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

// ── DocList / DocPane / StreamPanel (mostly unchanged) ──────────────

interface DocListProps {
  title: string;
  rows: DocOverview[];
  selected: { layer: Layer; key: string } | null;
  onSelect: (layer: Layer, key: string) => void;
}

function DocList({ title, rows, selected, onSelect }: DocListProps) {
  return (
    <div
      style={{
        borderRadius: 12,
        border: "1px solid var(--border, #d9d9d9)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          borderBottom: "1px solid var(--border, #d9d9d9)",
          padding: "8px 16px",
          fontSize: 11,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          color: "var(--muted-foreground, rgba(0,0,0,0.45))",
        }}
      >
        {title}
      </div>
      <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {rows.map((row) => {
          const isActive =
            selected?.layer === row.layer && selected.key === row.key;
          return (
            <li
              key={`${row.layer}-${row.key}`}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                borderBottom: "1px solid color-mix(in srgb, var(--border, #d9d9d9) 50%, transparent)",
                padding: "8px 16px",
                fontSize: 13,
                background: isActive ? "var(--muted, #f5f5f5)" : "transparent",
                listStyle: "none",
              }}
            >
              <button
                onClick={() => onSelect(row.layer, row.key)}
                style={{ flex: 1, textAlign: "left", border: "none", background: "transparent", cursor: "pointer", padding: 0 }}
              >
                <span style={{ fontWeight: 500, color: "var(--foreground, rgba(0,0,0,0.88))" }}>
                  {labelFor(row)}
                </span>
                <span
                  style={{
                    marginLeft: 8,
                    fontSize: 11,
                    color: "var(--muted-foreground, rgba(0,0,0,0.45))",
                  }}
                >
                  {row.entry_count} ·{" "}
                  {formatTimestamp(row.updated_at, t("not built"))}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

interface DocPaneProps {
  selected: { layer: Layer; key: string };
  content: string;
  editing: boolean;
  editorValue: string;
  busy: boolean;
  onEditValue: (v: string) => void;
  onEditToggle: () => void;
  onSave: () => void;
  onUpdate: () => void;
  onEntityLinkClick: (e: React.MouseEvent<HTMLDivElement>) => void;
}

function DocPane({
  selected,
  content,
  editing,
  editorValue,
  busy,
  onEditValue,
  onEditToggle,
  onSave,
  onUpdate,
  onEntityLinkClick,
}: DocPaneProps) {
  const isPrefs = selected.layer === "L3" && selected.key === "preferences";
  const renderedContent = useMemo(() => linkifyEntityRefs(content), [content]);
  return (
    <div
      style={{
        borderRadius: 12,
        border: "1px solid var(--border, #d9d9d9)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid var(--border, #d9d9d9)",
          padding: "8px 16px",
        }}
      >
        <span style={{ fontSize: 14, fontWeight: 500, color: "var(--foreground, rgba(0,0,0,0.88))" }}>
          {selected.layer} ·{" "}
          {labelFor({
            layer: selected.layer,
            key: selected.key,
          } as DocOverview)}
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            onClick={onEditToggle}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              borderRadius: 8,
              border: "1px solid var(--border, #d9d9d9)",
              padding: "4px 10px",
              fontSize: 12,
              color: "var(--muted-foreground, rgba(0,0,0,0.45))",
              background: "transparent",
              cursor: "pointer",
            }}
          >
            <EditOutlined style={{ fontSize: 12 }} />
            {editing ? t("Cancel") : t("Edit")}
          </button>
          {editing && (
            <button
              onClick={onSave}
              disabled={busy}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                borderRadius: 8,
                border: "1px solid color-mix(in srgb, var(--primary, #1677ff) 40%, transparent)",
                background: "color-mix(in srgb, var(--primary, #1677ff) 10%, transparent)",
                padding: "4px 10px",
                fontSize: 12,
                fontWeight: 500,
                color: "var(--primary, #1677ff)",
                cursor: busy ? "not-allowed" : "pointer",
                opacity: busy ? 0.5 : 1,
              }}
            >
              {busy ? (
                <LoadingOutlined style={{ fontSize: 12 }} />
              ) : (
                <SaveOutlined style={{ fontSize: 12 }} />
              )}
              {t("Save")}
            </button>
          )}
          {!isPrefs && (
            <button
              onClick={onUpdate}
              disabled={busy || editing}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                borderRadius: 8,
                border: "1px solid color-mix(in srgb, var(--primary, #1677ff) 40%, transparent)",
                background: "color-mix(in srgb, var(--primary, #1677ff) 10%, transparent)",
                padding: "4px 10px",
                fontSize: 12,
                fontWeight: 500,
                color: "var(--primary, #1677ff)",
                cursor: busy || editing ? "not-allowed" : "pointer",
                opacity: busy || editing ? 0.5 : 1,
              }}
            >
              {busy ? (
                <LoadingOutlined style={{ fontSize: 12 }} />
              ) : (
                <ReloadOutlined style={{ fontSize: 12 }} />
              )}
              {t("Update")}
            </button>
          )}
        </div>
      </div>
      <div style={{ padding: "16px 20px" }}>
        {editing ? (
          <textarea
            value={editorValue}
            onChange={(e) => onEditValue(e.target.value)}
            spellCheck={false}
            style={{
              minHeight: 420,
              width: "100%",
              resize: "none",
              borderRadius: 8,
              border: "1px solid var(--border, #d9d9d9)",
              background: "transparent",
              padding: 12,
              fontFamily: "monospace",
              fontSize: 13,
              lineHeight: 1.5,
              outline: "none",
              boxSizing: "border-box",
            }}
          />
        ) : content.trim() ? (
          <div onClick={onEntityLinkClick}>
            {/* 【降级登记】批8 MarkdownRenderer stub：allowHtml 接收不生效，
                linkifyEntityRefs 注入的 #entity- 锚点与 Workbench 的 m_xxx
                anchor span 不会渲染为真实元素（详见文件头注）。 */}
            <MarkdownRenderer
              content={renderedContent}
              variant="prose"
              className="text-[14px]"
            />
          </div>
        ) : (
          <p
            style={{
              fontSize: 13,
              color: "var(--muted-foreground, rgba(0,0,0,0.45))",
            }}
          >
            {isPrefs
              ? t(
                  "Preferences are written when you explicitly tell the chat assistant your preferences (style, language, format).",
                )
              : t(
                  "Empty. Click Update to consolidate from the current snapshot.",
                )}
          </p>
        )}
      </div>
    </div>
  );
}

interface StreamPanelProps {
  stages: StreamStage[];
  onDismiss: () => void;
}

function StreamPanel({ stages, onDismiss }: StreamPanelProps) {
  return (
    <div
      style={{
        borderRadius: 12,
        border: "1px solid var(--border, #d9d9d9)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid var(--border, #d9d9d9)",
          padding: "8px 16px",
        }}
      >
        <span
          style={{
            fontSize: 12,
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: "var(--muted-foreground, rgba(0,0,0,0.45))",
          }}
        >
          {t("Update progress")}
        </span>
        <button
          onClick={onDismiss}
          style={{
            borderRadius: 4,
            padding: 4,
            color: "var(--muted-foreground, rgba(0,0,0,0.45))",
            border: "none",
            background: "transparent",
            cursor: "pointer",
            lineHeight: 0,
          }}
        >
          <CloseOutlined style={{ fontSize: 12 }} />
        </button>
      </div>
      <ol style={{ display: "flex", flexDirection: "column", gap: 8, padding: "12px 16px", fontSize: 12, listStyle: "none", margin: 0 }}>
        {stages.map((s, i) => (
          <li
            key={i}
            style={{
              borderRadius: 4,
              background: "color-mix(in srgb, var(--muted, #f5f5f5) 50%, transparent)",
              padding: "8px 12px",
              fontFamily: "monospace",
              listStyle: "none",
            }}
          >
            <span style={{ fontWeight: 600, color: "var(--foreground, rgba(0,0,0,0.88))" }}>
              {s.stage}
              {typeof s.turn === "number" ? ` · t${s.turn}` : ""}
              {s.name ? ` · ${s.name}` : ""}
            </span>
            {typeof s.count === "number" && (
              <span style={{ marginLeft: 8, color: "var(--muted-foreground, rgba(0,0,0,0.45))" }}>
                count={s.count}
              </span>
            )}
            {s.delta && (
              <div
                style={{
                  marginTop: 4,
                  whiteSpace: "pre-wrap",
                  color: "var(--muted-foreground, rgba(0,0,0,0.45))",
                }}
              >
                {s.delta}
              </div>
            )}
            {s.brief && (
              <div style={{ marginTop: 4, color: "var(--muted-foreground, rgba(0,0,0,0.45))" }}>
                {s.brief}
              </div>
            )}
            {s.args && Object.keys(s.args).length > 0 && (
              <div style={{ marginTop: 4, color: "var(--muted-foreground, rgba(0,0,0,0.45))" }}>
                args: {JSON.stringify(s.args)}
              </div>
            )}
            {s.ops && (
              <div style={{ marginTop: 4, color: "var(--muted-foreground, rgba(0,0,0,0.45))" }}>
                ops: {s.ops.length}
              </div>
            )}
            {typeof s.ops_emitted === "number" && (
              <div style={{ marginTop: 4, color: "var(--muted-foreground, rgba(0,0,0,0.45))" }}>
                ops_emitted={s.ops_emitted} · turns={s.turns_used ?? "?"}
                {s.tools_used
                  ? ` · ${Object.entries(s.tools_used)
                      .map(([k, v]) => `${k}=${v}`)
                      .join(", ")}`
                  : ""}
              </div>
            )}
            {s.report && (
              <div style={{ marginTop: 4, color: "var(--muted-foreground, rgba(0,0,0,0.45))" }}>
                accepted={String(s.report.accepted)}
                {s.report.reason ? ` · ${s.report.reason}` : ""}
              </div>
            )}
            {s.message && (
              <div style={{ marginTop: 4, color: "var(--muted-foreground, rgba(0,0,0,0.45))" }}>
                {s.message}
              </div>
            )}
            {s.summary && (
              <div style={{ marginTop: 4, color: "var(--muted-foreground, rgba(0,0,0,0.45))" }}>
                {s.summary}
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

export default MemorySection;
