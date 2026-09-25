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
import { getAccessToken, getRefreshToken, isAccessTokenFresh } from './st';
import { tryRefresh } from '../services/http';
import Login from '../pages/Login';

export interface AuthContext {
  user: any | null;
  enableAuth: boolean;
  // 附件四 A-2：鉴权配置是否就绪（phase==='ready'）——守卫据此区分「加载中」与「确定非 admin」，
  // 防止 user 未就绪时闪跳重定向（admin 页被 Navigate 打断回门户）。
  authReady: boolean;
}

export const AuthCtx = React.createContext<AuthContext>({ user: null, enableAuth: false, authReady: false });

interface Props {
  children: React.ReactNode;
}

const CALLBACK_PATH = '/auth/callback';

const AuthGate: React.FC<Props> = ({ children }) => {
  const [phase, setPhase] = useState<'init' | 'login' | 'st-login' | 'exchange' | 'ready' | 'error'>('init');
  const [errMsg, setErrMsg] = useState<string>('');
  const [user, setUser] = useState<any | null>(null);
  const [enableAuth, setEnableAuth] = useState<boolean>(false);
  const [loginTick, setLoginTick] = useState(0); // T4：登录成功后重跑初始化

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

        // 权限重构T4：ST provider——自研登录页（不再跳 Authentik）
        if (cfg.provider === 'supertokens') {
          let t = getAccessToken();
          // access token 过期且有 refresh → 先续期（验收 #2：会话刷新不踢登录）
          if (t && !isAccessTokenFresh(t) && getRefreshToken()) {
            if (await tryRefresh()) t = getAccessToken();
          }
          if (t && isAccessTokenFresh(t)) {
            const me = await fetchMe();
            setUser(me);
            setPhase('ready');
            return;
          }
          // 无 access token 但 refresh 在 → 续期后恢复会话
          if (!t && getRefreshToken()) {
            const refreshed = await tryRefresh();
            if (refreshed) {
              const me = await fetchMe();
              setUser(me);
              setPhase('ready');
              return;
            }
          }
          setPhase('st-login');
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
  }, [loginTick]);

  if (phase === 'init') {
    return <FullScreen><Spin size="large" /><div style={{ marginTop: 12, fontSize: 13, color: "var(--text-tertiary)" }}>加载权限配置...</div></FullScreen>;
  }
  if (phase === 'login') {
    return <FullScreen><Spin size="large" /><div style={{ marginTop: 12, fontSize: 13, color: "var(--text-tertiary)" }}>跳转 Authentik 登录...</div></FullScreen>;
  }
  if (phase === 'st-login') {
    // 权限重构T4：ST provider 登录态——自研登录页（成功后重跑初始化）
    return (
      <AuthCtx.Provider value={{ user, enableAuth, authReady: false }}>
        <Login onSuccess={() => setLoginTick((v) => v + 1)} />
      </AuthCtx.Provider>
    );
  }
  if (phase === 'exchange') {
    return <FullScreen><Spin size="large" /><div style={{ marginTop: 12, fontSize: 13, color: "var(--text-tertiary)" }}>登录态交换中...</div></FullScreen>;
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
