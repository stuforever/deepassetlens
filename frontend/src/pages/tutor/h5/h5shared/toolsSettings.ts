/**
 * 复刻自 DeepTutor 原仓 web/lib/tools-settings.ts（整件 1:1）。
 * 替换点：apiFetch(apiUrl("/api/v1/tools")) → fetch('/api/v1/tools')（批8 同规则）。
 */
export interface ToolSettingsResponse {
  enabled_optional_tools: string[];
}

let cached: Promise<string[]> | null = null;

async function fetchEnabledOptionalTools(): Promise<string[]> {
  const res = await fetch("/api/v1/tools");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const payload = (await res.json()) as ToolSettingsResponse;
  return Array.isArray(payload.enabled_optional_tools)
    ? payload.enabled_optional_tools.slice()
    : [];
}

/** Read the user's saved set of enabled toggleable tools.
 *  Cached at module scope so multiple consumers on the same page share one
 *  network round-trip; call ``refreshEnabledOptionalTools`` to bust. */
export async function getEnabledOptionalTools(options?: {
  force?: boolean;
}): Promise<string[]> {
  if (options?.force || cached === null) {
    cached = fetchEnabledOptionalTools().catch((err) => {
      cached = null;
      throw err;
    });
  }
  return cached.then((list) => list.slice());
}

export function invalidateEnabledOptionalToolsCache(): void {
  cached = null;
}
