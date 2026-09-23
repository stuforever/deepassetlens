/**
 * ComposerAttachmentBar（批①b——v4§二.4；批⑤ v4§三/§四 接线）：composer 附件条四选择器（左→右）。
 * 📚知识库（多选，列知识库名禁裸 UUID，选择随会话保持）/ ⚡技能（单选，B2 后**只列场景技能**
 * type=scenario&status=published——通用技能自动装配不出现在下拉，§二.4）/ 🤖模型（单选启用连接，
 * 默认=LLM 配置页默认项）/ 🎭角色（wenshu 角色卡三卡——B2 GET /api/experts/{id}/roles，
 * role_id→ChatRequest.role_id；空=默认分析师现状等价）。其他专家角色位保持占位。
 * 数据源切换（批⑤）：⚡ 由 v1 /skills/list 改 v2 注册表（Skill.type 分型——8 问数场景技能宿主）。
 * 选择按专家记忆（localStorage attach:{expert}:{kb|skill|model|role}）。
 * 规范：md=200、选项>7 showSearch、选中态 chip 展示可随时改。
 */
import React, { useEffect, useState } from 'react';
import { Select, Typography } from 'antd';
import { knowledgeBaseApi } from '../../services/api';
import { skillV2Api } from '../../services/skillV2Api';
import { listLLMOptions } from '../../lib/llm-options';
import { apiFetch, apiUrl } from '../../lib/api';

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
  roleId?: string;
}

interface ExpertRole {
  role_id: string;
  name: string;
  description?: string;
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
  const [roles, setRoles] = useState<ExpertRole[]>([]);

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
    // ⚡技能（批⑤ v4§二.4/§三）：v2 注册表场景分型——只列 type=scenario 且已发布；
    // 通用技能走自动装配不出现在下拉
    skillV2Api.listSkills({ type: 'scenario', status: 'published', limit: 200 }).then((res) => {
      if (!alive) return;
      const rows = res?.data?.data || [];
      setSkills((rows || []).map((s: any) => ({ code: s.skill_code || '', name: s.name || s.skill_code || '' }))
        .filter((s) => s.code));
    }).catch(() => { /* 静默空列 */ });
    // 🎭角色（批⑤ v4§四）：wenshu 三角色卡——数据源=GET /api/experts/{id}/roles
    if (expertId === 'wenshu') {
      apiFetch(apiUrl(`/api/experts/wenshu/roles`)).then((r) => r.json()).then((j) => {
        if (!alive) return;
        setRoles(Array.isArray(j?.roles) ? j.roles : []);
      }).catch(() => { /* 静默空列 */ });
    } else {
      setRoles([]);
    }
    return () => { alive = false; };
  }, [expertId]);

  const kbKey = `attach:${expertId}:kb`;
  const skillKey = `attach:${expertId}:skill`;
  const modelKey = `attach:${expertId}:model`;
  const roleKey = `attach:${expertId}:role`;

  // 记忆加载（按专家）：value 为空时用 localStorage 回填一次
  useEffect(() => {
    const memoKb = loadLS<string[]>(kbKey, []);
    const memoSkill = loadLS<string | undefined>(skillKey, undefined);
    const memoModel = loadLS<string | undefined>(modelKey, undefined);
    const memoRole = loadLS<string | undefined>(roleKey, undefined);
    if ((memoKb.length || memoSkill || memoModel || memoRole) &&
        !value.kbIds.length && !value.skillCode && !value.modelId && !value.roleId) {
      onChange({ kbIds: memoKb, skillCode: memoSkill, modelId: memoModel, roleId: memoRole });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expertId]);

  const emit = (patch: Partial<AttachmentSelection>) => {
    const next = { ...value, ...patch };
    saveLS(kbKey, next.kbIds);
    saveLS(skillKey, next.skillCode ?? null);
    saveLS(modelKey, next.modelId ?? null);
    saveLS(roleKey, next.roleId ?? null);
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
      {/* ⚡ 技能（单选；批⑤ 起 v2 场景分型——通用技能自动装配不进下拉） */}
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
      {/* 🎭 角色（批⑤ v4§四：wenshu 三卡——analyst_default=默认现状等价；B2 role_id→ChatRequest） */}
      {expertId === 'wenshu' ? (
        <Select
          allowClear
          size="small"
          variant="borderless"
          style={{ minWidth: 140 }}
          placeholder="🎭 角色"
          value={value.roleId || ''}
          onChange={(rid) => emit({ roleId: rid || undefined })}
          popupMatchSelectWidth={180}
          options={[
            { value: '', label: '默认（分析师）' },
            ...roles.map((r) => ({ value: r.role_id, label: r.name, title: r.description || r.name })),
          ]}
          data-testid="attach-role"
        />
      ) : (
        <Text type="secondary" style={{ fontSize: 11 }} data-testid="attach-role-placeholder">🎭 角色</Text>
      )}
    </div>
  );
};

export default ComposerAttachmentBar;
