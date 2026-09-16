/**
 * 桌面同名件 1:1（复制自 DeepTutor 原仓 web/components/memory/MemoryHub.tsx，265 行）。
 * 替换点：
 *  - 删除 "use client"；next/link → props.onNavigate(path)（LayerCard/GraphCallout 的
 *    "/memory/l1" 等原路径形状逐字保留，宿主切 tab）；"Memory settings" 链接目标
 *    /settings/memory 在 tupu 无对应 tab/路由（原仓独立设置页，超出本批 8 壳+6 组件清单），
 *    与 entityDeepLinkUrl 同策略保留原 href 形状于原生 <a>（点击落 tupu 404 兜底，登记：
 *    待 settings/memory 批次并入时改为 onNavigate）；
 *  - lucide → @ant-design/icons：ArrowRight→ArrowRightOutlined、Brain→BulbOutlined
 *    （先例 MemoryPicker）、Layers→ApartmentOutlined、Network→ShareAltOutlined、
 *    RefreshCw→ReloadOutlined、Sparkles→ThunderboltOutlined（先例）、
 *    Workflow→PartitionOutlined；
 *  - react-i18next → 组内 zhT.t；apiFetch(apiUrl(...)) → fetch('/api/v1/...')；
 *  - Tailwind → 内联样式；hover:/group-hover: 伪类按先例省略并在此登记。
 * 交互逐字未改。
 */
import { useCallback, useEffect, useState } from "react";
import {
  ApartmentOutlined,
  ArrowRightOutlined,
  BulbOutlined,
  PartitionOutlined,
  ReloadOutlined,
  ShareAltOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

import MemoryArchivedBanner from "./MemoryArchivedBanner";
import { t } from "./zhT";

interface DocOverview {
  layer: "L2" | "L3";
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

interface SnapshotResponse {
  surface: string;
  entities: unknown[];
}

const SURFACES = [
  "chat",
  "notebook",
  "quiz",
  "kb",
  "book",
  "partner",
  "cowriter",
] as const;

const L3_VISIBLE = ["recent", "profile", "scope"] as const;

export interface MemoryHubProps {
  onNavigate?: (path: string) => void;
}

const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";
const CARD = "var(--card, #ffffff)";
const PRIMARY = "var(--primary, #1677ff)";
const BG = "var(--background, #ffffff)";

export function MemoryHub({ onNavigate }: MemoryHubProps = {}) {
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [l1Total, setL1Total] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ovRes, ...l1Counts] = await Promise.all([
        fetch("/api/v1/memory/overview").then((r) => r.json()),
        ...SURFACES.map((s) =>
          fetch(`/api/v1/memory/snapshot/${s}`)
            .then((r) => r.json())
            .then((d: SnapshotResponse) => d?.entities?.length ?? 0)
            .catch(() => 0),
        ),
      ]);
      setOverview(ovRes as OverviewResponse);
      setL1Total(l1Counts.reduce<number>((acc, n) => acc + (n as number), 0));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const l2Docs = (overview?.docs || []).filter((d) => d.layer === "L2");
  const l3Docs = (overview?.docs || []).filter(
    (d) => d.layer === "L3" && d.key !== "preferences",
  );
  const l2Total = l2Docs.reduce((acc, d) => acc + d.entry_count, 0);
  const l3Total = l3Docs.reduce((acc, d) => acc + d.entry_count, 0);
  const latestBackup = overview?.backups?.[overview.backups.length - 1] ?? null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 40 }}>
      <header style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span
            style={{
              display: "grid",
              height: 40,
              width: 40,
              placeItems: "center",
              borderRadius: 12,
              background: "color-mix(in srgb, var(--primary, #1677ff) 10%, transparent)",
              color: PRIMARY,
            }}
          >
            <BulbOutlined style={{ fontSize: 20 }} />
          </span>
          <h1
            style={{
              fontSize: 28,
              fontWeight: 600,
              letterSpacing: "-0.01em",
              color: FG,
              margin: 0,
              fontFamily: "Georgia, 'Times New Roman', serif",
            }}
          >
            {t("Memory")}
          </h1>
        </div>
        <p
          style={{
            maxWidth: 672,
            fontSize: 14,
            color: MUTED_FG,
            margin: 0,
          }}
        >
          {t(
            "Everything DeepTutor remembers about you, organised across three layers. Click into any layer to inspect or curate it.",
          )}
        </p>
        <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 12, color: MUTED_FG }}>
          <button
            type="button"
            onClick={() => void load()}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              borderRadius: 6,
              border: `1px solid ${BORDER}`,
              background: BG,
              padding: "4px 10px",
              cursor: "pointer",
              color: "inherit",
            }}
          >
            <ReloadOutlined spin={loading} style={{ fontSize: 12 }} />
            {t("Refresh")}
          </button>
          {/* 原仓 Link → /settings/memory（tupu 无对应路由，保留原 href，登记见头注） */}
          <a
            href="/settings/memory"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              borderRadius: 6,
              border: "1px solid transparent",
              padding: "4px 10px",
              color: "inherit",
              textDecoration: "none",
            }}
          >
            {t("Memory settings")}
          </a>
        </div>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr)",
          gap: 20,
        }}
        className="memory-hub-grid"
      >
        <LayerCard
          href="/memory/l1"
          icon={ApartmentOutlined}
          title={t("L1 · Workspace mirror")}
          tag={t("Live")}
          stat={l1Total === null ? "…" : l1Total.toLocaleString()}
          statLabel={t("entities tracked")}
          detail={t(
            "Snapshot of your live workspace across {{n}} surfaces. Refresh to record changes.",
            { n: SURFACES.length },
          )}
          onNavigate={onNavigate}
        />
        <LayerCard
          href="/memory/l2"
          icon={PartitionOutlined}
          title={t("L2 · Per-surface summaries")}
          tag={t("Curated")}
          stat={l2Total.toLocaleString()}
          statLabel={t("facts across {{n}} surfaces", {
            n: l2Docs.length || SURFACES.length,
          })}
          detail={t(
            "Surface-specific facts extracted by the consolidator. Run Update / Audit / Dedup per doc.",
          )}
          onNavigate={onNavigate}
        />
        <LayerCard
          href="/memory/l3"
          icon={ShareAltOutlined}
          title={t("L3 · Cross-surface knowledge")}
          tag={t("Synthesis")}
          stat={l3Total.toLocaleString()}
          statLabel={t("propositions across {{n}} slots", {
            n: l3Docs.length || L3_VISIBLE.length,
          })}
          detail={t(
            "Cross-surface synthesis: profile, recent timeline, knowledge scope. Hedged claims with L2 evidence.",
          )}
          onNavigate={onNavigate}
        />
      </div>

      <GraphCallout onNavigate={onNavigate} />

      <MemoryArchivedBanner latestBackup={latestBackup} variant="compact" />
    </div>
  );
}

function GraphCallout({ onNavigate }: { onNavigate?: (path: string) => void }) {
  return (
    <button
      type="button"
      onClick={() => onNavigate?.("/memory/graph")}
      style={{
        position: "relative",
        display: "block",
        width: "100%",
        overflow: "hidden",
        borderRadius: 16,
        border: `1px solid ${BORDER}`,
        background: CARD,
        padding: 24,
        cursor: "pointer",
        textAlign: "left",
      }}
    >
      <div
        style={{
          pointerEvents: "none",
          position: "absolute",
          inset: 0,
          opacity: 0.8,
          background:
            "radial-gradient(ellipse 60% 80% at 92% 50%, color-mix(in srgb, var(--primary, #1677ff) 16%, transparent), transparent 70%)",
        }}
      />
      <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 20 }}>
        <span
          style={{
            display: "grid",
            height: 48,
            width: 48,
            flexShrink: 0,
            placeItems: "center",
            borderRadius: 12,
            background: "color-mix(in srgb, var(--primary, #1677ff) 10%, transparent)",
            color: PRIMARY,
          }}
        >
          <ThunderboltOutlined style={{ fontSize: 20 }} />
        </span>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: FG, margin: 0 }}>
              {t("Memory graph")}
            </h3>
            <span
              style={{
                borderRadius: 999,
                border: `1px solid ${BORDER}`,
                background: "color-mix(in srgb, var(--background, #ffffff) 60%, transparent)",
                padding: "2px 8px",
                fontSize: 10.5,
                fontWeight: 500,
                textTransform: "uppercase",
                letterSpacing: "0.025em",
                color: MUTED_FG,
              }}
            >
              {t("New")}
            </span>
          </div>
          <p
            style={{
              marginTop: 4,
              fontSize: 13,
              lineHeight: 1.625,
              color: MUTED_FG,
              marginBottom: 0,
            }}
          >
            {t(
              "See all three layers at once — L3 synthesis at the centre, L2 facts in the middle, L1 traces on the outside. Hover any node for a preview.",
            )}
          </p>
        </div>
        <ArrowRightOutlined
          style={{ flexShrink: 0, fontSize: 16, color: PRIMARY }}
        />
      </div>
    </button>
  );
}

interface LayerCardProps {
  href: string;
  icon: typeof ApartmentOutlined;
  title: string;
  tag: string;
  stat: string;
  statLabel: string;
  detail: string;
  onNavigate?: (path: string) => void;
}

function LayerCard({
  href,
  icon: Icon,
  title,
  tag,
  stat,
  statLabel,
  detail,
  onNavigate,
}: LayerCardProps) {
  return (
    <button
      type="button"
      onClick={() => onNavigate?.(href)}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 16,
        borderRadius: 16,
        border: `1px solid ${BORDER}`,
        background: CARD,
        padding: 24,
        cursor: "pointer",
        textAlign: "left",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <span
          style={{
            display: "grid",
            height: 36,
            width: 36,
            placeItems: "center",
            borderRadius: 8,
            background: "color-mix(in srgb, var(--primary, #1677ff) 10%, transparent)",
            color: PRIMARY,
          }}
        >
          <Icon style={{ fontSize: 16 }} />
        </span>
        <span
          style={{
            borderRadius: 999,
            border: `1px solid ${BORDER}`,
            background: BG,
            padding: "2px 8px",
            fontSize: 10.5,
            fontWeight: 500,
            textTransform: "uppercase",
            letterSpacing: "0.025em",
            color: MUTED_FG,
          }}
        >
          {tag}
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, color: FG, margin: 0 }}>{title}</h2>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.01em", color: FG }}>
          {stat}
        </span>
        <span style={{ fontSize: 12, color: MUTED_FG }}>{statLabel}</span>
      </div>
      <p style={{ fontSize: 13, lineHeight: 1.625, color: MUTED_FG, margin: 0 }}>{detail}</p>
      <div
        style={{
          marginTop: "auto",
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
          fontSize: 12,
          fontWeight: 500,
          color: PRIMARY,
        }}
      >
        <span>{tag}</span>
        <ArrowRightOutlined style={{ fontSize: 14 }} />
      </div>
    </button>
  );
}

export default MemoryHub;
