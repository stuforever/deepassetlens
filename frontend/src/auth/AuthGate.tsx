import React, { useEffect, useState } from 'react';
import { Spin, Alert, Button } from 'antd';
import {
  fetchAuthConfig,
  getStoredToken,
  isTokenValid,
  startLogin,
  exchangeCode,
  popReturnTo,
  fetchMe,
} from './oidc';

export interface AuthContext {
  user: any | null;
  enableAuth: boolean;
}

export const AuthCtx = React.createContext<AuthContext>({ user: null, enableAuth: false });

interface Props {
  children: React.ReactNode;
}

const CALLBACK_PATH = '/auth/callback';

const AuthGate: React.FC<Props> = ({ children }) => {
  const [phase, setPhase] = useState<'init' | 'login' | 'exchange' | 'ready' | 'error'>('init');
  const [errMsg, setErrMsg] = useState<string>('');
  const [user, setUser] = useState<any | null>(null);
  const [enableAuth, setEnableAuth] = useState<boolean>(false);

  useEffect(() => {
    (async () => {
      try {
        const cfg = await fetchAuthConfig();
        setEnableAuth(cfg.enable_auth);

        // 关闭权限：直接放行
        if (!cfg.enable_auth) {
          const me = await fetchMe();
          setUser(me);
          setPhase('ready');
          return;
        }

        // 处理 OIDC callback
        if (window.location.pathname === CALLBACK_PATH) {
          setPhase('exchange');
          const params = new URLSearchParams(window.location.search);
          const code = params.get('code');
          const state = params.get('state');
          if (!code || !state) throw new Error('callback 缺 code/state');
          await exchangeCode(code, state);
          const back = popReturnTo();
          window.history.replaceState({}, '', back);
          const me = await fetchMe();
          setUser(me);
          setPhase('ready');
          return;
        }

        // 已有有效 token
        const t = getStoredToken();
        if (isTokenValid(t)) {
          const me = await fetchMe();
          setUser(me);
          setPhase('ready');
          return;
        }

        // 没 token → 跳登录
        setPhase('login');
        await startLogin();
      } catch (exc: any) {
        setErrMsg(String(exc?.message || exc));
        setPhase('error');
      }
    })();
  }, []);

  if (phase === 'init') {
    return <FullScreen><Spin tip="加载权限配置..." size="large" /></FullScreen>;
  }
  if (phase === 'login') {
    return <FullScreen><Spin tip="跳转 Authentik 登录..." size="large" /></FullScreen>;
  }
  if (phase === 'exchange') {
    return <FullScreen><Spin tip="登录态交换中..." size="large" /></FullScreen>;
  }
  if (phase === 'error') {
    return (
      <FullScreen>
        <Alert
          type="error"
          showIcon
          message="登录失败"
          description={errMsg}
          action={<Button onClick={() => window.location.reload()}>重试</Button>}
          style={{ maxWidth: 600 }}
        />
      </FullScreen>
    );
  }
  return <AuthCtx.Provider value={{ user, enableAuth }}>{children}</AuthCtx.Provider>;
};

const FullScreen: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      width: '100vw', height: '100vh', display: 'flex',
      alignItems: 'center', justifyContent: 'center', background: 'var(--bg-hover)',
    }}
  >
    {children}
  </div>
);

export default AuthGate;
