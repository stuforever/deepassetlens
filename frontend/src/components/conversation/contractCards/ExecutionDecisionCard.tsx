/**
 * ExecutionDecisionCard - 执行决策（设计 §5 selected_engine / output_mode）
 * 单引擎：展示由 batch_entity_source_mode 真实返回锁定的唯一引擎；
 * 多引擎（批4 project-lifecycle-cost 预算 duckdb + 成本 doris）：展示逐源分发，不唯一。
 */
import React from 'react';
import { Space, Tag, Typography } from 'antd';
import { ThunderboltOutlined, DatabaseOutlined } from '@ant-design/icons';
import ContractCardShell from './ContractCardShell';
import { ENGINE_META } from './types';

const { Text } = Typography;

type Props = {
  selectedEngine?: string | null;
  engineReason?: string | null;
  outputMode?: string;
  multiEngine?: boolean;
  forbidMarkdownDetailTable?: boolean;
  confirmedEngines?: string[];
  entityEngineMap?: Record<string, string>;
  stopReached?: boolean;
  // 评审 P1-1（二轮）：必达数据源与实体级完成进度（required_sources 声明）
  requiredEntities?: string[];
  confirmedEntities?: string[];
  completedEntities?: string[];
};

const OUTPUT_MODE_CN: Record<string, string> = {
  single_result_table: '单结果表（明细由前端查询结果表唯一展示）',
  analysis_and_result_table: '分析+结果表（答案呈现对比汇总）',
  default: '常规输出',
};

const ExecutionDecisionCard: React.FC<Props> = ({
  selectedEngine, engineReason, outputMode = 'default',
  multiEngine = false, forbidMarkdownDetailTable = true,
  confirmedEngines = [], entityEngineMap = {}, stopReached = false,
  requiredEntities = [], confirmedEntities = [], completedEntities = [],
}) => {
  const engines = confirmedEngines.length ? confirmedEngines
    : (multiEngine ? (selectedEngine ? selectedEngine.split(',') : []) : []);
  const eem = entityEngineMap || {};
  return (
    <ContractCardShell
      icon={<ThunderboltOutlined />}
      title="执行决策"
      subtitle={multiEngine ? '多引擎逐源分发 · batch_entity_source_mode 真实返回确认' : '引擎唯一 · 由 batch_entity_source_mode 真实返回锁定'}
    >
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        <div>
          {multiEngine ? (
            <>
              <Tag color="purple" icon={<DatabaseOutlined />} style={{ marginRight: 4 }}>多引擎</Tag>
              {/* 评审 P1-1（二轮）：必达数据源与完成进度不依赖"已确认引擎"——未确认前也展示声明 */}
              {requiredEntities.length > 0 ? (
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                  <Text type="secondary">必达数据源：</Text>
                  {requiredEntities.map((ec) => {
                    const done = (completedEntities || []).includes(ec);
                    const confirmed = (confirmedEntities || []).includes(ec);
                    return (
                      <Tag key={ec} color={done ? 'green' : confirmed ? 'blue' : 'default'} style={{ marginLeft: 4 }}>
                        {ec}{done ? ' ✓' : ''}
                      </Tag>
                    );
                  })}
                  <Text type="secondary" style={{ marginLeft: 8 }}>
                    {completedEntities.filter((e) => requiredEntities.includes(e)).length}/{requiredEntities.length} 已取齐
                  </Text>
                </div>
              ) : null}
              {engines.length ? (
                <>
                  <Text type="secondary" style={{ fontSize: 12 }}>已确认数据源：</Text>
                  {engines.map((e) => (
                    <Tag key={e} color={(ENGINE_META[e] || {}).color || 'default'} style={{ marginLeft: 4 }}>
                      {(ENGINE_META[e] || {}).label || e}
                    </Tag>
                  ))}
                  {Object.keys(eem).length > 0 ? (
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                      {Object.entries(eem).map(([ec, en]) => `${ec} → ${(ENGINE_META[en] || {}).label || en}`).join('；')}
                    </div>
                  ) : null}
                  {stopReached ? (
                    <Tag color="green" style={{ marginLeft: 8 }}>两源已取齐 · 终止</Tag>
                  ) : null}
                  {engineReason ? (
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{engineReason}</div>
                  ) : null}
                </>
              ) : (
                <Text type="warning" style={{ fontSize: 12 }}>
                  待确认 —— 先 batch_entity_source_mode 确认预算/成本数据源模式，确认后两引擎工具并存可用
                </Text>
              )}
            </>
          ) : selectedEngine ? (
            <>
              <Text type="secondary" style={{ fontSize: 12 }}>数据引擎：</Text>
              <Tag color={(ENGINE_META[selectedEngine] || {}).color || 'default'} style={{ marginLeft: 4 }}>
                {(ENGINE_META[selectedEngine] || {}).label || selectedEngine}
              </Tag>
              {engineReason ? (
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{engineReason}</div>
              ) : null}
            </>
          ) : (
            <Text type="warning" style={{ fontSize: 12 }}>
              尚未确认 —— 将先调用 batch_entity_source_mode 确定数据引擎，引擎锁定后其他查询工具失效
            </Text>
          )}
        </div>
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>输出模式：</Text>
          <Text style={{ fontSize: 12, marginLeft: 4 }}>{OUTPUT_MODE_CN[outputMode] || outputMode}</Text>
          <Tag
            color={forbidMarkdownDetailTable ? 'orange' : 'green'}
            style={{ marginLeft: 8 }}
            title={forbidMarkdownDetailTable ? '答案禁止再画明细表（明细由查询结果表唯一展示）' : '答案可呈现汇总对比表（跨源合成结果）'}
          >
            {forbidMarkdownDetailTable ? '禁明细表' : '允许答案表'}
          </Tag>
        </div>
      </Space>
    </ContractCardShell>
  );
};

export default ExecutionDecisionCard;
