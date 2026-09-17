/**
 * 复刻自 DeepTutor 原仓 web/components/settings/SettingsMain.tsx（整件 1:1，批5 5.2 壳族）。
 * 替换点：next/navigation usePathname → react-router-dom useLocation().pathname；
 * Tailwind → 内联样式（max-w-5xl=1024px、px-8/10、py-8、pb-12/16 逐项对位；颜色 token 兜底；
 * scrollbar-gutter: stable 用 CSS 属性原值保留）。默认导出/结构/data-testid/导航-only 路由
 * 判定逻辑逐字保留。
 */
import React from "react";
import { useLocation } from "react-router-dom";

import SettingsBreadcrumb from "./SettingsBreadcrumb";
import { SettingsToolbar } from "./SettingsToolbar";
import { SettingsLoadStatusBanner } from "./SettingsLoadStatusBanner";
import { SETTINGS_HUB_HREF, isNavOnlyRoute } from "../../lib/settings-nav";

import { tokens } from "../../theme/tokens";

const BG = `var(--background, ${tokens.colors.bgContent})`;

// Two-level hub: the dashboard at `/settings` is the entry; categories with
// several settings open a sub-hub, the rest go straight to a leaf. Every page
// below the hub carries a breadcrumb top-left so the user knows where they
// are. The sticky Save Draft / Apply toolbar rides above the scroll area on
// leaf pages only — nav-only pages (hub, sub-hubs) have nothing to save.

export default function SettingsMain({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const { pathname } = useLocation();
  const path = pathname ?? "";
  const isHub = path === SETTINGS_HUB_HREF;

  if (isHub) {
    return (
      <div
        data-testid="settings-main"
        style={{
          height: "100%",
          overflowY: "auto",
          background: BG,
          scrollbarGutter: "stable",
        }}
      >
        <div
          style={{
            margin: "0 auto",
            width: "100%",
            maxWidth: 1024,
            padding: 32,
            paddingBottom: 48,
          }}
        >
          {children}
        </div>
      </div>
    );
  }

  const showToolbar = !isNavOnlyRoute(path);

  return (
    <div
      data-testid="settings-main"
      style={{
        display: "flex",
        height: "100%",
        minWidth: 0,
        flexDirection: "column",
        overflow: "hidden",
        background: BG,
      }}
    >
      <div
        style={{
          margin: "0 auto",
          width: "100%",
          maxWidth: 1024,
          padding: "20px 40px 0",
        }}
      >
        <SettingsBreadcrumb />
        {showToolbar && (
          <div style={{ marginTop: 8 }}>
            <SettingsToolbar />
          </div>
        )}
        <SettingsLoadStatusBanner />
      </div>
      {/* Inner scroll container. Sticky elements inside (e.g. the profile-list
          aside in ServiceConfigEditor) anchor to this ancestor instead of the
          outer flex column, so the left column stays put while the right side
          scrolls. ``min-h-0`` is required for the flex child to constrain to
          remaining space — without it, ``overflow-y-auto`` would never clip. */}
      <div
        style={{
          minHeight: 0,
          flex: 1,
          overflowY: "auto",
          overflowX: "hidden",
          scrollbarGutter: "stable",
        }}
      >
        <div
          style={{
            margin: "0 auto",
            width: "100%",
            maxWidth: 1024,
            padding: "0 40px 64px",
          }}
        >
          <div style={{ marginTop: 16 }}>{children}</div>
        </div>
      </div>
    </div>
  );
}
