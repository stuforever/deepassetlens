/**
 * 权限重构T4（design §5.3）：角色管理——左角色列表+右矩阵编辑器+角色级 ACL 子表。
 * 矩阵行=resource_type（/iam/vocab 驱动）、列=actions、勾选格；保存走
 * PATCH /iam/roles/{code} default_permissions。tool 行按三态拆分语义展示（🛠R5）。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Input, Popconfirm, Table, Tag, message } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { SettingsPageHeader } from '../../../components/settings/shared';
import { iamApi } from '../../../services/api';

interface IamRole {
  code: string;
  name: string;
  description: string | null;
  is_system: boolean;
  default_permissions: Record<string, string[]>;
  member_count: number;
}

interface GrantRow {
  id: number;
  resource_type: string;
  resource_id: string;
  principal_type: string;
  principal_id: string;
  actions: string[];
}

const RolesPage: React.FC = () => {
  const [roles, setRoles] = useState<IamRole[]>([]);
  const [active, setActive] = useState<string>('');
  const [vocab, setVocab] = useState<Record<string, string[]>>({});
  const [draft, setDraft] = useState<Record<string, string[]>>({});
  const [creating, setCreating] = useState(false);
  const [newCode, setNewCode] = useState('');
  const [newName, setNewName] = useState('');
  const [grants, setGrants] = useState<GrantRow[]>([]);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async (selectCode?: string) => {
    try {
      const r = await iamApi.listRoles();
      const list: IamRole[] = r.data?.data || [];
      setRoles(list);
      const target = selectCode || active || list[0]?.code || '';
      setActive(target);
      const found = list.find((x) => x.code === target);
      setDraft(found ? { ...(found.default_permissions || {}) } : {});
    } catch { /* 拦截器已提示 */ }
  }, [active]);

  const loadVocab = useCallback(async () => {
    try {
      const r = await iamApi.getVocab();
      setVocab(r.data?.data || {});
    } catch { /* 同上 */ }
  }, []);

  const loadGrants = useCallback(async (code: string) => {
    if (!code) { setGrants([]); return; }
    try {
      const r = await iamApi.listGrants({ principal_type: 'role', principal_id: code });
      setGrants(r.data?.data || []);
    } catch {
      setGrants([]);
    }
  }, []);

  useEffect(() => { void loadVocab(); }, [loadVocab]);
  useEffect(() => { void load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const selectRole = useCallback((code: string) => {
    setActive(code);
    const found = roles.find((x) => x.code === code);
    setDraft(found ? { ...(found.default_permissions || {}) } : {});
    void loadGrants(code);
  }, [roles, loadGrants]);

  const toggle = useCallback((rt: string, action: string) => {
    setDraft((prev) => {
      const cur = new Set(prev[rt] || []);
      if (cur.has(action)) cur.delete(action);
      else cur.add(action);
      return { ...prev, [rt]: Array.from(cur) };
    });
  }, []);

  const save = useCallback(async () => {
    if (!active) return;
    setSaving(true);
    try {
      await iamApi.patchRole(active, { default_permissions: draft });
      message.success('默认权限已保存');
      await load(active);
    } catch { /* 同上 */ } finally {
      setSaving(false);
    }
  }, [active, draft, load]);

  const createRole = useCallback(async () => {
    try {
      await iamApi.createRole({ code: newCode, name: newName || newCode });
      message.success('角色已创建');
      setCreating(false);
      setNewCode('');
      setNewName('');
      await load(newCode);
    } catch { /* 同上 */ }
  }, [newCode, newName, load]);

  const deleteRole = useCallback(async (code: string) => {
    try {
      await iamApi.deleteRole(code);
      message.success('已删除');
      if (active === code) setActive('');
      await load();
    } catch { /* 同上 */ }
  }, [active, load]);

  const resourceTypes = useMemo(() => Object.keys(vocab), [vocab]);

  return (
    <div>
      <SettingsPageHeader title="角色管理" description="角色默认权限矩阵与角色级资源授权。" />
      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
        {/* 左：角色列表 */}
        <div style={{ width: 240, flexShrink: 0 }} data-testid="iam-roles-list">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <Button size="small" icon={<ReloadOutlined />} onClick={() => void load()} />
            <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setCreating(true)}>新建角色</Button>
          </div>
          {roles.map((r) => (
            <div
              key={r.code}
              onClick={() => selectRole(r.code)}
              style={{
                padding: '8px 10px', borderRadius: 8, cursor: 'pointer', marginBottom: 4,
                background: r.code === active ? 'rgba(37,99,235,0.08)' : 'transparent',
                border: r.code === active ? '1px solid rgba(37,99,235,0.35)' : '1px solid transparent',
              }}
            >
              <div style={{ fontSize: 13, fontWeight: 600 }}>
                {r.name} {r.is_system && <Tag style={{ marginLeft: 4 }}>内置</Tag>}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                {r.code} · {r.member_count} 成员
              </div>
              {!r.is_system && (
                <Popconfirm title="确认删除该角色？" onConfirm={() => void deleteRole(r.code)}>
                  <Button size="small" type="link" danger style={{ padding: 0, height: 18, fontSize: 11 }}>删除</Button>
                </Popconfirm>
              )}
            </div>
          ))}
          {creating && (
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <Input placeholder="code（小写下划线）" value={newCode} onChange={(e) => setNewCode(e.target.value)} data-testid="iam-role-new-code" />
              <Input placeholder="显示名" value={newName} onChange={(e) => setNewName(e.target.value)} />
              <Button type="primary" size="small" onClick={() => void createRole()}>创建</Button>
            </div>
          )}
        </div>

        {/* 右：矩阵编辑器 */}
        <div style={{ flex: 1, minWidth: 0 }} data-testid="iam-matrix">
          {active ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>默认权限矩阵：{active}</div>
                <Button size="small" type="primary" loading={saving} onClick={() => void save()} data-testid="iam-matrix-save">保存矩阵</Button>
              </div>
              <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 12 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid var(--border, #e5e7eb)' }}>资源类型</th>
                    {(vocab[Object.keys(vocab)[0]] || []).map(() => null)}
                  </tr>
                </thead>
                <tbody>
                  {resourceTypes.map((rt) => (
                    <tr key={rt}>
                      <td style={{ padding: '6px 8px', borderBottom: '1px solid #f0f0f0', fontWeight: 500 }}>
                        {rt}
                        {rt === 'tool' && (
                          <div style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>只读类默认含 execute；执行类走 ACL；写类恒拒（approval 预留）</div>
                        )}
                      </td>
                      {(vocab[rt] || []).map((a) => (
                        <td key={a} style={{ padding: '6px 8px', borderBottom: '1px solid #f0f0f0' }}>
                          <label style={{ cursor: 'pointer' }}>
                            <input
                              type="checkbox"
                              checked={(draft[rt] || []).includes(a)}
                              onChange={() => toggle(rt, a)}
                              data-testid={`iam-matrix-${rt}-${a}`}
                            />{' '}{a}
                          </label>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>角色级资源授权（{grants.length}）</div>
                {grants.map((g) => (
                  <div key={g.id} style={{ fontSize: 12, borderBottom: '1px solid #f0f0f0', padding: '4px 0', display: 'flex', justifyContent: 'space-between' }}>
                    <span>{g.resource_type}/{g.resource_id} · {g.actions.join(',')}</span>
                    <Button size="small" type="link" onClick={async () => {
                      await iamApi.revokeGrant(g.id);
                      await loadGrants(active);
                    }}>撤销</Button>
                  </div>
                ))}
                {!grants.length && <div style={{ fontSize: 12, color: '#999' }}>暂无（用专家赋权页新增 role 级授权）</div>}
              </div>
            </>
          ) : (
            <div style={{ color: 'var(--text-tertiary)' }}>← 选择一个角色</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RolesPage;
