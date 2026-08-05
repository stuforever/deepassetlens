import React, { useEffect, useState } from 'react';
import {
  Button, Space, Modal, Form, Input, InputNumber, Switch, message, Tag, Popconfirm,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, EditOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { PageShell, DataTableShell, StatusTag } from '../components/shell';

const API = axios.create({ baseURL: '/api/v1' });

interface DataSource {
  id: string;
  name: string;
  db_type: string;
  host: string;
  port: number;
  database: string;
  username: string;
  description?: string;
  is_default: boolean;
  enabled: boolean;
  doris_catalog_name?: string;
}

const DataSourceConfigPage: React.FC = () => {
  const [items, setItems] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<DataSource | null>(null);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const res = await API.get('/data-sources');
      setItems(res.data?.data || []);
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || '未知错误';
      message.error('加载失败: ' + detail);
      console.error('加载数据源失败:', e);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (modalOpen && editing) {
      form.setFieldsValue(editing);
    }
  }, [modalOpen, editing, form]);

  const save = async (values: any) => {
    try {
      // 清理空字符串为 undefined，避免后端验证问题
      const clean: any = {};
      Object.keys(values).forEach(k => {
        const v = values[k];
        clean[k] = (v === '' || v === null) ? undefined : v;
      });

      if (editing) {
        await API.put(`/data-sources/${editing.id}`, clean);
        message.success('更新成功');
      } else {
        await API.post('/data-sources', clean);
        message.success('创建成功');
      }
      setModalOpen(false);
      form.resetFields();
      setEditing(null);
      load();
    } catch (e: any) {
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail || e?.message || '未知错误';
      message.error(`保存失败(${status}): ${detail}`);
      console.error('保存数据源失败:', e?.response?.data || e);
    }
  };

  const del = async (id: string) => {
    try {
      await API.delete(`/data-sources/${id}`);
      message.success('删除成功');
      load();
    } catch (e: any) {
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail || e?.message || '未知错误';
      message.error(`删除失败(${status}): ${detail}`);
      console.error('删除数据源失败:', e?.response?.data || e);
    }
  };

  const test = async (id: string) => {
    try {
      const res = await API.post(`/data-sources/${id}/test`);
      const data = res.data?.data || {};
      if (data.connected) {
        message.success('连接测试成功');
      } else {
        message.error(`连接失败: ${data.message}`);
      }
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || '未知错误';
      message.error('测试失败: ' + detail);
    }
  };

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ db_type: 'mysql', port: 3306, is_default: false, enabled: true });
    setModalOpen(true);
  };

  const openEdit = (item: DataSource) => {
    setEditing({ ...item });
    form.setFieldsValue({ ...item });
    setModalOpen(true);
  };

  const columns = [
    { title: '名称', dataIndex: 'name' },
    { title: '类型', dataIndex: 'db_type', render: (v: string) => <StatusTag preset="info">{v}</StatusTag> },
    { title: 'Host', dataIndex: 'host' },
    { title: 'Port', dataIndex: 'port' },
    { title: '数据库', dataIndex: 'database' },
    { title: '用户名', dataIndex: 'username' },
    { title: '默认', dataIndex: 'is_default', render: (v: boolean) => v ? <StatusTag preset="success">是</StatusTag> : '-' },
    { title: '状态', dataIndex: 'enabled', render: (v: boolean) => v ? <StatusTag preset="success">启用</StatusTag> : <Tag>禁用</Tag> },
    { title: 'Doris Catalog', dataIndex: 'doris_catalog_name', render: (v: string) => v ? <StatusTag preset="ai">{v}</StatusTag> : '-' },
    {
      title: '操作',
      render: (_: any, r: DataSource) => (
        <Space>
          <Button size="small" icon={<ThunderboltOutlined />} onClick={() => test(r.id)}>测试</Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除?" onConfirm={() => del(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageShell
      title="数据源"
      description="管理业务数据库连接，供映射与数据问答使用"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增数据源</Button>}
    >
      <DataTableShell
        compact
        tableProps={{ dataSource: items, rowKey: 'id', columns, loading, pagination: false }}
      />
      <Modal
        title={editing ? '编辑数据源' : '新增数据源'}
        open={modalOpen}
        onOk={() => form.submit()}
        onCancel={() => { setModalOpen(false); setEditing(null); form.resetFields(); }}
        destroyOnHidden
        width={500}
      >
        <Form form={form} layout="vertical" onFinish={save} preserve={false}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '名称必填' }]}>
            <Input placeholder="例如：业务MySQL" />
          </Form.Item>
          <Form.Item name="db_type" label="数据库类型" initialValue="mysql">
            <Input disabled />
          </Form.Item>
          <Form.Item name="host" label="Host" rules={[{ required: true, message: 'Host必填' }]}>
            <Input placeholder="例如：localhost 或 192.168.1.100" />
          </Form.Item>
          <Form.Item name="port" label="Port" rules={[{ required: true, message: 'Port必填' }]} initialValue={3306}>
            <InputNumber min={1} max={65535} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="database" label="数据库名" rules={[{ required: true, message: '数据库名必填' }]}>
            <Input placeholder="例如：mydb" />
          </Form.Item>
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '用户名必填' }]}>
            <Input placeholder="例如：root" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '密码必填' }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="可选：备注说明" />
          </Form.Item>
          <Form.Item name="doris_catalog_name" label="Doris Catalog（跨源联邦用）">
            <Input placeholder="可选：如 pg_tupu、mysql_biz（在 Doris 配置页建好的 catalog 名）" />
          </Form.Item>
          <Form.Item name="is_default" label="设为默认数据源" valuePropName="checked" initialValue={false}>
            <Switch />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </PageShell>
  );
};

export default DataSourceConfigPage;
