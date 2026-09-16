/**
 * 桌面同名件 1:1（复制自 DeepTutor 原仓 web/components/memory/MemoryL1Workbench.tsx，280 行）。
 * 替换点：
 *  - 删除 "use client"；next/link → props.onNavigate(path) 回调（MemoryAdmin 单路由多 tab，
 *    原 href 形状 "/memory/l2" 等逐字保留、由宿主映射为 tab 切换；登记：壳 deep-link 契约转译）；
 *  - lucide → @ant-design/icons：ArrowLeft→ArrowLeftOutlined、BookOpen→ReadOutlined、
 *    Bot→RobotOutlined、ClipboardList→SnippetsOutlined、Layers→ApartmentOutlined、
 *    Library→DatabaseOutlined、MessageSquare→MessageOutlined、Network→ShareAltOutlined、
 *    NotebookPen→FormOutlined、PenLine→EditOutlined、Workflow→PartitionOutlined；
 *  - react-i18next → 组内 zhT.t 中文直出；L1View 调用点随新签名去掉 t prop；
 *  - apiFetch(apiUrl(...)) → fetch('/api/v1/...')；Tailwind → 内联样式（hover: 省略登记）；
 *    amber 待提交徽标 → #f59e0b 系内联色值。
 * 交互逐字未改。
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApartmentOutlined,
  ArrowLeftOutlined,
  PartitionOutlined,
  ReadOutlined,
  RobotOutlined,
  ShareAltOutlined,
  SnippetsOutlined,
  DatabaseOutlined,
  FormOutlined,
  MessageOutlined,
  EditOutlined,
} from "@ant-design/icons";
import type { CSSProperties } from "react";

import { L1View } from "./MemorySection";
import { t } from "./zhT";

type Surface =
  | "chat"
  | "notebook"
  | "quiz"
  | "kb"
  | "book"
  | "partner"
  | "cowriter";

interface NavEntry {
  key: Surface;
  label: string;
  icon: typeof MessageOutlined;
}

const L1_NAV: NavEntry[] = [
  { key: "chat", icon: MessageOutlined, label: "Chat" },
  { key: "notebook", icon: FormOutlined, label: "Notebook" },
  { key: "quiz", icon: SnippetsOutlined, label: "Quiz" },
  { key: "kb", icon: ReadOutlined, label: "Knowledge base" },
  { key: "book", icon: DatabaseOutlined, label: "Book" },
  { key: "partner", icon: RobotOutlined, label: "Partner" },
  { key: "cowriter", icon: EditOutlined, label: "Co-writer" },
];

interface SnapshotResponse {
  surface: Surface;
  entities: unknown[];
  pending_changes: unknown[];
}

export interface MemoryL1WorkbenchProps {
  initialSurface?: Surface;
  initialFocusRef?: string;
  /** 原仓 Link 语义转译：接收 "/memory"、"/memory/l2" 等原路径形状，宿主切 tab。 */
  onNavigate?: (path: string) => void;
}

const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";
const CARD = "var(--card, #ffffff)";
const MUTED = "var(--muted, #f5f5f5)";
const PRIMARY = "var(--primary, #1677ff)";

export function MemoryL1Workbench({
  initialSurface,
  initialFocusRef,
  onNavigate,
}: MemoryL1WorkbenchProps) {
  // ``initialSurface`` and ``initialFocusRef`` seed the picker + entity
  // highlight on first mount. The URL only drives initial state; once the
  // user clicks around the rail it's all local state again.
  const [surface, setSurface] = useState<Surface>(initialSurface || "notebook");
  const [counts, setCounts] = useState<Record<Surface, number>>(
    {} as Record<Surface, number>,
  );
  const [pending, setPending] = useState<Record<Surface, number>>(
    {} as Record<Surface, number>,
  );
  const [focusRef, setFocusRef] = useState<string | null>(
    initialFocusRef ?? null,
  );
  const [toast, setToast] = useState("");

  // Fetch counts + pending badges for the left rail in parallel.
  const loadCounts = useCallback(async () => {
    const entries = await Promise.all(
      L1_NAV.map(async ({ key }) => {
        try {
          const res = await fetch(`/api/v1/memory/snapshot/${key}`);
          const data = (await res.json()) as SnapshotResponse;
          return [
            key,
            data?.entities?.length ?? 0,
            data?.pending_changes?.length ?? 0,
          ] as const;
        } catch {
          return [key, 0, 0] as const;
        }
      }),
    );
    setCounts(
      Object.fromEntries(entries.map(([k, n]) => [k, n])) as Record<
        Surface,
        number
      >,
    );
    setPending(
      Object.fromEntries(entries.map(([k, , p]) => [k, p])) as Record<
        Surface,
        number
      >,
    );
  }, []);

  useEffect(() => {
    void loadCounts();
  }, [loadCounts]);

  // Re-fetch counts when the tab regains focus so the rail stays in sync.
  useEffect(() => {
    const refetch = () => {
      if (typeof document !== "undefined" && document.hidden) return;
      void loadCounts();
    };
    window.addEventListener("focus", refetch);
    document.addEventListener("visibilitychange", refetch);
    return () => {
      window.removeEventListener("focus", refetch);
      document.removeEventListener("visibilitychange", refetch);
    };
  }, [loadCounts]);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(""), 2500);
    return () => clearTimeout(id);
  }, [toast]);

  const nicelabel = useMemo(() => {
    const entry = L1_NAV.find((n) => n.key === surface);
    return entry ? t(entry.label) : surface;
  }, [surface]);

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
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <Breadcrumb label={nicelabel} onNavigate={onNavigate} />
        <LayerSwitcher onNavigate={onNavigate} />
      </div>

      <div
        style={{
          display: "grid",
          minHeight: 0,
          flex: 1,
          gridTemplateColumns: "180px minmax(0, 1fr)",
          gap: 16,
        }}
      >
        {/* Left rail */}
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
            {L1_NAV.map(({ key, icon: Icon, label }) => {
              const active = key === surface;
              const c = counts[key];
              const p = pending[key];
              const btnStyle: CSSProperties = {
                display: "flex",
                width: "100%",
                alignItems: "center",
                gap: 8,
                borderRadius: 6,
                padding: "6px 8px",
                textAlign: "left",
                fontSize: 12.5,
                border: "none",
                cursor: "pointer",
                background: active ? MUTED : "transparent",
                color: active ? FG : MUTED_FG,
              };
              return (
                <li key={key} style={{ listStyle: "none" }}>
                  <button
                    type="button"
                    onClick={() => {
                      setSurface(key);
                      setFocusRef(null);
                    }}
                    style={btnStyle}
                  >
                    <Icon
                      style={{ fontSize: 14, flexShrink: 0 }}
                    />
                    <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {t(label)}
                    </span>
                    {p > 0 ? (
                      <span
                        style={{
                          borderRadius: 999,
                          background: "rgba(245,158,11,0.1)",
                          padding: "2px 6px",
                          fontSize: 10,
                          color: "#d97706",
                        }}
                        title={t("{{n}} pending", { n: p })}
                      >
                        {p}
                      </span>
                    ) : typeof c === "number" ? (
                      <span
                        style={{
                          borderRadius: 999,
                          background: "var(--background, #ffffff)",
                          padding: "2px 6px",
                          fontSize: 10,
                          color: MUTED_FG,
                        }}
                      >
                        {c}
                      </span>
                    ) : null}
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        {/* Center: snapshot / changes / kb-queries preview */}
        <section
          style={{
            minHeight: 0,
            overflowY: "auto",
            borderRadius: 16,
            border: `1px solid ${BORDER}`,
            background: CARD,
            padding: 20,
            boxSizing: "border-box",
          }}
        >
          <L1View
            surface={surface}
            onSurfaceChange={(s) => {
              setSurface(s as Surface);
              setFocusRef(null);
            }}
            focusRef={focusRef}
            onClearFocus={() => setFocusRef(null)}
            onToast={setToast}
            compact
          />
        </section>
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
    </div>
  );
}

function LayerSwitcher({
  onNavigate,
}: {
  onNavigate?: (path: string) => void;
}) {
  // L1 is the current page, so it stays as a non-link pill; L2 + L3
  // link to their respective hubs.
  const entries: {
    key: "L1" | "L2" | "L3";
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
        const active = key === "L1";
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

function Breadcrumb({
  label,
  onNavigate,
}: {
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
        <ApartmentOutlined style={{ fontSize: 14 }} />
        {t("L1 · Workspace mirror")}
      </span>
      <span style={{ color: MUTED_FG }}>/</span>
      <span style={{ color: FG }}>{label}</span>
    </div>
  );
}

export default MemoryL1Workbench;
