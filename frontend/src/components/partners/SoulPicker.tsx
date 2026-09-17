/**
 * 复刻自 DeepTutor 原仓 web/components/partners/SoulPicker.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；t() → 文件内查表直出（zh/app.json 原译文）；Tailwind 类
 * 逐项换内联样式（hover 用事件直写；active:scale-[0.97] 由注入 CSS
 * .dsh-partner-soul-chip:active 承载，同批5 settings/shared.tsx 口径）。
 * lucide-react→antd 图标登记：BookHeart → BookOutlined（antd 无心形书）；Check →
 * CheckOutlined；Loader2 → LoadingOutlined(spin)；Save → SaveOutlined；
 * Sparkles → StarOutlined；UserRound → UserOutlined。
 *
 * Soul source selector for the creation wizard: start from the library, clone
 * one of the chat personas, or write a custom soul. Whatever the source, the
 * chosen text lands in the SoulEditor below — the text IS the partner's
 * SOUL.md, and editing it detaches a private custom copy. A custom soul can
 * be saved back into the shared library for future partners.
 */

import { useEffect, useState } from "react";
import {
  BookOutlined,
  CheckOutlined,
  LoadingOutlined,
  SaveOutlined,
  StarOutlined,
  UserOutlined,
} from "@ant-design/icons";
import {
  createSoulTemplate,
  getSoulSources,
  type SoulSources,
  type SoulSpec,
} from "../../lib/partners-api";
import SoulEditor from "./SoulEditor";

const ZH_MESSAGES: Record<string, string> = {
  "Soul library": "灵魂库",
  "Clone a persona": "克隆 Persona",
  "Write your own": "自己撰写",
  "No soul templates yet.": "还没有灵魂模板。",
  "No personas in your chat workspace yet.": "你的聊天工作区还没有 Persona。",
  "The persona's markdown is copied into the partner — later edits to the persona won't affect it.":
    "Persona 的内容会被复制给伙伴——之后修改 Persona 不会影响它。",
  "Edited — your version becomes this partner's soul. The original template is untouched.":
    "已编辑——你的版本将成为这个伙伴的 soul，原模板保持不变。",
  "Template name": "模板名称",
  "Save to soul library": "存入灵魂库",
  "Save failed": "保存失败",
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

/** active:scale-[0.97] 按压缩放无法内联——模块加载时注入一次（CRA 无 SSR）。 */
const STYLE_ID = "dsh-partner-soul-picker-styles";
if (typeof document !== "undefined" && !document.getElementById(STYLE_ID)) {
  const styleEl = document.createElement("style");
  styleEl.id = STYLE_ID;
  styleEl.textContent = ".dsh-partner-soul-chip:active{transform:scale(0.97)}";
  document.head.appendChild(styleEl);
}

type SourceTab = "library" | "persona" | "custom";

// Soul ids ride in /souls/<id> URLs, so keep them ASCII/URL-safe (a CJK id is
// unreachable) — the server re-slugs authoritatively and the create flow uses
// the returned id, but producing an ASCII slug here keeps the preview honest
// and avoids sending a non-ASCII id over the wire.
function slugifySoulId(name: string): string {
  return (
    name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || `soul-${Date.now().toString(36)}`
  );
}

export default function SoulPicker({
  value,
  onChange,
}: {
  value: SoulSpec;
  onChange: (next: SoulSpec) => void;
}) {
  const [sources, setSources] = useState<SoulSources | null>(null);
  const [tab, setTab] = useState<SourceTab>(
    value.source === "persona"
      ? "persona"
      : value.source === "custom"
        ? "custom"
        : "library",
  );
  const [saveName, setSaveName] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState("");
  const [saveError, setSaveError] = useState("");
  const [hoveredTab, setHoveredTab] = useState<SourceTab | null>(null);
  const [hoveredChip, setHoveredChip] = useState<string | null>(null);
  const [nameFocused, setNameFocused] = useState(false);
  const [saveHover, setSaveHover] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        setSources(await getSoulSources());
      } catch {
        setSources({ library: [], personas: [] });
      }
    })();
  }, []);

  // Untouched wizard ("default" source) → preselect the first library soul
  // so the editor is visible and the actual content explicit from the start.
  useEffect(() => {
    if (value.source !== "default") return;
    const first = sources?.library[0];
    if (first)
      onChange({ source: "library", id: first.id, content: first.content });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once when sources land
  }, [sources]);

  const tabs: { key: SourceTab; label: string; icon: typeof StarOutlined }[] = [
    { key: "library", label: t("Soul library"), icon: BookOutlined },
    { key: "persona", label: t("Clone a persona"), icon: UserOutlined },
    { key: "custom", label: t("Write your own"), icon: StarOutlined },
  ];

  const selectLibrary = (id: string) => {
    const entry = sources?.library.find((s) => s.id === id);
    onChange({ source: "library", id, content: entry?.content });
  };

  const selectPersona = (name: string) => {
    const entry = sources?.personas.find((p) => p.name === name);
    onChange({ source: "persona", id: name, content: entry?.content });
  };

  // Typing into the editor detaches a private copy of whatever was selected.
  const editContent = (next: string) =>
    onChange({ source: "custom", content: next });

  // A template/persona was edited into a private copy on this tab.
  const detached = tab !== "custom" && value.source === "custom";

  const saveToLibrary = async () => {
    const content = (value.content ?? "").trim();
    const name = saveName.trim();
    if (!content || !name) return;
    setSaving(true);
    setSaveError("");
    try {
      const entry = await createSoulTemplate(
        slugifySoulId(name),
        name,
        content,
      );
      setSavedId(entry.id);
      setSources(await getSoulSources());
      // Keep the wizard pointed at the (identical) library entry.
      onChange({ source: "library", id: entry.id, content });
      setTab("library");
      setSaveName("");
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : t("Save failed"));
    } finally {
      setSaving(false);
    }
  };

  const showEditor = tab === "custom" || value.content !== undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div
        style={{
          display: "flex",
          width: "fit-content",
          gap: 4,
          borderRadius: 12,
          background: "var(--muted, #f1f5f9)",
          padding: 4,
        }}
      >
        {tabs.map(({ key, label, icon: Icon }) => {
          const active = tab === key;
          const hovered = hoveredTab === key;
          return (
            <button
              key={key}
              type="button"
              onClick={() => {
                setTab(key);
                if (key === "custom")
                  onChange({ source: "custom", content: value.content ?? "" });
              }}
              onMouseEnter={() => setHoveredTab(key)}
              onMouseLeave={() => setHoveredTab(null)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                borderRadius: 8,
                padding: "6px 12px",
                fontSize: 13,
                border: "none",
                cursor: "pointer",
                background: active
                  ? "var(--background, #f6f8fc)"
                  : "transparent",
                fontWeight: active ? 500 : 400,
                color: active
                  ? "var(--foreground, #0f172a)"
                  : hovered
                    ? "var(--foreground, #0f172a)"
                    : "var(--muted-foreground, #64748b)",
                boxShadow: active ? "0 1px 2px 0 rgba(0, 0, 0, 0.05)" : "none",
                transition: "all 150ms",
              }}
            >
              <Icon style={{ fontSize: 16 }} />
              {label}
            </button>
          );
        })}
      </div>

      {tab === "library" && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {(sources?.library ?? []).map((soul) => {
            const active = value.source === "library" && value.id === soul.id;
            const hovered = hoveredChip === `lib:${soul.id}`;
            return (
              <button
                key={soul.id}
                type="button"
                onClick={() => selectLibrary(soul.id)}
                onMouseEnter={() => setHoveredChip(`lib:${soul.id}`)}
                onMouseLeave={() => setHoveredChip(null)}
                className="dsh-partner-soul-chip"
                style={{
                  borderRadius: 9999,
                  border: `1px solid ${
                    active
                      ? "var(--primary, #2563eb)"
                      : hovered
                        ? "var(--ring, #2563eb)"
                        : "var(--border, #e2e8f0)"
                  }`,
                  padding: "6px 14px",
                  fontSize: 13,
                  fontWeight: active ? 500 : 400,
                  color: active
                    ? "var(--primary, #2563eb)"
                    : hovered
                      ? "var(--foreground, #0f172a)"
                      : "var(--muted-foreground, #64748b)",
                  background: active
                    ? "var(--secondary, #f1f5f9)"
                    : "transparent",
                  cursor: "pointer",
                  transition: "all 150ms",
                }}
              >
                {soul.name}
                {savedId === soul.id && (
                  <CheckOutlined
                    style={{
                      marginLeft: 4,
                      fontSize: 14,
                      verticalAlign: "-0.125em",
                      color: "var(--primary, #2563eb)",
                    }}
                  />
                )}
              </button>
            );
          })}
          {sources && sources.library.length === 0 && (
            <p
              style={{
                fontSize: 13,
                color: "var(--muted-foreground, #64748b)",
                margin: 0,
              }}
            >
              {t("No soul templates yet.")}
            </p>
          )}
        </div>
      )}

      {tab === "persona" && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {(sources?.personas ?? []).map((persona) => {
            const active =
              value.source === "persona" && value.id === persona.name;
            const hovered = hoveredChip === `per:${persona.name}`;
            return (
              <button
                key={persona.name}
                type="button"
                onClick={() => selectPersona(persona.name)}
                onMouseEnter={() => setHoveredChip(`per:${persona.name}`)}
                onMouseLeave={() => setHoveredChip(null)}
                title={persona.description}
                className="dsh-partner-soul-chip"
                style={{
                  borderRadius: 9999,
                  border: `1px solid ${
                    active
                      ? "var(--primary, #2563eb)"
                      : hovered
                        ? "var(--ring, #2563eb)"
                        : "var(--border, #e2e8f0)"
                  }`,
                  padding: "6px 14px",
                  fontSize: 13,
                  fontWeight: active ? 500 : 400,
                  color: active
                    ? "var(--primary, #2563eb)"
                    : hovered
                      ? "var(--foreground, #0f172a)"
                      : "var(--muted-foreground, #64748b)",
                  background: active
                    ? "var(--secondary, #f1f5f9)"
                    : "transparent",
                  cursor: "pointer",
                  transition: "all 150ms",
                }}
              >
                {persona.name}
              </button>
            );
          })}
          {sources && sources.personas.length === 0 && (
            <p
              style={{
                fontSize: 13,
                color: "var(--muted-foreground, #64748b)",
                margin: 0,
              }}
            >
              {t("No personas in your chat workspace yet.")}
            </p>
          )}
        </div>
      )}

      {showEditor && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <SoulEditor value={value.content ?? ""} onChange={editContent} />
          {tab === "persona" && value.source === "persona" && value.id && (
            <p
              style={{
                fontSize: 12,
                lineHeight: 1.625,
                color: "var(--muted-foreground, #64748b)",
                margin: 0,
              }}
            >
              {t(
                "The persona's markdown is copied into the partner — later edits to the persona won't affect it.",
              )}
            </p>
          )}
          {detached && (
            <p
              style={{
                fontSize: 12,
                lineHeight: 1.625,
                color: "var(--muted-foreground, #64748b)",
                margin: 0,
              }}
            >
              {t(
                "Edited — your version becomes this partner's soul. The original template is untouched.",
              )}
            </p>
          )}
        </div>
      )}

      {tab === "custom" && (value.content ?? "").trim() && (
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8 }}>
          <input
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            onFocus={() => setNameFocused(true)}
            onBlur={() => setNameFocused(false)}
            placeholder={t("Template name")}
            style={{
              width: 192,
              borderRadius: 8,
              border: `1px solid ${
                nameFocused ? "var(--ring, #2563eb)" : "var(--border, #e2e8f0)"
              }`,
              background: "transparent",
              padding: "6px 12px",
              fontSize: 13,
              outline: "none",
              transition: "border-color 150ms",
            }}
          />
          <button
            type="button"
            onClick={() => void saveToLibrary()}
            onMouseEnter={() => setSaveHover(true)}
            onMouseLeave={() => setSaveHover(false)}
            disabled={saving || !saveName.trim()}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              borderRadius: 8,
              border: `1px solid ${
                saveHover ? "var(--ring, #2563eb)" : "var(--border, #e2e8f0)"
              }`,
              padding: "6px 12px",
              fontSize: 13,
              fontWeight: 500,
              color: "var(--foreground, #0f172a)",
              background: "transparent",
              cursor: "pointer",
              opacity: saving || !saveName.trim() ? 0.4 : 1,
              transition: "all 150ms",
            }}
          >
            {saving ? (
              <LoadingOutlined spin style={{ fontSize: 14 }} />
            ) : (
              <SaveOutlined style={{ fontSize: 14 }} />
            )}
            {t("Save to soul library")}
          </button>
          {saveError && (
            <span
              style={{
                fontSize: 12,
                color: "var(--destructive, #ef4444)",
              }}
            >
              {saveError}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
