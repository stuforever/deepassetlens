/**
 * 消息 Tab 分发组件
 *
 * 将助手消息内容按类型分发到 5 个 Tab：
 *   1. 答案  - FinalAnswer 文本 + 澄清卡片
 *   2. 思考  - ThinkStream 推理过程
 *   3. 数据  - SQL + 查询结果表格
 *   4. 定位  - L2/实体/属性/关系
 *   5. 推荐  - 推荐问题列表
 *
 * 仅在有 2+ 个 Tab 有内容时才显示 Tab 栏，否则直接渲染单个内容。
 */
import React, { useState, useMemo } from 'react';
import { Tabs, Tag, Table, Typography, Button, Empty, Space } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import ThinkStream from './ThinkStream';
import FinalAnswer from './FinalAnswer';
import RecommendationList from './RecommendationList';
import SqlResultTable from './SqlResultTable';
import CardRenderer from './CardRenderer';
import type { ChatMessagePayload, ConversationCardAction } from './types';
import { tokens } from '../../theme/tokens';
import { StatusTag } from '../shell';

const { Text } = Typography;

type MessageTabsProps = {
  payload?: ChatMessagePayload;
  isLast: boolean;
  liveMetaInfo?: string;
  liveFinalAnswer?: string;
  onCardAction?: (action: ConversationCardAction) => void;
  onSelectRecommendation?: (rec: any) => void;
  onExecuteSql?: (sql: string) => void;
  onEntityClick?: (entityCode: string, entityName?: string) => void;
};

type EntityAttr = {
  attribute_name?: string;
  attribute_code?: string;
};

type ExtraEntity = {
  entity_code?: string;
  entity_name?: string;
  attributes?: EntityAttr[];
};

const MessageTabs: React.FC<MessageTabsProps> = ({
  payload,
  isLast,
  liveMetaInfo,
  liveFinalAnswer,
  onCardAction,
  onSelectRecommendation,
  onExecuteSql,
  onEntityClick,
}) => {
  const [activeTab, setActiveTab] = useState('answer');

  const confirmed = payload?.confirmed || {};
  const { L2, L2X, L2X_name, attributes, extra_entities, relations, assembled_sql } = confirmed;
  const thinkStream = payload?.thinkStream || [];
  const cards = (payload?.cards || []).filter((c) => c.card_type !== 'sql_preview');
  const sqlResult = payload?.sql_result || null;
  const finalAnswer = payload?.final_answer || (isLast ? liveFinalAnswer : undefined);
  const recommendations = payload?.recommendations || [];

  // 判断各 Tab 是否有内容
  const hasAnswer = Boolean(finalAnswer || cards.length > 0);
  const hasThink = thinkStream.length > 0;
  const hasData = Boolean(assembled_sql || (sqlResult && sqlResult.columns && sqlResult.columns.length > 0));
  const hasLocation = Boolean(L2 || L2X || (attributes && attributes.length > 0) || (extra_entities && extra_entities.length > 0));
  const hasRecs = recommendations.length > 0;

  const visibleTabs = [
    { key: 'answer', label: '答案', has: hasAnswer },
    { key: 'think', label: '思考', has: hasThink },
    { key: 'data', label: '数据', has: hasData },
    { key: 'location', label: '定位', has: hasLocation },
    { key: 'recommend', label: '推荐', has: hasRecs },
  ].filter((t) => t.has);

  // 属性表格数据
  const tableData = useMemo(() => {
    const rows: Array<{ key: string; entity: string; entityCode: string; attrName: string; attrCode: string; isMain: boolean }> = [];
    if (attributes && attributes.length > 0) {
      attributes.forEach((attr: EntityAttr, i: number) => {
        rows.push({
          key: `main-${i}`,
          entity: L2X_name || L2X || '',
          entityCode: L2X || '',
          attrName: attr.attribute_name || '',
          attrCode: attr.attribute_code || '',
          isMain: true,
        });
      });
    }
    if (extra_entities && extra_entities.length > 0) {
      extra_entities.forEach((ee: ExtraEntity, ei: number) => {
        const eeName = ee.entity_name || ee.entity_code || '';
        const eeCode = ee.entity_code || '';
        (ee.attributes || []).forEach((attr: EntityAttr, ai: number) => {
          rows.push({
            key: `ee-${ei}-${ai}`,
            entity: eeName,
            entityCode: eeCode,
            attrName: attr.attribute_name || '',
            attrCode: attr.attribute_code || '',
            isMain: false,
          });
        });
      });
    }
    return rows;
  }, [attributes, extra_entities, L2X, L2X_name]);

  const tableColumns = [
    {
      title: '实体',
      dataIndex: 'entity',
      key: 'entity',
      render: (text: string, record: any) => (
        <span
          style={{ cursor: onEntityClick ? 'pointer' : 'default', color: onEntityClick ? tokens.colors.primary : undefined }}
          onClick={() => onEntityClick && record.entityCode && onEntityClick(record.entityCode, record.entity)}
        >
          <StatusTag preset={record.isMain ? 'info' : 'warning'}>{record.isMain ? '主表' : '联接表'}</StatusTag>
          {text}
        </span>
      ),
    },
    { title: '属性名', dataIndex: 'attrName', key: 'attrName' },
    { title: '属性code', dataIndex: 'attrCode', key: 'attrCode', render: (t: string) => <Text code style={{ fontSize: 11 }}>{t}</Text> },
  ];

  // 渲染各 Tab 内容
  const renderAnswer = () => (
    <Space direction="vertical" style={{ width: '100%' }} size={8}>
      {cards.map((card, index) => (
        <CardRenderer
          key={card.card_id || `${card.card_type}-${index}`}
          card={card}
          onAction={onCardAction}
          onSelectRecommendation={onSelectRecommendation}
          onExecuteSql={onExecuteSql ? () => onExecuteSql(assembled_sql || '') : undefined}
        />
      ))}
      {finalAnswer ? (
        <FinalAnswer answer={finalAnswer} tokens={[]} isStreaming={false} />
      ) : null}
      {!finalAnswer && cards.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无答案" />
      ) : null}
    </Space>
  );

  const renderThink = () => (
    <ThinkStream
      items={thinkStream}
      active={false}
      metaInfo={isLast ? liveMetaInfo : `推理完成 · 定位 ${thinkStream.length} 步`}
    />
  );

  const renderData = () => (
    <Space direction="vertical" style={{ width: '100%' }} size={8}>
      {assembled_sql ? (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>💻 联接 SQL</Text>
            {onExecuteSql ? (
              <Button type="primary" size="small" icon={<PlayCircleOutlined />} onClick={() => onExecuteSql(assembled_sql)}>
                执行 SQL
              </Button>
            ) : null}
          </div>
          <pre style={{
            padding: 10, background: 'var(--color-success-bg)', color: 'var(--color-success)',
            border: '1px solid var(--color-success-bg)', borderRadius: 6,
            fontFamily: 'Consolas, Monaco, monospace',
            fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all',
            margin: 0,
          }}>
            {assembled_sql}
          </pre>
        </div>
      ) : null}
      {sqlResult && sqlResult.columns && sqlResult.columns.length > 0 ? (
        <SqlResultTable data={sqlResult} />
      ) : null}
      {!assembled_sql && !sqlResult ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
      ) : null}
    </Space>
  );

  const renderLocation = () => (
    <Space direction="vertical" style={{ width: '100%' }} size={8}>
      {/* 定位标签 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {L2 ? <StatusTag preset="ai" style={{ fontSize: 12 }}>L2: {L2}</StatusTag> : null}
        {L2X ? <StatusTag preset="info" style={{ fontSize: 12 }}>主表: {L2X_name || L2X}</StatusTag> : null}
        {attributes && attributes.length > 0 ? <Tag style={{ fontSize: 12 }}>属性: {attributes.length} 个</Tag> : null}
        {extra_entities && extra_entities.length > 0 ? <StatusTag preset="warning" style={{ fontSize: 12 }}>联接表: {extra_entities.length} 个</StatusTag> : null}
        {relations && relations.length > 0 ? <StatusTag preset="success" style={{ fontSize: 12 }}>关系: {relations.length} 条</StatusTag> : null}
      </div>
      {/* 属性明细表格 */}
      {tableData.length > 0 ? (
        <div>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>🗂 属性明细</Text>
          <Table
            size="small"
            style={{ marginTop: 4 }}
            columns={tableColumns}
            dataSource={tableData}
            pagination={false}
          />
        </div>
      ) : null}
      {/* 实体间关系 */}
      {relations && relations.length > 0 ? (
        <div>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>🔗 实体间关系</Text>
          <div style={{ marginTop: 4, padding: 8, background: 'var(--color-success-bg)', border: '1px solid var(--color-success-bg)', borderRadius: 4 }}>
            {relations.map((rel: any, i: number) => {
              const joinType = rel.join_type || rel.type || 'JOIN';
              const fromEntity = rel.source_entity || rel.from || '';
              const toEntity = rel.target_entity || rel.to || '';
              const fromField = rel.source_field || '';
              const toField = rel.target_field || '';
              const joinLabel = rel.label || (fromField && toField ? `ON ${fromField} = ${toField}` : '');
              return (
                <div key={`rel-${i}`} style={{ fontSize: 12, marginBottom: 4 }}>
                  <StatusTag preset="success">{joinType}</StatusTag>
                  <Text style={{ fontSize: 12 }}>{fromEntity} {'->'} {toEntity}</Text>
                  {joinLabel ? <Text type="secondary" style={{ fontSize: 12 }}> ({joinLabel})</Text> : null}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
      {!L2 && !L2X && tableData.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无定位信息" />
      ) : null}
    </Space>
  );

  const renderRecommend = () => (
    <RecommendationList questions={recommendations} onSelect={onSelectRecommendation} />
  );

  // 只有一个 Tab 有内容时，直接渲染不显示 Tab 栏
  if (visibleTabs.length <= 1) {
    if (visibleTabs.length === 0) return null;
    const onlyKey = visibleTabs[0].key;
    if (onlyKey === 'answer') return <>{renderAnswer()}</>;
    if (onlyKey === 'think') return <>{renderThink()}</>;
    if (onlyKey === 'data') return <>{renderData()}</>;
    if (onlyKey === 'location') return <>{renderLocation()}</>;
    if (onlyKey === 'recommend') return <>{renderRecommend()}</>;
    return null;
  }

  const tabItems = [
    { key: 'answer', label: `答案`, children: renderAnswer() },
    { key: 'think', label: `思考`, children: renderThink() },
    { key: 'data', label: `数据`, children: renderData() },
    { key: 'location', label: `定位`, children: renderLocation() },
    { key: 'recommend', label: `推荐`, children: renderRecommend() },
  ].filter((t) => visibleTabs.some((v) => v.key === t.key));

  return (
    <Tabs
      activeKey={activeTab}
      onChange={setActiveTab}
      size="small"
      type="line"
      items={tabItems}
      style={{ minHeight: 60 }}
    />
  );
};

export default MessageTabs;
