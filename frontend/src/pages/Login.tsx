/**
 * 权限重构T4（design §4.4）：自研登录页——POST /api/v1/auth/session（ST SDK 签发）。
 * 沿用门户视觉（独立全屏卡）；成功后 token 入 ST 会话存储，回AuthGate 走 /auth/me。
 * 不引 supertokens-web-js（组件极简定调）；401 刷新重放在 http.ts 拦截器。
 */
import React, { useState } from 'react';
import { Button, Input } from 'antd';
import { LockOutlined, UserOutlined } from '@ant-design/icons';
import axios from 'axios';
import { saveSession } from '../auth/st';

interface Props {
  onSuccess: () => void;
}

const Login: React.FC<Props> = ({ onSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  const submit = async () => {
    if (!email.trim() || !password || loading) return;
    setLoading(true);
    setErr('');
    try {
      const r = await axios.post('/api/v1/auth/session', { email: email.trim(), password });
      const d = r?.data?.data || {};
      saveSession(d.access_token || '', d.refresh_token || '');
      onSuccess();
    } catch (e: any) {
      setErr(String(e?.response?.data?.detail || e?.message || '登录失败'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        width: '100vw', height: '100vh', display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: 'var(--bg-hover, #f7f8fa)',
      }}
      data-testid="st-login-page"
    >
      <div
        style={{
          width: 400, padding: '40px 36px 32px', borderRadius: 18, background: 'var(--bg-content, #fff)',
          boxShadow: '0 12px 32px rgba(15,23,42,0.10)', display: 'flex', flexDirection: 'column', gap: 14,
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 4 }}>
          <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary, #222)' }}>
            DeepAssetLens
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-tertiary, #999)', marginTop: 4 }}>
            资产深度探查平台
          </div>
        </div>
        <Input
          size="large"
          prefix={<UserOutlined style={{ color: '#bbb' }} />}
          placeholder="邮箱"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onPressEnter={submit}
          data-testid="login-email"
        />
        <Input.Password
          size="large"
          prefix={<LockOutlined style={{ color: '#bbb' }} />}
          placeholder="密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onPressEnter={submit}
          data-testid="login-password"
        />
        {err && (
          <div style={{ fontSize: 12, color: '#ef4444' }} data-testid="login-error">
            {err}
          </div>
        )}
        <Button
          type="primary"
          size="large"
          block
          loading={loading}
          onClick={submit}
          data-testid="login-submit"
        >
          登录
        </Button>
      </div>
    </div>
  );
};

export default Login;
