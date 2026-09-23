/**
 * ComposerAttachmentBar（批①b 四选择器；UX2批② 用户反馈：问数附件条只保留 🤖模型选择——
 * 知识库/技能/角色三选择器移除（知识库与技能走后端自动装配，角色=默认分析师现状等价）。
 * AttachmentSelection 结构保留（kbIds/skillCode/roleId 字段恒空——ExpertChat 请求链契约不变）。
 * 选择按专家记忆（localStorage attach:{expert}:model）。
 * 规范：md=200、选项>7 showSearch、选中态 chip 展示可随时改。
 */
import React, { useEffect, useState } from 'react';
import { Select } from 'antd';
import { llmAdminApi } from '../../services/api';

const md = 200;

function loadLS<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function saveLS(key: string, v: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(v));
  } catch { /* ignore */ }
}

export interface AttachmentSelection {
  kbIds: string[];
  skillCode?: string;
  modelId?: string;
  roleId?: string;
}

const ComposerAttachmentBar: React.FC<{
  expertId: string;
  value: AttachmentSelection;
  onChange: (next: AttachmentSelection) => void;
  testId?: string;
}> = ({ expertId, value, onChange, testId = 'attachment-bar' }) => {
  const [models, setModels] = useState<Array<{ id: string; name: string; isDefault?: boolean }>>([]);

  useEffect(() => {
    let alive = true;
    // UX2批②（反馈③）：模型下拉源=LLM 配置页连接表（llmAdminApi——id 即后端
    // get_llm_connection_by_id 认的连接键）；原 listLLMOptions 形状不匹配（profile_id/model_id
    // 无 connection_id 字段）→ 映射全被过滤=下拉恒空（用户实报「模型没有下拉框」根因）
    llmAdminApi.getConnections().then((resp: any) => {
      if (!alive) return;
      const body = resp?.data || resp;
      const list = (body?.data || body || []) as any[];
      setModels(list
        .filter((c: any) => c.enabled && c.capability === 'chat')
        .map((c: any) => ({
          id: c.id,
          name: c.name || c.model_name || c.id,
          isDefault: !!c.is_default,
        })));
      const def = list.find((c: any) => c.is_default && c.enabled && c.capability === 'chat');
      void def; // 默认项经 placeholder 展示（ExpertChat 自身 loader 已置默认连接）
    }).catch(() => { /* 静默空列 */ });
    return () => { alive = false; };
  }, []);

  const modelKey = `attach:${expertId}:model`;

  // 记忆加载（按专家）：value 为空时用 localStorage 回填一次
  useEffect(() => {
    const memoModel = loadLS<string | undefined>(modelKey, undefined);
    if (memoModel && !value.modelId) {
      onChange({ ...value, modelId: memoModel });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expertId]);

  const emit = (patch: Partial<AttachmentSelection>) => {
    const next = { ...value, ...patch };
    saveLS(modelKey, next.modelId ?? null);
    onChange(next);
  };

  return (
    <div
      data-testid={testId}
      style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}
    >
      {/* 🤖 模型（单选启用连接；默认=LLM 配置页 active 连接；UX2批② 只留此选择器） */}
      <Select
        allowClear
        size="small"
        variant="borderless"
        style={{ minWidth: md }}
        placeholder={(() => {
          const d = models.find((m) => m.isDefault);
          return d ? `🤖 ${d.name}（默认）` : '🤖 默认模型';
        })()}
        value={value.modelId}
        onChange={(id) => emit({ modelId: id || undefined })}
        showSearch={models.length > 7}
        optionFilterProp="label"
        popupMatchSelectWidth={md}
        options={models.map((m) => ({ value: m.id, label: m.isDefault ? `${m.name}（默认）` : m.name }))}
        data-testid="attach-model"
      />
    </div>
  );
};

export default ComposerAttachmentBar;
