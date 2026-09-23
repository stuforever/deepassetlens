/**
 * Map imported sessions (which live on the backend) back to the client-side
 * agents that own them. An agent's identity lives in IndexedDB, so this is how
 * both the Space management page and the chat reference picker decide which
 * conversations belong to which named agent.
 */

import type { SessionSummary } from "../session-api";
import type { ImportAgent } from "./agent-store";
import { epochMsToISODate } from "./shared";
import type { AgentScope, ImportSource } from "./types";

export interface SessionImportMeta {
  source: ImportSource;
  sourceCwd: string;
  agentId?: string;
}

export function readImportMeta(
  session: SessionSummary,
): SessionImportMeta | null {
  const imp = (
    session.preferences as
      | { import?: { source?: string; source_cwd?: string; agent_id?: string } }
      | undefined
  )?.import;
  const src = imp?.source;
  if (src !== "claude_code" && src !== "codex") return null;
  return {
    source: src,
    sourceCwd: imp?.source_cwd ?? "",
    agentId: imp?.agent_id || undefined,
  };
}

/** Which selection unit a session falls under, for scope membership tests. */
export function sessionUnitKey(
  source: ImportSource,
  meta: SessionImportMeta,
  createdAtSec: number,
): string {
  return source === "codex"
    ? epochMsToISODate(createdAtSec * 1000)
    : meta.sourceCwd;
}

export function scopeContainsSession(
  scope: AgentScope,
  meta: SessionImportMeta,
  createdAtSec: number,
): boolean {
  if (scope.kind === "all") return true;
  if (scope.kind === "projects") return scope.cwds.includes(meta.sourceCwd);
  return scope.days.includes(epochMsToISODate(createdAtSec * 1000));
}

/**
 * Assign each imported session to exactly one agent: by explicit `agent_id`
 * when present, else by source + scope membership. The fallback re-attaches
 * conversations imported before the agent model and migrated legacy agents
 * (whose scope is `all`). Returns sessionId → agentId; unmatched maps to null.
 */
export function assignSessionsToAgents(
  sessions: SessionSummary[],
  agents: ImportAgent[],
): Map<string, string | null> {
  const byId = new Map(agents.map((a) => [a.id, a]));
  const out = new Map<string, string | null>();
  for (const session of sessions) {
    const sid = session.session_id || session.id;
    const meta = readImportMeta(session);
    if (!meta) {
      out.set(sid, null);
      continue;
    }
    if (meta.agentId && byId.has(meta.agentId)) {
      out.set(sid, meta.agentId);
      continue;
    }
    const matches = agents.filter(
      (a) =>
        a.source === meta.source &&
        scopeContainsSession(a.scope, meta, session.created_at),
    );
    // R5批⑨：多匹配取最具体 scope（projects>days>all）——迁移遗留 all-scope 与具体
    // scope 重叠是预期常态（见本函数文档），先匹配先得会随同步顺序漂移（all 晚到
    // 吞掉具体 agent 名下会话）
    const matchesSpecificity = { projects: 2, dates: 1, all: 0 } as const;
    const owner =
      matches.sort(
        (a, b) =>
          matchesSpecificity[b.scope.kind] - matchesSpecificity[a.scope.kind],
      )[0] ?? null;
    out.set(sid, owner?.id ?? null);
  }
  return out;
}
