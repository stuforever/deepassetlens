/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/MemoryPicker.tsx，164 行）。
 * 替换点：删除 "use client"；lucide Brain/Check/FileText/ScrollText→BulbOutlined/
 * CheckOutlined/FileTextOutlined/ProfileOutlined（同 space-items 的 Brain 映射、
 * ScrollText→ProfileOutlined 近似）；PickerShell/PickerHeader→本目录件；
 * Tailwind→内联样式；t() 译文命中 zh/app.json 直出（"Select Memory"→选择记忆、
 * "Choose which long-form memory artifacts to attach to this turn."→选择本轮要附加的
 * 长期记忆条目。、"Inject the assistant's running summary of past learning sessions."
 * →注入助手对过往学习会话的累积摘要。、"Inject the learner profile (preferences,
 * goals, background)."→注入学习者画像（偏好、目标、背景）。、"Summary"→总结、
 * "Profile"→配置文件、"Clear"→清空），计数/按钮键未命中按 i18next 回退直出原 key。
 * 交互逐字未改。
 */
import { useEffect, useState, type ComponentType, type CSSProperties } from "react";
import {
  BulbOutlined,
  CheckOutlined,
  FileTextOutlined,
  ProfileOutlined,
} from "@ant-design/icons";
import PickerShell from "./PickerShell";
import PickerHeader from "./PickerHeader";
import type { SpaceMemoryFile } from "./space-items";
import { DT } from "./dtStyle";

interface MemoryPickerProps {
  open: boolean;
  initialFiles: SpaceMemoryFile[];
  onClose: () => void;
  onApply: (files: SpaceMemoryFile[]) => void;
}

interface MemoryOption {
  key: SpaceMemoryFile;
  label: string;
  description: string;
  icon: ComponentType<{ className?: string; style?: CSSProperties }>;
}

const MEMORY_OPTIONS: MemoryOption[] = [
  {
    key: "summary",
    label: "Summary",
    description:
      "Inject the assistant's running summary of past learning sessions.",
    icon: ProfileOutlined,
  },
  {
    key: "profile",
    label: "Profile",
    description: "Inject the learner profile (preferences, goals, background).",
    icon: FileTextOutlined,
  },
];

const ZH: Record<string, string> = {
  Summary: "总结",
  Profile: "配置文件",
  "Inject the assistant's running summary of past learning sessions.":
    "注入助手对过往学习会话的累积摘要。",
  "Inject the learner profile (preferences, goals, background).":
    "注入学习者画像（偏好、目标、背景）。",
};

function zh(text: string): string {
  return ZH[text] ?? text;
}

export default function MemoryPicker({
  open,
  initialFiles,
  onClose,
  onApply,
}: MemoryPickerProps) {
  const [selected, setSelected] = useState<SpaceMemoryFile[]>(initialFiles);

  // IIFE keeps the setState call out of the synchronous effect body to
  // satisfy `react-hooks/set-state-in-effect`.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    void (async () => {
      if (cancelled) return;
      setSelected(initialFiles);
    })();
    return () => {
      cancelled = true;
    };
  }, [open, initialFiles]);

  const toggle = (key: SpaceMemoryFile) => {
    setSelected((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key],
    );
  };

  const handleApply = () => {
    onApply(selected);
    onClose();
  };

  return (
    <PickerShell
      open={open}
      onClose={onClose}
      labelledBy="memory-picker-title"
      backdropClass="rgba(255,255,255,0.65)"
    >
      <div
        style={{
          width: "100%",
          maxWidth: 576,
          overflow: "hidden",
          borderRadius: 16,
          border: `1px solid ${DT.border}`,
          background: DT.card,
          color: DT.foreground,
          boxShadow: "0 22px 70px rgba(0,0,0,0.18)",
          padding: 16,
        }}
      >
        <PickerHeader
          icon={BulbOutlined}
          titleId="memory-picker-title"
          title={"选择记忆"}
          subtitle={"选择本轮要附加的长期记忆条目。"}
          onClose={onClose}
        />

        <div style={{ background: "rgba(255,255,255,0.4)", padding: 20 }}>
          <div
            style={{
              overflow: "hidden",
              borderRadius: 16,
              border: `1px solid ${DT.border}`,
              background: DT.card,
            }}
          >
            <div>
              {MEMORY_OPTIONS.map((option, idx) => {
                const active = selected.includes(option.key);
                const Icon = option.icon;
                return (
                  <button
                    key={option.key}
                    onClick={() => toggle(option.key)}
                    onMouseEnter={(e) => {
                      if (!active) {
                        e.currentTarget.style.background = DT.mutedAlpha(0.4);
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = active
                        ? DT.primaryAlpha(0.08)
                        : "transparent";
                    }}
                    style={{
                      display: "flex",
                      width: "100%",
                      alignItems: "flex-start",
                      gap: 12,
                      padding: "12px 16px",
                      textAlign: "left",
                      border: "none",
                      cursor: "pointer",
                      background: active ? DT.primaryAlpha(0.08) : "transparent",
                      font: "inherit",
                      borderTop: idx > 0 ? `1px solid ${DT.border}` : undefined,
                    }}
                  >
                    <div
                      style={{
                        marginTop: 2,
                        display: "flex",
                        height: 20,
                        width: 20,
                        flexShrink: 0,
                        alignItems: "center",
                        justifyContent: "center",
                        borderRadius: 6,
                        border: `1px solid ${active ? DT.primary : DT.border}`,
                        background: active ? DT.primary : "transparent",
                        color: active ? DT.primaryForeground : "transparent",
                        transition: "background-color 150ms, border-color 150ms",
                      }}
                    >
                      <CheckOutlined style={{ fontSize: 12 }} />
                    </div>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 500, color: DT.foreground }}>
                        <Icon style={{ fontSize: 14, color: DT.primary }} />
                        {zh(option.label)}
                      </div>
                      <p style={{ margin: "2px 0 0", fontSize: 12, lineHeight: "20px", color: DT.mutedForeground }}>
                        {zh(option.description)}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div style={{ marginTop: 16, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
            <div style={{ fontSize: 12, color: DT.mutedForeground }}>
              {selected.length === 1
                ? "1 memory artifact selected"
                : `${selected.length} memory artifacts selected`}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button
                onClick={() => setSelected([])}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = DT.muted;
                  e.currentTarget.style.color = DT.foreground;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = DT.card;
                  e.currentTarget.style.color = DT.mutedForeground;
                }}
                style={{
                  borderRadius: 12,
                  border: `1px solid ${DT.border}`,
                  background: DT.card,
                  padding: "10px 12px",
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: "pointer",
                  color: DT.mutedForeground,
                  transition: "background-color 150ms, color 150ms",
                }}
              >
                清空
              </button>
              <button
                onClick={handleApply}
                disabled={!selected.length}
                style={{
                  borderRadius: 12,
                  border: "none",
                  cursor: !selected.length ? "not-allowed" : "pointer",
                  background: DT.primary,
                  padding: "10px 16px",
                  fontSize: 13,
                  fontWeight: 500,
                  color: DT.primaryForeground,
                  opacity: !selected.length ? 0.4 : 1,
                  transition: "opacity 150ms",
                  font: "inherit",
                }}
              >
                {`Use Selected Memory (${selected.length})`}
              </button>
            </div>
          </div>
        </div>
      </div>
    </PickerShell>
  );
}

// 具名再导出：批9 SA-A FollowupChatComposer 以 lazy(() => import(...).then((m) => ({ default: m.MemoryPicker }))) 消费（桌面原件仅 default 导出，此为批内契约对齐，非新逻辑）。
export { MemoryPicker };
