/**
 * 权限重构T4（design §5.3）：用户管理——筛选条+撑满表格+400px 抽屉。
 * 抽屉=角色勾选/启停/有效权限预览（/auth/check 逐类型）/授权三件套内嵌。
 * 数据源：/api/v1/iam/*（T2 端点）。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Checkbox, Drawer, Form, Input, Select, Switch, Table, Tag, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { SettingsPageHeader } from '../../../components/settings/shared';
import { iamApi } from '../../../services/api';

interface IamUser {
  sub: string;
  username: string;
  email: string | null;
  display_name: string | null;
  is_active: boolean;
  last_login_at: string | null;
  roles: string[];
}

interface IamRole {
  code: string;
  name: string;
  is_system: boolean;
  member_count: number;
}

const PERM_TYPES = ['skill', 'workflow', 'data_source', 'expert', 'sishu', 'auth', 'tool', 'attachment'];

const UsersPage: React.FC = () => {
  const [items, setItems] = useState<IamUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [kw, setKw] = useState('');
  const [loading, setLoading] = useState(false);
  const [roles, setRoles] = useState<IamRole[]>([]);

  // 抽屉态
  const [drawerUser, setDrawerUser] = useState<IamUser | null>(null);
  const [drawerRoles, setDrawerRoles] = useState<string[]>([]);
  const [permPreview, setPermPreview] = useState<Record<string, boolean>>({});
  const [grants, setGrants] = useState<Array<{ id: number; resource_type: string; resource_id: string; actions: string[] }>>([]);

  // 新建用户
  const [createOpen, setCreateOpen] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async (p = page, keyword = kw) => {
    setLoading(true);
    try {
      const r = await iamApi.listUsers({ kw: keyword || undefined, page: p, page_size: 50 });
      setItems(r.data?.data?.items || []);
      setTotal(r.data?.data?.total || 0);
    } catch {
      // 拦截器已提示
    } finally {
      setLoading(false);
    }
  }, [page, kw]);

  const loadRoles = useCallback(async () => {
    try {
      const r = await iamApi.listRoles();
      setRoles(r.data?.data || []);
    } catch { /* 同上 */ }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { void loadRoles(); }, [loadRoles]);

  const openDrawer = useCallback(async (u: IamUser) => {
    setDrawerUser(u);
    setDrawerRoles(u.roles || []);
    // 有效权限预览：逐资源类型查 /auth/check
    const preview: Record<string, boolean> = {};
    for (const t of PERM_TYPES) {
      try {
        const r = await iamApi.checkPermission(t, PERM_ACTION_FOR[t] || 'read', '');
        preview[t] = Boolean(r.data?.data?.allowed);
      } catch {
        preview[t] = false;
      }
    }
    setPermPreview(preview);
    try {
      const r = await iamApi.listGrants({ principal_type: 'user', principal_id: u.sub });
      setGrants(r.data?.data || []);
    } catch {
      setGrants([]);
    }
  }, []);

  const saveDrawerRoles = useCallback(async () => {
    if (!drawerUser) return;
    try {
      await iamApi.replaceUserRoles(drawerUser.sub, drawerRoles);
      message.success('角色已更新');
      await load();
    } catch { /* 拦截器已提示 */ }
  }, [drawerUser, drawerRoles, load]);

  const toggleActive = useCallback(async (u: IamUser, next: boolean) => {
    try {
      await iamApi.patchUser(u.sub, { is_active: next });
      message.success(next ? '已启用' : '已停用');
      await load();
    } catch { /* 同上 */ }
  }, [load]);

  const createUser = useCallback(async () => {
    try {
      const v = await form.validateFields();
      await iamApi.createUser({
        username: v.username,
        email: v.email || undefined,
        display_name: v.display_name || undefined,
        roles: v.roles || [],
        password: v.password || undefined,
      });
      message.success('用户已创建');
      setCreateOpen(false);
      form.resetFields();
      await load();
    } catch { /* 校验错误就地显示 */ }
  }, [form, load]);

  const columns = useMemo(() => [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '邮箱', dataIndex: 'email', key: 'email', render: (v: string | null) => v || '—' },
    {
      title: '角色', dataIndex: 'roles', key: 'roles',
      render: (roles: string[]) => (roles || []).map((r) => <Tag key={r} color={r === 'admin' ? 'red' : 'blue'}>{r}</Tag>),
    },
    {
      title: '状态', dataIndex: 'is_active', key: 'is_active',
      render: (v: boolean, u: IamUser) => <Switch size="small" checked={v} onChange={(n) => void toggleActive(u, n)} />,
    },
    {
      title: '最近登录', dataIndex: 'last_login_at', key: 'last_login_at',
      render: (v: string | null) => v ? new Date(v).toLocaleString() : '—',
    },
    {
      title: '操作', key: 'op',
      render: (_: unknown, u: IamUser) => <Button size="small" onClick={() => void openDrawer(u)}>管理</Button>,
    },
  ], [openDrawer, toggleActive]);

  return (
    <div>
      <SettingsPageHeader title="用户管理" description="用户列表与角色分配。角色变更即时生效。" />
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <Input
          allowClear
          placeholder="搜索用户名/邮箱/显示名"
          style={{ width: 280 }}
          value={kw}
          onChange={(e) => setKw(e.target.value)}
          onPressEnter={() => { setPage(1); void load(1, kw); }}
          data-testid="iam-users-kw"
        />
        <Button icon={<ReloadOutlined />} onClick={() => void load()} data-testid="iam-users-reload">刷新</Button>
        <Button type="primary" onClick={() => setCreateOpen(true)} data-testid="iam-users-create">新建用户</Button>
      </div>
      <Table<IamUser>
        rowKey="sub"
        loading={loading}
        columns={columns as never}
        dataSource={items}
        pagination={{ current: page, total, pageSize: 50, onChange: (p) => { setPage(p); void load(p); } }}
        scroll={{ y: 'calc(100vh - 320px)' }}
        onRow={(record) => ({ onClick: () => void openDrawer(record), style: { cursor: 'pointer' } })}
        data-testid="iam-users-table"
      />

      <Drawer
        title={drawerUser ? `用户：${drawerUser.username}` : ''}
        width={400}
        open={Boolean(drawerUser)}
        onClose={() => setDrawerUser(null)}
        data-testid="iam-user-drawer"
      >
        {drawerUser && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>角色</div>
              <Checkbox.Group
                value={drawerRoles}
                onChange={(v) => setDrawerRoles(v as string[])}
                options={roles.map((r) => ({ label: `${r.name}（${r.code}）`, value: r.code }))}
              />
              <Button size="small" type="primary" style={{ marginTop: 8 }} onClick={() => void saveDrawerRoles()} data-testid="iam-drawer-save-roles">
                保存角色
              </Button>
            </div>
            <div>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>有效权限预览</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {PERM_TYPES.map((t) => (
                  <Tag key={t} color={permPreview[t] ? 'green' : 'default'}>
                    {t}: {permPreview[t] ? '有' : '无'}
                  </Tag>
                ))}
              </div>
            </div>
            <div>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>资源授权（{grants.length}）</div>
              {grants.map((g) => (
                <div key={g.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, borderBottom: '1px solid #f0f0f0', padding: '4px 0' }}>
                  <span>{g.resource_type}/{g.resource_id} · {g.actions.join(',')}</span>
                  <Button size="small" type="link" onClick={async () => {
                    await iamApi.revokeGrant(g.id);
                    const r = await iamApi.listGrants({ principal_type: 'user', principal_id: drawerUser.sub });
                    setGrants(r.data?.data || []);
                  }}>撤销</Button>
                </div>
              ))}
              {!grants.length && <div style={{ fontSize: 12, color: '#999' }}>暂无资源级授权</div>}
            </div>
          </div>
        )}
      </Drawer>

      <Drawer
        title="新建用户"
        width={400}
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      >
        <Form form={form} layout="vertical" onFinish={() => void createUser()}>
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input data-testid="iam-create-username" />
          </Form.Item>
          <Form.Item name="email" label="邮箱">
            <Input type="email" data-testid="iam-create-email" />
          </Form.Item>
          <Form.Item name="display_name" label="显示名">
            <Input />
          </Form.Item>
          <Form.Item name="password" label="初始密码" extra="留空则仅建本地镜像（不建登录身份）">
            <Input.Password data-testid="iam-create-password" />
          </Form.Item>
          <Form.Item name="roles" label="初始角色">
            <Select mode="multiple" options={roles.map((r) => ({ label: r.code, value: r.code }))} />
          </Form.Item>
          <Button type="primary" block htmlType="submit" data-testid="iam-create-submit">创建</Button>
        </Form>
      </Drawer>
    </div>
  );
};

const PERM_ACTION_FOR: Record<string, string> = {
  skill: 'read', workflow: 'read', data_source: 'read', expert: 'use',
  sishu: 'use', auth: 'read', tool: 'execute', attachment: 'read',
};

export default UsersPage;
