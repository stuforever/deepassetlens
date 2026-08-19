/**
 * SourceModals —— 来源表管理的动态表单模态 + 表详情模态（纯展示 + 事件上抛）
 *
 * 从 SourceManager 抽离：新增/修改（表/字段/关联关系 动态表单）与
 * 「表详情与全量字段列表」弹窗。表单实例与数据由容器经 props 传入。
 */
import React from 'react';
import { Modal, Form, Input, Select, Spin, Descriptions, Divider, Table } from 'antd';
import type { FormInstance } from 'antd';
import { StatusTag } from './shell';
import { TERMS } from '../constants/standardTerms';
import type { RelationSubTab } from './SourceRelationTables';

// 新增/修改动态表单模态框
export type SourceFormModalProps = {
  open: boolean;
  modalType: 'create' | 'edit';
  activeTab: string;
  relationSubTab: RelationSubTab;
  referenceData: any[];
  form: FormInstance;
  onOk: () => void;
  onCancel: () => void;
};

export const SourceFormModal: React.FC<SourceFormModalProps> = (p) => (
  <Modal
    title={`${p.modalType === 'create' ? '新增' : '修改'}${p.activeTab === '4' ? '字段' : p.activeTab === '5' ? '关联关系' : '表'}`}
    open={p.open}
    onOk={p.onOk}
    onCancel={p.onCancel}
    width={650}
    destroyOnHidden
  >
    <Form form={p.form} layout="vertical">
      {['1', '2', '3'].includes(p.activeTab) && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <Form.Item name="sysName" label="来源系统名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="sysCode" label="来源系统编码" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="cnName" label={TERMS.sourceTableCnName} rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="enName" label={TERMS.sourceTableEnName} rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="major" label="专业"><Input /></Form.Item>
          <Form.Item name="deploy" label="部署方式"><Input /></Form.Item>
          <Form.Item name="type" label="表类型"><Input /></Form.Item>
        </div>
      )}
      {p.activeTab === '1' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <Form.Item name="l1" label="L1-主数据"><Input /></Form.Item>
          <Form.Item name="l2" label="L2-主数据对象"><Input /></Form.Item>
        </div>
      )}
      {p.activeTab === '2' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <Form.Item name="l3" label="L3-业务模块"><Input /></Form.Item>
          <Form.Item name="l4" label="L4-业务活动对象"><Input /></Form.Item>
          <Form.Item name="relL1" label="关联主数据大类"><Input /></Form.Item>
          <Form.Item name="relL2" label="关联主数据小类"><Input /></Form.Item>
        </div>
      )}
      {p.activeTab === '3' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <Form.Item name="category" label="参考数据分类"><Input /></Form.Item>
        </div>
      )}
      {p.activeTab === '4' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <Form.Item name="table_cn" label={TERMS.sourceTableCnName} rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="table_en" label={TERMS.sourceTableEnName} rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="field_cn" label={TERMS.sourceFieldCnName} rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="field_en" label={TERMS.sourceFieldEnName} rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="data_type" label="数据类型"><Input /></Form.Item>
          <Form.Item name="length_precision" label="长度/精度"><Input /></Form.Item>
          <Form.Item name="pk_fk" label="主/外键"><Input /></Form.Item>
          <Form.Item name="is_ref_data" label="是否参考数据"><Select options={[{value: '是', label: '是'}, {value: '否', label: '否'}]} /></Form.Item>
          <Form.Item name="ref_table_en" label="引用参考数据表英文名">
            <Select
              allowClear
              showSearch
              options={p.referenceData.map(item => ({ value: item.enName, label: `${item.enName} (${item.cnName})` }))}
            />
          </Form.Item>
          <Form.Item name="ref_data_desc" label="参考数据引用说明" style={{ gridColumn: 'span 2' }}><Input.TextArea /></Form.Item>
          <Form.Item name="ref_data_usage_desc" label="参考数据调用说明" style={{ gridColumn: 'span 2' }}><Input.TextArea /></Form.Item>
          <Form.Item name="field_desc" label="字段描述" style={{ gridColumn: 'span 2' }}><Input.TextArea /></Form.Item>
        </div>
      )}
      {p.activeTab === '5' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <Form.Item name="l1" label="L1名称"><Input /></Form.Item>
          <Form.Item name="l2" label="L2名称"><Input /></Form.Item>
          {p.relationSubTab !== 'l2' && <Form.Item name="l3" label="L3名称"><Input /></Form.Item>}
          {p.relationSubTab !== 'l2' && <Form.Item name="l4" label="L4名称"><Input /></Form.Item>}
          <Form.Item name="relation_desc" label="关联说明"><Input /></Form.Item>
          <Form.Item name="relation_category" label="关系类别"><Input /></Form.Item>
          <Form.Item name="main_table_cn" label={p.relationSubTab === 'cross' ? '主表中文名(L4前)' : '主表中文名'}><Input /></Form.Item>
          <Form.Item name="main_table_en" label={p.relationSubTab === 'cross' ? '主表英文名(L4前)' : '主表英文名'} rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="related_table_cn" label={p.relationSubTab === 'cross' ? '关联表中文名(L2后)' : '关联表中文名'}><Input /></Form.Item>
          <Form.Item name="related_table_en" label={p.relationSubTab === 'cross' ? '关联表英文名(L2后)' : '关联表英文名'} rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="relation_expr" label="关联条件说明（关联表达式）" style={{ gridColumn: 'span 2' }} rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="remark" label="备注" style={{ gridColumn: 'span 2' }}><Input.TextArea /></Form.Item>
        </div>
      )}
    </Form>
  </Modal>
);

// 表详情与全量字段列表
export type SourceDetailModalProps = {
  open: boolean;
  loading: boolean;
  currentRecord: any | null;
  tableInfo: any;
  tableFields: any[];
  onCancel: () => void;
};

export const SourceDetailModal: React.FC<SourceDetailModalProps> = (p) => (
  <Modal
    title="表详情与全量字段列表"
    open={p.open}
    onCancel={p.onCancel}
    footer={null}
    width={1000}
  >
    <Spin spinning={p.loading}>
      {p.currentRecord && (
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label={TERMS.sourceTableEnName} span={1}><StatusTag preset="info">{p.currentRecord.enName}</StatusTag></Descriptions.Item>
          <Descriptions.Item label={TERMS.sourceTableCnName} span={1}>{p.tableInfo.table_cn || p.currentRecord.cnName}</Descriptions.Item>
          <Descriptions.Item label="系统名称">{p.currentRecord.sysName}</Descriptions.Item>
          <Descriptions.Item label="表类型"><StatusTag preset="success">{p.currentRecord.type}</StatusTag></Descriptions.Item>
        </Descriptions>
      )}
      <Divider orientation="left">表字段列表</Divider>
      <Table
        size="small"
        rowKey={(record) => `${record.seq_no || 'no_seq'}_${record.field_en || 'no_field'}`}
        dataSource={p.tableFields}
        pagination={false}
        scroll={{ y: 400, x: 'max-content' }}
        columns={[
          { title: TERMS.sourceFieldEnName, dataIndex: 'field_en', width: 160 },
          { title: TERMS.sourceFieldCnName, dataIndex: 'field_cn', width: 160 },
          { title: '数据类型', dataIndex: 'data_type', width: 120 },
          { title: '字段描述', dataIndex: 'field_desc', width: 250 },
        ]}
      />
    </Spin>
  </Modal>
);
