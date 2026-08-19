/**
 * EvidenceCard - 证据链卡片（融合设计 M3 G7，第 6 胶囊详情）
 *
 * 展示一次问答的答案依据链：
 *   · 路由（route_type）
 *   · 数据表清单（tables）
 *   · 示例命中（examples_used，G1 示例库召回）
 *   · 验证结论（verification：row_count / null_rates / warnings，G4）
 *   · 自评状态（rubric：satisfied / needs_revision / failed，DA-2）
 *   · 纠错次数（corrections，G2）
 * 置信度三级（高/中/低）徽标随卡头展示。
 */
import React from 'react';
import { Tag, Typography } from 'antd';
import { AuditOutlined } from '@ant-design/icons';
import ContractCardShell from './ContractCardShell';
import { tokens } from '../../../theme/tokens';

const { Text } = Typography;

const CONF_META: Record<string, { label: string; color: string; bg: string }> = {
  高: { label: '置信度高', color: tokens.colors.success, bg: tokens.colors.successBg },
  中: { label: '置信度中', color: tokens.colors.warning, bg: tokens.colors.warningBg },
  低: { label: '置信度低', color: tokens.colors.error, bg: tokens.colors.errorBg },
};

const RUBRIC_CN: Record<string, string> = {
  satisfied: '自评通过',
  needs_revision: '需修订',
  failed: '自评失败',
  max_iterations_reached: '自评超限',
  grader_error: '自评异常',
};

type Props = {
  evidence?: Record<string, any> | null;
  confidence?: string;
};

const Row: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div style={{ fontSize: 12, lineHeight: 1.9 }}>
    <Text type="secondary" style={{ marginRight: 6 }}>{label}</Text>
    {children}
  </div>
);

const EvidenceCard: React.FC<Props> = ({ evidence, confidence }) => {
  const ev = evidence || {};
  const conf = confidence || (CONF_META[String(confidence || '')] ? confidence : '');
  const confMeta = CONF_META[conf || ''] || null;

  const tables: string[] = Array.isArray(ev.tables) ? ev.tables : [];
  const examples: Array<{ q?: string; sim?: number }> = Array.isArray(ev.examples_used) ? ev.examples_used : [];
  const verification = ev.verification || null;
  const rubric = ev.rubric || null;
  const corrections = Number(ev.corrections || 0);
  const routeLabel = ev.route || '—';
  const warnings: string[] = (verification?.warnings || []).map(String);

  return (
    <ContractCardShell
      icon={<AuditOutlined />}
      title="证据链"
      subtitle={
        confMeta ? (
          <Tag
            color={confMeta.color}
            style={{
              color: confMeta.color, background: confMeta.bg,
              border: 'none', borderRadius: tokens.radius.pill, fontSize: 11, padding: '0 8px', lineHeight: '18px',
            }}
          >
            {confMeta.label}
          </Tag>
        ) : null
      }
    >
      <Row label="路由">{routeLabel}</Row>
      <Row label="数据表">
        {tables.length > 0
          ? tables.map((t, i) => <Text code key={`t-${i}`} style={{ fontSize: 11, marginRight: 4 }}>{t}</Text>)
          : <Text type="secondary">未执行取数</Text>}
      </Row>
      <Row label="示例命中">
        {examples.length > 0
          ? examples.map((e, i) => (
            <span key={`e-${i}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginRight: 8 }}>
              <Text style={{ fontSize: 11 }}>{e.q || '—'}</Text>
              <Text type="secondary" style={{ fontSize: 10 }}>{e.sim != null ? `sim=${Number(e.sim).toFixed(2)}` : ''}</Text>
            </span>
          ))
          : <Text type="secondary">未命中示例</Text>}
      </Row>
      <Row label="验证">
        {verification ? (
          <>
            <Text style={{ fontSize: 12 }}>返回 {verification.row_count ?? 0} 行</Text>
            {warnings.length > 0
              ? warnings.map((w, i) => (
                <Text key={`w-${i}`} type="warning" style={{ fontSize: 12, marginLeft: 6 }}>⚠ {w}</Text>
              ))
              : <Text type="success" style={{ fontSize: 12, marginLeft: 6 }}>无告警</Text>}
          </>
        ) : <Text type="secondary">无验证数据</Text>}
      </Row>
      <Row label="自评">
        {rubric?.status
          ? <>
            <Text style={{ fontSize: 12 }}>{RUBRIC_CN[rubric.status] || rubric.status}</Text>
            {rubric.iterations != null ? <Text type="secondary" style={{ fontSize: 11, marginLeft: 4 }}>{rubric.iterations} 轮</Text> : null}
          </>
          : <Text type="secondary">未启用 Rubric 自评</Text>}
      </Row>
      <Row label="纠错">
        <Text style={{ fontSize: 12 }}>{corrections > 0 ? `已自纠 ${corrections} 次` : '无'}</Text>
      </Row>
    </ContractCardShell>
  );
};

export default EvidenceCard;
