import { apiFetch, apiUrl } from "./api";
import { invalidateClientCache, withClientCache } from "./client-cache";

const PERSONAS_CACHE_PREFIX = "personas:";

export type PersonaSource = "user" | "admin";

export interface PersonaInfo {
  name: string;
  description: string;
  source: PersonaSource;
  read_only: boolean;
}

export interface PersonaDetail extends PersonaInfo {
  content: string;
}

export interface CreatePersonaPayload {
  name: string;
  description: string;
  content: string;
}

export interface UpdatePersonaPayload {
  description?: string;
  content?: string;
  rename_to?: string;
}

function normalizeSource(raw: unknown): PersonaSource {
  return raw === "admin" ? "admin" : "user";
}

async function asJson(response: Response) {
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  // R5批④：204/205 与空响应体兜底——deletePersona 等空体写操作不再被误判为失败
  if (response.status === 204 || response.status === 205) return undefined;
  const text = await response.text();
  if (!text.trim()) return undefined;
  return JSON.parse(text);
}

function normalizeInfo(item: {
  name?: unknown;
  description?: unknown;
  source?: unknown;
  read_only?: unknown;
}): PersonaInfo {
  return {
    name: String(item?.name ?? ""),
    description: String(item?.description ?? ""),
    source: normalizeSource(item?.source),
    read_only: Boolean(item?.read_only),
  };
}

export async function listPersonas(options?: {
  force?: boolean;
}): Promise<PersonaInfo[]> {
  return withClientCache<PersonaInfo[]>(
    `${PERSONAS_CACHE_PREFIX}list`,
    async () => {
      const response = await apiFetch(apiUrl("/api/v1/personas/list"), {
        cache: "no-store",
      });
      const data = await asJson(response);
      const items = Array.isArray(data?.personas) ? data.personas : [];
      return items.map(normalizeInfo);
    },
    { force: options?.force },
  );
}

export async function getPersona(name: string): Promise<PersonaDetail> {
  const response = await apiFetch(
    apiUrl(`/api/v1/personas/${encodeURIComponent(name)}`),
    {
      cache: "no-store",
    },
  );
  const data = await asJson(response);
  return {
    ...normalizeInfo({ ...data, name: data?.name ?? name }),
    content: String(data?.content ?? ""),
  };
}

export async function createPersona(
  payload: CreatePersonaPayload,
): Promise<PersonaInfo> {
  const response = await apiFetch(apiUrl("/api/v1/personas/create"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: payload.name,
      description: payload.description,
      content: payload.content,
    }),
  });
  const data = await asJson(response);
  invalidatePersonasCache();
  return normalizeInfo({ ...data, name: data?.name ?? payload.name });
}

export async function updatePersona(
  name: string,
  payload: UpdatePersonaPayload,
): Promise<PersonaInfo> {
  const response = await apiFetch(
    apiUrl(`/api/v1/personas/${encodeURIComponent(name)}`),
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  const data = await asJson(response);
  invalidatePersonasCache();
  return normalizeInfo({ ...data, name: data?.name ?? name });
}

export async function deletePersona(name: string): Promise<void> {
  const response = await apiFetch(
    apiUrl(`/api/v1/personas/${encodeURIComponent(name)}`),
    {
      method: "DELETE",
    },
  );
  await asJson(response);
  invalidatePersonasCache();
}

export function invalidatePersonasCache() {
  invalidateClientCache(PERSONAS_CACHE_PREFIX);
}
