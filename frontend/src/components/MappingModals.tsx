/**
 * MappingModals —— 映射管理的字段选择器 + SQL 预览弹窗（纯展示 + 事件上抛）
 *
 * 从 MappingManager 抽离：字段选择器（含 fieldPickerRows 派生）与 SQL 预览。
 * 数据与回调全部经 props 传入；容器负责保存与可见性状态。
 */
import React, { useMemo } from 'react';
import { Modal, Space, Select, Table, Input } from 'antd';
import { TERMS } from '../constants/standardTerms';

const { TextArea } = Input;

// 字段选择器弹窗
export type FieldPickerModalProps = {
  open: boolean;
  title: string;
  tableId: string;
  tempValues: string[];
  selectedSourceTables: any[];
  sourceTableFields: Record<string, any[]>;
  onTableIdChange: (v: string) => void;
  onTempValuesChange: (keys: string[]) => void;
  onOk: () => void;
  onCancel: () => void;
};

export const FieldPickerModal: React.FC<FieldPickerModalProps> = (p) => {
  const fieldPickerRows = useMemo(() => {
    const tables = p.tableId
      ? p.selectedSourceTables.filter(t => String(t.id) === String(p.tableId))
      : p.selectedSourceTables;
    const rows: any[] = [];
    tables.forEach(t => {
      const fields = p.sourceTableFields[t.id] || [];
      fields.forEach((f: any) => {
        rows.push({
          key: `${t.id}_${f.field_en}`,
          tableEn: t.enName,
          tableCn: t.cnName,
          fieldEn: f.field_en,
          fieldCn: f.field_cn,
        });
      });
    });
    return rows;
  }, [p.tableId, p.selectedSourceTables, p.sourceTableFields]);

  return (
    <Modal
      title={p.title}
      open={p.open}
      width={980}
      onOk={p.onOk}
      onCancel={p.onCancel}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <Select
          allowClear
          placeholder="按来源表过滤字段"
          value={p.tableId || undefined}
          onChange={(v) => p.onTableIdChange(v || '')}
          options={p.selectedSourceTables.map(t => ({ value: String(t.id), label: `${t.enName} (${t.cnName || ''})` }))}
          style={{ width: 360 }}
        />
        <Table
          size="small"
          rowKey="key"
          dataSource={fieldPickerRows}
          pagination={{ pageSize: 10 }}
          scroll={{ y: 360 }}
          rowSelection={{
            selectedRowKeys: p.tempValues,
            onChange: (keys) => p.onTempValuesChange(keys as string[]),
          }}
          columns={[
            { title: TERMS.sourceTableEnName, dataIndex: 'tableEn', width: 180 },
            { title: TERMS.sourceTableCnName, dataIndex: 'tableCn', width: 160 },
            { title: TERMS.sourceFieldEnName, dataIndex: 'fieldEn', width: 200 },
            { title: TERMS.sourceFieldCnName, dataIndex: 'fieldCn', width: 220 },
          ]}
        />
      </Space>
    </Modal>
  );
};

// SQL 预览弹窗
export type SqlPreviewModalProps = {
  open: boolean;
  title: string;
  content: string;
  onCancel: () => void;
};

export const SqlPreviewModal: React.FC<SqlPreviewModalProps> = (p) => (
  <Modal
    title={p.title}
    open={p.open}
    width={900}
    onCancel={p.onCancel}
    footer={null}
  >
    <TextArea
      rows={18}
      readOnly
      value={p.content}
      style={{ fontFamily: 'monospace', background: '#1e1e1e', color: '#d4d4d4' }}
    />
  </Modal>
);
