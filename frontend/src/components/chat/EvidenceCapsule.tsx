/**
 * EvidenceCapsule（批①a——v4§11.2/§12.2 尾行）：证据胶囊——「依据什么」。
 * ContractCardsPanel 前台下线后的前台证据呈现：胶囊单行（📎 依据：… · 置信度高），
 * 点击展开证据列表（路由技能/实体表/金标示例/校验摘要）。
 * props 按计划接口：{sources: {name,type}[], confidence}；confidence 兼容 高/中/低 与 high/medium/low。
 */
import React, { useState } from 'react';
import { Typography } from 'antd';
import { DownOutlined, FileTextOutlined, TableOutlined, BulbOutlined, ApiOutlined } from '@ant-design/icons';
import { tokens } from '../../theme/tokens';

const { Text } = Typography;

export type EvidenceSource = { name: string; type: string };
export type EvidenceConfidence = 'high' | 'medium' | 'low' | '高' | '中' | '低';

const CONF_CN: Record<string, string> = { high: '高', medium: '中', low: '低', '高': '高', '中': '中', '低': '低' };
const CONF_COLOR: Record<string, string> = {
  high: 'var(--color-success)', medium: 'var(--color-warning, #faad14)', low: 'var(--color-error)',
  '高': 'var(--color-success)', '中': 'var(--color-warning, #faad14)', '低': 'var(--color-error)',
};

const TYPE_ICON: Record<string, React.ReactNode> = {
  table: <TableOutlined />,
  skill: <ApiOutlined />,
  golden: <BulbOutlined />,
};

const EvidenceCapsule: React.FC<{
  sources: EvidenceSource[];
  confidence?: EvidenceConfidence;
}> = ({ sources, confidence }) => {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;
  const conf = CONF_CN[confidence || ''] || '';
  const confColor = CONF_COLOR[confidence || ''] || 'var(--text-tertiary)';
  const summary = sources.slice(0, 3).map((s) => s.name).join(' · ');
  const more = sources.length > 3 ? ` 等 ${sources.length} 项` : '';
  return (
    <div data-testid="evidence-capsule" style={{ margin: '8px 0 0' }}>
      <div
        onClick={() => setOpen(!open)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6, cursor: 'pointer',
          padding: '2px 10px', borderRadius: 999, border: '1px solid var(--border-color)',
          background: 'var(--bg-subtle)', maxWidth: '100%',
        }}
      >
        <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>📎 依据：</span>
        <Text ellipsis style={{ fontSize: 12, color: 'var(--text-secondary)', maxWidth: 420 }}>{summary}{more}</Text>
        {conf ? <Text style={{ fontSize: 12, color: confColor, flexShrink: 0 }}>· 置信度{conf}</Text> : null}
        <DownOutlined style={{ fontSize: 10, color: 'var(--text-tertiary)', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .15s' }} />
      </div>
      {open ? (
        <div style={{ marginTop: 6, padding: 12, border: '1px solid var(--border-color)', borderRadius: 8, background: 'var(--bg-content)' }}>
          {sources.map((s, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 0', fontSize: 12, color: 'var(--text-secondary)' }}>
              <span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>{TYPE_ICON[s.type] || <FileTextOutlined />}</span>
              <Text style={{ fontSize: 12, color: 'var(--text-primary)' }}>{s.name}</Text>
              <Text type="secondary" style={{ fontSize: 11 }}>{s.type}</Text>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
};

/** payload.evidence（done 快照）→ 胶囊 sources 适配器（调用方共用）。 */
export function evidenceToSources(evidence: any): EvidenceSource[] {
  if (!evidence || typeof evidence !== 'object') return [];
  const out: EvidenceSource[] = [];
  const skill = evidence.route?.skill;
  if (skill && skill !== '__generic__') out.push({ name: String(skill), type: 'skill' });
  for (const t of evidence.tables || []) out.push({ name: String(t), type: 'table' });
  for (const e of evidence.examples_used || []) {
    if (e && e.q) out.push({ name: String(e.q), type: 'golden' });
  }
  return out;
}

export default EvidenceCapsule;
