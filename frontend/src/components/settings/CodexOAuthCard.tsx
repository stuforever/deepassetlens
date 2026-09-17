/**
 * 复刻自 DeepTutor 原仓 web/components/settings/CodexOAuthCard.tsx（整件 1:1，批5 5.2）。
 * 替换点：
 * - 去 "use client"；react-i18next → 本地 zh 消息表 + 插值 translate()：
 *   源件全部 t() 键均为 "codex.oauth.*" 运行时键（含 lib/codex-oauth 返回的状态/错误键），
 *   中文文案逐条照抄源 web/locales/zh/app.json L540-L572，{{port}}/{{seconds}}/{{count}} 同步插值；
 * - "@/components/ui/Button"（原仓自研按钮）→ antd Button：
 *   size="sm"→size="small"，variant 缺省→type="primary"，variant="secondary"→default，
 *   variant="danger"→danger，loading/disabled/icon 语义一一对应；
 * - "@/lib/codex-oauth" → "../../lib/codex-oauth"（并行批同步落盘，按名 import）；
 * - Tailwind 类逐项换为内联样式，颜色用原仓语义 var(--xxx, 兜底值) 承载
 *   （与同批 Toggle.tsx 口径一致）；amber-600 文案色用字面 #d97706。
 * lucide-react→antd 图标登记：
 *   ShieldCheck → SafetyCertificateOutlined；ExternalLink → ExportOutlined；
 *   RefreshCw → SyncOutlined；Unplug → DisconnectOutlined。
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "antd";
import {
  DisconnectOutlined,
  ExportOutlined,
  SafetyCertificateOutlined,
  SyncOutlined,
} from "@ant-design/icons";

import {
  buildSshForwardCommand,
  cancelCodexLogin,
  codexRemoteGuidance,
  CodexOAuthApiError,
  codexErrorMessageKey,
  codexStatusMessageKey,
  getCodexStatus,
  isLoopbackHostname,
  logoutCodex,
  refreshCodexModels,
  shouldPollCodexStatus,
  startCodexLogin,
  type CodexLoginStart,
  type CodexOAuthStatus,
} from "../../lib/codex-oauth";

import { useSettings } from "./SettingsContext";

// ─── zh 消息表（源 web/locales/zh/app.json 逐条照抄，t('key')→中文规约承载）─────
const ZH_MESSAGES: Record<string, string> = {
  "codex.oauth.activated": "Codex 已连接，并已设为当前模型。",
  "codex.oauth.callbackAddress": "OAuth 回调地址",
  "codex.oauth.callbackMissing":
    "DeepTutor 服务器未在 localhost:{{port}} 收到 OAuth 回调。远程部署请保持 SSH 隧道运行并重试。",
  "codex.oauth.callbackMissingUnknown":
    "DeepTutor 服务器未收到 OAuth 回调。请重新开始登录，并按照新一轮显示的授权说明操作。",
  "codex.oauth.callbackUnavailable":
    "DeepTutor 无法监听 localhost:1455 和 localhost:1457。请释放其中一个端口后重试。",
  "codex.oauth.cancel": "取消",
  "codex.oauth.cancelled": "已取消 Codex 登录。",
  "codex.oauth.catalogFailed": "无法刷新 Codex 模型目录，登录状态和当前模型均已保留。",
  "codex.oauth.commandCopied": "SSH 隧道命令已复制。",
  "codex.oauth.connected": "Codex 已连接。",
  "codex.oauth.copyCommand": "复制命令",
  "codex.oauth.copyFailed": "无法复制 SSH 隧道命令。",
  "codex.oauth.denied": "Codex 授权被拒绝。",
  "codex.oauth.disconnected": "Codex 尚未连接。",
  "codex.oauth.experimental": "实验性连接：上游 Codex 兼容接口未来可能变化。",
  "codex.oauth.expired": "Codex 登录已超时，请重新开始。",
  "codex.oauth.expiresIn": "剩余 {{seconds}} 秒。",
  "codex.oauth.inferenceActive": "请等待当前 Codex 回复结束后再退出登录。",
  "codex.oauth.invalidResponse":
    "DeepTutor OAuth 接口返回了异常响应。请检查反向代理是否正确转发 /api/v1/settings/providers/openai-codex/。",
  "codex.oauth.isolated": "凭据仅由 DeepTutor 保存，不会读取或修改 Codex CLI 的登录状态。",
  "codex.oauth.localOnly": "本地访问会直接打开授权页面；远程访问会先显示 SSH 隧道命令。",
  "codex.oauth.logout": "退出登录",
  "codex.oauth.modelCount": "模型：{{count}}",
  "codex.oauth.openAuthorization": "打开授权页面",
  "codex.oauth.ownerBound":
    "使用你本人的 ChatGPT 套餐登录。凭据仅归你的账号所有，不会共享给本部署的其他用户。",
  "codex.oauth.refresh": "刷新模型",
  "codex.oauth.reloadDeferred":
    "Codex 已连接。应用当前未保存的更改后即可在列表中看到它的模型。",
  "codex.oauth.remoteSteps": "先运行下方命令并保持 SSH 隧道运行，再点击“打开授权页面”。",
  "codex.oauth.remoteTitle": "远程 OAuth 授权",
  "codex.oauth.requestFailed": "Codex 请求失败，请重试。",
  "codex.oauth.signIn": "使用 Codex 登录",
  "codex.oauth.title": "OpenAI Codex OAuth",
  "codex.oauth.waiting": "等待浏览器授权…",
};

/** 原仓 t(key, params) 的等价承载：查 zh 表 + {{name}} 插值；未收录键原样返回。 */
function translate(key: string, params?: Record<string, unknown>): string {
  let text = ZH_MESSAGES[key] ?? key;
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      text = text.replace(
        new RegExp(`{{\\s*${name}\\s*}}`, "g"),
        String(value),
      );
    }
  }
  return text;
}

export function CodexOAuthCard() {
  const t = translate;
  const { reloadSettings, hasUnsavedChanges, setToast } = useSettings();
  const [status, setStatus] = useState<CodexOAuthStatus | null>(null);
  const [pending, setPending] = useState(false);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [pollTick, setPollTick] = useState(0);
  const [loginStart, setLoginStart] = useState<CodexLoginStart | null>(null);
  const reloadedOperation = useRef<string | null>(null);
  const statusRequestSequence = useRef(0);
  const remoteAccess =
    typeof window !== "undefined" &&
    !isLoopbackHostname(window.location.hostname);

  const recordStatus = useCallback((nextStatus: CodexOAuthStatus) => {
    setStatus(nextStatus);
    const terminalOperation =
      nextStatus.operation_state === "completed" ||
      nextStatus.operation_state === "cancelled" ||
      nextStatus.operation_state === "expired" ||
      nextStatus.operation_state === "failed";
    if (!terminalOperation) return;
    setLoginStart((loginStart) =>
      loginStart && nextStatus.operation_id === loginStart.operation_id
        ? null
        : loginStart,
    );
  }, []);

  const invalidateStatusRequests = useCallback(() => {
    statusRequestSequence.current += 1;
  }, []);

  const loadStatus = useCallback(
    async (shouldApply: () => boolean = () => true) => {
      statusRequestSequence.current += 1;
      const requestSequence = statusRequestSequence.current;
      try {
        const next = await getCodexStatus();
        if (
          requestSequence !== statusRequestSequence.current ||
          !shouldApply()
        ) {
          return null;
        }
        recordStatus(next);
        setErrorKey(null);
        return next;
      } catch (error) {
        if (
          requestSequence !== statusRequestSequence.current ||
          !shouldApply()
        ) {
          return null;
        }
        setErrorKey(
          codexErrorMessageKey(
            error instanceof CodexOAuthApiError ? error.code : null,
          ),
        );
        return null;
      }
    },
    [recordStatus],
  );

  useEffect(() => {
    let cancelled = false;
    void loadStatus(() => !cancelled);
    return () => {
      cancelled = true;
      invalidateStatusRequests();
    };
  }, [invalidateStatusRequests, loadStatus]);

  useEffect(() => {
    if (pending || !status || !shouldPollCodexStatus(status)) return;
    // pollTick, not the status object, is what schedules the next poll: a failed
    // request leaves `status` identical, and keying the timer off it alone would
    // strand the card on "waiting" forever after one dropped response.
    let cancelled = false;
    const timer = window.setTimeout(() => {
      void (async () => {
        await loadStatus(() => !cancelled);
        if (!cancelled) setPollTick((tick) => tick + 1);
      })();
    }, 1_000);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [loadStatus, pending, status, pollTick]);

  // Reloading replaces the whole catalog draft, so this must never run behind
  // the operator's back while they have unsaved edits open on another provider.
  const syncCatalog = useCallback(async () => {
    if (hasUnsavedChanges) {
      setToast(t("codex.oauth.reloadDeferred"));
      return;
    }
    await reloadSettings();
  }, [hasUnsavedChanges, reloadSettings, setToast, t]);

  useEffect(() => {
    if (
      status?.operation_state !== "completed" ||
      !status.operation_id ||
      reloadedOperation.current === status.operation_id
    ) {
      return;
    }
    reloadedOperation.current = status.operation_id;
    void syncCatalog();
  }, [syncCatalog, status]);

  const localSignIn = async () => {
    invalidateStatusRequests();
    const authWindow = window.open("about:blank", "_blank", "popup");
    if (authWindow) authWindow.opener = null;
    setPending(true);
    setErrorKey(null);
    try {
      const started = await startCodexLogin();
      if (authWindow) {
        authWindow.location.replace(started.authorize_url);
      } else {
        window.location.assign(started.authorize_url);
      }
      await loadStatus();
    } catch (error) {
      authWindow?.close();
      setErrorKey(
        codexErrorMessageKey(
          error instanceof CodexOAuthApiError ? error.code : null,
        ),
      );
    } finally {
      setPending(false);
    }
  };

  const remoteSignIn = async () => {
    invalidateStatusRequests();
    setPending(true);
    setErrorKey(null);
    try {
      const started = await startCodexLogin();
      setLoginStart(started);
      await loadStatus();
    } catch (error) {
      setErrorKey(
        codexErrorMessageKey(
          error instanceof CodexOAuthApiError ? error.code : null,
        ),
      );
    } finally {
      setPending(false);
    }
  };

  const signIn = remoteAccess ? remoteSignIn : localSignIn;

  const remoteGuidance = codexRemoteGuidance(status, loginStart);
  const sshCommand = remoteGuidance
    ? buildSshForwardCommand(
        remoteGuidance.callback_port,
        window.location.hostname,
        remoteGuidance.callback_forward_port,
      )
    : "";

  const copyCommand = async () => {
    if (!sshCommand) return;
    try {
      await navigator.clipboard.writeText(sshCommand);
      setToast(t("codex.oauth.commandCopied"));
    } catch {
      setToast(t("codex.oauth.copyFailed"));
    }
  };

  const openAuthorization = () => {
    if (!remoteGuidance) return;
    window.open(remoteGuidance.authorize_url, "_blank", "noopener");
  };

  const cancel = async () => {
    invalidateStatusRequests();
    setPending(true);
    try {
      const nextStatus = await cancelCodexLogin();
      invalidateStatusRequests();
      recordStatus(nextStatus);
    } catch (error) {
      setErrorKey(
        codexErrorMessageKey(
          error instanceof CodexOAuthApiError ? error.code : null,
        ),
      );
    } finally {
      setLoginStart(null);
      setPending(false);
    }
  };

  const refresh = async () => {
    invalidateStatusRequests();
    setPending(true);
    try {
      const nextStatus = await refreshCodexModels();
      invalidateStatusRequests();
      recordStatus(nextStatus);
      await syncCatalog();
      setErrorKey(null);
    } catch (error) {
      setErrorKey(
        codexErrorMessageKey(
          error instanceof CodexOAuthApiError ? error.code : null,
        ),
      );
    } finally {
      setPending(false);
    }
  };

  const logout = async () => {
    invalidateStatusRequests();
    setPending(true);
    try {
      const nextStatus = await logoutCodex();
      invalidateStatusRequests();
      recordStatus(nextStatus);
      setLoginStart(null);
      await syncCatalog();
      setErrorKey(null);
    } catch (error) {
      setErrorKey(
        codexErrorMessageKey(
          error instanceof CodexOAuthApiError ? error.code : null,
        ),
      );
    } finally {
      setPending(false);
    }
  };

  const polling = Boolean(status && shouldPollCodexStatus(status));
  const connected = status?.connection === "connected";
  const messageKey =
    errorKey || (status ? codexStatusMessageKey(status) : null);
  const callbackPort = status?.callback_port ?? loginStart?.callback_port;
  const displayMessageKey =
    messageKey === "codex.oauth.callbackMissing" && callbackPort == null
      ? "codex.oauth.callbackMissingUnknown"
      : messageKey;

  return (
    <section
      data-testid="codex-oauth-card"
      style={{
        borderRadius: 12,
        border: "1px solid var(--border, #e5e7eb)",
        background: "var(--muted, rgba(0, 0, 0, 0.03))",
        padding: 16,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <SafetyCertificateOutlined
          style={{
            marginTop: 2,
            fontSize: 20,
            color: "var(--primary, #2563eb)",
          }}
        />
        <div style={{ minWidth: 0, flex: 1 }}>
          <p style={{ margin: 0, fontSize: 14, fontWeight: 500 }}>
            {t("codex.oauth.title")}
          </p>
          <p
            style={{
              margin: 0,
              marginTop: 4,
              fontSize: 12,
              color: "var(--muted-foreground, #64748b)",
            }}
          >
            {t("codex.oauth.isolated")}
          </p>
          <p
            style={{
              margin: 0,
              marginTop: 4,
              fontSize: 12,
              color: "var(--muted-foreground, #64748b)",
            }}
          >
            {t("codex.oauth.ownerBound")}
          </p>
          {!connected && (
            <p
              style={{
                margin: 0,
                marginTop: 4,
                fontSize: 12,
                color: "var(--muted-foreground, #64748b)",
              }}
            >
              {t("codex.oauth.localOnly")}
            </p>
          )}
          <p
            style={{
              margin: 0,
              marginTop: 4,
              fontSize: 12,
              color: "var(--amber-600, #d97706)",
            }}
          >
            {t("codex.oauth.experimental")}
          </p>
          {displayMessageKey && (
            <p style={{ margin: 0, marginTop: 12, fontSize: 14 }}>
              {t(displayMessageKey, {
                port: callbackPort,
              })}
            </p>
          )}
          {connected && status?.model_count !== undefined && (
            <p
              style={{
                margin: 0,
                marginTop: 4,
                fontSize: 12,
                color: "var(--muted-foreground, #64748b)",
              }}
            >
              {t("codex.oauth.modelCount", { count: status.model_count })}
            </p>
          )}
          {remoteAccess && remoteGuidance && (
            <div
              style={{
                marginTop: 16,
                borderRadius: 8,
                border: "1px solid var(--border, #e5e7eb)",
                background: "var(--background, #ffffff)",
                padding: 12,
              }}
            >
              <p style={{ margin: 0, fontSize: 14, fontWeight: 500 }}>
                {t("codex.oauth.remoteTitle")}
              </p>
              <p
                style={{
                  margin: 0,
                  marginTop: 8,
                  fontSize: 12,
                  color: "var(--muted-foreground, #64748b)",
                }}
              >
                {t("codex.oauth.remoteSteps")}
              </p>
              <p style={{ margin: 0, marginTop: 12, fontSize: 12, fontWeight: 500 }}>
                {t("codex.oauth.callbackAddress")}
              </p>
              <code
                style={{
                  display: "block",
                  marginTop: 4,
                  wordBreak: "break-all",
                  fontSize: 12,
                }}
              >
                {remoteGuidance.redirect_uri}
              </code>
              <p
                style={{
                  margin: 0,
                  marginTop: 8,
                  fontSize: 12,
                  color: "var(--muted-foreground, #64748b)",
                }}
              >
                {t("codex.oauth.expiresIn", {
                  seconds: remoteGuidance.expires_in,
                })}
              </p>
              <pre
                style={{
                  overflowX: "auto",
                  borderRadius: 6,
                  background: "var(--muted, rgba(0, 0, 0, 0.03))",
                  padding: 8,
                  fontSize: 12,
                  margin: "12px 0 0",
                }}
              >
                <code>{sshCommand}</code>
              </pre>
              <div
                style={{
                  marginTop: 12,
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 8,
                }}
              >
                <Button
                  size="small"
                  onClick={() => void copyCommand()}
                >
                  {t("codex.oauth.copyCommand")}
                </Button>
                <Button
                  size="small"
                  onClick={openAuthorization}
                  icon={<ExportOutlined />}
                >
                  {t("codex.oauth.openAuthorization")}
                </Button>
                <Button
                  size="small"
                  disabled={pending}
                  onClick={() => void cancel()}
                >
                  {t("codex.oauth.cancel")}
                </Button>
              </div>
            </div>
          )}
          <div
            style={{
              marginTop: 16,
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
            }}
          >
            {!connected && !polling && (
              <Button
                type="primary"
                size="small"
                loading={pending}
                onClick={() => void signIn()}
                icon={<ExportOutlined />}
              >
                {t("codex.oauth.signIn")}
              </Button>
            )}
            {polling && !(remoteAccess && remoteGuidance) && (
              <Button
                size="small"
                disabled={pending}
                onClick={() => void cancel()}
              >
                {t("codex.oauth.cancel")}
              </Button>
            )}
            {connected && (
              <>
                <Button
                  size="small"
                  loading={pending}
                  onClick={() => void refresh()}
                  icon={<SyncOutlined />}
                >
                  {t("codex.oauth.refresh")}
                </Button>
                <Button
                  danger
                  size="small"
                  disabled={pending}
                  onClick={() => void logout()}
                  icon={<DisconnectOutlined />}
                >
                  {t("codex.oauth.logout")}
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
