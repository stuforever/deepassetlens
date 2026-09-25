import React, { useContext } from 'react';
import { Button, Dropdown, Space, Tooltip } from 'antd';
import { LogoutOutlined, UserOutlined } from '@ant-design/icons';
import { AuthCtx } from '../auth/AuthGate';
import { logoutST } from '../auth/st';
import { StatusTag } from './shell';
import { tokens } from '../theme/tokens';

/**
 * 三轨M6(U1) §2.1：用户区三徽章合并单头像下拉——用户名 + 角色 + 环境徽标 +（预留）退出。
 * 顶栏只留头像按钮（环境徽标不再常驻）。
 */
const UserBadge: React.FC = () => {
  const { user, enableAuth } = useContext(AuthCtx);

  if (!user) return null;

  const roles: string[] = user.roles || [];
  const isAnon = !!user.is_anonymous;
  const isProdEnv = process.env.NODE_ENV === 'production' && process.env.REACT_APP_ENV !== 'dev';

  const menu = {
    items: [
      {
        key: 'whoami',
        label: (
          <div style={{ minWidth: 168, padding: '4px 0' }} data-testid="user-badge-dropdown">
            <div style={{ fontWeight: tokens.fontWeight.semibold, marginBottom: 4 }}>
              {user.username || user.sub}
            </div>
            <Space size={6} wrap>
              {roles.map((r) => (
                <StatusTag preset={r === 'admin' ? 'error' : r === 'operator' ? 'info' : 'default'} key={r}>
                  {r}
                </StatusTag>
              ))}
              <StatusTag preset={isProdEnv ? 'success' : 'warning'}>{isProdEnv ? '生产' : '开发'}</StatusTag>
              {!enableAuth && <StatusTag preset="warning">权限关闭</StatusTag>}
            </Space>
          </div>
        ),
      },
      ...(roles.length ? [{ type: 'divider' as const }] : []),
      ...(!isAnon && enableAuth
        ? [{
            key: 'logout',
            icon: <LogoutOutlined />,
            label: '登出',
            onClick: () => { logoutST(); window.location.href = '/login'; },
          }]
        : []),
    ],
  };

  return (
    <Dropdown menu={menu} trigger={['click']} placement="bottomRight">
      <Button
        type="text"
        shape="circle"
        aria-label="用户菜单"
        data-testid="user-badge-trigger"
        icon={<UserOutlined style={{ fontSize: 18, color: tokens.colors.textSecondary }} />}
      />
    </Dropdown>
  );
};

export default UserBadge;
