import React, { useContext } from 'react';
import { Button, Space, Tooltip } from 'antd';
import { LogoutOutlined, UserOutlined } from '@ant-design/icons';
import { AuthCtx } from '../auth/AuthGate';
import { logout } from '../auth/oidc';
import { StatusTag } from './shell';

const UserBadge: React.FC = () => {
  const { user, enableAuth } = useContext(AuthCtx);

  if (!user) return null;

  const roles: string[] = user.roles || [];
  const isAnon = !!user.is_anonymous;

  return (
    <Space size={8}>
      <UserOutlined />
      <span style={{ fontWeight: 500 }}>{user.username || user.sub}</span>
      {roles.map((r) => (
        <StatusTag preset={r === 'admin' ? 'error' : r === 'operator' ? 'info' : 'default'} key={r}>
          {r}
        </StatusTag>
      ))}
      {!enableAuth && <StatusTag preset="warning">权限关闭</StatusTag>}
      {!isAnon && enableAuth && (
        <Tooltip title="登出">
          <Button
            type="text"
            size="small"
            icon={<LogoutOutlined />}
            onClick={() => logout()}
          />
        </Tooltip>
      )}
    </Space>
  );
};

export default UserBadge;
