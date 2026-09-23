/**
 * ComposerAttachmentBar（批①b——v4§二.4）：composer 附件条四选择器（左→右）。
 * 📚知识库（多选，列知识库名禁裸 UUID，选择随会话保持）/ ⚡技能（单选，B2 前全列+注释，
 * B2 后过滤 type=scenario）/ 🤖模型（单选启用连接，默认=LLM 配置页默认项）/ 🎭角色
 * （wenshu 角色卡 B2 后接，先隐藏位）。选择按专家记忆（localStorage attach:{expert}:{kb|skill|model}）。
 * 规范：md=200、选项>7 showSearch、选中态 chip 展示可随时改。
 */
import React, { useEffect, useState } from 'react';
import { Select, Typography } from 'antd';
import { knowledgeBaseApi } from '../../services/api';
import { listLLMOptions } from '../../lib/llm-options';
import { listSkills } from '../../lib/skills-api';

const { Text } = Typography;

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
}

const ComposerAttachmentBar: React.FC<{
  expertId: string;
  value: AttachmentSelection;
  onChange: (next: AttachmentSelection) => void;
  testId?: string;
}> = ({ expertId, value, onChange, testId = 'attachment-bar' }) => {
  const [kbs, setKbs] = useState<Array<{ id: string; name: string }>>([]);
  const [models, setModels] = useState<Array<{ id: string; name: string; isDefault?: boolean }>>([]);
  const [skills, setSkills] = useState<Array<{ code: string; name: string }>>([]);

  useEffect(() => {
    let alive = true;
    // 📚 数据源=自定义知识库（/api/v1/knowledge-bases，id+name——与 B1 kb_search_filtered 同域；
    // /api/v1/knowledge/list 是教学域注册表（无 id），不用于 kb_ids）
    knowledgeBaseApi.list().then((res: any) => {
      if (!alive) return;
      const rows: any[] = Array.isArray(res?.data) ? res.data : (res?.data?.data || []);
      setKbs(rows.map((k: any) => ({ id: k.id || k.kb_id || '', name: k.name || k.title || k.id || '' }))
        .filter((k) => k.id));
    }).catch(() => { /* 静默空列 */ });
    listLLMOptions().then((res) => {
      if (!alive) return;
      setModels((res.options || []).map((o: any) => ({
        id: o.connection_id || o.id || '',
        name: o.name || o.model_name || o.connection_id || '',
        isDefault: !!(res.active && (o.connection_id || o.id) && res.active === (o.connection_id || o.id)),
      })).filter((m) => m.id));
    }).catch(() => { /* 静默空列 */ });
    // ⚡技能：B2 前先全列（B2 落 type=scenario 后此处改 filter(s => s.type === 'scenario')）
    listSkills().then((rows) => {
      if (!alive) return;
      setSkills((rows || []).map((s: any) => ({ code: s.skill_code || s.code || '', name: s.name || s.skill_code || '' }))
        .filter((s) => s.code));
    }).catch(() => { /* 静默空列 */ });
    return () => { alive = false; };
  }, []);

  const kbKey = `attach:${expertId}:kb`;
  const skillKey = `attach:${expertId}:skill`;
  const modelKey = `attach:${expertId}:model`;

  // 记忆加载（按专家）：value 为空时用 localStorage 回填一次
  useEffect(() => {
    const memoKb = loadLS<string[]>(kbKey, []);
    const memoSkill = loadLS<string | undefined>(skillKey, undefined);
    const memoModel = loadLS<string | undefined>(modelKey, undefined);
    if ((memoKb.length || memoSkill || memoModel) &&
        !value.kbIds.length && !value.skillCode && !value.modelId) {
      onChange({ kbIds: memoKb, skillCode: memoSkill, modelId: memoModel });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expertId]);

  const emit = (patch: Partial<AttachmentSelection>) => {
    const next = { ...value, ...patch };
    saveLS(kbKey, next.kbIds);
    saveLS(skillKey, next.skillCode ?? null);
    saveLS(modelKey, next.modelId ?? null);
    onChange(next);
  };

  const selStyle = { minWidth: md } as const;

  return (
    <div
      data-testid={testId}
      style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}
    >
      {/* 📚 知识库（多选——B1 ChatRequest.kb_ids 消费链） */}
      <Select
        mode="multiple"
        allowClear
        size="small"
        variant="borderless"
        style={selStyle}
        placeholder="📚 知识库"
        maxTagCount="responsive"
        value={value.kbIds}
        onChange={(ids) => emit({ kbIds: ids })}
        showSearch={kbs.length > 7}
        optionFilterProp="label"
        popupMatchSelectWidth={md}
        options={kbs.map((k) => ({ value: k.id, label: k.name }))}
        data-testid="attach-kb"
      />
      {/* ⚡ 技能（单选；B2 前全列——B2 后只列 type=scenario） */}
      <Select
        allowClear
        size="small"
        variant="borderless"
        style={selStyle}
        placeholder="⚡ 技能"
        value={value.skillCode}
        onChange={(code) => emit({ skillCode: code || undefined })}
        showSearch={skills.length > 7}
        optionFilterProp="label"
        popupMatchSelectWidth={md}
        options={skills.map((s) => ({ value: s.code, label: s.name }))}
        data-testid="attach-skill"
      />
      {/* 🤖 模型（单选启用连接；默认=LLM 配置页 active 连接） */}
      <Select
        allowClear
        size="small"
        variant="borderless"
        style={selStyle}
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
      {/* 🎭 角色（wenshu 角色卡 B2 后接入——位先隐藏，保持附件条四槽位语义） */}
      <Text type="secondary" style={{ fontSize: 11 }} data-testid="attach-role-placeholder">🎭 角色</Text>
    </div>
  );
};

export default ComposerAttachmentBar;
