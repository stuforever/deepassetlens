/**
 * M22 部署版本感知工具层（D1/D2/D3 + Q4 共用）——原仓 lib/h5-version.ts 1:1 移植。
 */

/** 从 HTML 里提取 dt-build meta 内容（仅支持 name 在前的规范形态，注入器保证）。 */
export function extractDtBuild(html: string): string {
  if (!html) return "";
  const m = /<meta\s+name=["']dt-build["']\s+content=["']([^"']*)["']/i.exec(html);
  return m?.[1] || "";
}

/** Service Worker 的 NEW_VERSION 广播消息判定（H5Shell 黄条触发条件）。 */
export function isNewVersionMessage(data: unknown): boolean {
  if (typeof data !== "object" || data === null) return false;
  return (data as { type?: unknown }).type === "NEW_VERSION";
}

const PRIVATE_HOST_RE =
  /^(localhost$|127\.\d+\.\d+\.\d+$|10\.\d+\.\d+\.\d+$|192\.168\.\d+\.\d+$|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+$)/i;

/** Q4：URL 是否指向内网地址（公网设备打不开 → 分享页黄条警示）。 */
export function isIntranetUrl(raw: string): boolean {
  if (!raw) return false;
  try {
    const url = new URL(raw);
    return PRIVATE_HOST_RE.test(url.hostname);
  } catch {
    return false;
  }
}
