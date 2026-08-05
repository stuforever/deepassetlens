/**
 * 总结卡片 - 问数流程统一展示（5 部分全部色块/表格，不要大段纯文本）
 *
 *   1. 总结        - 蓝色色块（来自 LLM final_answer 第1段）
 *   2. 执行过程     - 灰色色块（来自 LLM final_answer 第2段）
 *   3. 属性明细     - 表格
 *   4. 实体间关系   - 绿色色块
 *   5. 联接 SQL     - 淡绿色色块 + 执行按钮
 */
import React from 'react';
import { Card, Table, Tag, Typography, Button, Divider, Empty } from 'antd';
import { PlayCircleOutlined, ShareAltOutlined } from '@ant-design/icons';
import SqlResultTable from './SqlResultTable';
import { tokens } from '../../theme/tokens';
import { StatusTag } from '../shell';

const { Text, Paragraph } = Typography;

type EntityAttr = {
  attribute_name?: string;
  attribute_code?: string;
};

type ExtraEntity = {
  entity_code?: string;
  entity_name?: string;
  attributes?: EntityAttr[];
};

type SummaryCardProps = {
  confirmed: {
    L2?: string | null;
    L2X?: string | null;
    L2X_name?: string | null;
    attributes?: EntityAttr[];
    extra_entities?: ExtraEntity[];
    relations?: Array<{
      type?: string; from?: string; to?: string; label?: string;
      join_type?: string; source_entity?: string; target_entity?: string;
      source_field?: string; target_field?: string; join_expr?: string;
    }>;
    assembled_sql?: string | null;
  };
  finalAnswer?: string;
  finalAnswerStructured?: { summary?: string; execution_process?: string; sql?: string; row_count?: number; recommendations?: string[] } | null;
  sqlResult?: { columns?: string[]; rows?: any[]; row_count?: number; sql?: string } | null;
  completedTasks?: string[];
  onEntityClick?: (entityCode: string, entityName?: string) => void;
  onExecuteSql?: (sql: string) => void;
};

const SummaryCard: React.FC<SummaryCardProps> = ({ confirmed, finalAnswer, finalAnswerStructured, sqlResult, onEntityClick, onExecuteSql }) => {
  const { L2, L2X, L2X_name, attributes, extra_entities, relations, assembled_sql } = confirmed;

  if (!L2 && !L2X && !assembled_sql && !finalAnswer && !finalAnswerStructured) return null;

  // #20: 优先用结构化答案（response_format 产出），回退到字符串切片
  const splitAnswer = (text: string): { summary: string; process: string } => {
    if (!text) return { summary: '', process: '' };
    let idx1 = text.indexOf('1.总结');
    let idx2 = text.indexOf('2.执行过程');
    if (idx1 < 0) idx1 = text.indexOf('1. 总结');
    if (idx2 < 0) idx2 = text.indexOf('2. 执行过程');
    if (idx1 < 0) idx1 = text.indexOf('总结');
    if (idx2 < 0) idx2 = text.indexOf('执行过程');
    if (idx1 >= 0 && idx2 > idx1) {
      let s = text.slice(idx1, idx2);
      s = s.replace(/^[\s]*\d+[.、]\s*总结\s*[:：]?\s*/, '').trim();
      let p = text.slice(idx2);
      p = p.replace(/^[\s]*\d+[.、]\s*执行过程\s*[:：]?\s*/, '').trim();
      p = p.split(/\n\s*\d+[.、]\s/)[0].trim();
      return { summary: s, process: p };
    }
    if (idx1 >= 0) {
      let s = text.slice(idx1);
      s = s.replace(/^[\s]*\d+[.、]\s*总结\s*[:：]?\s*/, '').trim();
      return { summary: s, process: '' };
    }
    return { summary: text.trim(), process: '' };
  };
  const fallback = splitAnswer(finalAnswer || '');
  const summary = finalAnswerStructured?.summary || fallback.summary;
  const process = finalAnswerStructured?.execution_process || fallback.process;

  // 属性表格数据
  const tableData: Array<{ key: string; entity: string; entityCode: string; attrName: string; attrCode: string; isMain: boolean }> = [];
  if (attributes && attributes.length > 0) {
    attributes.forEach((attr, i) => {
      tableData.push({
        key: `main-${i}`,
        entity: L2X || '',
        entityCode: L2X || '',
        attrName: attr.attribute_name || '',
        attrCode: attr.attribute_code || '',
        isMain: true,
      });
    });
  }
  if (extra_entities && extra_entities.length > 0) {
    extra_entities.forEach((ee, ei) => {
      const eeName = ee.entity_name || ee.entity_code || '';
      const eeCode = ee.entity_code || '';
      (ee.attributes || []).forEach((attr, ai) => {
        tableData.push({
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

  const allEntities: string[] = [];
  if (L2X) allEntities.push(L2X);
  if (extra_entities) {
    extra_entities.forEach((ee) => {
      const name = ee.entity_name || ee.entity_code;
      if (name) allEntities.push(name);
    });
  }

  return (
    <Card
      size="small"
      style={{ marginTop: 8, border: '1px solid var(--border-color)' }}
      title={
        <span>
          <StatusTag preset="info">结构化</StatusTag>
          <Text strong style={{ fontSize: 14 }}>问答定位总结</Text>
        </span>
      }
    >
      {/* 0. 定位信息 - L2/实体/属性数量 快速概览 */}
      {(L2 || L2X) ? (
        <div style={{ marginBottom: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {L2 ? <StatusTag preset="ai" style={{ fontSize: 12 }}>L2: {L2}</StatusTag> : null}
          {L2X ? <StatusTag preset="info" style={{ fontSize: 12 }}>主表: {L2X_name || L2X}</StatusTag> : null}
          {attributes && attributes.length > 0 ? <Tag style={{ fontSize: 12 }}>属性: {attributes.length} 个</Tag> : null}
          {extra_entities && extra_entities.length > 0 ? <StatusTag preset="warning" style={{ fontSize: 12 }}>联接表: {extra_entities.length} 个</StatusTag> : null}
          {relations && relations.length > 0 ? <StatusTag preset="success" style={{ fontSize: 12 }}>关系: {relations.length} 条</StatusTag> : null}
        </div>
      ) : null}

      {/* 1. 总结 - 纯文字段落（无色块） */}
      {summary ? (
        <div style={{ marginBottom: 10 }}>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>📝 总结</Text>
          <Paragraph style={{ margin: '4px 0 0 0', fontSize: 13, lineHeight: 1.7 }}>{summary}</Paragraph>
        </div>
      ) : null}

      {/* 2. 执行过程 - 灰色色块 */}
      {process ? (
        <div style={{ marginBottom: 10 }}>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>📋 执行过程</Text>
          <div style={{ marginTop: 4, padding: 8, background: 'var(--bg-subtle)', border: '1px solid var(--border-color)', borderRadius: 4 }}>
            <Paragraph style={{ margin: 0, fontSize: 13, lineHeight: 1.7 }}>{process}</Paragraph>
          </div>
        </div>
      ) : null}

      {/* 3. 属性明细 - 表格 */}
      {tableData.length > 0 ? (
        <div style={{ marginBottom: 10 }}>
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

      {/* 4. 实体间关系 - 绿色色块 */}
      {allEntities.length > 1 ? (
        <div style={{ marginBottom: 10 }}>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>🔗 实体间关系</Text>
          <div style={{ marginTop: 4, padding: 8, background: 'var(--color-success-bg)', border: '1px solid var(--color-success-bg)', borderRadius: 4 }}>
            {relations && relations.length > 0 ? (
              relations.map((rel, i) => {
                // 兼容两种字段命名: 后端(source_entity/target_entity/join_type/source_field/target_field) 和 旧版(from/to/type/label)
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
              })
            ) : (
              <Text style={{ fontSize: 12 }}>
                {allEntities.map((e, i) => (
                  <span key={i}>
                    {i > 0 ? <StatusTag preset="success" style={{ margin: '0 4px' }}>LEFT JOIN</StatusTag> : null}
                    <span
                      style={{ cursor: onEntityClick ? 'pointer' : 'default', color: onEntityClick ? tokens.colors.primary : undefined }}
                      onClick={() => onEntityClick && onEntityClick(e, e)}
                    >
                      {e}
                    </span>
                  </span>
                ))}
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {(() => {
                    // 从 SQL 解析 JOIN ON 字段
                    const sql = (assembled_sql || '').toString()
                    const re = /\bJOIN\s+`?([A-Za-z0-9_]+)`?\s+ON\s+`?([A-Za-z0-9_]+)`?\.`?([A-Za-z0-9_]+)`?\s*=\s*`?([A-Za-z0-9_]+)`?\.`?([A-Za-z0-9_]+)`?/gi
                    const m = re.exec(sql)
                    if (m) return ` ON ${m[3]} = ${m[6]}`
                    return ' ON cust_id'
                  })()}
                </Text>
              </Text>
            )}
          </div>
        </div>
      ) : null}

      {/* 5. 联接 SQL - 淡绿色色块 + 执行按钮 */}
      {assembled_sql ? (
        <div style={{ marginBottom: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>💻 联接 SQL</Text>
            {onExecuteSql ? (
              <Button
                type="primary"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => onExecuteSql(assembled_sql)}
              >
                执行 SQL
              </Button>
            ) : null}
          </div>
          <pre style={{
            marginTop: 4, padding: 10, background: 'var(--color-success-bg)', color: 'var(--color-success)',
            border: '1px solid var(--color-success-bg)', borderRadius: 6,
            fontFamily: 'Consolas, Monaco, monospace',
            fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all',
          }}>
            {assembled_sql}
          </pre>
        </div>
      ) : null}

      {/* 6. SQL 查询结果表格 */}
      {sqlResult && sqlResult.columns && sqlResult.columns.length > 0 ? (
        <div style={{ marginBottom: 4 }}>
          <Divider style={{ margin: '8px 0' }} />
          <SqlResultTable data={sqlResult} />
        </div>
      ) : null}

      {/* 跳转图谱提示 */}
      {onEntityClick && allEntities.length > 0 ? (
        <>
          <Divider style={{ margin: '4px 0' }} />
          <Text type="secondary" style={{ fontSize: 11 }}>
            <ShareAltOutlined /> 点击上方实体名称可跳转图谱查看该实体详情
          </Text>
        </>
      ) : null}
    </Card>
  );
};

export default SummaryCard;
