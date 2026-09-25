/**
 * 三轨M16(批15) C3 传输层补丁：Bearer 注入单点（豁免类——总编排 Global Constraints 授权）。
 *
 * 照 H5Shell.tsx:22-40 既有补丁模式（X-Access-Code 块不动，另起同款）：
 * 全局 fetch wrapper——auth=1 且 localStorage 有有效 token 时，给所有
 * 未携带 Authorization 的 fetch 请求注入 Bearer header。
 *
 * 消费面：dataIntelligenceApi.ts / knowledge-api.ts / partners-api.ts 等裸 fetch 路径
 * （http.ts axios 拦截器已有 Bearer 注入——本件补 fetch 缺口）。
 *
 * 安装点：expertPages.ts 顶部（模块加载期一次执行）。
 * 幂等：已有 Authorization header 的请求不重复注入。
 */
// 权限重构T7：token 源切 ST 会话（oidc.ts 退役）
import { getAccessToken, isAccessTokenFresh } from "./auth/st";

if (typeof window !== "undefined") {
  const _origFetch = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const t = getAccessToken();
    if (t && isAccessTokenFresh(t)) {
      const headers = new Headers(init?.headers);
      if (!headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${t}`);
        init = { ...init, headers };
      }
    }
    return _origFetch(input, init);
  };
}
