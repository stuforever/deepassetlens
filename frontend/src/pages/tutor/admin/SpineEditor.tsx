/**
 * SpineEditor —— 章节主线（spine）编辑器：确认编译前调整顺序/重命名/增删章节。
 * 1:1 复刻自原仓 DeepTutor web/app/(workspace)/book/components/SpineEditor.tsx（266 行）。
 * 复刻来源：Next.js + Tailwind + react-i18next + lucide-react + "@/lib/book-types"
 * 替换点：
 *  - "use client" 删除；
 *  - react-i18next（useTranslation/t(key)）→ 中文直出（译文取自原仓 web/locales/zh/app.json）；
 *  - lucide-react → @ant-design/icons 语义就近（ArrowUp→ArrowUpOutlined、ArrowDown→ArrowDownOutlined、
 *    Plus→PlusOutlined、Trash2→DeleteOutlined、CheckCircle2→CheckCircleOutlined、Loader2→LoadingOutlined spin）；
 *  - import 契约：@/lib/book-types → './book-types'（并行 Agent 同步产出，导出名
 *    Chapter / ContentType / Spine 与原仓一致）；
 *  - Tailwind → antd 组件 + 最小内联样式：标题/摘要输入 → antd Input，内容类型下拉 → antd Select，
 *    学习目标 → Input.TextArea（resize none），增章节 → Button type="dashed" block，
 *    确认 → Button type="primary"（loading 态等价原 Loader2 spin + disabled）；
 *  - 删除按钮 hover:bg-rose-50 → onMouseEnter/Leave 置 #fff1f2；
 *  - 保留原 ContentTypeOption 注释语义（overview 由引擎保留，不在选项中）。
 * 不变：props 契约（spine/onConfirm/loading）、chapters 本地状态与 move/remove/addChapter/
 *       handleConfirm（过滤空标题并重排 order）、新章节 id 生成规则、data-testid="book-spine-confirm"。
 */
import { useState } from "react";
import { Button, Input, Select } from "antd";
import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import type { Chapter, ContentType, Spine } from "./book-types";

/**
 * Each chapter declares a *content type* — a hint to the SectionArchitect
 * about what kind of block sequence to plan (e.g. theory chapters get
 * Section + Figure + Quiz; practice chapters get more Quiz + Code).
 *
 * `overview` is intentionally excluded — it's reserved for the engine-injected
 * first chapter (the table of contents + concept map).
 */
interface ContentTypeOption {
  value: ContentType;
  label: string;
  description: string;
}

const CONTENT_TYPE_OPTIONS: ContentTypeOption[] = [
  {
    value: "theory",
    label: "理论",
    description: "长篇解释，包含图示、闪卡和测验。",
  },
  {
    value: "derivation",
    label: "推导",
    description: "分步推导，通常包含动画和验证代码。",
  },
  {
    value: "history",
    label: "历史记录",
    description: "叙事、时间线与时期图示，并以回顾测验收尾。",
  },
  {
    value: "practice",
    label: "练习",
    description: "以测验为主，包含可运行代码脚手架和解释。",
  },
  {
    value: "concept",
    label: "概念",
    description: "定义、图示、闪卡与常见误区提示。",
  },
];

export interface SpineEditorProps {
  spine: Spine;
  onConfirm: (spine: Spine) => void | Promise<void>;
  loading?: boolean;
}

export default function SpineEditor({
  spine,
  onConfirm,
  loading = false,
}: SpineEditorProps) {
  const [chapters, setChapters] = useState<Chapter[]>(spine.chapters);

  const updateChapter = (idx: number, patch: Partial<Chapter>) => {
    setChapters((prev) =>
      prev.map((c, i) => (i === idx ? { ...c, ...patch } : c)),
    );
  };

  const move = (idx: number, dir: -1 | 1) => {
    setChapters((prev) => {
      const next = [...prev];
      const target = idx + dir;
      if (target < 0 || target >= next.length) return prev;
      [next[idx], next[target]] = [next[target], next[idx]];
      return next.map((c, i) => ({ ...c, order: i }));
    });
  };

  const remove = (idx: number) => {
    setChapters((prev) =>
      prev.filter((_, i) => i !== idx).map((c, i) => ({ ...c, order: i })),
    );
  };

  const addChapter = () => {
    setChapters((prev) => [
      ...prev,
      {
        id: `ch_new_${prev.length + 1}_${Date.now().toString(36)}`,
        title: "新章节",
        learning_objectives: [],
        content_type: "theory",
        source_anchors: [],
        prerequisites: [],
        page_ids: [],
        summary: "",
        order: prev.length,
      },
    ]);
  };

  const handleConfirm = async () => {
    const cleaned = chapters
      .filter((c) => c.title.trim())
      .map((c, i) => ({ ...c, order: i }));
    await onConfirm({ ...spine, chapters: cleaned });
  };

  return (
    <div style={{ display: "flex", height: "100%", flexDirection: "column" }}>
      <header
        style={{
          borderBottom: "1px solid #e4e4e7",
          background: "rgba(255,255,255,0.6)",
          padding: "16px 24px",
        }}
      >
        <h2
          style={{
            margin: 0,
            fontSize: 16,
            fontWeight: 600,
            color: "rgba(0,0,0,0.88)",
          }}
        >
          检查章节主线
        </h2>
        <p style={{ margin: "4px 0 0", fontSize: 14, color: "#6b7280" }}>
          在书籍开始编译前，可调整顺序、重命名或删除章节。
        </p>
      </header>

      <div style={{ flex: 1, overflowY: "auto", padding: "16px 24px" }}>
        <div
          style={{
            margin: "0 auto",
            display: "flex",
            width: "100%",
            maxWidth: 768,
            flexDirection: "column",
            gap: 12,
          }}
        >
          {chapters.map((chapter, idx) => (
            <div
              key={chapter.id}
              style={{
                borderRadius: 16,
                border: "1px solid #e4e4e7",
                background: "#fff",
                padding: 16,
                boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  gap: 8,
                }}
              >
                <Input
                  value={chapter.title}
                  onChange={(e) => updateChapter(idx, { title: e.target.value })}
                  style={{
                    flex: 1,
                    borderRadius: 8,
                    fontSize: 16,
                    fontWeight: 600,
                    border: "1px solid #e4e4e7",
                  }}
                />
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <Button
                    onClick={() => move(idx, -1)}
                    disabled={idx === 0}
                    icon={<ArrowUpOutlined style={{ fontSize: 12 }} />}
                    style={{
                      borderRadius: 6,
                      borderColor: "#e4e4e7",
                      color: "#6b7280",
                    }}
                  />
                  <Button
                    onClick={() => move(idx, 1)}
                    disabled={idx === chapters.length - 1}
                    icon={<ArrowDownOutlined style={{ fontSize: 12 }} />}
                    style={{
                      borderRadius: 6,
                      borderColor: "#e4e4e7",
                      color: "#6b7280",
                    }}
                  />
                  <Button
                    onClick={() => remove(idx)}
                    icon={<DeleteOutlined style={{ fontSize: 12 }} />}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "#fff1f2";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "";
                    }}
                    style={{
                      borderRadius: 6,
                      borderColor: "rgba(253,164,175,0.6)",
                      color: "#f43f5e",
                    }}
                  />
                </div>
              </div>

              <div
                style={{
                  marginTop: 12,
                  display: "grid",
                  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                  gap: 12,
                }}
              >
                <label style={{ fontSize: 12, color: "#6b7280", display: "block" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    内容类型
                    <span
                      style={{ cursor: "help", fontSize: 10, opacity: 0.6 }}
                      title="用于指导章节内容块规划的提示（文本长度、是否包含图示/测验/代码等）。"
                    >
                      ⓘ
                    </span>
                  </span>
                  <Select
                    value={chapter.content_type}
                    onChange={(value) =>
                      updateChapter(idx, { content_type: value as ContentType })
                    }
                    style={{ marginTop: 4, width: "100%" }}
                    options={CONTENT_TYPE_OPTIONS.map((opt) => ({
                      value: opt.value,
                      label: opt.label,
                    }))}
                  />
                  <span
                    style={{
                      marginTop: 4,
                      display: "block",
                      fontSize: 11,
                      lineHeight: 1.375,
                      color: "rgba(107,114,128,0.8)",
                    }}
                  >
                    {CONTENT_TYPE_OPTIONS.find(
                      (o) => o.value === chapter.content_type,
                    )?.description || "给章节架构器的内容块规划提示。"}
                  </span>
                </label>
                <label style={{ fontSize: 12, color: "#6b7280", display: "block" }}>
                  总结
                  <Input
                    value={chapter.summary}
                    onChange={(e) =>
                      updateChapter(idx, { summary: e.target.value })
                    }
                    placeholder="可选的一行描述"
                    style={{ marginTop: 4, borderRadius: 6 }}
                  />
                </label>
              </div>

              <label
                style={{
                  marginTop: 12,
                  display: "block",
                  fontSize: 12,
                  color: "#6b7280",
                }}
              >
                学习目标（每行一个）
                <Input.TextArea
                  value={chapter.learning_objectives.join("\n")}
                  onChange={(e) =>
                    updateChapter(idx, {
                      learning_objectives: e.target.value
                        .split("\n")
                        .map((s) => s.trim())
                        .filter(Boolean),
                    })
                  }
                  rows={3}
                  style={{ marginTop: 4, resize: "none", borderRadius: 6 }}
                />
              </label>
            </div>
          ))}

          <Button
            type="dashed"
            block
            onClick={addChapter}
            icon={<PlusOutlined style={{ fontSize: 16 }} />}
            style={{
              height: 38,
              borderRadius: 12,
              fontSize: 14,
              fontWeight: 500,
              color: "#6b7280",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
            }}
          >
            添加章节
          </Button>
        </div>
      </div>

      <footer
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          gap: 12,
          borderTop: "1px solid #e4e4e7",
          background: "rgba(255,255,255,0.6)",
          padding: "12px 24px",
        }}
      >
        <Button
          type="primary"
          onClick={handleConfirm}
          loading={loading}
          data-testid="book-spine-confirm"
          icon={<CheckCircleOutlined style={{ fontSize: 16 }} />}
          style={{
            height: 38,
            borderRadius: 12,
            fontSize: 14,
            fontWeight: 500,
            padding: "0 16px",
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          确认主线并开始编译
        </Button>
      </footer>
    </div>
  );
}
