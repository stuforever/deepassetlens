/**
 * 复刻自 DeepTutor 原仓 web/components/partners/AssetPicker.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；t() → 文件内查表直出（zh/app.json 原译文，"Knowledge bases"
 * 键原译文即"个知识库"，照抄）；Tailwind 类逐项换内联样式（hover 用事件直写；
 * active:scale-[0.97] 按压缩放由模块加载时注入一次的 CSS 承载，
 * <style id="dsh-partner-asset-picker-styles">，同批5 settings/shared.tsx 口径）。
 * lucide-react→antd 图标登记：BookOpen → ReadOutlined；Database → DatabaseOutlined；
 * NotebookPen → FormOutlined（antd 无"笔记本+笔"组合图标）。
 *
 * Multi-select picker for the three asset classes a partner can be equipped
 * with. Selected items are COPIED into the partner workspace on submit —
 * the copy is the partner's own; later edits to the source don't propagate.
 */

import { useEffect, useRef, useState } from "react";
import {
  DatabaseOutlined,
  FormOutlined,
  ReadOutlined,
} from "@ant-design/icons";
import { listKnowledgeBases } from "../../lib/knowledge-api";
import { listSkills } from "../../lib/skills-api";
import { listNotebooks } from "../../lib/notebook-api";

const ZH_MESSAGES: Record<string, string> = {
  "Knowledge bases": "个知识库",
  Skills: "技能",
  Notebooks: "笔记本",
  "No knowledge bases available.": "暂无可用知识库。",
  "No skills available.": "暂无可用技能。",
  "No notebooks available.": "暂无可用笔记本。",
  "Selected items are copied into the partner's private workspace.":
    "选中的内容会复制进伙伴的私有工作区。",
  "Loading your library…": "正在加载你的资料库…",
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

/** :active 按压缩放无法内联——模块加载时注入一次（CRA 无 SSR）。 */
const STYLE_ID = "dsh-partner-asset-picker-styles";
if (typeof document !== "undefined" && !document.getElementById(STYLE_ID)) {
  const styleEl = document.createElement("style");
  styleEl.id = STYLE_ID;
  styleEl.textContent = ".dsh-partner-asset-chip:active{transform:scale(0.97)}";
  document.head.appendChild(styleEl);
}

export interface AssetSelection {
  knowledge_bases: string[];
  skills: string[];
  notebooks: string[];
}

interface Option {
  id: string;
  label: string;
  hint?: string;
}

function ChipGroup({
  icon: Icon,
  title,
  options,
  selected,
  onToggle,
  emptyText,
}: {
  icon: typeof DatabaseOutlined;
  title: string;
  options: Option[];
  selected: string[];
  onToggle: (id: string) => void;
  emptyText: string;
}) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  return (
    <div>
      <h4
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          fontSize: 13,
          fontWeight: 500,
          color: "var(--muted-foreground, #64748b)",
          margin: "0 0 6px",
        }}
      >
        <Icon style={{ fontSize: 16 }} />
        {title}
        {selected.length > 0 && (
          <span
            style={{
              borderRadius: 9999,
              background: "var(--secondary, #f1f5f9)",
              padding: "0 6px",
              fontSize: 11,
              fontWeight: 500,
              color: "var(--primary, #2563eb)",
            }}
          >
            {selected.length}
          </span>
        )}
      </h4>
      {options.length === 0 ? (
        <p
          style={{
            fontSize: 13,
            color: "var(--muted-foreground, #64748b)",
            margin: 0,
          }}
        >
          {emptyText}
        </p>
      ) : (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {options.map((option) => {
            const active = selected.includes(option.id);
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => onToggle(option.id)}
                onMouseEnter={() => setHoveredId(option.id)}
                onMouseLeave={() => setHoveredId(null)}
                title={option.hint}
                className="dsh-partner-asset-chip"
                style={{
                  borderRadius: 9999,
                  border: `1px solid ${
                    active
                      ? "var(--primary, #2563eb)"
                      : hoveredId === option.id
                        ? "var(--ring, #2563eb)"
                        : "var(--border, #e2e8f0)"
                  }`,
                  padding: "6px 14px",
                  fontSize: 13,
                  fontWeight: active ? 500 : 400,
                  color: active
                    ? "var(--primary, #2563eb)"
                    : hoveredId === option.id
                      ? "var(--foreground, #0f172a)"
                      : "var(--muted-foreground, #64748b)",
                  background: active
                    ? "var(--secondary, #f1f5f9)"
                    : "transparent",
                  cursor: "pointer",
                  transition: "all 150ms",
                }}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function AssetPicker({
  value,
  onChange,
  excluded,
  preselectAllSkills = false,
}: {
  value: AssetSelection;
  onChange: (next: AssetSelection) => void;
  /** Asset ids already provisioned (hidden from the picker). */
  excluded?: Partial<AssetSelection>;
  /** Select every skill once loaded (creation-wizard default). */
  preselectAllSkills?: boolean;
}) {
  const [kbs, setKbs] = useState<Option[]>([]);
  const [skills, setSkills] = useState<Option[]>([]);
  const [notebooks, setNotebooks] = useState<Option[]>([]);
  const [loading, setLoading] = useState(true);
  const latest = useRef({ value, onChange });
  latest.current = { value, onChange };

  useEffect(() => {
    void (async () => {
      setLoading(true);
      try {
        const [kbList, skillList, notebookList] = await Promise.all([
          listKnowledgeBases().catch(() => []),
          listSkills().catch(() => []),
          listNotebooks().catch(() => []),
        ]);
        setKbs(
          kbList.map((kb) => ({
            id: kb.id || kb.name,
            label: kb.name,
            hint: kb.provenance_label,
          })),
        );
        setSkills(
          skillList.map((skill) => ({
            id: skill.name,
            label: skill.name,
            hint: skill.description,
          })),
        );
        setNotebooks(
          notebookList.map((nb) => ({
            id: nb.id,
            label: nb.name,
            hint: nb.description,
          })),
        );
        if (preselectAllSkills && latest.current.value.skills.length === 0) {
          latest.current.onChange({
            ...latest.current.value,
            skills: skillList.map((skill) => skill.name),
          });
        }
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <p
        style={{
          fontSize: 13,
          color: "var(--muted-foreground, #64748b)",
          margin: 0,
        }}
      >
        {t("Loading your library…")}
      </p>
    );
  }

  const toggle = (key: keyof AssetSelection, id: string) => {
    const current = value[key];
    onChange({
      ...value,
      [key]: current.includes(id)
        ? current.filter((x) => x !== id)
        : [...current, id],
    });
  };

  const visible = (options: Option[], hidden?: string[]) =>
    hidden && hidden.length > 0
      ? options.filter(
          (o) => !hidden.includes(o.id) && !hidden.includes(o.label),
        )
      : options;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      <ChipGroup
        icon={DatabaseOutlined}
        title={t("Knowledge bases")}
        options={visible(kbs, excluded?.knowledge_bases)}
        selected={value.knowledge_bases}
        onToggle={(id) => toggle("knowledge_bases", id)}
        emptyText={t("No knowledge bases available.")}
      />
      <ChipGroup
        icon={ReadOutlined}
        title={t("Skills")}
        options={visible(skills, excluded?.skills)}
        selected={value.skills}
        onToggle={(id) => toggle("skills", id)}
        emptyText={t("No skills available.")}
      />
      <ChipGroup
        icon={FormOutlined}
        title={t("Notebooks")}
        options={visible(notebooks, excluded?.notebooks)}
        selected={value.notebooks}
        onToggle={(id) => toggle("notebooks", id)}
        emptyText={t("No notebooks available.")}
      />
      <p
        style={{
          fontSize: 12,
          color: "var(--muted-foreground, #64748b)",
          margin: 0,
        }}
      >
        {t("Selected items are copied into the partner's private workspace.")}
      </p>
    </div>
  );
}
