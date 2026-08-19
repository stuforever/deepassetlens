/**
 * ModelFormDrawer —— 模型树全部弹窗表单（纯展示 + 事件上抛）
 *
 * 从 ModelTreeManager 抽离：概念/实体/属性/关键词选择/数据预览 5 个 Modal。
 * 不持有状态；Form 实例、可见性、数据与回调全部经 props 传入。
 */
import React from 'react';
import {
  Modal, Form, Input, InputNumber, Select, Switch, Button, Space, Empty, Table, Typography,
} from 'antd';
import type { FormInstance } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { StatusTag } from '../shell';
import { getEntityCategoryLabel, EXPLANATION_SOURCE_META, type ExplanationItem, type ExplanationSource } from './modelTree';

const { Text } = Typography;

export type ModelFormDrawerProps = {
  // 概念分类弹窗
  conceptForm: FormInstance;
  conceptModalMode: 'create' | 'edit';
  conceptModalVisible: boolean;
  conceptFormLevel: any;
  selectedMeta: any;
  onCancelConcept: () => void;
  onSaveConcept: () => void;

  // 数据实体弹窗（含解释/同义词维护）
  entityForm: FormInstance;
  editingEntity: any;
  entityTargetConcept: any;
  entityModalVisible: boolean;
  loadingExplanationSuggest: boolean;
  explanationItems: ExplanationItem[];
  explanationValue: string;
  explanationStats: { manual: number; auto: number; field: number };
  currentPropertyKeywordOptions: string[];
  newManualExplanation: string;
  onCancelEntity: () => void;
  onSaveEntity: () => void;
  onAutoSuggestExplanation: () => void;
  onOpenKeywordPicker: () => void;
  onNewManualExplanationChange: (v: string) => void;
  onAddManualExplanation: () => void;
  onUpdateExplanationItem: (id: string, text: string) => void;
  onRemoveExplanationItem: (id: string) => void;
  onClearExplanationItems: () => void;

  // 关键词选择弹窗
  explanationKeywordModalVisible: boolean;
  selectedExplanationKeywords: string[];
  onCancelKeywordModal: () => void;
  onKeywordSelectChange: (values: string[]) => void;
  onApplyKeywords: () => void;

  // 属性弹窗
  propertyForm: FormInstance;
  editingPropertyIndex: number | null;
  propertyModalVisible: boolean;
  onCancelProperty: () => void;
  onSaveProperty: () => void;

  // 数据预览弹窗
  previewTitle: string;
  previewOpen: boolean;
  previewLoading: boolean;
  previewRows: any[];
  previewColumns: any[];
  onCancelPreview: () => void;
};

const ModelFormDrawer: React.FC<ModelFormDrawerProps> = (p) => (
  <>
    {/* 概念分类弹窗 */}
    <Modal
      title={p.conceptModalMode === 'create' ? '新增概念分类' : '编辑概念分类'}
      open={p.conceptModalVisible}
      onCancel={p.onCancelConcept}
      onOk={p.onSaveConcept}
      destroyOnHidden
    >
      <Form form={p.conceptForm} layout="vertical">
        {p.conceptModalMode === 'create' ? (
          <>
            <Form.Item name="level" label="层级">
              <Input disabled />
            </Form.Item>
            <Form.Item name="parent_id" label="父级ID">
              <Input disabled />
            </Form.Item>
          </>
        ) : null}
        <Form.Item name="name" label="概念分类名称" rules={[{ required: true, message: '请输入概念分类名称' }]}>
          <Input />
        </Form.Item>
        <Form.Item name="sort_order" label="显示顺序">
          <InputNumber min={0} precision={0} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="description" label="描述">
          <Input.TextArea rows={3} />
        </Form.Item>
        {(p.conceptModalMode === 'create' ? Number(p.conceptFormLevel) : p.selectedMeta?.concept?.level) === 3 ? (
          <Form.Item name="system_names" label="所属系统">
            <Select
              mode="tags"
              allowClear
              tokenSeparators={[',', '，', ';', '；']}
              placeholder="可输入 1 个或多个所属系统"
            />
          </Form.Item>
        ) : null}
      </Form>
    </Modal>

    {/* 数据实体弹窗 */}
    <Modal
      title={p.editingEntity ? `编辑${getEntityCategoryLabel(p.entityTargetConcept?.level)}` : `新增${getEntityCategoryLabel(p.entityTargetConcept?.level)}`}
      open={p.entityModalVisible}
      onCancel={p.onCancelEntity}
      onOk={p.onSaveEntity}
      destroyOnHidden
    >
      <Form form={p.entityForm} layout="vertical">
        <Form.Item label="所属概念分类">
          <Input value={p.entityTargetConcept?.name || ''} disabled />
        </Form.Item>
        <Form.Item name="entity_name" label={`${getEntityCategoryLabel(p.entityTargetConcept?.level)}名称`} rules={[{ required: true, message: `请输入${getEntityCategoryLabel(p.entityTargetConcept?.level)}名称` }]}>
          <Input />
        </Form.Item>
        <Form.Item name="entity_en_name" label="落地英文表名">
          <Input />
        </Form.Item>
        <Form.Item name="entity_code" label={`${getEntityCategoryLabel(p.entityTargetConcept?.level)}编码`} rules={[{ required: true, message: `请输入${getEntityCategoryLabel(p.entityTargetConcept?.level)}编码` }]}>
          <Input disabled={!!p.editingEntity} />
        </Form.Item>
        <Form.Item label="解释（别名同义词）" extra="自动提取、字段选择、手工新增三路解耦维护；最终统一汇总到下方总表，任何一条都可以直接修改或删除。">
          <Space wrap style={{ marginBottom: 12 }}>
            <Button onClick={p.onAutoSuggestExplanation} loading={p.loadingExplanationSuggest}>
              自动提取同义词
            </Button>
            <Button onClick={p.onOpenKeywordPicker} disabled={!p.currentPropertyKeywordOptions.length}>
              从字段选择同义词
            </Button>
            <Button onClick={p.onClearExplanationItems} disabled={!p.explanationItems.length}>
              清空全部
            </Button>
            <StatusTag preset="info">手工 {p.explanationStats.manual}</StatusTag>
            <StatusTag preset="ai">自动 {p.explanationStats.auto}</StatusTag>
            <StatusTag preset="info">字段 {p.explanationStats.field}</StatusTag>
            <Text type="secondary">总计 {p.explanationItems.length} 条</Text>
          </Space>

          <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
            <Input
              value={p.newManualExplanation}
              onChange={(e) => p.onNewManualExplanationChange(e.target.value)}
              onPressEnter={p.onAddManualExplanation}
              placeholder="输入手工同义词，支持逗号/分号批量录入"
            />
            <Button type="primary" icon={<PlusOutlined />} onClick={p.onAddManualExplanation}>
              新增手工同义词
            </Button>
          </Space.Compact>

          <Table
            size="small"
            pagination={false}
            rowKey="id"
            dataSource={p.explanationItems}
            locale={{ emptyText: '暂无同义词，可先自动提取、从字段选择，或手工新增' }}
            columns={[
              {
                title: '来源',
                dataIndex: 'source',
                width: 100,
                render: (source: ExplanationSource) => (
                  <StatusTag preset={EXPLANATION_SOURCE_META[source].preset}>{EXPLANATION_SOURCE_META[source].label}</StatusTag>
                ),
              },
              {
                title: '同义词',
                dataIndex: 'text',
                render: (value: string, row: ExplanationItem) => (
                  <Input
                    value={value}
                    placeholder="请输入同义词"
                    onChange={(e) => p.onUpdateExplanationItem(row.id, e.target.value)}
                  />
                ),
              },
              {
                title: '操作',
                width: 90,
                render: (_: any, row: ExplanationItem) => (
                  <Button danger type="link" size="small" onClick={() => p.onRemoveExplanationItem(row.id)}>
                    删除
                  </Button>
                ),
              },
            ]}
          />
          {p.explanationItems.length ? (
            <div style={{ marginTop: 12 }}>
              <Text type="secondary">最终保存值：</Text>
              <div style={{ marginTop: 8, color: 'var(--text-secondary)', wordBreak: 'break-all' }}>{p.explanationValue || '-'}</div>
            </div>
          ) : null}
        </Form.Item>
        <Form.Item name="sort_order" label="显示顺序">
          <InputNumber min={0} precision={0} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="description" label="描述">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item name="data_layer" label="数据层级">
          <Select allowClear>
            <Select.Option value="ODS">ODS</Select.Option>
            <Select.Option value="DWD">DWD</Select.Option>
            <Select.Option value="DWS">DWS</Select.Option>
            <Select.Option value="ADS">ADS</Select.Option>
          </Select>
        </Form.Item>
        <Form.Item name="is_main_table" label="是否主表" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>

    {/* 从字段选择关键词弹窗 */}
    <Modal
      title="从字段选择关键词"
      open={p.explanationKeywordModalVisible}
      onCancel={p.onCancelKeywordModal}
      onOk={p.onApplyKeywords}
      destroyOnHidden
    >
      {p.currentPropertyKeywordOptions.length ? (
        <>
          <div style={{ color: 'var(--text-tertiary)', marginBottom: 12 }}>
            这里只维护“来自字段”的关键词。勾选后会写入解释字段，取消勾选后保存会真正移除；你手工录入的其它同义词不会受影响。
          </div>
          <Select
            mode="multiple"
            value={p.selectedExplanationKeywords}
            onChange={p.onKeywordSelectChange}
            style={{ width: '100%' }}
            placeholder="请选择要写入解释字段的属性关键词"
            options={p.currentPropertyKeywordOptions.map((item) => ({ label: item, value: item }))}
          />
        </>
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前实体暂无可用属性关键词" />
      )}
    </Modal>

    {/* 属性弹窗 */}
    <Modal
      title={p.editingPropertyIndex === null ? '新增属性' : '编辑属性'}
      open={p.propertyModalVisible}
      onCancel={p.onCancelProperty}
      onOk={p.onSaveProperty}
      destroyOnHidden
    >
      <Form form={p.propertyForm} layout="vertical">
        <Form.Item name="name" label="属性英文名" rules={[{ required: true, message: '请输入属性英文名' }]}>
          <Input />
        </Form.Item>
        <Form.Item name="cnName" label="属性中文名" rules={[{ required: true, message: '请输入属性中文名' }]}>
          <Input />
        </Form.Item>
        <Form.Item name="type" label="类型" rules={[{ required: true, message: '请选择类型' }]}>
          <Select>
            <Select.Option value="string">string</Select.Option>
            <Select.Option value="int">int</Select.Option>
            <Select.Option value="float">float</Select.Option>
            <Select.Option value="boolean">boolean</Select.Option>
            <Select.Option value="datetime">datetime</Select.Option>
          </Select>
        </Form.Item>
        <Form.Item name="isPrimaryKey" label="主键" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item
          name="enable_query_entity"
          label="参与问实体识别"
          valuePropName="checked"
          extra="开启后，该属性会作为问实体的关键属性参与识别。"
        >
          <Switch checkedChildren="参与" unCheckedChildren="不参与" />
        </Form.Item>
        <Form.Item name="description" label="说明">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>

    {/* 数据预览弹窗 */}
    <Modal
      title={p.previewTitle}
      open={p.previewOpen}
      onCancel={p.onCancelPreview}
      footer={null}
      width={1100}
      destroyOnHidden
    >
      <Table
        size="small"
        loading={p.previewLoading}
        dataSource={p.previewRows}
        columns={p.previewColumns}
        rowKey={(_: any, i?: number) => String(i ?? 0)}
        pagination={{ pageSize: 10, showSizeChanger: true, size: 'small' }}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: '暂无预览数据' }}
      />
    </Modal>
  </>
);

export default ModelFormDrawer;
