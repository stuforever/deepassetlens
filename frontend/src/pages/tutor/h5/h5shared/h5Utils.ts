/**
 * H5 移动端共享工具（design: H5 自包含闭环 + URL 用户标识）——原仓 lib/h5-utils.ts 1:1 移植。
 *
 * H5 用 `?u=<用户标识>` 区分使用者（如家长扫码后 /h5?u=小明）。
 * 所有 H5 内部路由透传 u，后端按 u 取对应学情/会话。
 * 路由前缀映射：原 /h5/* → tupu /e/tutor/h5/*。
 */

/** 从当前 URL 读取用户标识 u（可能为空）。 */
export function getH5User(): string {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams(window.location.search);
  return params.get("u") || params.get("openid") || "";
}

/** 把 u 透传到目标路径：/e/tutor/h5/learn -> /e/tutor/h5/learn?u=小明 */
export function withU(path: string, u?: string): string {
  const uid = u ?? getH5User();
  if (!uid) return path;
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}u=${encodeURIComponent(uid)}`;
}

/** 拼接后端 API 的 u 参数查询串（含已有 qs 时追加）。 */
export function uQuery(u?: string, existingQs = ""): string {
  const uid = u ?? getH5User();
  if (!uid) return existingQs;
  const sep = existingQs.includes("?") ? "&" : "?";
  return `${existingQs}${sep}u=${encodeURIComponent(uid)}`;
}

/** 当前页面完整 URL（含 u），用于生成分享二维码。 */
export function currentShareUrl(u?: string): string {
  if (typeof window === "undefined") return "";
  const base = window.location.origin + window.location.pathname;
  return withU(base, u);
}
