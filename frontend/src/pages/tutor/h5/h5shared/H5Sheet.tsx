/**
 * S1（M23）统一 H5 弹层基座——原仓 components/h5/H5Sheet.tsx 1:1 移植。
 * 等价替换：lucide X → CloseOutlined；Tailwind → 内联样式（视觉逐项对位）。
 * 设计约定：
 *  - 宽度 max-width 448 对齐 H5Shell 的 448px 壳列
 *  - 恒 max-height 85dvh + 内容区 overflow-y auto（弹性内滚）
 *  - sticky 头（title + 关闭）/ footer 槽（footer prop）
 *  - Esc / 点遮罩关闭；lockBody=false 供嵌在滚动容器里的弹层（追问卡）使用
 *  - testid：h5-sheet（弹层根）/ sheet-close（右上角关闭）/ h5-sheet-overlay（遮罩）
 */
import React, { useEffect, useCallback } from "react";
import { CloseOutlined } from "@ant-design/icons";

export function H5Sheet({
  open,
  onClose,
  title,
  footer,
  children,
  align = "bottom",
  lockBody = true,
  testId,
}: {
  open: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
  /** bottom：底部抽屉（移动端拇指区）；center：居中对话框 */
  align?: "bottom" | "center";
  /** false 时不锁 body 滚动（弹层自身在页面滚动流内的场景） */
  lockBody?: boolean;
  testId?: string;
}) {
  const onKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (!open) return;
    document.addEventListener("keydown", onKey);
    if (lockBody) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.removeEventListener("keydown", onKey);
        document.body.style.overflow = prev;
      };
    }
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onKey, lockBody]);

  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 50, background: "rgba(0,0,0,0.4)",
        display: "flex", justifyContent: "center",
        alignItems: align === "bottom" ? "flex-end" : "center",
        padding: align === "bottom" ? 0 : 16,
      }}
      onClick={onClose}
      data-testid={testId || "h5-sheet-overlay"}
    >
      <div
        style={{
          background: "#fff", width: "100%", maxWidth: 448, margin: "0 auto",
          display: "flex", flexDirection: "column", overflow: "hidden",
          boxShadow: "0 20px 25px -5px rgba(0,0,0,.1), 0 8px 10px -6px rgba(0,0,0,.1)",
          maxHeight: "85dvh",
          borderRadius: align === "bottom" ? "24px 24px 0 0" : 24,
        }}
        onClick={(e) => e.stopPropagation()}
        data-testid="h5-sheet"
      >
        {(title !== undefined) && (
          <div
            style={{
              position: "sticky", top: 0, zIndex: 10, background: "#fff",
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "16px 20px 12px", borderBottom: "1px solid #f1f5f9", flexShrink: 0,
            }}
          >
            <div style={{ fontWeight: 600, fontSize: 16, color: "#1e293b", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{title}</div>
            <button
              onClick={onClose}
              aria-label="关闭"
              style={{ background: "none", border: "none", cursor: "pointer", color: "#94a3b8", flexShrink: 0, marginLeft: 8, padding: 0, lineHeight: 1 }}
              data-testid="sheet-close"
            >
              <CloseOutlined style={{ fontSize: 20 }} />
            </button>
          </div>
        )}
        <div style={{ minHeight: 0, flex: 1, overflowY: "auto", overscrollBehavior: "contain" }}>{children}</div>
        {footer && (
          <div style={{ position: "sticky", bottom: 0, background: "#fff", borderTop: "1px solid #f1f5f9", padding: "12px 20px", flexShrink: 0 }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
