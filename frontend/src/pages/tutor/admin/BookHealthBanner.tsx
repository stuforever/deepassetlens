/**
 * BookHealthBanner —— 书籍健康警示横幅（知识库漂移 + 重复失败日志）。
 * 1:1 复刻自原仓 DeepTutor web/app/(workspace)/book/components/BookHealthBanner.tsx（222 行）。
 * 复刻来源：Next.js + Tailwind + react-i18next + lucide-react + "@/lib/book-api"
 * 替换点：
 *  - "use client" 删除；
 *  - react-i18next（useTranslation/t(key)）→ 中文直出（译文取自原仓 web/locales/zh/app.json）；
 *  - lucide-react → @ant-design/icons 语义就近（AlertTriangle→WarningOutlined #f59e0b、RefreshCcw→RedoOutlined、
 *    X→CloseOutlined、ScrollText→FileTextOutlined）；
 *  - import 契约：@/lib/book-api → './book-api'（并行 Agent 同步产出，导出名 bookApi 与原仓一致）；
 *  - Tailwind → antd 组件 + 最小内联样式：外层警示横幅用 antd Alert（type="warning" closable + action），
 *    底色 #fffbeb / 边框 rgba(252,211,77,0.6)（amber-50 / amber-300/60）/ 文字 #78350f（amber-900）；
 *  - hover:bg-white/40 类交互 → onMouseEnter/Leave 内联置 background rgba(255,255,255,0.4)。
 * 不变：props 契约（bookId/refreshKey/onRecompile）、bookApi.health / bookApi.refreshFingerprints 调用时序、
 *       dismissed/busy 状态机、kb_drift 过滤逻辑（kb_health / kb drift 签名排除、slice(0,3)）、
 *       humanizeSignature 截断 80 字符、签名人性化逻辑。
 */
import { useEffect, useState } from "react";
import { Alert, Button } from "antd";
import {
  CloseOutlined,
  FileTextOutlined,
  RedoOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { bookApi } from "./book-api";

export interface BookHealthBannerProps {
  bookId: string | null;
  refreshKey?: number;
  onRecompile?: (pageId: string) => void;
}

interface KbDrift {
  has_drift: boolean;
  new_kbs?: string[];
  removed_kbs?: string[];
  changed_kbs?: string[];
  stale_page_ids?: string[];
}

interface LogHealth {
  total_entries: number;
  error_entries: number;
  block_failures: number;
  repeated_failures?: { signature: string; count: number }[];
}

export default function BookHealthBanner({
  bookId,
  refreshKey,
  onRecompile,
}: BookHealthBannerProps) {
  const [kbDrift, setKbDrift] = useState<KbDrift | null>(null);
  const [logHealth, setLogHealth] = useState<LogHealth | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!bookId) {
      setKbDrift(null);
      setLogHealth(null);
      return;
    }
    setDismissed(false);
    (async () => {
      try {
        const data = await bookApi.health(bookId);
        if (cancelled) return;
        setKbDrift(data.kb_drift);
        setLogHealth(data.log_health);
      } catch {
        // ignore – health is non-critical
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [bookId, refreshKey]);

  if (!bookId || dismissed) return null;

  const hasDrift = !!kbDrift?.has_drift;
  // Filter out repeated failures that are already represented elsewhere
  // (kb_health drift logs are surfaced via the kb-drift section above).
  const repeated = (logHealth?.repeated_failures || [])
    .filter((r) => {
      const sig = (r.signature || "").toLowerCase();
      if (sig.includes("kb_health")) return false;
      if (sig.includes("kb drift")) return false;
      return true;
    })
    .slice(0, 3);
  const blockFailures = logHealth?.block_failures || 0;
  const hasLogIssues = blockFailures >= 3 || repeated.length > 0;

  if (!hasDrift && !hasLogIssues) return null;

  // Convert technical signatures into a short human label.
  const humanizeSignature = (sig: string): string => {
    if (!sig) return "未知失败";
    const stripped = sig.replace(/^[a-z_]+:/i, "").trim();
    return stripped.length > 80 ? `${stripped.slice(0, 80)}…` : stripped;
  };

  const acknowledge = async () => {
    if (!bookId) return;
    setBusy(true);
    try {
      await bookApi.refreshFingerprints(bookId);
      setKbDrift({ has_drift: false });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ margin: "16px 24px 0" }}>
      <Alert
        type="warning"
        showIcon
        icon={<WarningOutlined style={{ color: "#f59e0b", fontSize: 16 }} />}
        closeIcon={<CloseOutlined style={{ color: "#b45309", fontSize: 16 }} />}
        onClose={() => setDismissed(true)}
        action={
          hasDrift ? (
            <Button
              onClick={acknowledge}
              disabled={busy}
              title="将当前知识库状态标记为新的基线（不会重新编译页面；如需重编译请使用上方按钮）。"
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255,255,255,0.4)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
              }}
              style={{
                whiteSpace: "nowrap",
                borderRadius: 6,
                border: "1px solid currentColor",
                background: "transparent",
                color: "inherit",
                fontWeight: 500,
                fontSize: 12,
                height: 26,
                padding: "0 8px",
              }}
            >
              {busy ? "…" : "标记为已查看"}
            </Button>
          ) : undefined
        }
        style={{
          borderRadius: 12,
          border: "1px solid rgba(252,211,77,0.6)",
          background: "#fffbeb",
          fontSize: 14,
          color: "#78350f",
        }}
        message={
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {hasDrift && (
              <div>
                <strong>
                  自本书生成后，你的知识库发生了变化。
                </strong>{" "}
                <span style={{ opacity: 0.9 }}>
                  {kbDrift?.new_kbs?.length ? (
                    <>
                      新增:{" "}
                      <code
                        style={{
                          borderRadius: 4,
                          background: "rgba(255,255,255,0.4)",
                          padding: "0 4px",
                          fontSize: 11,
                        }}
                      >
                        {kbDrift.new_kbs.join(", ")}
                      </code>
                      .{" "}
                    </>
                  ) : null}
                  {kbDrift?.changed_kbs?.length ? (
                    <>
                      最近更新:{" "}
                      <code
                        style={{
                          borderRadius: 4,
                          background: "rgba(255,255,255,0.4)",
                          padding: "0 4px",
                          fontSize: 11,
                        }}
                      >
                        {kbDrift.changed_kbs.join(", ")}
                      </code>
                      .{" "}
                    </>
                  ) : null}
                  {kbDrift?.removed_kbs?.length ? (
                    <>
                      已移除:{" "}
                      <code
                        style={{
                          borderRadius: 4,
                          background: "rgba(255,255,255,0.4)",
                          padding: "0 4px",
                          fontSize: 11,
                        }}
                      >
                        {kbDrift.removed_kbs.join(", ")}
                      </code>
                      .{" "}
                    </>
                  ) : null}
                </span>
                {kbDrift?.stale_page_ids?.length ? (
                  <div style={{ marginTop: 6, fontSize: 12, opacity: 0.9 }}>
                    {kbDrift.stale_page_ids.length === 1
                      ? "1 个已编译页面可能已过期。"
                      : `${kbDrift.stale_page_ids.length} 个已编译页面可能已过期。`}{" "}
                    {onRecompile && kbDrift.stale_page_ids[0] && (
                      <Button
                        onClick={() => onRecompile(kbDrift.stale_page_ids![0])}
                        icon={<RedoOutlined style={{ fontSize: 12 }} />}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background =
                            "rgba(255,255,255,0.4)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = "transparent";
                        }}
                        style={{
                          marginLeft: 4,
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                          borderRadius: 4,
                          border: "1px solid currentColor",
                          background: "transparent",
                          color: "inherit",
                          fontSize: 12,
                          height: 22,
                          padding: "0 6px",
                        }}
                      >
                        重新编译第一个过期页面
                      </Button>
                    )}
                  </div>
                ) : null}
              </div>
            )}
            {hasLogIssues && (
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  gap: 8,
                  fontSize: 12,
                }}
              >
                <FileTextOutlined style={{ fontSize: 14 }} />
                {blockFailures > 0 && (
                  <span>
                    {`记录到 ${blockFailures} 次内容块生成失败。`}
                  </span>
                )}
                {repeated.length > 0 && (
                  <span>
                    {repeated.length === 1 ? "重复问题" : "重复问题"}
                    {": "}
                    {repeated
                      .map(
                        (r) => `${humanizeSignature(r.signature)} (×${r.count})`,
                      )
                      .join("; ")}
                    .
                  </span>
                )}
              </div>
            )}
          </div>
        }
      />
    </div>
  );
}
