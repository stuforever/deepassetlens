/**
 * MetricBaseInfo —— 指标基础信息（指标字典按属性分组表单，纯展示 + 事件上抛）
 *
 * 从 MetricManager 抽离：基础/业务/技术/管理属性四组 Form 字段。
 */
import React from 'react';
import { Card, Form, Input, Select, Space, Button, Tag } from 'antd';
import type { FormInstance } from 'antd';

export type MetricBaseInfoProps = {
  baseForm: FormInstance;
  metricDetail: any;
  onSave: () => void;
  loading: boolean;
};

const MetricBaseInfo: React.FC<MetricBaseInfoProps> = (p) => {
  const metric = p.metricDetail?.metric || {};
  return (
    <Card size="small" title="指标字典（按属性分组）">
      <Form form={p.baseForm} layout="vertical">
        <Card size="small" title="基础属性" style={{ marginBottom: 12 }}>
          <Space wrap>
            <Form.Item label="指标ID" style={{ width: 220 }}>
              <Input value={metric.metric_code || ''} disabled />
            </Form.Item>
            <Form.Item name="metric_name" label="指标中文名" style={{ width: 260 }} rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="metric_name_en" label="指标英文名" style={{ width: 220 }}><Input /></Form.Item>
            <Form.Item name="metric_level" label="指标等级" style={{ width: 160 }}>
              <Select
                allowClear
                options={[
                  { label: 'L1', value: 'L1' },
                  { label: 'L2', value: 'L2' },
                  { label: 'L3', value: 'L3' },
                  { label: 'L4', value: 'L4' },
                ]}
              />
            </Form.Item>
            <Form.Item name="metric_unit" label="计量单位" style={{ width: 160 }}><Input /></Form.Item>
          </Space>
          <Space wrap>
            <Form.Item label="创建时间" style={{ width: 240 }}>
              <Input value={metric.created_at || ''} disabled />
            </Form.Item>
            <Form.Item label="更新时间" style={{ width: 240 }}>
              <Input value={metric.updated_at || ''} disabled />
            </Form.Item>
            <Form.Item name="enabled" label="启用" style={{ width: 160 }}>
              <Select options={[{ label: 'true', value: true }, { label: 'false', value: false }]} />
            </Form.Item>
          </Space>
        </Card>

        <Card size="small" title="业务属性" style={{ marginBottom: 12 }}>
          <Form.Item name="business_caliber" label="业务口径"><Input.TextArea rows={3} /></Form.Item>
          <Space wrap>
            <Form.Item name="business_owner" label="业务负责人" style={{ width: 220 }}><Input /></Form.Item>
            <Form.Item name="business_dept" label="负责部门" style={{ width: 220 }}><Input /></Form.Item>
            <Form.Item name="requester_user" label="提需人" style={{ width: 220 }}><Input /></Form.Item>
          </Space>
        </Card>

        <Card size="small" title="技术属性" style={{ marginBottom: 12 }}>
          <Space wrap>
            <Form.Item name="metric_type" label="指标类型" style={{ width: 160 }} rules={[{ required: true }]}>
              <Select options={[{ label: 'atomic', value: 'atomic' }, { label: 'derived', value: 'derived' }]} />
            </Form.Item>
            <Form.Item name="metric_subject" label="指标主题" style={{ width: 220 }}><Input /></Form.Item>
            <Form.Item name="stat_grain" label="统计粒度" style={{ width: 160 }}>
              <Select
                allowClear
                options={[
                  { label: 'day', value: 'day' },
                  { label: 'month', value: 'month' },
                  { label: 'year', value: 'year' },
                ]}
              />
            </Form.Item>
            <Form.Item name="domain" label="域" style={{ width: 200 }}><Input /></Form.Item>
          </Space>
          <Form.Item name="tech_caliber" label="技术口径"><Input.TextArea rows={3} /></Form.Item>
          <Space wrap>
            <Form.Item name="dev_owner" label="研发负责人" style={{ width: 220 }}><Input /></Form.Item>
            <Form.Item name="similarity_threshold" label="检索阈值" style={{ width: 180 }}><Input /></Form.Item>
          </Space>
        </Card>

        <Card size="small" title="管理属性">
          <Space wrap>
            <Form.Item label="版本号" style={{ width: 160 }}>
              <Input value={String(metric.version_current ?? '')} disabled />
            </Form.Item>
            <Form.Item name="owner_user" label="指标负责人" style={{ width: 220 }}><Input /></Form.Item>
            <Form.Item name="manager_owner" label="管理负责人" style={{ width: 220 }}><Input /></Form.Item>
            <Form.Item name="reviewer_user" label="审核人" style={{ width: 220 }}><Input /></Form.Item>
          </Space>
          <Form.Item name="description" label="补充说明"><Input.TextArea rows={2} /></Form.Item>
        </Card>

        <Space wrap style={{ marginTop: 12 }}>
          <Button type="primary" onClick={p.onSave} loading={p.loading}>保存基础信息</Button>
          <Tag>status: {metric.status}</Tag>
        </Space>
      </Form>
    </Card>
  );
};

export default MetricBaseInfo;
