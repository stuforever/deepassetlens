/**
 * 复刻自 DeepTutor 原仓 web/components/settings/SettingsBreadcrumb.tsx（整件 1:1，批5 5.2 壳族）。
 * 替换点：next/link → react-router-dom Link（href→to）；usePathname → useLocation().pathname；
 * ChevronRight → RightOutlined；react-i18next t() → 文件内查表直出（zh/app.json 原译文）；
 * Tailwind → 内联样式 + 页内 <style>（颜色语义一致，token 兜底）。结构/data-testid 逐字保留。
 */
import { Fragment } from "react";
import { Link, useLocation } from "react-router-dom";
import { RightOutlined } from "@ant-design/icons";

import { breadcrumbFor, type Lang } from "../../lib/settings-nav";

import { tokens } from "../../theme/tokens";

const FG = `var(--foreground, ${tokens.colors.textPrimary})`;
const MUTED = `var(--muted-foreground, ${tokens.colors.textSecondary})`;

/** i18next 兼容直出（见头注）：web/locales/zh/app.json 原译文。 */
const ZH: Record<string, string> = {
  Breadcrumb: "导航路径",
};

function t(key: string): string {
  return Object.prototype.hasOwnProperty.call(ZH, key) ? ZH[key] : key;
}

// Top-left location trail, e.g. 设置 / 模型 / LLM. Earlier crumbs are links;
// the current page is plain text. Replaces the old single "back" link so the
// user always knows where they are inside Settings and can jump up a level.
export default function SettingsBreadcrumb() {
  const { pathname } = useLocation();
  // tupu 无 i18next（中文产品）：语言恒为中文（原仓按 i18n.language 判定）。
  const zh = true;
  const tr = (l: Lang) => (zh ? l.zh : l.en);

  const crumbs = breadcrumbFor(pathname ?? "");

  return (
    <>
      <style>{`
.dsh-set-crumb-link {
  border-radius: 2px;
  padding: 0 2px;
  color: ${MUTED};
  text-decoration: none;
  transition: color 150ms;
}
.dsh-set-crumb-link:hover {
  color: ${FG};
}
`}</style>
      <nav
        aria-label={t("Breadcrumb")}
        data-testid="settings-breadcrumb"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          fontSize: 12.5,
          color: MUTED,
        }}
      >
        {crumbs.map((crumb: { label: Lang; href?: string }, i: number) => {
          const last = i === crumbs.length - 1;
          return (
            <Fragment key={`${crumb.label.en}-${i}`}>
              {i > 0 && (
                <RightOutlined
                  style={{
                    fontSize: 13,
                    flexShrink: 0,
                    color: "rgba(100, 116, 139, 0.4)",
                  }}
                />
              )}
              {crumb.href && !last ? (
                <Link
                  to={crumb.href}
                  data-testid={`settings-crumb-${i}`}
                  className="dsh-set-crumb-link"
                >
                  {tr(crumb.label)}
                </Link>
              ) : (
                <span
                  data-testid={`settings-crumb-${i}`}
                  style={{
                    padding: "0 2px",
                    ...(last
                      ? { fontWeight: 500, color: FG }
                      : {}),
                  }}
                >
                  {tr(crumb.label)}
                </span>
              )}
            </Fragment>
          );
        })}
      </nav>
    </>
  );
}
