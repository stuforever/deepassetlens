/**
 * KbSettingsSection —— 知识库「设置」区（只读元数据概览 + 设为默认 + 危险区删除入口）。
 * 1:1 复刻自原仓 DeepTutor web/components/knowledge/KbSettingsSection.tsx（130 行）。
 * 复刻来源：Next.js + Tailwind + react-i18next + lucide-react + "@/lib/knowledge-helpers"
 * 替换点：
 *  - "use client" 删除；
 *  - react-i18next（useTranslation/t(key)）→ 中文直出（译文取自原仓 web/locales/zh/app.json：
 *    "Overview"→概览、"RAG provider"→RAG 提供商、"Embedding"→嵌入模型、"d"→维、
 *    "Default embedding"→默认嵌入配置、"Created"→创建时间、"Updated"→最近更新、
 *    "Last indexed"→最近索引、"On-disk path"→磁盘路径、"Default knowledge base"→默认知识库、
 *    "Currently default"→当前默认、"Set as default"→设为默认、"Danger zone"→危险操作、
 *    "Delete knowledge base"→删除知识库 等）；
 *  - lucide-react → @ant-design/icons 语义就近：Star(fill)→StarFilled、Star→StarOutlined、
 *    Trash2→DeleteOutlined；
 *  - Tailwind → antd 组件 + 最小内联样式（概览 dl 网格 grid 2 列、危险区红框 #fecaca/
 *    rgba(254,242,242,0.4)、当前默认 amber #fef3c7/#b45309、muted #8c8c8c）；
 *  - window.confirm（源在 KnowledgePage）→ 本组件删除按钮经 antd Modal.confirm 确认，
 *    文案对拍 zh/app.json「Delete knowledge base "{{name}}"?」→「确定删除知识库「{{name}}」吗？」；
 *  - import 契约：formatKnowledgeTimestamp/KnowledgeBase → './knowledge-helpers'
 *    （并行 Agent 同步产出，按名 import）。
 * 不变：props 契约（kb/onSetDefault/onDelete）、provider 缺省 "llamaindex"、
 *       embeddingLabel 兜底链（model·dim维 → model → 默认嵌入配置）、
 *       kb.path 仅存在时显示（跨 2 列 mono 小字）、is_default 双态（徽标/按钮）、
 *       空时间显示 "—"、Field 标签 10.5px 大写字距样式。
 */
import type { CSSProperties, ReactNode } from "react";
import { Button, Flex, Modal } from "antd";
import { DeleteOutlined, StarFilled, StarOutlined } from "@ant-design/icons";
import {
  formatKnowledgeTimestamp,
  type KnowledgeBase,
} from "./knowledge-helpers";

const BORDER = "#f0f0f0";
const MUTED = "#8c8c8c";
const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

interface KbSettingsSectionProps {
  kb: KnowledgeBase;
  onSetDefault: () => Promise<void>;
  onDelete: () => Promise<void>;
}

export default function KbSettingsSection({
  kb,
  onSetDefault,
  onDelete,
}: KbSettingsSectionProps) {
  const meta = kb.metadata || {};
  const provider = kb.statistics?.rag_provider || "llamaindex";
  const embeddingLabel = meta.embedding_model
    ? typeof meta.embedding_dim === "number"
      ? `${meta.embedding_model} · ${meta.embedding_dim}维`
      : meta.embedding_model
    : "默认嵌入配置";
  const created = formatKnowledgeTimestamp(meta.created_at);
  const updated = formatKnowledgeTimestamp(meta.last_updated);
  const lastIndexed = formatKnowledgeTimestamp(meta.last_indexed_at);

  // 源仓删除确认在 KnowledgePage 用 window.confirm；本复刻按规约改为 antd Modal.confirm。
  const confirmDelete = () => {
    Modal.confirm({
      title: `确定删除知识库「${kb.name}」吗？`,
      okText: "删除",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: () => onDelete(),
    });
  };

  return (
    <Flex vertical gap={24}>
      <Flex vertical gap={12}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 500 }}>概览</div>
          <div style={{ marginTop: 2, fontSize: 11.5, color: MUTED }}>
            只读元数据。使用下方操作来管理此知识库。
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 12,
            border: `1px solid ${BORDER}`,
            borderRadius: 8,
            background: "#ffffff",
            padding: 12,
          }}
        >
          <Field label="RAG 提供商">{provider}</Field>
          <Field label="嵌入模型">{embeddingLabel}</Field>
          <Field label="创建时间">{created || "—"}</Field>
          <Field label="最近更新">{updated || "—"}</Field>
          <Field label="最近索引">{lastIndexed || "—"}</Field>
          {kb.path && (
            <Field label="磁盘路径" style={{ gridColumn: "span 2" }}>
              <span style={{ fontFamily: MONO, fontSize: 10.5, color: MUTED }}>
                {kb.path}
              </span>
            </Field>
          )}
        </div>
      </Flex>

      <Flex
        vertical
        gap={12}
        style={{
          border: `1px solid ${BORDER}`,
          borderRadius: 8,
          background: "#ffffff",
          padding: 12,
        }}
      >
        <div>
          <div style={{ fontSize: 12.5, fontWeight: 500 }}>默认知识库</div>
          <div style={{ marginTop: 2, fontSize: 11.5, color: MUTED }}>
            默认知识库会在 Chat 与伙伴中被自动选用。
          </div>
        </div>
        {kb.is_default ? (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              borderRadius: 6,
              background: "#fef3c7",
              padding: "4px 10px",
              fontSize: 12,
              fontWeight: 500,
              color: "#b45309",
              alignSelf: "flex-start",
            }}
          >
            <StarFilled style={{ fontSize: 12 }} />
            当前默认
          </span>
        ) : (
          <div>
            <Button
              icon={<StarOutlined />}
              onClick={() => void onSetDefault()}
              style={{ fontSize: 12, fontWeight: 500 }}
            >
              设为默认
            </Button>
          </div>
        )}
      </Flex>

      <Flex
        vertical
        gap={12}
        style={{
          border: "1px solid #fecaca",
          borderRadius: 8,
          background: "rgba(254,242,242,0.4)",
          padding: 12,
        }}
      >
        <div>
          <div style={{ fontSize: 12.5, fontWeight: 500, color: "#b91c1c" }}>
            危险操作
          </div>
          <div
            style={{
              marginTop: 2,
              fontSize: 11.5,
              color: "rgba(185,28,28,0.8)",
            }}
          >
            删除知识库会永久移除其原始文档与所有索引版本。
          </div>
        </div>
        <div>
          <Button
            icon={<DeleteOutlined />}
            onClick={confirmDelete}
            style={{
              fontSize: 12,
              fontWeight: 500,
              border: "1px solid #fca5a5",
              background: "#fef2f2",
              color: "#b91c1c",
            }}
          >
            删除知识库
          </Button>
        </div>
      </Flex>
    </Flex>
  );
}

function Field({
  label,
  children,
  style,
}: {
  label: string;
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <div style={style}>
      <div
        style={{
          fontSize: 10.5,
          textTransform: "uppercase",
          letterSpacing: "0.14em",
          color: MUTED,
        }}
      >
        {label}
      </div>
      <div style={{ marginTop: 4, fontSize: 12.5 }}>{children}</div>
    </div>
  );
}
