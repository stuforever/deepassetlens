/**
 * 知识库详情容器（IA批4 复刻——源 DeepTutor web/components/knowledge/KnowledgeBaseDetail.tsx 1:1，antd 重建）。
 * 区块：空态卡 / 头卡（返回行 · 标题+徽标行 · 元信息行 · 重试动作 · 分区导航）/ 分区体（files 主从全宽 + add/versions/settings 居中）。
 * ④语义迁移（B0 增量迁进复刻页对应位，见 docs/superpowers/plans/2026-09-16 三专家门户批4 4.4）：
 *   判定 isTutorKb（rag_provider==='tutor_dt' 或 pointer_params.source==='tutor'）；
 *   ② tutor 分支提示（元信息行下，与 connected 提示同位置，注册表镜像说明+pointer_params）；
 *   ④ connected 提示行 gate（connected 文案行加 !isTutorKb，不得盖 tutor 行）；
 *   ③ isTutorKb 隐藏「添加文档」（上传文档）入口并显示 ② 提示。
 */
import { useState } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import { Button, Typography } from 'antd';
import {
  ArrowLeftOutlined,
  BlockOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  LoadingOutlined,
  ReloadOutlined,
  SettingOutlined,
  StarFilled,
  UploadOutlined,
} from '@ant-design/icons';
import type { KnowledgeUploadPolicy } from './knowledge-api';
import {
  formatKnowledgeTimestamp,
  resolveKbStatus,
  type KnowledgeBase,
} from './knowledge-helpers';
import type { TaskState } from './useKnowledgeProgress';
import type { HistoryEntry } from './useKnowledgeHistory';
import KbStatusBadge from './KbStatusBadge';
import KbFilesTab from './KbFilesTab';
import KbDocumentsSection from './KbDocumentsSection';
import KbIndexVersionsSection from './KbIndexVersionsSection';
import KbSettingsSection from './KbSettingsSection';

type DetailSection = 'files' | 'add' | 'versions' | 'settings';

interface KnowledgeBaseDetailProps {
  kb: KnowledgeBase | null;
  uploadPolicy: KnowledgeUploadPolicy;
  task?: TaskState;
  history: HistoryEntry[];
  onCreate: () => void;
  onUpload: (kbName: string, files: File[]) => Promise<void>;
  onReindex: (kbName: string) => Promise<void>;
  onRetry: (kbName: string) => Promise<void>;
  onSetDefault: (kbName: string) => Promise<void>;
  onDelete: (kbName: string) => Promise<void>;
  onClearHistory: (kbName: string) => void;
  onBack?: () => void;
}

const SECTIONS: {
  key: DetailSection;
  label: string;
  Icon: typeof FileTextOutlined;
}[] = [
  { key: 'files', label: '文件', Icon: FileTextOutlined },
  { key: 'add', label: '添加文档', Icon: UploadOutlined },
  { key: 'versions', label: '索引版本', Icon: BlockOutlined },
  { key: 'settings', label: '设置', Icon: SettingOutlined },
];

/** 全宽（不加 max-w 包裹）填充详情体的分区。 */
const FULL_BLEED_SECTIONS = new Set<DetailSection>(['files']);

const COLOR_BORDER = '#e5e7eb';
const COLOR_CARD = '#ffffff';
const COLOR_MUTED_BG = '#f3f4f6';
const COLOR_MUTED_FG = '#6b7280';
const COLOR_FG = '#1f2937';
const COLOR_PRIMARY = '#1677ff';

const badgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
  borderRadius: 999,
  padding: '2px 8px',
  fontSize: 10,
  fontWeight: 500,
  lineHeight: '14px',
};

const sectionNavBtnStyle = (active: boolean): CSSProperties => ({
  display: 'inline-flex',
  flexShrink: 0,
  alignItems: 'center',
  gap: 6,
  padding: '8px 12px',
  fontSize: 12.5,
  fontWeight: 500,
  color: active ? COLOR_FG : COLOR_MUTED_FG,
  borderBottom: `2px solid ${active ? COLOR_PRIMARY : 'transparent'}`,
  background: 'transparent',
  borderLeft: 0,
  borderRight: 0,
  borderTop: 0,
  cursor: 'pointer',
});

export default function KnowledgeBaseDetail({
  kb,
  uploadPolicy,
  task,
  history,
  onCreate,
  onUpload,
  onReindex,
  onRetry,
  onSetDefault,
  onDelete,
  onClearHistory,
  onBack,
}: KnowledgeBaseDetailProps) {
  const [section, setSection] = useState<DetailSection>('files');
  const [retrySubmitting, setRetrySubmitting] = useState(false);

  if (!kb) {
    return (
      <main
        style={{
          display: 'flex',
          flex: 1,
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--background, #fff)',
          padding: 24,
        }}
      >
        <div
          style={{
            maxWidth: 384,
            borderRadius: 16,
            border: `1px dashed ${COLOR_BORDER}`,
            background: 'rgba(255,255,255,0.4)',
            padding: 32,
            textAlign: 'center',
          }}
        >
          <div
            style={{
              margin: '0 auto 16px',
              display: 'flex',
              height: 48,
              width: 48,
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 16,
              background: COLOR_MUTED_BG,
              color: COLOR_MUTED_FG,
            }}
          >
            <DatabaseOutlined style={{ fontSize: 20 }} />
          </div>
          <div style={{ fontSize: 14, fontWeight: 500, color: COLOR_FG }}>
            尚未选择知识库
          </div>
          <p
            style={{
              margin: '8px auto 0',
              maxWidth: 320,
              fontSize: 12,
              lineHeight: 1.6,
              color: COLOR_MUTED_FG,
            }}
          >
            从左侧列表选择一个知识库，或新建一个以开始。
          </p>
          <Button
            type="primary"
            onClick={onCreate}
            style={{ marginTop: 16, height: 30, fontSize: 13 }}
          >
            创建你的第一个知识库
          </Button>
        </div>
      </main>
    );
  }

  const meta = (kb.metadata || {}) as {
    embedding_model?: string;
    embedding_dim?: number;
    last_updated?: string;
    last_indexed_at?: string;
  };
  const provider = kb.statistics?.rag_provider || 'llamaindex';
  const embeddingLabel = meta.embedding_model
    ? typeof meta.embedding_dim === 'number'
      ? `${meta.embedding_model} · ${meta.embedding_dim}维`
      : meta.embedding_model
    : '默认嵌入配置';
  const updatedLabel = formatKnowledgeTimestamp(meta.last_updated) || '未知时间';
  const lastIndexedLabel = formatKnowledgeTimestamp(meta.last_indexed_at);

  const isReindexingLocally =
    (task?.kind === 'reindex' || task?.kind === 'retry') &&
    task.executing === true;
  const status = resolveKbStatus(kb);
  const canRetry = status === 'error' && !kb.read_only;

  // ④语义迁移：tutor 域导入行判定——教学域注册表镜像，机制面走教学域原通道
  const isTutorKb = !!(
    kb &&
    ((kb as any).rag_provider === 'tutor_dt' ||
      ((((kb as any).pointer_params || {}) as any).source === 'tutor'))
  );

  const handleRetry = async () => {
    if (!canRetry || retrySubmitting || isReindexingLocally) return;
    setRetrySubmitting(true);
    try {
      await onRetry(kb.name);
    } finally {
      setRetrySubmitting(false);
    }
  };

  const fullBleed = FULL_BLEED_SECTIONS.has(section);
  // ③头卡动作行：isTutorKb 隐藏「添加文档」（上传文档）入口——上传走教学域原通道
  const navSections = isTutorKb
    ? SECTIONS.filter((s) => s.key !== 'add')
    : SECTIONS;

  const navButton = ({
    key,
    label,
    Icon,
  }: {
    key: DetailSection;
    label: string;
    Icon: typeof FileTextOutlined;
  }): ReactNode => {
    const active = section === key;
    return (
      <button
        key={key}
        type="button"
        onClick={() => setSection(key)}
        style={sectionNavBtnStyle(active)}
      >
        <Icon style={{ fontSize: 13 }} />
        {label}
      </button>
    );
  };

  return (
    <main
      style={{
        display: 'flex',
        height: '100%',
        flex: 1,
        flexDirection: 'column',
        overflow: 'hidden',
        background: 'var(--background, #fff)',
      }}
    >
      {/* 头卡（Header） */}
      <div
        style={{
          borderBottom: `1px solid ${COLOR_BORDER}`,
          background: COLOR_CARD,
          padding: '16px 24px 0',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 12,
          }}
        >
          <div style={{ minWidth: 0, flex: 1 }}>
            {onBack && (
              <button
                type="button"
                onClick={onBack}
                style={{
                  marginBottom: 6,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  fontSize: 11.5,
                  fontWeight: 500,
                  color: COLOR_MUTED_FG,
                  background: 'transparent',
                  border: 0,
                  padding: 0,
                  cursor: 'pointer',
                }}
              >
                <ArrowLeftOutlined style={{ fontSize: 14 }} />
                知识库列表
              </button>
            )}
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <h1
                style={{
                  margin: 0,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  fontFamily:
                    "ui-serif, Georgia, Cambria, 'Times New Roman', serif",
                  fontSize: 18,
                  fontWeight: 600,
                  letterSpacing: -0.2,
                  color: COLOR_FG,
                }}
              >
                {kb.name}
              </h1>
              {kb.is_default && (
                <span
                  style={{
                    ...badgeStyle,
                    background: '#fef3c7',
                    color: '#b45309',
                  }}
                >
                  <StarFilled style={{ fontSize: 12 }} />
                  默认
                </span>
              )}
              {/* ④语义迁移 gate：connected/来源提示文案行不盖 tutor 行 */}
              {kb.assigned && !isTutorKb && (
                <span
                  style={{
                    ...badgeStyle,
                    background: 'rgba(16,185,129,0.1)',
                    color: '#047857',
                  }}
                >
                  {kb.provenance_label || '由管理员分配'}
                </span>
              )}
              <KbStatusBadge
                kb={kb}
                isReindexingLocally={isReindexingLocally}
              />
            </div>
            <p
              style={{
                margin: '4px 0 0',
                fontSize: 12,
                color: COLOR_MUTED_FG,
              }}
            >
              {provider} · {embeddingLabel} · 最近更新 {updatedLabel}
              {lastIndexedLabel ? ` · 最近索引 ${lastIndexedLabel}` : ''}
            </p>
            {/* ④语义迁移：connected 提示行（gate !isTutorKb——connected 文案不得盖 tutor 行） */}
            {((kb as any).type || 'indexed') === 'connected' && !isTutorKb && (
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                指针型知识库：检索实时透传外部索引，无向量化工序。
              </Typography.Text>
            )}
            {/* ②语义迁移：tutor 分支提示（与 connected 提示同位置——注册表镜像说明+pointer_params） */}
            {isTutorKb && (
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                tutor 域导入库（教学域注册表镜像）：文档管理/解析状态/检索测试走教学域原通道（tutor
                知识库），本页仅注册表浏览；指针参数{' '}
                {(() => {
                  try {
                    return (
                      (JSON.stringify((kb as any).pointer_params) || '').slice(
                        0,
                        120,
                      ) || ''
                    );
                  } catch {
                    return '';
                  }
                })()}
              </Typography.Text>
            )}
          </div>
          {canRetry && (
            <Button
              size="small"
              danger
              onClick={() => void handleRetry()}
              disabled={retrySubmitting || isReindexingLocally}
              title="使用此知识库中已经保存的文档重试索引。"
              style={{
                flexShrink: 0,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                borderColor: '#fecaca',
                background: '#fef2f2',
                color: '#b91c1c',
                fontSize: 12,
              }}
              icon={
                retrySubmitting || isReindexingLocally ? (
                  <LoadingOutlined spin />
                ) : (
                  <ReloadOutlined />
                )
              }
            >
              {retrySubmitting || isReindexingLocally ? '正在重试…' : '重试索引'}
            </Button>
          )}
        </div>

        {/* 分区导航（Section nav） */}
        <nav
          style={{
            marginTop: 12,
            display: 'flex',
            gap: 4,
            overflowX: 'auto',
          }}
        >
          {navSections.map((s) => navButton(s))}
        </nav>
      </div>

      {/* 分区体（Body） */}
      <div style={{ minHeight: 0, flex: 1, overflow: 'hidden' }}>
        {section === 'files' ? (
          <KbFilesTab key={kb.name} kb={kb} task={task} />
        ) : (
          <div style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
            <div style={fullBleed ? undefined : { maxWidth: 768, margin: '0 auto' }}>
              {section === 'add' && (
                <KbDocumentsSection
                  kb={kb}
                  uploadPolicy={uploadPolicy}
                  task={task}
                  history={history}
                  onClearHistory={() => onClearHistory(kb.name)}
                  onRetry={handleRetry}
                  onUpload={(files) =>
                    kb.read_only ? Promise.resolve() : onUpload(kb.name, files)
                  }
                />
              )}
              {section === 'versions' && (
                <KbIndexVersionsSection
                  kb={kb}
                  task={task}
                  onReindex={() =>
                    kb.read_only
                      ? Promise.resolve()
                      : status === 'error'
                        ? handleRetry()
                        : onReindex(kb.name)
                  }
                />
              )}
              {section === 'settings' && (
                <KbSettingsSection
                  kb={kb}
                  onSetDefault={() =>
                    kb.read_only ? Promise.resolve() : onSetDefault(kb.name)
                  }
                  onDelete={() =>
                    kb.read_only ? Promise.resolve() : onDelete(kb.name)
                  }
                />
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
