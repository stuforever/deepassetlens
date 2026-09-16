/**
 * 桌面同名件 1:1（复制自 DeepTutor 原仓 web/components/memory/MemoryArchivedBanner.tsx，97 行）。
 * 替换点：删除 "use client"；lucide Archive/ChevronDown/ChevronUp/X → ContainerOutlined/
 * DownOutlined/UpOutlined/CloseOutlined（同批先例映射）；react-i18next → 组内 zhT.t 中文直出；
 * Tailwind → 内联样式（hover: 伪类按先例省略并在此登记）；localStorage key
 * "dt:memory:banner-dismissed" 逐字保留。
 * 交互逐字未改。
 */
import { useCallback, useState, type CSSProperties } from "react";
import {
  CloseOutlined,
  ContainerOutlined,
  DownOutlined,
  UpOutlined,
} from "@ant-design/icons";

import { t } from "./zhT";

const STORAGE_KEY = "dt:memory:banner-dismissed";

interface MemoryArchivedBannerProps {
  latestBackup: string | null;
  variant?: "full" | "compact";
}

const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";

export function MemoryArchivedBanner({
  latestBackup,
  variant = "compact",
}: MemoryArchivedBannerProps) {
  const [dismissed, setDismissed] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(STORAGE_KEY);
  });
  const [expanded, setExpanded] = useState(false);

  const dismiss = useCallback(() => {
    if (!latestBackup) return;
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, latestBackup);
    }
    setDismissed(latestBackup);
  }, [latestBackup]);

  if (!latestBackup || dismissed === latestBackup) return null;

  if (variant === "full") {
    return (
      <div
        style={{
          position: "relative",
          display: "flex",
          alignItems: "flex-start",
          gap: 12,
          borderRadius: 16,
          border: `1px solid ${BORDER}`,
          background: "var(--muted, #f5f5f5)",
          padding: "16px 48px 16px 20px",
          fontSize: 13,
        }}
      >
        <ContainerOutlined
          style={{
            marginTop: 2,
            fontSize: 16,
            flexShrink: 0,
            color: MUTED_FG,
          }}
        />
        <div>
          <p style={{ fontWeight: 500, color: FG, margin: 0 }}>
            {t("Your v1 memory was archived")}
          </p>
          <p style={{ marginTop: 2, color: MUTED_FG, marginBottom: 0 }}>
            {t(
              "Stored at memory/backup/{{name}}. v2 starts fresh — interact with DeepTutor and click Update on each doc to build memory.",
              { name: latestBackup },
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={dismiss}
          aria-label={t("Dismiss")}
          style={
            {
              position: "absolute",
              right: 8,
              top: 8,
              borderRadius: 6,
              padding: 6,
              color: MUTED_FG,
              transition: "all 0.15s",
              border: "none",
              background: "transparent",
              cursor: "pointer",
              lineHeight: 0,
            } as CSSProperties
          }
        >
          <CloseOutlined style={{ fontSize: 14 }} />
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        borderRadius: 12,
        border: `1px solid ${BORDER}`,
        background: "color-mix(in srgb, var(--muted, #f5f5f5) 60%, transparent)",
        fontSize: 12,
      }}
    >
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        style={{
          display: "flex",
          width: "100%",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          padding: "8px 16px",
          textAlign: "left",
          background: "transparent",
          border: "none",
          cursor: "pointer",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 8, color: MUTED_FG }}>
          <ContainerOutlined style={{ fontSize: 14 }} />
          {t("Your v1 memory was archived")}
        </span>
        {expanded ? (
          <UpOutlined style={{ fontSize: 14, color: MUTED_FG }} />
        ) : (
          <DownOutlined style={{ fontSize: 14, color: MUTED_FG }} />
        )}
      </button>
      {expanded && (
        <div
          style={{
            position: "relative",
            borderTop: `1px solid ${BORDER}`,
            padding: "12px 40px 12px 16px",
            color: MUTED_FG,
          }}
        >
          {t(
            "Stored at memory/backup/{{name}}. v2 starts fresh — interact with DeepTutor and click Update on each doc to build memory.",
            { name: latestBackup },
          )}
          <button
            type="button"
            onClick={dismiss}
            aria-label={t("Dismiss")}
            style={
              {
                position: "absolute",
                right: 8,
                top: 8,
                borderRadius: 6,
                padding: 4,
                color: MUTED_FG,
                transition: "all 0.15s",
                border: "none",
                background: "transparent",
                cursor: "pointer",
                lineHeight: 0,
              } as CSSProperties
            }
          >
            <CloseOutlined style={{ fontSize: 12 }} />
          </button>
        </div>
      )}
    </div>
  );
}

export default MemoryArchivedBanner;
