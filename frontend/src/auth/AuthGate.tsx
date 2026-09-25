import React, { useEffect, useState } from 'react';
import { Spin, Alert, Button } from 'antd';
// 权限重构T7：oidc.ts 退役——身份层 SuperTokens 单栈（authentik provider 后端保留
// 一版作回滚保险，前端流已删；回滚=git revert 本提交）。
import { fetchAuthConfig, fetchMeST, getAccessToken, getRefreshToken, isAccessTokenFresh } from './st';
import { tryRefresh } from '../services/http';
import Login from '../pages/Login';

export interface AuthContext {
  user: any | null;
  enableAuth: boolean;
  authReady: boolean;
}

export const AuthCtx = React.createContext<AuthContext>({ user: null, enableAuth: false, authReady: false });

interface Props {
  children: React.ReactNode;
}

const AuthGate: React.FC<Props> = ({ children }) => {
  const [phase, setPhase] = useState<'init' | 'st-login' | 'ready' | 'error'>('init');
  const [errMsg, setErrMsg] = useState<string>('');
  const [user, setUser] = useState<any | null>(null);
  const [enableAuth, setEnableAuth] = useState<boolean>(false);
  const [loginTick, setLoginTick] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const cfg = await fetchAuthConfig();
        setEnableAuth(cfg.enableAuth);

        // 关闭权限：直接放行（开发态语义，auth=0）
        if (!cfg.enableAuth) {
          const me = await fetchMeST();
          setUser(me);
          setPhase('ready');
          return;
        }

        // ST：access 有效 → 就绪；过期但有 refresh → 续期（验收 #2，🛠R2）
        let t = getAccessToken();
        if (t && !isAccessTokenFresh(t) && getRefreshToken()) {
          if (await tryRefresh()) t = getAccessToken();
        }
        if (t && isAccessTokenFresh(t)) {
          const me = await fetchMeST();
          setUser(me);
          setPhase('ready');
          return;
        }
        if (!t && getRefreshToken()) {
          if (await tryRefresh()) {
            const me = await fetchMeST();
            setUser(me);
            setPhase('ready');
            return;
          }
        }
        setPhase('st-login');
      } catch (exc: any) {
        setErrMsg(String(exc?.message || exc));
        setPhase('error');
      }
    })();
  }, [loginTick]);

  if (phase === 'init') {
    return <FullScreen><Spin size="large" /><div style={{ marginTop: 12, fontSize: 13, color: "var(--text-tertiary)" }}>加载权限配置...</div></FullScreen>;
  }
  if (phase === 'st-login') {
    return (
      <AuthCtx.Provider value={{ user, enableAuth, authReady: false }}>
        <Login onSuccess={() => setLoginTick((v) => v + 1)} />
      </AuthCtx.Provider>
    );
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
  return <AuthCtx.Provider value={{ user, enableAuth, authReady: phase === 'ready' }}>{children}</AuthCtx.Provider>;
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