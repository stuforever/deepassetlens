/**
 * SQL 查询结果表格（B2 美化：S1 容器 / 吸顶表头 / 列类型图标 / 工具条 / 空态 / 全屏）
 * 接收后端 sql_result 事件推送的 { columns, rows, row_count, sql }
 *
 * 增强：
 * - 列类型图标（文本=𝐓 / 数字=# / 日期=📅 / id=🔑）
 * - 表头吸顶 sticky；行 hover bg-hover
 * - 工具条：行数徽标、复制 SQL、导出 CSV、全屏
 * - 空结果 EmptyState + 建议改写提示
 */
import React, { useMemo, useState } from 'react';
import { Table, Typography, Empty, Button, Space, Tooltip, message, Segmented } from 'antd';
import { TableOutlined, BarChartOutlined, DownloadOutlined, CopyOutlined, FullscreenOutlined, FullscreenExitOutlined, ClockCircleOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { StatusTag } from '../shell';
import { tokens } from '../../theme/tokens';
import { detectChartShape } from '../../utils/chartShape';
import ChartView from './ChartView';

const { Text } = Typography;

export type SqlResultData = {
  columns?: string[];
  rows?: any[];
  row_count?: number;
  sql?: string;
  returned_rows?: number;
  preview_row_count?: number;
  is_preview?: boolean;
  result_available_for_ui?: boolean;
  // 批3：数据快照披露（API 内存缓存命中时由执行结果携带）
  data_snapshot_at?: string;
  cache_sources?: string[];
  // P5：预聚合加速器（命中加速表时携带）
  accelerated?: boolean;
  accelerator?: { name?: string; target_table?: string; agg_expr?: string; staleness_note?: boolean };
  data_as_of?: string;
};

type SqlResultTableProps = {
  data: SqlResultData | null;
};

/** 列类型图标（B2：文本=𝐓 / 数字=# / 日期=📅 / id=🔑） */
function colTypeIcon(colName: string, colIndex: number, rows: any[]): { icon: string; tip: string; cls?: string } {
  const first = (rows || []).find((r) => {
    const v = Array.isArray(r) ? r[colIndex] : r && typeof r === 'object' ? r[colName] : undefined;
    return v !== null && v !== undefined;
  });
  const v = first !== undefined ? (Array.isArray(first) ? first[colIndex] : first[colName]) : undefined;
  const name = String(colName || '').toLowerCase();
  if (typeof v === 'number') return { icon: '#', tip: '数值', cls: 'dal-num' };
  if (typeof v === 'string') {
    if (/^\d{4}-\d{2}-\d{2}/.test(v.trim())) return { icon: '📅', tip: '日期' };
    if (/^-?\d+(\.\d+)?$/.test(v.trim())) return { icon: '#', tip: '数值', cls: 'dal-num' };
  }
  if (/id|编码|编号|code/i.test(name)) return { icon: '🔑', tip: '标识' };
  return { icon: '𝐓', tip: '文本' };
}

const SqlResultTable: React.FC<SqlResultTableProps> = ({ data }) => {
  const [copied, setCopied] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [pager, setPager] = useState<{ current: number; pageSize: number }>({ current: 1, pageSize: 20 });
  // S3a（G8）：图表形态识别——仅形态可识别时显示「表格|图表」切换，否则不渲染切换（避免空态）
  const chartShape = useMemo(() => detectChartShape(data?.columns, data?.rows), [data?.columns, data?.rows]);
  const [view, setView] = useState<'table' | 'chart'>('table');

  const columns = useMemo(() => {
    if (!data?.columns || data.columns.length === 0) return [];
    return data.columns.map((col, i) => {
      const t = colTypeIcon(col, i, data.rows || []);
      const isNum = t.cls === 'dal-num';
      return {
        title: (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, justifyContent: isNum ? 'flex-end' : 'flex-start', width: '100%' }}>
            <Tooltip title={`${t.tip}列`}>
              <span className={t.cls} style={{ fontSize: 12, fontWeight: 700, color: tokens.colors.textTertiary }}>{t.icon}</span>
            </Tooltip>
            {col}
          </span>
        ),
        dataIndex: `c${i}`,
        key: `c${i}`,
        ellipsis: true,
        width: 160,
        align: isNum ? 'right' as const : 'left' as const,
        sorter: (a: any, b: any) => {
          const va = a[`c${i}`];
          const vb = b[`c${i}`];
          if (va === null || va === undefined) return -1;
          if (vb === null || vb === undefined) return 1;
          if (typeof va === 'number' && typeof vb === 'number') return va - vb;
          return String(va).localeCompare(String(vb), 'zh-CN');
        },
        render: (val: any) => {
          if (val === null || val === undefined) return <Text type="secondary">NULL</Text>;
          return <span className={t.cls}>{String(val)}</span>;
        },
      };
    });
  }, [data?.columns, data?.rows]);

  const dataSource = useMemo(() => {
    if (!data?.rows || data.rows.length === 0) return [];
    return data.rows.map((row, ri) => {
      const obj: any = { key: ri };
      if (Array.isArray(row)) {
        row.forEach((cell, ci) => { obj[`c${ci}`] = cell; });
      } else if (typeof row === 'object' && row !== null) {
        (data.columns || []).forEach((col, ci) => { obj[`c${ci}`] = row[col]; });
      }
      return obj;
    });
  }, [data?.rows, data?.columns]);

  if (!data || !data.columns || data.columns.length === 0) return null;

  const totalCount = data.row_count ?? dataSource.length;
  const hasPagination = dataSource.length > 20;

  // CSV 导出：前端拼装 + Blob 下载
  const handleExportCsv = () => {
    if (!dataSource.length || !data.columns) return;
    const header = data.columns.map((c) => `"${(c || '').replace(/"/g, '""')}"`).join(',');
    const body = dataSource.map((row) =>
      data.columns!.map((_, ci) => {
        const val = row[`c${ci}`];
        if (val === null || val === undefined) return '';
        return `"${String(val).replace(/"/g, '""')}"`;
      }).join(',')
    ).join('\n');
    const csv = '\ufeff' + header + '\n' + body; // BOM 防止中文乱码
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `query_result_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    message.success('已导出 CSV');
  };

  // 复制 SQL
  const handleCopySql = () => {
    if (!data.sql) return;
    navigator.clipboard.writeText(data.sql).then(() => {
      setCopied(true);
      message.success('SQL 已复制');
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {
      message.error('复制失败');
    });
  };

  const tableNode = dataSource.length === 0 ? (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <span>
          <Text strong style={{ display: 'block', fontSize: 13, color: tokens.colors.textPrimary }}>未查到符合条件的数据</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>建议改写问题条件（如放宽时间范围、更换筛选维度）后重试</Text>
        </span>
      }
    />
  ) : (
    <Table
      size="small"
      columns={columns}
      dataSource={dataSource}
      sticky={{ offsetHeader: 0 }}
      pagination={hasPagination ? {
        pageSize: 20,
        size: 'small',
        showSizeChanger: true,
        showTotal: (total) => `共 ${total} 条`,
        pageSizeOptions: ['10', '20', '50', '100'],
        onChange: (page, pageSize) => setPager({ current: page, pageSize }),
      } : false}
      scroll={{ x: 'max-content' }}
      bordered
      style={{ fontSize: 12 }}
      locale={{ emptyText: '查询结果为空' }}
    />
  );

  const content = (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6, flexWrap: 'wrap', gap: 8 }}>
        <Space size={8}>
          <StatusTag icon={<TableOutlined />} preset="info">查询明细（唯一数据表）</StatusTag>
          <Text type="secondary" style={{ fontSize: 12 }}>
            共 <b className="dal-num" style={{ color: tokens.colors.textPrimary }}>{totalCount}</b> 条 × {data.columns.length} 列
            {hasPagination ? `，当前第 ${pager.current} 页 · 每页 ${pager.pageSize} 条` : ''}
          </Text>
          {data.data_snapshot_at ? (
            <Tooltip title={`缓存来源表：${(data.cache_sources || []).join('、') || '未知'}（同问题二问直接命中 API 内存缓存，不再重复拉取上游）`}>
              <StatusTag preset="warning" icon={<ClockCircleOutlined />}>数据快照 {data.data_snapshot_at}</StatusTag>
            </Tooltip>
          ) : null}
          {/* P5：预聚合加速器标注（命中加速表 -> 平台层拦截改写，附数据截至时间） */}
          {data.accelerated ? (
            <Tooltip title={`预聚合表 ${data.accelerator?.target_table || ''}（${data.accelerator?.name || '加速器'}）· 周期性刷新，查询直接返回物化结果`}>
              <StatusTag preset="success" icon={<ThunderboltOutlined />}>
                预聚合 · 数据截至 {data.data_as_of || data.data_snapshot_at || '--:--'}
              </StatusTag>
            </Tooltip>
          ) : null}
        </Space>
        <Space size={4}>
          {chartShape && dataSource.length > 0 ? (
            <Segmented
              size="small"
              value={view}
              onChange={(v) => setView(v as 'table' | 'chart')}
              options={[
                { value: 'table', icon: <TableOutlined />, label: '表格' },
                { value: 'chart', icon: <BarChartOutlined />, label: '图表' },
              ]}
            />
          ) : null}
          {data.sql ? (
            <Tooltip title={copied ? '已复制' : '复制 SQL'}>
              <Button type="text" size="small" icon={<CopyOutlined />} onClick={handleCopySql} />
            </Tooltip>
          ) : null}
          {dataSource.length > 0 ? (
            <Tooltip title="导出 CSV">
              <Button type="text" size="small" icon={<DownloadOutlined />} onClick={handleExportCsv} />
            </Tooltip>
          ) : null}
          <Tooltip title={fullscreen ? '退出全屏' : '全屏'}>
            <Button
              type="text"
              size="small"
              icon={fullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
              onClick={() => setFullscreen(!fullscreen)}
            />
          </Tooltip>
        </Space>
      </div>
      {view === 'chart' && chartShape ? <ChartView data={data} shape={chartShape} /> : tableNode}
    </div>
  );

  return (
    <>
      {/* B2 美化：容器 S1 + radius.card */}
      <div style={{ border: `1px solid ${tokens.colors.border}`, borderRadius: tokens.radius.card, padding: '4px 12px 8px', background: tokens.colors.bgContent, boxShadow: tokens.elevation.s1 }}>
        {content}
      </div>
      {/* 全屏浮层 */}
      {fullscreen ? (
        <div style={{ position: 'fixed', inset: 0, zIndex: 1000, background: tokens.colors.bgContent, overflow: 'auto', padding: 24 }}>
          <div style={{ maxWidth: 1440, margin: '0 auto' }}>
            {content}
          </div>
        </div>
      ) : null}
    </>
  );
};

export default React.memo(SqlResultTable);
