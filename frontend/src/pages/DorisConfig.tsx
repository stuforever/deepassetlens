import React, { useEffect, useState } from 'react';
import {
  Card, Button, Table, Space, Modal, Form, Input, InputNumber, message, Tag, Popconfirm, Divider,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, ThunderboltOutlined, SaveOutlined, DatabaseOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { PageShell, StatusTag } from '../components/shell';
import { tokens } from '../theme/tokens';

const API = axios.create({ baseURL: '/api/v1' });

interface Catalog {
  name: string;
  catalog_type: string;
  in_db: boolean;
  jdbc_url?: string;
  jdbc_user?: string;
  driver_class?: string;
  driver_url?: string;
  created_at?: string;
}

const DorisConfigPage: React.FC = () => {
  // Doris 连接配置
  const [cfg, setCfg] = useState<any>({ host: 'localhost', port: 9030, user: 'root', password: '', charset: 'utf8mb4', connect_timeout: 10 });
  const [cfgLoading, setCfgLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [savingCfg, setSavingCfg] = useState(false);
  const [cfgForm] = Form.useForm();

  // Catalog 管理
  const [catalogs, setCatalogs] = useState<Catalog[]>([]);
  const [catLoading, setCatLoading] = useState(false);
  const [catModalOpen, setCatModalOpen] = useState(false);
  const [catForm] = Form.useForm();

  const loadCfg = async () => {
    setCfgLoading(true);
    try {
      const res = await API.get('/doris/config');
      const d = res.data?.data || {};
      setCfg(d);
      cfgForm.setFieldsValue(d);
    } catch (e: any) {
      message.error('加载 Doris 配置失败: ' + (e?.response?.data?.detail || e?.message));
    } finally { setCfgLoading(false); }
  };

  const loadCatalogs = async () => {
    setCatLoading(true);
    try {
      const res = await API.get('/doris/catalogs');
      setCatalogs(res.data?.data || []);
    } catch (e: any) {
      message.error('加载 Catalog 列表失败: ' + (e?.response?.data?.detail || e?.message));
    } finally { setCatLoading(false); }
  };

  useEffect(() => { loadCfg(); loadCatalogs(); }, []); // eslint-disable-line

  const testConn = async () => {
    const v = cfgForm.getFieldsValue();
    setTesting(true);
    try {
      await API.post('/doris/config/test', { host: v.host, port: v.port, user: v.user, password: v.password });
      message.success('Doris 连接测试成功');
    } catch (e: any) {
      message.error('连接失败: ' + (e?.response?.data?.detail || e?.message));
    } finally { setTesting(false); }
  };

  const saveCfg = async () => {
    const v = cfgForm.getFieldsValue();
    setSavingCfg(true);
    try {
      await API.put('/doris/config', v);
      message.success('Doris 配置已保存');
    } catch (e: any) {
      message.error('保存失败: ' + (e?.response?.data?.detail || e?.message));
    } finally { setSavingCfg(false); }
  };

  const createCatalog = async (values: any) => {
    try {
      await API.post('/doris/catalogs', values);
      message.success(`Catalog ${values.name} 创建成功`);
      setCatModalOpen(false);
      catForm.resetFields();
      loadCatalogs();
    } catch (e: any) {
      message.error('创建失败: ' + (e?.response?.data?.detail || e?.message));
    }
  };

  const deleteCatalog = async (name: string) => {
    try {
      await API.delete(`/doris/catalogs/${encodeURIComponent(name)}`);
      message.success(`Catalog ${name} 已删除`);
      loadCatalogs();
    } catch (e: any) {
      message.error('删除失败: ' + (e?.response?.data?.detail || e?.message));
    }
  };

  const catColumns = [
    { title: 'Catalog 名称', dataIndex: 'name', render: (v: string) => <StatusTag preset="info">{v}</StatusTag> },
    { title: '类型', dataIndex: 'catalog_type' },
    {
      title: '纳管',
      dataIndex: 'in_db',
      render: (v: boolean) => v ? <StatusTag preset="success">已纳管</StatusTag> : <Tag>外部</Tag>,
    },
    { title: 'JDBC URL', dataIndex: 'jdbc_url', ellipsis: true, render: (v: string) => v || '-' },
    { title: '创建时间', dataIndex: 'created_at', render: (v: string) => v || '-' },
    {
      title: '操作',
      render: (_: any, r: Catalog) => (
        <Popconfirm title={`确认删除 Catalog ${r.name}？（Doris 与本地记录一并删除）`} onConfirm={() => deleteCatalog(r.name)}>
          <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <PageShell title="Doris 配置">
      <Card
        title={<Space><DatabaseOutlined />Doris 连接配置</Space>}
        size="small"
        loading={cfgLoading}
        extra={<Space>
          <Button icon={<ThunderboltOutlined />} loading={testing} onClick={testConn}>测试连接</Button>
          <Button type="primary" icon={<SaveOutlined />} loading={savingCfg} onClick={saveCfg}>保存配置</Button>
        </Space>}
      >
        <Form form={cfgForm} layout="inline" initialValues={cfg}>
          <Form.Item name="host" label="Host"><Input placeholder="localhost" style={{ width: 160 }} /></Form.Item>
          <Form.Item name="port" label="Port"><InputNumber min={1} max={65535} style={{ width: 100 }} /></Form.Item>
          <Form.Item name="user" label="用户名"><Input style={{ width: 120 }} /></Form.Item>
          <Form.Item name="password" label="密码"><Input.Password style={{ width: 140 }} /></Form.Item>
          <Form.Item name="charset" label="charset"><Input style={{ width: 100 }} /></Form.Item>
          <Form.Item name="connect_timeout" label="连接超时(秒)"><InputNumber min={1} style={{ width: 90 }} /></Form.Item>
        </Form>
        <div style={{ marginTop: 8, fontSize: 12, color: tokens.colors.textTertiary }}>
          Doris FE 暴露 MySQL 协议（默认 9030），pymysql 直连。sql_integration 模式执行 integration_sql 时使用此连接。
        </div>
      </Card>

      <Card
        title={<Space><DatabaseOutlined />Catalog 管理（jdbc 联邦）</Space>}
        size="small"
        style={{ marginTop: 12 }}
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => { catForm.resetFields(); catForm.setFieldsValue({ catalog_type: 'jdbc', driver_class: 'com.mysql.cj.jdbc.Driver' }); setCatModalOpen(true); }}>新建 Catalog</Button>}
      >
        <Table size="small" dataSource={catalogs} rowKey="name" columns={catColumns} loading={catLoading} pagination={false} />
        <div style={{ marginTop: 8, fontSize: 12, color: tokens.colors.textTertiary }}>
          「外部」= Doris 已存在但未在本平台纳管（如 mysql_tupu），可直接在「数据来源映射」SQL 编辑器选用；「已纳管」= 本平台创建可重建/编辑。
        </div>
      </Card>

      <Modal
        title="新建 Catalog"
        open={catModalOpen}
        onOk={() => catForm.submit()}
        onCancel={() => { setCatModalOpen(false); catForm.resetFields(); }}
        destroyOnHidden
        width={620}
      >
        <Form form={catForm} layout="vertical" onFinish={createCatalog} preserve={false}>
          <Form.Item name="name" label="Catalog 名称" rules={[{ required: true, message: '名称必填' }, { pattern: /^[a-zA-Z_][a-zA-Z0-9_]*$/, message: '仅限字母/数字/下划线，首字符非数字' }]}>
            <Input placeholder="例如：mysql_tupu" />
          </Form.Item>
          <Form.Item name="catalog_type" label="类型" initialValue="jdbc">
            <Input disabled />
          </Form.Item>
          <Form.Item name="jdbc_url" label="JDBC URL" rules={[{ required: true, message: 'JDBC URL 必填' }]}>
            <Input placeholder="jdbc:mysql://host.docker.internal:3306/tupu?useUnicode=true&characterEncoding=utf-8" />
          </Form.Item>
          <Form.Item name="jdbc_user" label="用户名" rules={[{ required: true, message: '用户名必填' }]}>
            <Input placeholder="root" />
          </Form.Item>
          <Form.Item name="jdbc_password" label="密码" rules={[{ required: true, message: '密码必填' }]}>
            <Input.Password placeholder="root" />
          </Form.Item>
          <Form.Item name="driver_class" label="Driver Class">
            <Input placeholder="com.mysql.cj.jdbc.Driver" />
          </Form.Item>
          <Form.Item name="driver_url" label="Driver URL（jar 下载地址）">
            <Input placeholder="http://172.28.80.2:8888/mysql-connector-j-8.0.33.jar" />
          </Form.Item>
        </Form>
      </Modal>
    </PageShell>
  );
};

export default DorisConfigPage;
