/**
 * IA批6 lib 补件：1:1 移植自 DeepTutor web/hooks/useAuthStatus.ts。
 * 运行时认证状态（/api/v1/auth/status）：enabled/authenticated/isAdmin/loading；
 * in-flight 共享（同页多消费者只发一次请求）。fetchAuthStatus ← ../lib/auth（tupu 同名 1:1 件）。
 */
import { useEffect, useState } from "react";
import { fetchAuthStatus } from "../lib/auth";

export interface AuthStatusState {
  /** Whether auth is enabled on the backend. */
  enabled: boolean;
  /** Whether the current session is authenticated. */
  authenticated: boolean;
  /** Whether the authenticated user is an admin. */
  isAdmin: boolean;
  /** True until the first status fetch resolves. */
  loading: boolean;
}

const INITIAL: AuthStatusState = {
  enabled: false,
  authenticated: false,
  isAdmin: false,
  loading: true,
};

/**
 * Resolve auth state at runtime from the backend (`/api/v1/auth/status`).
 *
 * The frontend bundle is URL- and auth-agnostic: the auth toggle is a runtime
 * setting read from the backend, never baked into the build. Components that
 * need to know whether auth is on use this hook instead of a build-time
 * constant.
 */
// Several components mount this hook at once. Share a single in-flight request
// so a page load makes one /api/v1/auth/status call instead of one per
// consumer, and clear it once settled so a later mount fetches fresh.
let inflight: Promise<AuthStatusState> | null = null;

function loadAuthStatus(): Promise<AuthStatusState> {
  if (!inflight) {
    // TS4.9 无自引用收窄豁免：先落局部 const 再赋 inflight（语义等价）。
    const p = fetchAuthStatus()
      .then((status) => ({
        enabled: Boolean(status?.enabled),
        authenticated: Boolean(status?.authenticated),
        isAdmin: status?.role === "admin",
        loading: false,
      }))
      .finally(() => {
        inflight = null;
      });
    inflight = p;
    return p;
  }
  return inflight;
}

export function useAuthStatus(): AuthStatusState {
  const [state, setState] = useState<AuthStatusState>(INITIAL);

  useEffect(() => {
    let alive = true;
    loadAuthStatus().then((next) => {
      if (alive) setState(next);
    });
    return () => {
      alive = false;
    };
  }, []);

  return state;
}
