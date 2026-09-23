/**
 * 复刻自 DeepTutor 原仓 web/components/partners/SoulEditor.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；react-i18next t() → 文件内 ZH_MESSAGES 查表直出
 * （web/locales/zh/app.json 原译文，未收录键保留英文原文，{{x}} 插值语义一致）；
 * Tailwind 类逐项换为内联样式（hover/focus 用事件直写；::placeholder 由模块加载时
 * 注入一次的等价 CSS 承载，<style id="dsh-partner-soul-editor-styles">，同批5
 * settings/shared.tsx 口径）；heightClass 参数签名逐字保留（含默认 "h-[320px]"），
 * 内部以 parseHeight 兼容解析 h-[Npx] → N px 高度（CRA 无 tailwind）；
 * 预览区 animate-fade-in 类在无 tailwind 环境不生效（纯装饰性淡入，登记省略）。
 * lucide-react→antd 图标登记：PencilLine → EditOutlined；Eye → EyeOutlined。
 *
 * Soul markdown editor with an edit/preview toggle, shared by the creation
 * wizard (SoulPicker) and the Configure tab. Styled as a quiet "file card":
 * a SOUL.md chrome strip with an iOS-style sliding segmented control, and a
 * fixed-height body so toggling never shifts the layout.
 */

import { useState } from "react";
import { EditOutlined, EyeOutlined } from "@ant-design/icons";
import MarkdownRenderer from "../common/MarkdownRenderer";

const ZH_MESSAGES: Record<string, string> = {
  Edit: "编辑",
  Preview: "预览",
  "# Soul\nDescribe who this partner is, how it speaks, what it values…":
    "# 灵魂\n描述这个伙伴是谁、如何说话、看重什么……",
  "Nothing to preview yet.": "暂无内容可预览。",
};

function t(key: string, vars?: Record<string, string | number>): string {
  let text = ZH_MESSAGES[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.split(`{{${name}}}`).join(String(value));
    }
  }
  return text;
}

/** heightClass 签名保留原仓 "h-[Npx]" 写法；此处解析为内联 px 高度。 */
function parseHeight(heightClass: string): number | string {
  const match = /^h-\[(\d+(?:\.\d+)?)px\]$/.exec(heightClass.trim());
  if (match) return Number(match[1]);
  return heightClass;
}

/** ::placeholder 色无法内联——模块加载时注入一次（CRA 无 SSR）。 */
const STYLE_ID = "dsh-partner-soul-editor-styles";
if (typeof document !== "undefined" && !document.getElementById(STYLE_ID)) {
  const styleEl = document.createElement("style");
  styleEl.id = STYLE_ID;
  styleEl.textContent =
    ".dsh-partner-soul-textarea::placeholder{color:rgba(100,116,139,0.6)}";
  document.head.appendChild(styleEl);
}

type Mode = "edit" | "preview";

export default function SoulEditor({
  value,
  onChange,
  placeholder,
  heightClass = "h-[320px]",
}: {
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
  heightClass?: string;
}) {
  const [mode, setMode] = useState<Mode>("edit");
  const [chromeFocused, setChromeFocused] = useState(false);
  const [editHover, setEditHover] = useState(false);
  const [previewHover, setPreviewHover] = useState(false);
  const height = parseHeight(heightClass);

  const segments: { key: Mode; label: string; icon: typeof EditOutlined }[] = [
    { key: "edit", label: t("Edit"), icon: EditOutlined },
    { key: "preview", label: t("Preview"), icon: EyeOutlined },
  ];

  return (
    <div
      style={{
        overflow: "hidden",
        borderRadius: 12,
        border: `1px solid ${
          chromeFocused
            ? "var(--ring, #2563eb)"
            : "var(--border, #e2e8f0)"
        }`,
        background: "var(--background, #f6f8fc)",
        transition: "border-color 150ms",
      }}
      onFocus={() => setChromeFocused(true)}
      onBlur={() => setChromeFocused(false)}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid var(--border, #e2e8f0)",
          background: "rgba(241, 245, 249, 0.4)",
          padding: "6px 6px 6px 16px",
        }}
      >
        <span
          style={{
            fontFamily:
              'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
            fontSize: 11,
            letterSpacing: "0.025em",
            color: "var(--muted-foreground, #64748b)",
          }}
        >
          SOUL.md
        </span>
        <div
          style={{
            position: "relative",
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            borderRadius: 8,
            background: "var(--muted, #f1f5f9)",
            padding: 2,
          }}
        >
          <span
            aria-hidden
            style={{
              pointerEvents: "none",
              position: "absolute",
              bottom: 2,
              left: 2,
              top: 2,
              width: "calc(50% - 2px)",
              borderRadius: 6,
              background: "var(--background, #f6f8fc)",
              boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
              transition: "transform 200ms ease-out",
              transform: mode === "preview" ? "translateX(100%)" : "translateX(0)",
            }}
          />
          {segments.map(({ key, label, icon: Icon }) => {
            const hovered = key === "edit" ? editHover : previewHover;
            const setHovered = key === "edit" ? setEditHover : setPreviewHover;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setMode(key)}
                onMouseDown={(e) => e.preventDefault()}
                onMouseEnter={() => setHovered(true)}
                onMouseLeave={() => setHovered(false)}
                aria-pressed={mode === key}
                style={{
                  position: "relative",
                  zIndex: 1,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                  borderRadius: 6,
                  padding: "4px 12px",
                  fontSize: 12,
                  border: "none",
                  background: "transparent",
                  cursor: "pointer",
                  fontWeight: mode === key ? 500 : 400,
                  color:
                    mode === key
                      ? "var(--foreground, #0f172a)"
                      : hovered
                        ? "var(--foreground, #0f172a)"
                        : "var(--muted-foreground, #64748b)",
                  transition: "color 200ms",
                }}
              >
                <Icon style={{ fontSize: 14 }} />
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {mode === "edit" ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={
            placeholder ??
            t(
              "# Soul\nDescribe who this partner is, how it speaks, what it values…",
            )
          }
          spellCheck={false}
          className="dsh-partner-soul-textarea"
          style={{
            display: "block",
            width: "100%",
            resize: "none",
            background: "transparent",
            padding: "14px 16px",
            fontFamily:
              'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
            fontSize: 13,
            lineHeight: 1.7,
            color: "var(--foreground, #0f172a)",
            outline: "none",
            border: "none",
            height,
          }}
        />
      ) : (
        <div
          style={{
            overflowY: "auto",
            padding: "16px 20px",
            height,
          }}
        >
          {value.trim() ? (
            <MarkdownRenderer
              content={value}
              variant="compact"
              className="!font-sans"
            />
          ) : (
            <p
              style={{
                fontSize: 13,
                color: "var(--muted-foreground, #64748b)",
              }}
            >
              {t("Nothing to preview yet.")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
