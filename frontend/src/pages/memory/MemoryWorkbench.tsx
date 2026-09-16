/**
 * 桌面同名件 1:1（复制自 DeepTutor 原仓 web/components/memory/MemoryWorkbench.tsx，639 行；
 * layer prop L2/L3 双用）。随 MemoryAdmin 的 L2/L3 工作台两个 tab 消费。
 * 替换点：
 *  - 删除 "use client"；next/dynamic(MarkdownRenderer) → 直接 import 批8 已移植
 *    ../tutor/admin/MarkdownRenderer stub（【降级登记】stub 的 allowHtml 不生效，
 *    prepareDocForRender 注入的 <span id="m_xxx"> anchor 不渲染为真实元素：
 *    ?focus=m_xxx 深链的 scrollIntoView 定位与 #m_xxx 同文档跳转在 stub 下静默失效，
 *    恢复点=Rich 渲染链（rehype-raw）并入时；不新增依赖故按批8 Mermaid 先例登记降级）；
 *  - next/navigation useRouter.replace + next/link → props.onNavigate(path)（原路径形状
 *    "/memory/l2/{key}"、"/memory/l1?ref=..."、"/memory/resolve?id=..." 逐字保留，宿主切 tab；
 *    预览区 markdown 链接点击经容器 onClick 拦截转为 onNavigate——等价原 next/link 内部
 *    导航语义，登记为 Link 转译的一部分）；
 *  - lucide → @ant-design/icons：ArrowLeft→ArrowLeftOutlined、BookOpen→ReadOutlined、
 *    Bot→RobotOutlined、ClipboardList→SnippetsOutlined、FileText→FileTextOutlined、
 *    Hash→NumberOutlined、Layers→ApartmentOutlined、Library→DatabaseOutlined、
 *    Loader2→LoadingOutlined、MessageSquare→MessageOutlined、Network→ShareAltOutlined、
 *    NotebookPen→FormOutlined、PenLine/Pencil→EditOutlined、Save→SaveOutlined、
 *    Workflow→PartitionOutlined；
 *  - react-i18next → 组内 zhT.t；apiFetch(apiUrl(...)) → fetch('/api/v1/...')；
 *  - Tailwind → 内联样式；hover: 省略登记；[&_.data-footnote-backref]:hidden →
 *    组件内一次性 <style>（.memory-doc-content .data-footnote-backref{display:none}）。
 * 交互逐字未改。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ApartmentOutlined,
  ArrowLeftOutlined,
  DatabaseOutlined,
  EditOutlined,
  FileTextOutlined,
  FormOutlined,
  LoadingOutlined,
  MessageOutlined,
  NumberOutlined,
  PartitionOutlined,
  ReadOutlined,
  RobotOutlined,
  SaveOutlined,
  ShareAltOutlined,
  SnippetsOutlined,
} from "@ant-design/icons";
import type { CSSProperties } from "react";

import MarkdownRenderer from "../tutor/admin/MarkdownRenderer";
import MemoryRunPanel from "./MemoryRunPanel";
import { t } from "./zhT";

type Layer = "L2" | "L3";

// Each bullet ends with an HTML comment carrying the entry id
// (``<!--m_01HZK...-->``). The parser round-trips it but the rendered
// view should not show it as text — and we want clicking a same-doc
// m_xxx footnote to scroll the user back to the citing bullet. Convert
// the comment to an inline span with an ``id`` so:
//   * the rendered output is visually empty (zero-width span)
//   * ``#m_xxx`` hash navigation works within the doc
// Requires ``allowHtml`` on the markdown renderer (we set it below).
const _ENTRY_ANCHOR_RE = /\s*<!--\s*(m_[0-9A-HJKMNP-TV-Z]{26})\s*-->/g;

// Rewrite footnote definitions so the ref text becomes a markdown link.
//
// Four link targets, picked by (ref shape, current layer):
//   * ``surface:id``       → ``/memory/l1?ref=surface:id`` (L2 → L1 hop)
//   * ``m_<ULID>`` in L2   → ``#m_<ULID>`` (same-doc scroll; anchor
//     span above provides the target)
//   * ``m_<ULID>`` in L3   → ``/memory/resolve?id=m_<ULID>``
//     (legacy pre-pivot doc; resolver page redirects to the right L2)
//   * bare ``<surface>``   → ``/memory/l2/<surface>`` (L3 → L2 hop;
//     new design, L3 cites L2 files not L2 entries)
//
// The label regex is intentionally loose so this hits BOTH layouts —
// the new consolidated ``[^1]:`` and the legacy entry-keyed
// ``[^m_xxx]:`` — so docs that pre-date the merge step still get
// clickable footnotes until the next mode pass migrates them.
const _FOOTNOTE_DEF_LINKIFY_SURFACE_REF_RE =
  /^(\[\^[^\]]+\]:\s*)([a-z][a-z0-9_-]*):([A-Za-z0-9_-]+)\s*$/gm;
const _FOOTNOTE_DEF_LINKIFY_ENTRY_RE =
  /^(\[\^[^\]]+\]:\s*)(m_[0-9A-HJKMNP-TV-Z]{26})\s*$/gm;
// Bare surface name — keep tight (whitelist) so a typo can't accidentally
// turn into an L2 hub link.
const _L3_SURFACES = new Set([
  "chat",
  "notebook",
  "quiz",
  "kb",
  "book",
  "partner",
  "cowriter",
]);
const _FOOTNOTE_DEF_LINKIFY_BARE_RE =
  /^(\[\^[^\]]+\]:\s*)([a-z][a-z0-9_-]*)\s*$/gm;

function prepareDocForRender(md: string, layer: Layer): string {
  // Anchor injection MUST come before linkify so that ``m_xxx`` text on
  // a footnote-definition line is matched as a ref, not chewed up by the
  // anchor regex (which only matches inside HTML comments).
  const withAnchors = md.replace(
    _ENTRY_ANCHOR_RE,
    ' <span id="$1" class="memory-entry-anchor"></span>',
  );
  // ``surface:id`` must be tried before bare-surface because the bare
  // regex would otherwise match the surface prefix and leave ``:id``
  // dangling.
  const withSurfaceLinks = withAnchors.replace(
    _FOOTNOTE_DEF_LINKIFY_SURFACE_REF_RE,
    (_match, prefix: string, surface: string, entityId: string) => {
      const ref = `${surface}:${entityId}`;
      const url = `/memory/l1?ref=${encodeURIComponent(ref)}`;
      return `${prefix}[${ref}](${url})`;
    },
  );
  const withEntryLinks = withSurfaceLinks.replace(
    _FOOTNOTE_DEF_LINKIFY_ENTRY_RE,
    (_match, prefix: string, entryId: string) => {
      // L2: entry id refers to a bullet in *this* doc → local anchor.
      // L3: entry id refers to a bullet in some L2 doc → resolver page
      //     does the surface lookup, then redirects.
      const href =
        layer === "L2"
          ? `#${entryId}`
          : `/memory/resolve?id=${encodeURIComponent(entryId)}`;
      return `${prefix}[${entryId}](${href})`;
    },
  );
  // Bare surface name — only meaningful for L3 refs (new design).
  // Whitelist guards against linkifying arbitrary words that happen to
  // end up alone on a footnote definition line.
  return withEntryLinks.replace(
    _FOOTNOTE_DEF_LINKIFY_BARE_RE,
    (match, prefix: string, name: string) => {
      if (!_L3_SURFACES.has(name)) return match;
      return `${prefix}[${name}](/memory/l2/${name})`;
    },
  );
}

interface DocResponse {
  layer: Layer;
  key: string;
  content: string;
}

interface LineRowDTO {
  number: number;
  kind: "title" | "blank" | "section" | "bullet";
  text: string;
  entry_id: string | null;
  section: string | null;
}

interface DocOverview {
  layer: Layer;
  key: string;
  exists: boolean;
  updated_at: string | null;
  entry_count: number;
  backlog: number;
}

interface NavEntry {
  key: string;
  label: string;
  icon: typeof MessageOutlined;
}

const L2_NAV: NavEntry[] = [
  { key: "chat", icon: MessageOutlined, label: "Chat" },
  { key: "notebook", icon: FormOutlined, label: "Notebook" },
  { key: "quiz", icon: SnippetsOutlined, label: "Quiz" },
  { key: "kb", icon: ReadOutlined, label: "Knowledge base" },
  { key: "book", icon: DatabaseOutlined, label: "Book" },
  { key: "partner", icon: RobotOutlined, label: "Partner" },
  { key: "cowriter", icon: EditOutlined, label: "Co-writer" },
];

const L3_NAV: NavEntry[] = [
  { key: "recent", icon: ShareAltOutlined, label: "Recent summary" },
  { key: "profile", icon: ShareAltOutlined, label: "User profile" },
  { key: "scope", icon: ShareAltOutlined, label: "Knowledge scope" },
];

type ViewMode = "plain" | "lines";

export interface MemoryWorkbenchProps {
  layer: Layer;
  initialKey?: string;
  /**
   * Entry id to scroll into view + briefly highlight after the markdown
   * renders. Set by the deep-link contract (``?focus=m_xxx``) when the
   * user lands here from an L3 footnote click.
   */
  initialFocus?: string;
  /** 原仓 Link/useRouter 语义转译：接收原路径形状，宿主切 tab / 更新深链 state。 */
  onNavigate?: (path: string) => void;
}

const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";
const CARD = "var(--card, #ffffff)";
const MUTED = "var(--muted, #f5f5f5)";
const PRIMARY = "var(--primary, #1677ff)";
const PRIMARY_FG = "var(--primary-foreground, #ffffff)";
const BG = "var(--background, #ffffff)";

export function MemoryWorkbench({
  layer,
  initialKey,
  initialFocus,
  onNavigate,
}: MemoryWorkbenchProps) {
  const nav = layer === "L2" ? L2_NAV : L3_NAV;
  const [docKey, setDocKey] = useState<string>(initialKey || nav[0].key);

  useEffect(() => {
    if (initialKey) setDocKey(initialKey);
  }, [initialKey]);

  const [overview, setOverview] = useState<Record<string, DocOverview>>({});
  const [content, setContent] = useState("");
  const [lines, setLines] = useState<LineRowDTO[]>([]);
  const [view, setView] = useState<ViewMode>("plain");
  const [editing, setEditing] = useState(false);
  const [editorValue, setEditorValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");
  // Focus is one-shot — once we've scrolled-to + flashed the anchor we
  // don't want subsequent content reloads (e.g. after a Run) to keep
  // re-scrolling. ``initialFocus`` seeds it; the effect clears it.
  const [pendingFocus, setPendingFocus] = useState<string | null>(
    initialFocus || null,
  );
  const previewRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (initialFocus) setPendingFocus(initialFocus);
  }, [initialFocus]);

  const loadOverview = useCallback(async () => {
    const res = await fetch("/api/v1/memory/overview");
    const data = await res.json();
    const map: Record<string, DocOverview> = {};
    for (const d of data.docs || []) {
      if (d.layer === layer) map[d.key] = d;
    }
    setOverview(map);
  }, [layer]);

  const loadDoc = useCallback(async () => {
    const res = await fetch(`/api/v1/memory/doc/${layer}/${docKey}`);
    const data = (await res.json()) as DocResponse;
    setContent(data?.content || "");
    setEditorValue(data?.content || "");
  }, [layer, docKey]);

  const loadLines = useCallback(async () => {
    const res = await fetch(`/api/v1/memory/doc/${layer}/${docKey}/lines`);
    const data = (await res.json()) as { lines: LineRowDTO[] };
    setLines(data?.lines || []);
  }, [layer, docKey]);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);
  useEffect(() => {
    void loadDoc();
    void loadLines();
  }, [loadDoc, loadLines]);
  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(""), 2200);
    return () => clearTimeout(id);
  }, [toast]);

  // Scroll-to + flash the focused entry once the markdown is in the
  // DOM. Markdown renders via a dynamic import → we can't fire on
  // ``content`` change alone; wait a frame so the anchor span exists.
  // ``editing`` mode hides the rendered preview, so skip then.
  useEffect(() => {
    if (!pendingFocus || editing) return;
    if (!content || !previewRef.current) return;
    const anchorId = pendingFocus.startsWith("m_")
      ? pendingFocus
      : `m_${pendingFocus}`;
    let cancelled = false;
    const id = window.setTimeout(() => {
      if (cancelled) return;
      const span = document.getElementById(anchorId);
      // Highlight the bullet, not the zero-width anchor span.
      const li = (span?.closest("li") as HTMLElement | null) ?? span;
      if (!li) return;
      li.scrollIntoView({ block: "center", behavior: "smooth" });
      const prev = {
        outline: li.style.outline,
        outlineOffset: li.style.outlineOffset,
        borderRadius: li.style.borderRadius,
        transition: li.style.transition,
      };
      li.style.outline = "2px solid var(--primary)";
      li.style.outlineOffset = "4px";
      li.style.borderRadius = "6px";
      li.style.transition = "outline-color 1.4s ease-out";
      const clear = window.setTimeout(() => {
        li.style.outline = prev.outline;
        li.style.outlineOffset = prev.outlineOffset;
        li.style.borderRadius = prev.borderRadius;
        li.style.transition = prev.transition;
      }, 1800);
      // Consume the focus token so reloads don't re-trigger.
      setPendingFocus(null);
      return () => window.clearTimeout(clear);
    }, 80);
    return () => {
      cancelled = true;
      window.clearTimeout(id);
    };
  }, [pendingFocus, content, editing]);

  const selectDoc = useCallback(
    (next: string) => {
      if (next === docKey) return;
      setDocKey(next);
      // Reflect selection in the URL so refresh + share keep state.
      // （转译：原 router.replace → onNavigate，路径形状逐字保留）
      onNavigate?.(layer === "L2" ? `/memory/l2/${next}` : `/memory/l3/${next}`);
    },
    [docKey, layer, onNavigate],
  );

  const saveDoc = useCallback(async () => {
    setSaving(true);
    try {
      await fetch(`/api/v1/memory/doc/${layer}/${docKey}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: editorValue }),
      });
      setContent(editorValue);
      setEditing(false);
      setToast(t("Saved"));
      void loadLines();
    } catch (e) {
      setToast(e instanceof Error ? e.message : t("Save failed"));
    } finally {
      setSaving(false);
    }
  }, [editorValue, layer, docKey, loadLines]);

  const nicelabel = useMemo(() => {
    const entry = nav.find((n) => n.key === docKey);
    return entry ? t(entry.label) : docKey;
  }, [docKey, nav]);

  const handleRunComplete = useCallback(() => {
    void loadDoc();
    void loadLines();
    void loadOverview();
  }, [loadDoc, loadLines, loadOverview]);

  // 预览区链接点击拦截（原 next/link SPA 导航语义转译；登记见头注）：
  //  * href 以 "/memory/" 开头 → onNavigate（L1 hop / resolve / L2 hop）
  //  * href 以 "#m_" 开头 → 同文档滚动（stub 不渲染 anchor 时静默失效，同深链降级）
  const handlePreviewClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const link = (e.target as HTMLElement | null)?.closest("a");
      if (!link) return;
      const href = link.getAttribute("href") || "";
      if (href.startsWith("/memory/")) {
        e.preventDefault();
        onNavigate?.(href);
        return;
      }
      if (href.startsWith("#m_")) {
        e.preventDefault();
        const span = document.getElementById(href.slice(1));
        const li = (span?.closest("li") as HTMLElement | null) ?? span;
        if (li) {
          li.scrollIntoView({ block: "center", behavior: "smooth" });
        }
      }
    },
    [onNavigate],
  );

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        minHeight: 0,
        flexDirection: "column",
        gap: 12,
        padding: "16px 40px",
        boxSizing: "border-box",
      }}
    >
      {/* 等价原 Tailwind [&_.data-footnote-backref]:hidden（隐藏 remark-gfm 自带的 ↩ 回跳箭头） */}
      <style>{`.memory-doc-content .data-footnote-backref{display:none !important;}`}</style>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <Breadcrumb layer={layer} label={nicelabel} onNavigate={onNavigate} />
        <LayerSwitcher current={layer} onNavigate={onNavigate} />
      </div>

      <div
        style={{
          display: "grid",
          minHeight: 0,
          flex: 1,
          gridTemplateColumns: "180px minmax(0, 1fr) 360px",
          gap: 16,
        }}
      >
        {/* ── Left rail ── */}
        <aside
          style={{
            minHeight: 0,
            overflowY: "auto",
            borderRadius: 16,
            border: `1px solid ${BORDER}`,
            background: CARD,
            padding: 8,
            boxSizing: "border-box",
          }}
        >
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 2 }}>
            {nav.map(({ key, icon: Icon, label }) => {
              const doc = overview[key];
              const active = key === docKey;
              return (
                <li key={key} style={{ listStyle: "none" }}>
                  <button
                    type="button"
                    onClick={() => selectDoc(key)}
                    style={{
                      display: "flex",
                      width: "100%",
                      alignItems: "center",
                      gap: 8,
                      borderRadius: 6,
                      padding: "6px 8px",
                      fontSize: 12.5,
                      textAlign: "left",
                      border: "none",
                      cursor: "pointer",
                      background: active ? MUTED : "transparent",
                      color: active ? FG : MUTED_FG,
                    }}
                  >
                    <Icon style={{ fontSize: 14, flexShrink: 0 }} />
                    <span
                      style={{
                        flex: 1,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {t(label)}
                    </span>
                    {doc?.exists && (
                      <span
                        style={{
                          borderRadius: 999,
                          background: BG,
                          padding: "2px 6px",
                          fontSize: 10,
                          color: MUTED_FG,
                        }}
                      >
                        {doc.entry_count}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        {/* ── Center: preview ── */}
        <section style={{ display: "flex", minHeight: 0, flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
            <ViewSwitch view={view} setView={setView} />
            {!editing ? (
              <button
                type="button"
                onClick={() => setEditing(true)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  borderRadius: 6,
                  border: `1px solid ${BORDER}`,
                  background: BG,
                  padding: "4px 10px",
                  fontSize: 12,
                  cursor: "pointer",
                  color: "inherit",
                }}
              >
                <EditOutlined style={{ fontSize: 14 }} />
                {t("Edit raw")}
              </button>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <button
                  type="button"
                  onClick={() => {
                    setEditorValue(content);
                    setEditing(false);
                  }}
                  style={{
                    borderRadius: 6,
                    border: `1px solid ${BORDER}`,
                    background: BG,
                    padding: "4px 12px",
                    fontSize: 12,
                    cursor: "pointer",
                    color: "inherit",
                  }}
                >
                  {t("Cancel")}
                </button>
                <button
                  type="button"
                  onClick={() => void saveDoc()}
                  disabled={saving}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    borderRadius: 6,
                    background: PRIMARY,
                    padding: "4px 12px",
                    fontSize: 12,
                    color: PRIMARY_FG,
                    border: "none",
                    cursor: saving ? "wait" : "pointer",
                    opacity: saving ? 0.5 : 1,
                  }}
                >
                  {saving ? (
                    <LoadingOutlined style={{ fontSize: 14 }} />
                  ) : (
                    <SaveOutlined style={{ fontSize: 14 }} />
                  )}
                  {t("Save")}
                </button>
              </div>
            )}
          </div>
          <div
            ref={previewRef}
            style={{
              minHeight: 0,
              flex: 1,
              overflowY: "auto",
              borderRadius: 16,
              border: `1px solid ${BORDER}`,
              background: CARD,
              padding: 20,
              boxSizing: "border-box",
            }}
          >
            {editing ? (
              <textarea
                value={editorValue}
                onChange={(e) => setEditorValue(e.target.value)}
                style={{
                  height: "60vh",
                  width: "100%",
                  resize: "none",
                  borderRadius: 6,
                  border: `1px solid ${BORDER}`,
                  background: BG,
                  padding: 12,
                  fontFamily: "monospace",
                  fontSize: 12.5,
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            ) : view === "lines" ? (
              <LineNumberedView lines={lines} />
            ) : content.trim().length > 0 ? (
              // The wrapper hides the default footnote backref arrow
              // (``data-footnote-backref``). Without this the rendered
              // doc has two clickable elements per footnote: the L1
              // text link we inject (correct) and the ↩ icon
              // remark-gfm auto-generates that jumps back to the
              // citation marker (confusing — users expect every link
              // in the footnote to go to L1).
              <div className="memory-doc-content" onClick={handlePreviewClick}>
                <MarkdownRenderer
                  content={prepareDocForRender(content, layer)}
                  variant="prose"
                  className="text-[14px]"
                  allowHtml
                />
              </div>
            ) : (
              <EmptyState />
            )}
          </div>
          {toast && (
            <div
              style={{
                alignSelf: "flex-start",
                borderRadius: 6,
                border: "1px solid color-mix(in srgb, var(--primary, #1677ff) 30%, transparent)",
                background: "color-mix(in srgb, var(--primary, #1677ff) 10%, transparent)",
                padding: "4px 12px",
                fontSize: 11.5,
                color: PRIMARY,
              }}
            >
              {toast}
            </div>
          )}
        </section>

        {/* ── Right: LLM work area ── */}
        <aside style={{ minHeight: 0 }}>
          <MemoryRunPanel
            layer={layer}
            docKey={docKey}
            onRunComplete={handleRunComplete}
            onDocUpdated={handleRunComplete}
          />
        </aside>
      </div>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────

function Breadcrumb({
  layer,
  label,
  onNavigate,
}: {
  layer: Layer;
  label: string;
  onNavigate?: (path: string) => void;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5 }}>
      <button
        type="button"
        onClick={() => onNavigate?.("/memory")}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
          borderRadius: 6,
          padding: "4px 8px",
          color: MUTED_FG,
          border: "none",
          background: "transparent",
          cursor: "pointer",
        }}
      >
        <ArrowLeftOutlined style={{ fontSize: 14 }} />
        {t("Memory")}
      </button>
      <span style={{ color: MUTED_FG }}>/</span>
      <span style={{ display: "inline-flex", alignItems: "center", gap: 6, color: FG }}>
        {layer === "L2" ? (
          <PartitionOutlined style={{ fontSize: 14 }} />
        ) : (
          <ShareAltOutlined style={{ fontSize: 14 }} />
        )}
        {layer === "L2"
          ? t("L2 · Per-surface summaries")
          : t("L3 · Cross-surface knowledge")}
      </span>
      <span style={{ color: MUTED_FG }}>/</span>
      <span style={{ color: FG }}>{label}</span>
    </div>
  );
}

function LayerSwitcher({
  current,
  onNavigate,
}: {
  current: Layer;
  onNavigate?: (path: string) => void;
}) {
  // L1 page is a single workbench (no per-key route); L2/L3 hubs land
  // on /memory/l2 and /memory/l3 which list the surfaces / slots.
  const entries: {
    key: "L1" | Layer;
    href: string;
    icon: typeof MessageOutlined;
    label: string;
  }[] = [
    { key: "L1", href: "/memory/l1", icon: ApartmentOutlined, label: t("L1") },
    { key: "L2", href: "/memory/l2", icon: PartitionOutlined, label: t("L2") },
    { key: "L3", href: "/memory/l3", icon: ShareAltOutlined, label: t("L3") },
  ];
  return (
    <nav
      style={{
        display: "flex",
        alignItems: "center",
        gap: 2,
        borderRadius: 999,
        border: `1px solid ${BORDER}`,
        background: CARD,
        padding: 2,
      }}
    >
      {entries.map(({ key, href, icon: Icon, label }) => {
        const active = key === current;
        if (active) {
          return (
            <span
              key={key}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                borderRadius: 999,
                background: MUTED,
                padding: "2px 10px",
                fontSize: 11.5,
                fontWeight: 500,
                color: FG,
              }}
            >
              <Icon style={{ fontSize: 12 }} />
              {label}
            </span>
          );
        }
        return (
          <button
            key={key}
            type="button"
            onClick={() => onNavigate?.(href)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              borderRadius: 999,
              padding: "2px 10px",
              fontSize: 11.5,
              color: MUTED_FG,
              border: "none",
              background: "transparent",
              cursor: "pointer",
            }}
          >
            <Icon style={{ fontSize: 12 }} />
            {label}
          </button>
        );
      })}
    </nav>
  );
}

function ViewSwitch({
  view,
  setView,
}: {
  view: ViewMode;
  setView: (v: ViewMode) => void;
}) {
  const items: { key: ViewMode; label: string; icon: typeof FileTextOutlined }[] = [
    { key: "plain", label: t("Rendered"), icon: FileTextOutlined },
    { key: "lines", label: t("Line numbers"), icon: NumberOutlined },
  ];
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        borderRadius: 8,
        border: `1px solid ${BORDER}`,
        background: BG,
        padding: 4,
      }}
    >
      {items.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          type="button"
          onClick={() => setView(key)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            borderRadius: 6,
            padding: "4px 10px",
            fontSize: 11.5,
            border: "none",
            cursor: "pointer",
            background: view === key ? MUTED : "transparent",
            color: view === key ? FG : MUTED_FG,
          }}
        >
          <Icon style={{ fontSize: 14 }} />
          {label}
        </button>
      ))}
    </div>
  );
}

function LineNumberedView({ lines }: { lines: LineRowDTO[] }) {
  if (lines.length === 0) return <EmptyState />;
  const width = Math.max(2, String(lines[lines.length - 1].number).length);
  return (
    <pre
      style={{
        overflowX: "auto",
        whiteSpace: "pre-wrap",
        fontFamily: "monospace",
        fontSize: 12.5,
        lineHeight: 1.625,
        color: FG,
        margin: 0,
      }}
    >
      {lines.map((line) => {
        const num = String(line.number).padStart(width, " ");
        const muted = line.kind === "blank" || line.kind === "title";
        return (
          <div
            key={line.number}
            style={{ color: muted ? MUTED_FG : FG }}
          >
            <span
              style={{
                userSelect: "none",
                paddingRight: 12,
                color: MUTED_FG,
              }}
            >
              {num}:
            </span>
            {line.text || " "}
          </div>
        );
      })}
    </pre>
  );
}

function EmptyState() {
  return (
    <div
      style={{
        display: "grid",
        height: 300,
        placeItems: "center",
        textAlign: "center",
        fontSize: 13,
        color: MUTED_FG,
      }}
    >
      <div style={{ maxWidth: 384, display: "flex", flexDirection: "column", gap: 8 }}>
        <PartitionOutlined style={{ margin: "0 auto", fontSize: 24, opacity: 0.6 }} />
        <p style={{ margin: 0 }}>
          {t("Empty. Click Update to extract facts from your traces.")}
        </p>
      </div>
    </div>
  );
}

export default MemoryWorkbench;
