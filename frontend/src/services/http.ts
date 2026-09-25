/**
 * 统一 axios 客户端工厂：token 注入 + 401 刷新重放 + 统一错误提示。
 *
 * 所有服务层（/api/v1、/api/v2、/api/data-intelligence）与个别组件
 * 一律通过 createApiClient 创建实例，不再各自 `import axios` 裸建，
 * 保证认证与错误处理行为一致（收敛前存在 5 处绕行 + 1 处自管 token）。
 *
 * 权限重构T4（design §4.4 🛠R2）：token 源切 ST 会话（auth/st）；401 时先
 * POST /auth/session/refresh 换新 access_token 并重放原请求，仍失败才清会话
 * 跳 /login——自研登录页无 web SDK，1h access token 必须自管刷新。刷新单飞
 * （并发 401 共享同一次 refresh），防风暴。
 */
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { getAccessToken, getRefreshToken, saveSession, clearSession } from '../auth/st';
import { message } from 'antd';

/** 扩展 axios 请求配置：`silent: true` 跳过统一错误提示（供已自带精细报错的调用方使用） */
declare module 'axios' {
  export interface AxiosRequestConfig {
    silent?: boolean;
    /** 内部标记：本请求是 refresh 重放——再 401 不再二次刷新 */
    _stReplayed?: boolean;
  }
}

export interface ApiClientOptions {
  timeout?: number;
}

const REFRESH_PATH = '/api/v1/auth/session/refresh';

let refreshing: Promise<string | null> | null = null;

/** 单飞刷新：并发 401 共享一次 refresh 调用。成功返回新 access_token。 */
function refreshOnce(): Promise<string | null> {
  if (!refreshing) {
    refreshing = axios
      .post(REFRESH_PATH, { refresh_token: getRefreshToken() }, { silent: true })
      .then((r) => {
        const at = r?.data?.data?.access_token || '';
        const rt = r?.data?.data?.refresh_token || getRefreshToken();
        if (at) saveSession(at, rt);
        return at || null;
      })
      .catch(() => null)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

/** 对外暴露：有 refresh token 时尝试续期（AuthGate 冷启动用）。 */
export async function tryRefresh(): Promise<boolean> {
  if (!getRefreshToken()) return false;
  return (await refreshOnce()) !== null;
}

export function createApiClient(baseURL: string, options: ApiClientOptions = {}): AxiosInstance {
  const instance: AxiosInstance = axios.create({ baseURL, timeout: options.timeout });

  // ST access_token 自动注入（Bearer）
  instance.interceptors.request.use((config) => {
    const t = getAccessToken();
    if (t) {
      config.headers = config.headers || {};
      (config.headers as any)['Authorization'] = `Bearer ${t}`;
    }
    return config;
  });

  instance.interceptors.response.use(
    (resp) => resp,
    async (error) => {
      const cfg = (error?.config || {}) as AxiosRequestConfig;
      const status = error?.response?.status;

      // 401 → 先刷新重放一次；仍失败才清会话跳登录（🛠R2）
      if (status === 401 && !cfg._stReplayed && !String(cfg.url || '').includes('session/refresh')) {
        const newToken = await refreshOnce();
        if (newToken) {
          const replayCfg: AxiosRequestConfig = {
            ...cfg,
            _stReplayed: true,
            headers: { ...(cfg.headers as any), Authorization: `Bearer ${newToken}` },
          };
          return instance.request(replayCfg);
        }
        clearSession();
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      } else if (status === 401) {
        clearSession();
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      } else if (!(cfg as AxiosRequestConfig).silent) {
        const detail =
          error?.response?.data?.detail ||
          error?.response?.data?.message ||
          error?.message ||
          '请求失败';
        message.error(detail);
      }
      return Promise.reject(error);
    }
  );

  return instance;
}

/** 平台主实例（/api/v1）——api.ts 等服务层消费。 */
export const v1Api = createApiClient('/api/v1');

export default v1Api;
