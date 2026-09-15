/**
 * ⑥-2a B-2：专家赋权管理面（平台配置层——附件四 §10.2 治理层位置）。
 * 后端零新增：复用 grant 三端点（aclApi.getGrants/grant/revoke）+listUsers。
 * 用户下拉×专家下拉×动作勾选（use/manage）+expires_at（可选 30 天临时授权——spec D5）。
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  Button, Card, Checkbox, DatePicker, Form, Select, Space, Table, Tag, message,
} from 'antd';
import { aclApi, expertsApi } from '../services/api';

interface GrantRow {
  id: number;
  resource_type: string;
  resource_id: string;
  principal_type: string;
  principal_id: string;
  actions: string[];
  expires_at: string | null;
  granted_by?: string;
  granted_at?: string;
}

const ACTION_LABEL: Record<string, string> = {
  use: '使用（门户+对话+功能页）',
  manage: '管理（+专家后台）',
};

const ExpertGrants: React.FC = () => {
  const [users, setUsers] = useState<{ sub: string; username?: string }[]>([]);
  const [experts, setExperts] = useState<{ expert_id: string; name?: string }[]>([]);
  const [grants, setGrants] = useState<GrantRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [actions, setActions] = useState<string[]>(['use']);
  const [temp30, setTemp30] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const j = await aclApi.getGrants('expert', '').then((r: any) => r.data);
      const arr = Array.isArray(j) ? j : Array.isArray(j?.data) ? j.data : j?.data?.items || [];
      setGrants(arr);
    } catch {
      message.error('赋权列表获取失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const u = await aclApi.listUsers().then((r: any) => r.data);
        const ua = Array.isArray(u) ? u : Array.isArray(u?.data) ? u.data : u?.data?.items || [];
        setUsers(ua);
      } catch { /* 用户列表失败静默（下拉留空） */ }
      try {
        const e = await expertsApi.list().then((r: any) => r.data);
        const ea2 = Array.isArray(e) ? e : Array.isArray(e?.data) ? e.data : e?.items || [];
        setExperts(ea2);
      } catch { /* 专家列表失败静默 */ }
      load();
    })();
  }, [load]);

  const submit = async (v: any) => {
    if (!actions.length) { message.error('至少勾选一个动作'); return; }
    try {
      const body: any = {
        resource_type: 'expert',
        resource_id: v.expert_id,
        principal_type: 'user',
        principal_id: v.principal_id,
        actions,
      };
      if (temp30) {
        const d = new Date(Date.now() + 30 * 86400 * 1000);
        body.expires_at = d.toISOString().slice(0, 19).replace('T', ' ');
      }
      await aclApi.grant(body);
      message.success(`已赋权：${v.principal_id} → ${v.expert_id} [${actions.join(', ')}]`);
      form.resetFields();
      setActions(['use']);
      setTemp30(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '赋权失败');
    }
  };

  const revoke = async (id: number) => {
    try {
      await aclApi.revoke(id);
      message.success('已回收');
      load();
    } catch {
      message.error('回收失败');
    }
  };

  return (
    <div style={{ margin: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card title="专家赋权（用户 × 专家 × use/manage）" style={{ borderRadius: 12 }}>
        <Form form={form} layout="inline" onFinish={submit} style={{ rowGap: 8 }}>
          <Form.Item name="principal_id" label="用户" rules={[{ required: true, message: '选用户' }]}>
            <Select
              showSearch optionFilterProp="label" placeholder="选用户" style={{ minWidth: 160 }}
              options={users.map((u) => ({ value: u.sub, label: u.username || u.sub }))}
            />
          </Form.Item>
          <Form.Item name="expert_id" label="专家" rules={[{ required: true, message: '选专家' }]}>
            <Select
              showSearch optionFilterProp="label" placeholder="选专家" style={{ minWidth: 140 }}
              options={experts.map((e) => ({ value: e.expert_id, label: e.name || e.expert_id }))}
            />
          </Form.Item>
          <Form.Item label="动作">
            <Checkbox.Group
              value={actions}
              onChange={(v) => setActions(v as string[])}
              options={Object.entries(ACTION_LABEL).map(([k, l]) => ({ value: k, label: l }))}
            />
          </Form.Item>
          <Form.Item label="30 天临时授权">
            <Checkbox checked={temp30} onChange={(e) => setTemp30(e.target.checked)} />
          </Form.Item>
          {temp30 && (
            <Form.Item label="到期日">
              <DatePicker disabled placeholder={`默认 30 天后（自动）`} />
            </Form.Item>
          )}
          <Form.Item>
            <Button type="primary" htmlType="submit">赋权</Button>
          </Form.Item>
        </Form>
      </Card>

      <Card title="生效赋权（expert 资源）" style={{ borderRadius: 12 }}>
        <Table<GrantRow>
          rowKey="id" size="small" loading={loading} dataSource={grants}
          pagination={{ pageSize: 10 }}
          columns={[
            { title: '用户', dataIndex: 'principal_id', width: 160,
              render: (v: string, r: GrantRow) => (r.principal_type === 'role' ? <Tag>角色:{v}</Tag> : v) },
            { title: '专家', dataIndex: 'resource_id', width: 120 },
            { title: '动作', dataIndex: 'actions', width: 200,
              render: (a: string[]) => <Space>{(a || []).map((x) => <Tag key={x} color={x === 'manage' ? 'orange' : 'blue'}>{x}</Tag>)}</Space> },
            { title: '到期', dataIndex: 'expires_at', width: 170,
              render: (v: string | null) => (v ? <Tag color="volcano">{v.slice(0, 16).replace('T', ' ')}</Tag> : <Tag>永久</Tag>) },
            { title: '操作', width: 90,
              render: (_: any, r: GrantRow) => <Button size="small" danger onClick={() => revoke(r.id)}>回收</Button> },
          ]}
          locale={{ emptyText: '暂无 expert 赋权记录' }}
        />
      </Card>
    </div>
  );
};

export default ExpertGrants;
