/**
 * H5PageHeader（第十一篇 N1）：全站统一的二级页顶栏行——原仓 1:1 移植。
 * 结构：[← 返回] [标题] [右侧插槽]，一行 44px。
 * - 返回行为：有历史 router.back()，无历史 fallback 到 backHref（默认 /e/tutor/h5）；
 * - 设计为「嵌入」各页现有渐变头的第一行（不重写各页配色），
 *   一级 tab 页（home）不用；chat 页用内联版（保持全屏布局）。
 */
import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { LeftOutlined } from "@ant-design/icons";

export function H5PageHeader({
  title,
  backHref = "/e/tutor/h5",
  right,
  onBack,
}: {
  /** 标题（居中）；不传则只渲染返回+右侧插槽 */
  title?: React.ReactNode;
  /** 无历史时的 fallback 路由 */
  backHref?: string;
  /** 右侧操作区（按钮组） */
  right?: React.ReactNode;
  /** 覆盖默认返回行为（如带确认的页面） */
  onBack?: () => void;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const goBack = () => {
    if (onBack) {
      onBack();
      return;
    }
    // 直接打开（无 referrer）时 back() 会退到 about:blank——回 backHref 更稳
    if (
      typeof window !== "undefined" &&
      window.history.length > 1 &&
      document.referrer
    ) {
      navigate(-1);
    } else {
      navigate(backHref);
    }
  };
  void location;
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", minHeight: 44 }}>
      <button
        onClick={goBack}
        aria-label="返回"
        data-testid="h5-back"
        style={{
          display: "flex", alignItems: "center", gap: 2, fontSize: 14, color: "rgba(255,255,255,0.9)",
          background: "none", border: "none", cursor: "pointer", flexShrink: 0, marginLeft: -4, paddingRight: 8,
        }}
      >
        <LeftOutlined style={{ fontSize: 18 }} /> 返回
      </button>
      {title !== undefined ? (
        <div style={{ flex: 1, minWidth: 0, textAlign: "center", fontSize: 18, fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", padding: "0 4px" }}>
          {title}
        </div>
      ) : (
        <div style={{ flex: 1 }} />
      )}
      <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>{right}</div>
    </div>
  );
}
