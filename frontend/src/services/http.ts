/**
 * 统一 axios 客户端工厂：token 注入 + 401 跳登录 + 统一错误提示。
 *
 * 所有服务层（/api/v1、/api/v2、/api/data-intelligence）与个别组件
 * 一律通过 createApiClient 创建实例，不再各自 `import axios` 裸建，
 * 保证认证与错误处理行为一致（收敛前存在 5 处绕行 + 1 处自管 token）。
 */
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { getStoredToken, clearToken, isTokenValid } from '../auth/oidc';
import { message } from 'antd';

/** 扩展 axios 请求配置：`silent: true` 跳过统一错误提示（供已自带精细报错的调用方使用） */
declare module 'axios' {
  export interface AxiosRequestConfig {
    silent?: boolean;
  }
}

export interface ApiClientOptions {
  timeout?: number;
}

export function createApiClient(baseURL: string, options: ApiClientOptions = {}): AxiosInstance {
  const instance: AxiosInstance = axios.create({ baseURL, timeout: options.timeout });

  // Authentik Bearer 自动注入
  instance.interceptors.request.use((config) => {
    const t = getStoredToken();
    if (t && isTokenValid(t)) {
      config.headers = config.headers || {};
      (config.headers as any)['Authorization'] = `${t.token_type} ${t.access_token}`;
    }
    return config;
  });

  // 401 → 清 token 跳登录；其余错误 → 统一 message.error 兜底（silent 跳过）
  instance.interceptors.response.use(
    (resp) => resp,
    (error) => {
      if (error?.response?.status === 401) {
        clearToken();
        // 不 reload 主流程内的所有请求，让 AuthGate 重入；或硬跳一次首页
        if (window.location.pathname !== '/auth/callback') {
          window.location.href = '/';
        }
      } else if (!(error?.config as AxiosRequestConfig | undefined)?.silent) {
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

/** /api/v1 共享实例（api.ts 默认导出即此实例） */
export const v1Api = createApiClient('/api/v1');

export default v1Api;
