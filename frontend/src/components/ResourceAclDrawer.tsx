/**
 * 资源级 ACL 抽屉
 *
 * 用法：
 *   <ResourceAclDrawer
 *     open={...}
 *     onClose={...}
 *     resourceType="skill"
 *     resourceId="my_skill_code"
 *   />
 */
import React, { useEffect, useState } from 'react';
import { Drawer, Table, Tag, Button, Space, Form, Select, Input, message, Popconfirm } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { StatusTag, DrawerFooter } from './shell';
import { aclApi } from '../services/api';

interface Props {
  open: boolean;
  onClose: () => void;
  resourceType: string;
  resourceId: string;
  title?: string;
}

interface Grant {
  id: number;
  resource_type: string;
  resource_id: string;
  principal_type: string;
  principal_id: string;
  actions: string[];
  granted_by?: string;
  granted_at?: string;
  expires_at?: string | null;
}

interface UserItem {
  sub: string;
  username: string;
  roles: string[];
}

const ALL_ACTIONS = ['read', 'write', 'execute', 'delete', 'admin'];

const ResourceAclDrawer: React.FC<Props> = ({ open, onClose, resourceType, resourceId, title }) => {
  const [grants, setGrants] = useState<Grant[]>([]);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const refresh = async () => {
    if (!open) return;
    setLoading(true);
    try {
      const [g, u] = await Promise.all([
        aclApi.getGrants(resourceType, resourceId, { silent: true }),
        aclApi.listUsers({ silent: true }).catch(() => ({ data: { data: [] } })),
      ]);
      setGrants(g.data.data || []);
      setUsers(u.data.data || []);
    } catch (e: any) {
      message.error(`加载授权失败: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [open, resourceType, resourceId]);

  const handleAdd = async (values: any) => {
    try {
      await aclApi.grant({
        resource_type: resourceType,
        resource_id: resourceId,
        principal_type: values.principal_type,
        principal_id: values.principal_id,
        actions: values.actions,
      }, { silent: true });
      message.success('授权成功');
      form.resetFields();
      refresh();
    } catch (e: any) {
      message.error(`授权失败: ${e?.response?.data?.detail || e.message}`);
    }
  };

  const handleRevoke = async (id: number) => {
    try {
      await aclApi.revoke(id, { silent: true });
      message.success('已撤销');
      refresh();
    } catch (e: any) {
      message.error(`撤销失败: ${e?.response?.data?.detail || e.message}`);
    }
  };

  return (
    <Drawer
      title={title || `权限管理 — ${resourceType}/${resourceId}`}
      width={720}
      open={open}
      onClose={onClose}
      destroyOnHidden
      footer={
        <DrawerFooter extra={<Tag>{grants.length} 条授权</Tag>}>
          <Button onClick={onClose}>关闭</Button>
          <Button type="primary" htmlType="submit" onClick={() => form.submit()}>授权</Button>
        </DrawerFooter>
      }
    >
      <h4 style={{ marginTop: 0 }}>新增授权</h4>
      <Form layout="inline" form={form} onFinish={handleAdd} style={{ marginBottom: 24, gap: 8, flexWrap: 'wrap' }}>
        <Form.Item name="principal_type" rules={[{ required: true }]} initialValue="user">
          <Select style={{ width: 100 }} options={[
            { value: 'user', label: '用户' },
            { value: 'role', label: '角色' },
          ]} />
        </Form.Item>
        <Form.Item name="principal_id" rules={[{ required: true }]}>
          <Input placeholder="用户 sub 或角色 code" style={{ width: 220 }} />
        </Form.Item>
        <Form.Item name="actions" rules={[{ required: true, type: 'array', min: 1 }]} initialValue={['read']}>
          <Select mode="multiple" style={{ width: 240 }} placeholder="动作"
                  options={ALL_ACTIONS.map(a => ({ value: a, label: a }))} />
        </Form.Item>
      </Form>

      <h4>已授权列表</h4>
      <Table
        dataSource={grants}
        rowKey="id"
        loading={loading}
        size="small"
        pagination={false}
        columns={[
          { title: '主体类型', dataIndex: 'principal_type', width: 80,
            render: (v) => <StatusTag preset={v === 'user' ? 'info' : 'warning'}>{v}</StatusTag> },
          { title: '主体', dataIndex: 'principal_id', ellipsis: true },
          { title: '动作', dataIndex: 'actions', width: 200,
            render: (acts: string[]) => acts.map(a => <Tag key={a}>{a}</Tag>) },
          { title: '授权时间', dataIndex: 'granted_at', width: 150,
            render: (v) => v?.slice(0, 19).replace('T', ' ') || '-' },
          { title: '操作', width: 60,
            render: (_, row) => (
              <Popconfirm title="撤销该授权？" onConfirm={() => handleRevoke(row.id)}>
                <Button type="link" size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            ) },
        ]}
      />

      {users.length > 0 && (
        <>
          <h4 style={{ marginTop: 24 }}>已知用户（点击复制 sub）</h4>
          <Space wrap>
            {users.map(u => (
              <Tag key={u.sub} style={{ cursor: 'pointer' }}
                   onClick={() => { navigator.clipboard.writeText(u.sub); message.success('已复制 sub'); }}>
                {u.username} {u.roles.length > 0 && `(${u.roles.join(',')})`}
              </Tag>
            ))}
          </Space>
        </>
      )}
    </Drawer>
  );
};

export default ResourceAclDrawer;
