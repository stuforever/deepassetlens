/**
 * 复刻自 DeepTutor 原仓 web/components/settings/SettingsSectionGrid.tsx（整件 1:1，批5 5.2 壳族）。
 * 替换点：next/link → react-router-dom Link（href→to）；lucide（ArrowUpRight、leaf.icon）→
 * @ant-design/icons（ArrowUpOutlined 旋转 45° 等价 ↗、icon 以 style.fontSize 调用）；
 * @/lib/auth fetchAuthStatus → 就地等价内联（fetch('/api/v1/auth/status')，!ok/异常返回 null，
 * 仅取本组件消费的 enabled/is_admin；401→login 跳转为原仓鉴权专属不复刻）；
 * react-i18next → tupu 无 i18next（中文产品），tr 恒取 Lang.zh；Tailwind → 内联样式 +
 * 页内 <style>（hover 位移/阴影、sm:grid-cols-2 进样式块；leaf.tile 为 settings-nav 提供的
 * 着色类字符串，原样透传 className）。结构/data-testid/chip 就绪语义逐字保留。
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpOutlined } from "@ant-design/icons";

import {
  serviceReadiness,
  useSettings,
} from "./SettingsContext";
import {
  SETTINGS_CATEGORIES,
  type Lang,
  type SettingsCategory,
  type SettingsLeaf,
} from "../../lib/settings-nav";

import { tokens } from "../../theme/tokens";

const FG = `var(--foreground, ${tokens.colors.textPrimary})`;
const CARD = `var(--card, ${tokens.colors.bgContent})`;
const BORDER = `var(--border, ${tokens.colors.border})`;
const MUTED = `var(--muted-foreground, ${tokens.colors.textSecondary})`;

/**
 * Second-level grid for a sub-hub category (Models, Chat). Lists the
 * category's leaves as tiles — colored icon, configured chip for model
 * services, and a blurb — the focused view the user reaches by clicking the
 * hub block.
 */
export default function SettingsSectionGrid({
  categoryKey,
}: {
  categoryKey: string;
}) {
  // tupu 无 i18next（中文产品）：语言恒为中文（原仓按 i18n.language 判定）。
  const zh = true;
  const tr = useCallback((l: Lang) => (zh ? l.zh : l.en), [zh]);

  const { catalog, catalogEditable, diagnosticsResults } = useSettings();

  const category = SETTINGS_CATEGORIES.find(
    (c: SettingsCategory) => c.key === categoryKey,
  );

  const [hideAdminOnly, setHideAdminOnly] = useState(false);
  useEffect(() => {
    let cancelled = false;
    fetchAuthStatus().then((authStatus) => {
      if (cancelled || !authStatus) return;
      setHideAdminOnly(Boolean(authStatus.enabled) && !authStatus.is_admin);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const chipFor = useCallback(
    (
      leaf: SettingsLeaf,
    ): { label: Lang; tone: "ok" | "bad" | "neutral"; dot: boolean } | null => {
      if (!leaf.service) return null;
      if (catalogEditable !== true) return null;
      const readiness = serviceReadiness(
        catalog,
        leaf.service,
        diagnosticsResults,
      );
      if (readiness === "failed") {
        return {
          tone: "bad",
          dot: true,
          label: { zh: "测试失败", en: "Test failed" },
        };
      }
      if (readiness === "passed") {
        return {
          tone: "ok",
          dot: true,
          label: { zh: "测试通过", en: "Test passed" },
        };
      }
      if (readiness === "untested") {
        return {
          tone: "neutral",
          dot: true,
          label: { zh: "已配置", en: "Configured" },
        };
      }
      return {
        tone: "neutral",
        dot: false,
        label: { zh: "未配置", en: "Not set" },
      };
    },
    [catalog, catalogEditable, diagnosticsResults],
  );

  if (!category?.children) return null;

  const leaves = (category.children as SettingsLeaf[]).filter(
    (leaf: SettingsLeaf) => !(leaf.adminOnly && hideAdminOnly),
  );

  return (
    <>
      <style>{`
.dsh-set-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: 1fr;
}
@media (min-width: 640px) {
  .dsh-set-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.dsh-set-leaf {
  position: relative;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  border: 1px solid ${BORDER};
  background: ${CARD};
  padding: 16px;
  text-decoration: none;
  transition: all 150ms;
}
.dsh-set-leaf:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, ${FG} 20%, transparent);
  box-shadow: 0 6px 20px -12px rgba(0, 0, 0, 0.25);
}
.dsh-set-leaf-arrow {
  flex-shrink: 0;
  color: color-mix(in srgb, ${MUTED} 40%, transparent);
  transition: color 150ms;
}
.dsh-set-leaf:hover .dsh-set-leaf-arrow { color: ${FG}; }
`}</style>
      <div data-testid={`settings-grid-${categoryKey}`}>
        <header style={{ marginBottom: 24 }}>
          <h1
            style={{
              margin: 0,
              fontFamily: "Georgia, 'Times New Roman', serif",
              fontSize: 22,
              fontWeight: 600,
              letterSpacing: "-0.01em",
              color: FG,
            }}
          >
            {tr(category.label)}
          </h1>
          <p
            style={{
              marginTop: 6,
              marginBottom: 0,
              fontSize: 13,
              lineHeight: 1.625,
              color: MUTED,
            }}
          >
            {tr(category.blurb)}
          </p>
        </header>

        <div className="dsh-set-grid">
          {leaves.map((leaf: SettingsLeaf) => (
            <LeafCard key={leaf.key} leaf={leaf} chip={chipFor(leaf)} tr={tr} />
          ))}
        </div>
      </div>
    </>
  );
}

function LeafCard({
  leaf,
  chip,
  tr,
}: {
  leaf: SettingsLeaf;
  chip: { label: Lang; tone: "ok" | "bad" | "neutral"; dot: boolean } | null;
  tr: (l: Lang) => string;
}) {
  const Icon = leaf.icon;
  const tone = chip?.tone ?? "neutral";
  return (
    <Link
      to={leaf.href}
      data-testid={`settings-leaf-${leaf.key}`}
      className="dsh-set-leaf"
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 12,
        }}
      >
        <span
          aria-hidden
          className={leaf.tile}
          style={{
            display: "flex",
            height: 40,
            width: 40,
            flexShrink: 0,
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 8,
          }}
        >
          <Icon style={{ fontSize: 18 }} />
        </span>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h3
              style={{
                margin: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                fontSize: 14.5,
                fontWeight: 500,
                lineHeight: 1.25,
                letterSpacing: "-0.01em",
                color: FG,
              }}
            >
              {tr(leaf.label)}
            </h3>
            {chip && (
              <span
                style={{
                  display: "inline-flex",
                  flexShrink: 0,
                  alignItems: "center",
                  gap: 4,
                  fontSize: 10.5,
                  fontWeight: 500,
                  ...(chip.dot
                    ? {
                        borderRadius: 9999,
                        padding: "2px 6px",
                        ...(tone === "bad"
                          ? { background: "rgba(239, 68, 68, 0.1)", color: tokens.colors.error }
                          : tone === "ok"
                            ? { background: "rgba(22, 163, 74, 0.1)", color: tokens.colors.success }
                            : { background: "rgba(113, 113, 122, 0.1)", color: "#52525b" }),
                      }
                    : { color: MUTED }),
                }}
              >
                {chip.dot && (
                  <span
                    style={{
                      height: 6,
                      width: 6,
                      borderRadius: 9999,
                      display: "inline-block",
                      background:
                        tone === "bad"
                          ? tokens.colors.error
                          : tone === "ok"
                            ? tokens.colors.success
                            : "#a1a1aa", // zinc-400（暗色 zinc-500）
                    }}
                  />
                )}
                {tr(chip.label)}
              </span>
            )}
          </div>
        </div>
        <ArrowUpOutlined
          className="dsh-set-leaf-arrow"
          style={{
            fontSize: 16,
            transform: "rotate(45deg)", // lucide ArrowUpRight（↗）等价
          }}
        />
      </div>
      <p
        style={{
          marginTop: 12,
          marginBottom: 0,
          fontSize: 12.5,
          lineHeight: 1.625,
          color: MUTED,
        }}
      >
        {tr(leaf.blurb)}
      </p>
    </Link>
  );
}

/** 原仓 lib/auth.fetchAuthStatus 的等价内联（见头注）。 */
type AuthStatus = {
  enabled: boolean;
  authenticated: boolean;
  user_id?: string;
  username?: string;
  role?: string;
  is_admin?: boolean;
  avatar?: string;
};

async function fetchAuthStatus(): Promise<AuthStatus | null> {
  try {
    const res = await fetch("/api/v1/auth/status");
    if (!res.ok) return null;
    const status: AuthStatus = await res.json();
    return status;
  } catch {
    return null;
  }
}
