/**
 * 复刻自 DeepTutor 原仓 web/components/settings/SettingsHub.tsx（整件 1:1，批5 5.2 壳族）。
 * 替换点：next/link → react-router-dom Link（href→to）；lucide（Rocket/ChevronRight、
 * category.icon）→ @ant-design/icons（RocketOutlined/RightOutlined、icon 以 style.fontSize
 * 调用——settings-nav 落盘侧同为 antd 图标）；react-i18next → tupu 无 i18next（中文产品），
 * tr 恒取 Lang.zh（原仓按 i18n.language 判定）；apiFetch(apiUrl(p)) → fetch(p)（恒等内联）；
 * Tailwind → 内联样式 + 页内 <style>（grid 响应式/group-hover 进样式块，颜色 token 兜底）。
 * 结构/data-tour/data-testid/modelStats·network 预览逻辑逐字保留。
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { RocketOutlined, RightOutlined } from "@ant-design/icons";

import {
  serviceReadiness,
  useSettings,
  type ServiceReadiness,
} from "./SettingsContext";
import SettingsStatusPanel from "./SettingsStatusPanel";
import {
  SETTINGS_CATEGORIES,
  type Lang,
  type SettingsCategory,
} from "../../lib/settings-nav";
import type { ServiceName } from "./SettingsContext";

import { tokens } from "../../theme/tokens";

const FG = `var(--foreground, ${tokens.colors.textPrimary})`;
const BG = `var(--background, ${tokens.colors.bgPage})`;
const CARD = `var(--card, ${tokens.colors.bgContent})`;
const BORDER = `var(--border, ${tokens.colors.border})`;
const MUTED = `var(--muted-foreground, ${tokens.colors.textSecondary})`;
const SERIF = "Georgia, 'Times New Roman', serif";
const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

/**
 * Settings hub — the landing page of `/settings`.
 *
 * Six category blocks and a resident Status module, nothing else. The blocks
 * are intentionally calmer than the Learning Space tiles (monochrome inline
 * icons, a chevron, a quiet preview line instead of a focal count) so Settings
 * reads as a control surface rather than a dashboard. Categories with several
 * settings (Models, Chat) open a sub-hub; the rest link straight to their leaf.
 */

type NetworkPreview = {
  apiBase: string;
};

export default function SettingsHub() {
  // tupu 无 i18next（中文产品）：语言恒为中文（原仓按 i18n.language 判定）。
  const zh = true;
  const tr = useCallback((l: Lang) => (zh ? l.zh : l.en), [zh]);

  const { catalog, catalogEditable, diagnosticsResults, startTour } =
    useSettings();

  // Model preview: how many of the model-service leaves are configured.
  const modelStats = useMemo(() => {
    const cat = SETTINGS_CATEGORIES.find(
      (c: SettingsCategory) => c.key === "models",
    );
    const services = ((cat?.children ?? []) as {
      service?: ServiceName;
    }[]).filter((l: { service?: ServiceName }) => l.service);
    if (catalogEditable !== true) {
      return {
        total: services.length,
        configured: -1,
        passed: 0,
        failed: 0,
        states: [] as ServiceReadiness[],
      };
    }
    const states = services.map((leaf: { service?: ServiceName }) =>
      serviceReadiness(catalog, leaf.service!, diagnosticsResults),
    );
    return {
      total: services.length,
      configured: states.filter(
        (state: ServiceReadiness) => state !== "not_configured",
      ).length,
      passed: states.filter((state: ServiceReadiness) => state === "passed")
        .length,
      failed: states.filter((state: ServiceReadiness) => state === "failed")
        .length,
      states,
    };
  }, [catalog, catalogEditable, diagnosticsResults]);

  // Network preview: a guarded peek at the effective browser API base. Fails
  // quietly (non-admins get 403) → the block falls back to its blurb.
  const [network, setNetwork] = useState<NetworkPreview | null>(null);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/v1/settings/network");
        if (!res.ok) return;
        const data = (await res.json()) as {
          effective?: { browser_api_base?: string };
        };
        if (cancelled) return;
        setNetwork({ apiBase: data.effective?.browser_api_base || "" });
      } catch {
        /* leave null → block shows its blurb */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <style>{`
.dsh-set-hub-grid {
  margin-top: 20px;
  display: grid;
  gap: 16px;
  grid-template-columns: 1fr;
}
@media (min-width: 640px) {
  .dsh-set-hub-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (min-width: 1024px) {
  .dsh-set-hub-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
.dsh-set-cat {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 120px;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, ${BORDER} 70%, transparent);
  background: ${CARD};
  padding: 20px;
  text-decoration: none;
  transition: all 150ms;
}
.dsh-set-cat:hover {
  border-color: color-mix(in srgb, ${FG} 20%, transparent);
  box-shadow: 0 4px 24px -16px rgba(0, 0, 0, 0.3);
}
.dsh-set-cat-icon {
  color: ${MUTED};
  transition: color 150ms;
}
.dsh-set-cat:hover .dsh-set-cat-icon { color: ${FG}; }
.dsh-set-cat-chevron {
  color: color-mix(in srgb, ${MUTED} 30%, transparent);
  transition: all 150ms;
}
.dsh-set-cat:hover .dsh-set-cat-chevron {
  transform: translateX(2px);
  color: ${MUTED};
}
.dsh-set-hub-tour-btn {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 6px;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, ${BORDER} 60%, transparent);
  background: transparent;
  padding: 6px 12px;
  font-size: 12.5px;
  font-weight: 500;
  color: ${MUTED};
  cursor: pointer;
  transition: color 150ms, border-color 150ms;
}
.dsh-set-hub-tour-btn:hover {
  border-color: ${BORDER};
  color: ${FG};
}
`}</style>
      <div data-testid="settings-hub">
        <header
          style={{
            marginBottom: 28,
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 16,
          }}
        >
          <div style={{ minWidth: 0 }}>
            <h1
              data-testid="settings-hub-title"
              style={{
                margin: 0,
                fontFamily: SERIF,
                fontSize: 24,
                fontWeight: 600,
                lineHeight: 1.25,
                letterSpacing: "-0.01em",
                color: FG,
              }}
            >
              {tr({ zh: "设置", en: "Settings" })}
            </h1>
            <p
              style={{
                marginTop: 6,
                marginBottom: 0,
                maxWidth: 576,
                fontSize: 13,
                lineHeight: 1.625,
                color: MUTED,
              }}
            >
              {tr({
                zh: "管理外观、模型与服务、知识库、聊天与记忆。",
                en: "Manage appearance, models and services, knowledge base, chat, and memory.",
              })}
            </p>
          </div>
          <button
            type="button"
            onClick={startTour}
            data-testid="settings-tour-btn"
            className="dsh-set-hub-tour-btn"
          >
            <RocketOutlined style={{ fontSize: 13 }} />
            {tr({ zh: "引导", en: "Tour" })}
          </button>
        </header>

        <SettingsStatusPanel />

        <div className="dsh-set-hub-grid">
          {SETTINGS_CATEGORIES.map((category: SettingsCategory) => (
            <CategoryBlock
              key={category.key}
              category={category}
              tr={tr}
              modelStats={category.key === "models" ? modelStats : undefined}
              network={category.key === "network" ? network : undefined}
            />
          ))}
        </div>
      </div>
    </>
  );
}

function CategoryBlock({
  category,
  tr,
  modelStats,
  network,
}: {
  category: SettingsCategory;
  tr: (l: Lang) => string;
  modelStats?: {
    total: number;
    configured: number;
    passed: number;
    failed: number;
    states: ServiceReadiness[];
  };
  network?: NetworkPreview | null;
}) {
  const Icon = category.icon;

  return (
    <Link
      to={category.href}
      data-tour={`tour-cat-${category.key}`}
      data-testid={`settings-cat-${category.key}`}
      className="dsh-set-cat"
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Icon className="dsh-set-cat-icon" style={{ fontSize: 19 }} />
          <h3
            style={{
              margin: 0,
              fontSize: 15.5,
              fontWeight: 500,
              letterSpacing: "-0.01em",
              color: FG,
            }}
          >
            {tr(category.label)}
          </h3>
        </div>
        <RightOutlined
          className="dsh-set-cat-chevron"
          style={{ fontSize: 16, marginTop: 2, flexShrink: 0 }}
        />
      </div>

      <div style={{ marginTop: 16 }}>
        {modelStats ? (
          <ModelPreview stats={modelStats} blurb={tr(category.blurb)} tr={tr} />
        ) : network !== undefined && network !== null ? (
          <NetworkPreviewRow network={network} tr={tr} />
        ) : (
          <p
            style={{
              margin: 0,
              fontSize: 12.5,
              lineHeight: 1.625,
              color: MUTED,
            }}
          >
            {tr(category.blurb)}
          </p>
        )}
      </div>
    </Link>
  );
}

function ModelPreview({
  stats,
  blurb,
  tr,
}: {
  stats: {
    total: number;
    configured: number;
    passed: number;
    failed: number;
    states: ServiceReadiness[];
  };
  blurb: string;
  tr: (l: Lang) => string;
}) {
  // Restricted deployments (no editable catalog) can't know — show the blurb.
  if (stats.configured < 0) {
    return (
      <p
        style={{
          margin: 0,
          fontSize: 12.5,
          lineHeight: 1.625,
          color: MUTED,
        }}
      >
        {blurb}
      </p>
    );
  }
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        {stats.states.map((state, i) => (
          <span
            key={i}
            style={{
              height: 6,
              width: 6,
              borderRadius: 9999,
              display: "inline-block",
              background:
                state === "passed"
                  ? tokens.colors.success // emerald-500 语义
                  : state === "failed"
                    ? tokens.colors.error // red-500 语义
                    : state === "untested"
                      ? "#a1a1aa" // zinc-400（暗色 zinc-500；tupu 单亮色主题）
                      : "rgba(212, 212, 216, 0.6)", // zinc-300/60（暗色 zinc-700）
            }}
          />
        ))}
      </div>
      <span
        style={{
          fontSize: 12,
          fontVariantNumeric: "tabular-nums",
          color: MUTED,
        }}
      >
        {stats.failed > 0
          ? tr({
              zh: `${stats.configured}/${stats.total} 已配置 · ${stats.failed} 个失败`,
              en: `${stats.configured}/${stats.total} configured · ${stats.failed} failed`,
            })
          : stats.passed > 0
            ? tr({
                zh: `${stats.configured}/${stats.total} 已配置 · ${stats.passed} 个通过`,
                en: `${stats.configured}/${stats.total} configured · ${stats.passed} passed`,
              })
            : tr({
                zh: `${stats.configured}/${stats.total} 已配置`,
                en: `${stats.configured}/${stats.total} configured`,
              })}
      </span>
    </div>
  );
}

function NetworkPreviewRow({
  network,
  tr,
}: {
  network: NetworkPreview;
  tr: (l: Lang) => string;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        fontSize: 12,
        color: MUTED,
      }}
    >
      <span
        style={{
          flexShrink: 0,
          color: `color-mix(in srgb, ${MUTED} 70%, transparent)`,
        }}
      >
        {tr({ zh: "API", en: "API" })}
      </span>
      <span
        title={network.apiBase}
        style={{
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          fontFamily: MONO,
          fontSize: 11.5,
          color: FG,
        }}
      >
        {network.apiBase || tr({ zh: "本地", en: "local" })}
      </span>
    </div>
  );
}
