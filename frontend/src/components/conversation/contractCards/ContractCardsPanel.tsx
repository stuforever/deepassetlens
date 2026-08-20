/**
 * ContractCardsPanel - 受控执行卡片容器（B2 美化：折叠态改为「过程胶囊条」）
 *
 * 折叠态：一行 6 枚彩色胶囊（命中剧本 / 范围 / 引擎 / 决策 / 终止 / 证据），
 *         每枚 = 彩色图标 + 短摘要 + 状态色点（成功绿/降级黄/阻止红），
 *         一行读完一次运行的全貌（设计 §4.3；证据胶囊为融合 M3 G7 第 6 枚）。
 * 点击某枚胶囊 -> 展开对应卡详情；右侧箭头 -> 展开全部六卡。
 * 展开态卡片：沿用 RouteCard/ScopeCard/DataAccessCard/ExecutionDecisionCard/StopReasonCard + EvidenceCard。
 * 同时保留 policy/template 事件徽标与列表（评审 P2：策略拒绝、模板绑定/漂移不丢失）。
 */
import React, { useState } from 'react';
import { Badge, Space, Tooltip, Typography } from 'antd';
import {
  ApiOutlined, AuditOutlined, DownOutlined, EnvironmentOutlined, ExperimentOutlined,
  PartitionOutlined, RightOutlined, SafetyCertificateOutlined, StopOutlined,
} from '@ant-design/icons';
import RouteCard from './RouteCard';
import ScopeCard from './ScopeCard';
import DataAccessCard from './DataAccessCard';
import ExecutionDecisionCard from './ExecutionDecisionCard';
import StopReasonCard from './StopReasonCard';
import EvidenceCard from './EvidenceCard';
import { ENGINE_META, SKILL_CN } from './types';
import type { PolicyEventView, QueryContractView, RouteResult, TemplateEventView } from './types';
import { tokens } from '../../../theme/tokens';

const { Text } = Typography;

type Props = {
  route?: RouteResult | null;
  contract?: QueryContractView | null;
  policyEvents?: PolicyEventView[];
  templateEvents?: TemplateEventView[];
  /** 融合 M3 G7：证据链 + 置信度三级 */
  evidence?: Record<string, any> | null;
  confidence?: string;
};

export type Capsule = {
  key: string;
  label: string;
  icon: React.ReactNode;
  summary: string;
  color: string;      // 图标/主色
  softBg: string;     // 胶囊底色
  dot: string;        // 状态色点
  running: boolean;   // 运行中当前步骤（色点脉冲）
};

// 状态色点：全部走 token 语义色（P1 修复：零硬编码）
const DOT = {
  success: tokens.colors.success,
  warning: tokens.colors.warning,
  error: tokens.colors.error,
  info: tokens.colors.info,
  mute: tokens.colors.textTertiary,
} as const;

export function buildCapsules(
  route?: RouteResult | null,
  contract?: QueryContractView | null,
  evidence?: Record<string, any> | null,
  confidence?: string,
): Capsule[] {
  const scope = (contract?.scope as Record<string, any>) || {};
  const custCount = Array.isArray(scope.customer_names) ? scope.customer_names.length : 0;
  const rt = contract?.route_type || route?.route_type || 'generic';
  const isScenario = rt === 'scenario';
  const skillCn = isScenario ? (SKILL_CN[contract?.skill_id || ''] || contract?.skill_id || '') : '';

  // 命中剧本
  const routeCap: Capsule = {
    key: 'route',
    label: '命中剧本',
    icon: <EnvironmentOutlined style={{ fontSize: 13 }} />,
    summary: isScenario ? (skillCn ? skillCn.slice(0, 8) : '已命中') : '通用只读',
    color: tokens.colors.primary,
    softBg: tokens.colors.primaryBg,
    dot: isScenario ? DOT.success : DOT.info,
    running: false,
  };
  // 范围
  const scopeCap: Capsule = {
    key: 'scope',
    label: '范围',
    icon: <PartitionOutlined style={{ fontSize: 13 }} />,
    summary: custCount > 0 ? `${custCount} 客户` : '未限定',
    color: tokens.colors.primary,
    softBg: tokens.colors.primaryBg,
    dot: custCount > 0 ? DOT.success : DOT.mute,
    running: false,
  };
  // 引擎
  const confirmed = contract?.confirmed_engines || [];
  const selected = contract?.selected_engine;
  const enginePending = contract?.multi_engine ? confirmed.length === 0 : (!selected && isScenario);
  const engSummary = contract?.multi_engine
    ? (confirmed.length > 0 ? '多源已确认' : '待确认数据源')
    : (selected ? (ENGINE_META[selected]?.label || selected).slice(0, 6) : (isScenario ? '待确认' : '只读'));
  const engineCap: Capsule = {
    key: 'engine',
    label: '引擎',
    icon: <ApiOutlined style={{ fontSize: 13 }} />,
    summary: engSummary,
    color: tokens.colors.success,
    softBg: tokens.colors.successBg,
    dot: (contract?.multi_engine ? confirmed.length > 0 : !!selected) ? DOT.success : (isScenario ? DOT.warning : DOT.mute),
    running: enginePending,
  };
  // 决策
  const decisionSummary = contract?.multi_engine
    ? '多源分发'
    : (contract?.output_mode === 'single_result_table' ? '单表结果' : (contract?.output_mode || '默认'));
  const decisionCap: Capsule = {
    key: 'decision',
    label: '决策',
    icon: <ExperimentOutlined style={{ fontSize: 13 }} />,
    summary: decisionSummary,
    color: tokens.colors.ai,
    softBg: tokens.colors.aiBg,
    dot: DOT.success,
    running: false,
  };
  // 终止
  const stopReached = !!contract?.stop_reached;
  const stopWhenLen = (contract?.stop_when || []).length;
  const stopCap: Capsule = {
    key: 'stop',
    label: '终止',
    icon: <StopOutlined style={{ fontSize: 13 }} />,
    summary: stopReached ? '已终止' : (stopWhenLen > 0 ? `${stopWhenLen} 条件` : '—'),
    color: stopReached ? tokens.colors.error : tokens.colors.textSecondary,
    softBg: stopReached ? tokens.colors.errorBg : tokens.colors.bgHover,
    dot: stopReached ? DOT.error : (stopWhenLen > 0 ? DOT.info : DOT.mute),
    running: false,
  };
  // 证据（融合 M3 G7 第 6 胶囊）：表清单 + 自评状态 + 置信度
  const evTablesRaw = evidence?.tables;
  const evTables = Array.isArray(evTablesRaw) ? (evTablesRaw as string[]).length : 0;
  const evRubricStatus = evidence?.rubric?.status as string | undefined;
  const evCorrections = Number(evidence?.corrections || 0);
  const evMissingData = !!evidence?.missing_data_support;  // S1（b）：零执行但回答含数字
  const confDot = confidence === '高' ? DOT.success : (confidence === '低' ? DOT.error : (confidence === '中' ? DOT.warning : DOT.mute));
  const evCap: Capsule = {
    key: 'evidence',
    label: '证据',
    icon: <AuditOutlined style={{ fontSize: 13 }} />,
    summary: [
      evTables > 0 ? `${evTables} 表` : '无取数',
      evRubricStatus ? (evRubricStatus === 'satisfied' ? '自评通过' : '自评' + (evRubricStatus === 'needs_revision' ? '修订' : evRubricStatus)) : '未自评',
      evCorrections > 0 ? `纠${evCorrections}` : '',
      confidence ? `信${confidence}` : '',
      evMissingData ? '无数据支撑' : '',
    ].filter(Boolean).join('·') || '—',
    color: confidence === '高' ? tokens.colors.success : (confidence === '低' ? tokens.colors.error : tokens.colors.primary),
    softBg: confidence === '高' ? tokens.colors.successBg : (confidence === '低' ? tokens.colors.errorBg : tokens.colors.primaryBg),
    dot: confDot,
    running: false,
  };

  if (!contract) {
    // 仅有路由（未建立契约）：只展示命中剧本胶囊
    return [routeCap];
  }
  return [routeCap, scopeCap, engineCap, decisionCap, stopCap, evCap];
}

const ContractCardsPanel: React.FC<Props> = ({ route, contract, policyEvents, templateEvents, evidence, confidence }) => {
  const [collapsed, setCollapsed] = useState(true);
  const [activeCard, setActiveCard] = useState<string | null>(null);

  if (!contract && !route) {
    return null;
  }

  const capsules = buildCapsules(route, contract, evidence, confidence);
  const policyCount = (policyEvents || []).length;
  const templateCount = (templateEvents || []).length;
  const hasEvents = policyCount > 0 || templateCount > 0;
  const expanded = !collapsed;
  const showAll = expanded && !activeCard;

  const handleCapsuleClick = (key: string) => {
    if (activeCard === key) {
      // 再点同一胶囊：收起回胶囊条
      setActiveCard(null);
      setCollapsed(true);
    } else {
      // 点击胶囊：展开对应卡（或切换）
      setActiveCard(key);
      setCollapsed(false);
    }
  };
  const handleToggleAll = () => {
    setActiveCard(null);
    setCollapsed((c) => !c);
  };

  const cardByKey = (key: string): React.ReactNode => {
    switch (key) {
      case 'route': return route ? <RouteCard route={route} /> : null;
      case 'scope': return contract ? <ScopeCard scope={contract.scope} /> : null;
      case 'engine': return contract ? (
        <DataAccessCard
          allowedTools={contract.allowed_tools}
          forbiddenTools={contract.forbidden_tools}
          templateIds={contract.template_ids}
        />
      ) : null;
      case 'decision': return contract ? (
        <ExecutionDecisionCard
          selectedEngine={contract.selected_engine}
          engineReason={contract.engine_reason}
          outputMode={contract.output_mode}
          multiEngine={contract.multi_engine}
          forbidMarkdownDetailTable={contract.forbid_markdown_detail_table}
          confirmedEngines={contract.confirmed_engines}
          entityEngineMap={contract.entity_engine_map}
          stopReached={contract.stop_reached}
          requiredEntities={contract.required_entities}
          confirmedEntities={contract.confirmed_entities}
          completedEntities={contract.completed_entities}
        />
      ) : null;
      case 'stop': return contract ? <StopReasonCard stopWhen={contract.stop_when} /> : null;
      case 'evidence': return <EvidenceCard evidence={evidence} confidence={confidence} />;
      default: return null;
    }
  };

  return (
    <div style={{ marginTop: 8 }}>
      {/* 过程胶囊条（B2 美化：一行 5 枚彩色胶囊，点击展开对应卡） */}
      <div
        role="group"
        aria-label="受控执行过程"
        style={{
          display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap',
          border: `1px solid ${tokens.colors.border}`, borderRadius: tokens.radius.card,
          padding: '5px 8px', background: 'var(--color-bg-container)',
          userSelect: 'none',
        }}
      >
        <SafetyCertificateOutlined style={{ color: tokens.colors.primary, fontSize: 13 }} />
        {capsules.map((cap) => (
          <div
            key={cap.key}
            role="button"
            tabIndex={0}
            aria-expanded={activeCard === cap.key || showAll}
            onClick={() => handleCapsuleClick(cap.key)}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleCapsuleClick(cap.key); } }}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '2px 9px', borderRadius: tokens.radius.pill,
              background: cap.softBg, cursor: 'pointer',
              boxShadow: activeCard === cap.key ? tokens.elevation.s2 : 'none',
              transition: `box-shadow ${tokens.motion.duration.fast}ms ${tokens.motion.easing.enter}`,
            }}
            title={`${cap.label}：${cap.summary}（点击展开）`}
          >
            <span style={{ color: cap.color, display: 'inline-flex', alignItems: 'center' }}>{cap.icon}</span>
            <Text style={{ fontSize: 12, color: tokens.colors.textSecondary }}>{cap.label}</Text>
            <Text strong style={{ fontSize: 12, color: tokens.colors.textPrimary }}>{cap.summary}</Text>
            <span className={cap.running ? 'dal-capsule-pulse' : undefined} style={{ width: 6, height: 6, borderRadius: 3, background: cap.dot, flexShrink: 0 }} />
          </div>
        ))}
        {hasEvents ? (
          <Space size={4}>
            {policyCount > 0 ? (
              <Tooltip title={`${policyCount} 次策略事件（含拒绝/引导）`}>
                <Badge count={policyCount} color="red" showZero={false} style={{ boxShadow: 'none' }}>
                  <StopOutlined style={{ fontSize: 13, color: tokens.colors.error }} />
                </Badge>
              </Tooltip>
            ) : null}
            {templateCount > 0 ? (
              <Tooltip title={`${templateCount} 次模板事件（绑定/漂移）`}>
                <Badge count={templateCount} color="blue" showZero={false} style={{ boxShadow: 'none' }}>
                  <ApiOutlined style={{ fontSize: 13, color: tokens.colors.primary }} />
                </Badge>
              </Tooltip>
            ) : null}
          </Space>
        ) : null}
        <span style={{ flex: 1 }} />
        {expanded ? (
          <span
            role="button"
            tabIndex={0}
            onClick={handleToggleAll}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleToggleAll(); } }}
            style={{ display: 'inline-flex', alignItems: 'center', cursor: 'pointer', color: tokens.colors.textSecondary }}
          >
            {activeCard ? <RightOutlined style={{ fontSize: 11 }} /> : <DownOutlined style={{ fontSize: 11 }} />}
          </span>
        ) : (
          <span
            role="button"
            tabIndex={0}
            onClick={handleToggleAll}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleToggleAll(); } }}
            style={{ display: 'inline-flex', alignItems: 'center', cursor: 'pointer', color: tokens.colors.textSecondary }}
          >
            <DownOutlined style={{ fontSize: 11 }} />
          </span>
        )}
      </div>

      {/* 展开明细：单卡（activeCard）或全部六卡 + 事件 */}
      {expanded ? (
        <div style={{ marginTop: 8 }}>
          {activeCard ? (
            <>
              {cardByKey(activeCard)}
              <div style={{ marginTop: 4, textAlign: 'right' }}>
                <Text
                  type="secondary"
                  style={{ fontSize: 12, cursor: 'pointer' }}
                  onClick={() => setActiveCard(null)}
                >
                  展开全部六卡 ▾
                </Text>
              </div>
            </>
          ) : (
            <>
              {contract ? (
                <>
                  {route ? <RouteCard route={route} /> : null}
                  <ScopeCard scope={contract.scope} />
                  <DataAccessCard
                    allowedTools={contract.allowed_tools}
                    forbiddenTools={contract.forbidden_tools}
                    templateIds={contract.template_ids}
                  />
                  <ExecutionDecisionCard
                    selectedEngine={contract.selected_engine}
                    engineReason={contract.engine_reason}
                    outputMode={contract.output_mode}
                    multiEngine={contract.multi_engine}
                    forbidMarkdownDetailTable={contract.forbid_markdown_detail_table}
                    confirmedEngines={contract.confirmed_engines}
                    entityEngineMap={contract.entity_engine_map}
                    stopReached={contract.stop_reached}
                    requiredEntities={contract.required_entities}
                    confirmedEntities={contract.confirmed_entities}
                    completedEntities={contract.completed_entities}
                  />
                  <StopReasonCard stopWhen={contract.stop_when} />
                  <EvidenceCard evidence={evidence} confidence={confidence} />
                </>
              ) : (
                <>
                  {route ? <RouteCard route={route} /> : null}
                  <Text type="secondary" style={{ fontSize: 12 }}>本次请求未建立受控契约（无场景命中且后端未返回契约）。</Text>
                </>
              )}
            </>
          )}
          {hasEvents ? (
            <div style={{ marginTop: 8, border: '1px dashed var(--border-color)', borderRadius: tokens.radius.card, padding: '8px 12px' }}>
              <Text strong style={{ fontSize: 12 }}>运行事件（{policyCount + templateCount}）</Text>
              {(policyEvents || []).map((p, i) => (
                <div key={`p-${p.run_id || ''}-${p.tool_call_id || ''}-${i}`} style={{ fontSize: 12, marginTop: 4 }}>
                  <Text type="danger">策略·{p.kind || '事件'}</Text>
                  <Text type="secondary"> {p.detail || p.reason || ''}</Text>
                </div>
              ))}
              {(templateEvents || []).map((t, i) => (
                <div key={`t-${t.run_id || ''}-${t.tool_call_id || ''}-${i}`} style={{ fontSize: 12, marginTop: 4 }}>
                  <Text type={t.kind === 'template.drift' ? 'warning' : 'success'}>
                    {t.kind === 'template.drift' ? '模板·漂移' : '模板·绑定'}
                  </Text>
                  <Text type="secondary"> {t.detail || ''}</Text>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
};

export default ContractCardsPanel;
