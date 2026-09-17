/**
 * 网络设置（1:1 复刻自原仓 web/app/(utility)/settings/network/page.tsx）：
 * 聊天响应超时（独立小节，自取自存 localStorage）+ 状态瓦片（浏览器 API/CORS 模式/
 * 认证 Cookie/重启）+ 运行端口 + 浏览器 API base + CORS 来源 + 安全 Cookie 警示。
 * 保存走全局 Apply（registerExtension）；app-shell-storage 常量/工具复用本仓复刻件；
 * apiFetch/apiUrl → 相对路径 fetch。
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Col, Input, InputNumber, Row, Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import {
  SettingRow,
  SettingSection,
  SettingsPageHeader,
} from '../../components/settings/shared';
import { useSettings } from '../../components/settings/SettingsContext';
import {
  DEFAULT_CHAT_RESPONSE_TIMEOUT_SECONDS,
  MAX_CHAT_RESPONSE_TIMEOUT_SECONDS,
  MIN_CHAT_RESPONSE_TIMEOUT_SECONDS,
  clampChatResponseTimeout,
  writeStoredChatResponseTimeout,
} from '../tutor/h5/h5shared/appShellStorage';

type NetworkSettings = {
  backend_port: number;
  frontend_port: number;
  public_api_base: string;
  cors_origins: string[];
};

type NetworkSettingsPayload = {
  settings: NetworkSettings;
  effective: {
    backend_url: string;
    frontend_url: string;
    browser_api_base: string;
    api_base_source: string;
    cors_mode: 'explicit' | 'permissive';
    cors_origins: string[];
    allow_remote_http_origins: boolean;
  };
  auth: {
    enabled: boolean;
    cookie_secure: boolean;
    cookie_samesite: string;
    cross_site_cookie_ready: boolean;
  };
  restart_required: boolean;
};

function splitOrigins(value: string): string[] {
  return value
    .split(/[,;\n]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeDraft(payload: NetworkSettingsPayload): NetworkSettings {
  return {
    backend_port: payload.settings.backend_port,
    frontend_port: payload.settings.frontend_port,
    public_api_base: payload.settings.public_api_base || '',
    cors_origins: payload.settings.cors_origins || [],
  };
}

function DetailTile({
  label,
  value,
  tone = 'neutral',
}: {
  label: string;
  value: string;
  tone?: 'neutral' | 'ok' | 'warn';
}) {
  const dot =
    tone === 'ok' ? '#52c41a' : tone === 'warn' ? '#faad14' : '#f0f0f0';
  return (
    <div
      style={{
        borderRadius: 12,
        border: '1px solid rgba(0, 0, 0, 0.06)',
        background: '#fff',
        padding: '12px 16px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          fontSize: 11,
          fontWeight: 500,
          color: 'rgba(0, 0, 0, 0.45)',
        }}
      >
        <span style={{ width: 6, height: 6, borderRadius: 999, background: dot }} />
        {label}
      </div>
      <div
        style={{
          marginTop: 8,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          fontSize: 13,
          fontWeight: 500,
          color: 'rgba(0, 0, 0, 0.88)',
        }}
        title={value}
      >
        {value || '-'}
      </div>
    </div>
  );
}

/**
 * Per-user chat idle-timeout control. Self-contained (its own fetch + save via
 * the dedicated ``/settings/chat-response-timeout`` endpoint) and renders
 * independently of the admin network settings below, so any user can adjust it.
 * Mirrors the value to localStorage so the chat watchdog picks it up at once.
 */
function ChatResponseTimeoutSection() {
  const { registerExtension } = useSettings();
  const [seconds, setSeconds] = useState<number>(
    DEFAULT_CHAT_RESPONSE_TIMEOUT_SECONDS,
  );
  const [initial, setInitial] = useState<number>(
    DEFAULT_CHAT_RESPONSE_TIMEOUT_SECONDS,
  );
  const [message, setMessage] = useState('');

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const response = await fetch('/api/v1/settings');
        const data = (await response.json().catch(() => ({}))) as {
          ui?: { chat_response_timeout?: number };
        };
        const value = clampChatResponseTimeout(
          Number(data?.ui?.chat_response_timeout) ||
            DEFAULT_CHAT_RESPONSE_TIMEOUT_SECONDS,
        );
        if (cancelled) return;
        setSeconds(value);
        setInitial(value);
        writeStoredChatResponseTimeout(value);
      } catch {
        // keep the default
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const dirty = seconds !== initial;

  // Flush through the global Apply (top toolbar) instead of a local button.
  const secondsRef = useRef(seconds);
  secondsRef.current = seconds;
  const save = useCallback(async () => {
    setMessage('');
    try {
      const value = clampChatResponseTimeout(secondsRef.current);
      const response = await fetch('/api/v1/settings/chat-response-timeout', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_response_timeout: value }),
      });
      if (!response.ok) throw new Error('Failed to save.');
      setSeconds(value);
      setInitial(value);
      writeStoredChatResponseTimeout(value);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    registerExtension('chat-timeout', { dirty, save });
    return () => registerExtension('chat-timeout', null);
  }, [dirty, save, registerExtension]);

  return (
    <SettingSection
      title="Chat response timeout"
      description="How long chat waits for a reply before showing a timeout error. Increase it for slow tools like image or video generation."
    >
      <SettingRow
        title="Timeout (seconds)"
        description={`Between ${MIN_CHAT_RESPONSE_TIMEOUT_SECONDS} and ${MAX_CHAT_RESPONSE_TIMEOUT_SECONDS} seconds. Takes effect immediately — no restart.`}
        control={
          <InputNumber
            min={MIN_CHAT_RESPONSE_TIMEOUT_SECONDS}
            max={MAX_CHAT_RESPONSE_TIMEOUT_SECONDS}
            value={seconds}
            onChange={(v) => setSeconds(typeof v === 'number' ? v : DEFAULT_CHAT_RESPONSE_TIMEOUT_SECONDS)}
            style={{ width: 112 }}
          />
        }
      />
      {message && (
        <p
          style={{
            padding: '0 4px 12px',
            fontSize: 11.5,
            color: 'rgba(0, 0, 0, 0.45)',
          }}
        >
          {message}
        </p>
      )}
    </SettingSection>
  );
}

export default function NetworkSettingsPage() {
  const { registerExtension } = useSettings();
  const apiBasePlaceholder = 'https://api.example.com';
  const corsPlaceholder = 'https://learn.example.com\nhttp://10.0.0.5:3782';
  const [payload, setPayload] = useState<NetworkSettingsPayload | null>(null);
  const [draft, setDraft] = useState<NetworkSettings | null>(null);
  const [corsText, setCorsText] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/v1/settings/network');
        const data = (await response.json().catch(() => ({}))) as
          | NetworkSettingsPayload
          | { detail?: string };
        if (!response.ok) {
          throw new Error(
            'detail' in data && data.detail
              ? data.detail
              : '加载网络设置失败。',
          );
        }
        if (cancelled) return;
        const next = data as NetworkSettingsPayload;
        setPayload(next);
        setDraft(normalizeDraft(next));
        setCorsText((next.settings.cors_origins || []).join('\n'));
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const dirty = useMemo(() => {
    if (!payload || !draft) return false;
    const current = normalizeDraft(payload);
    return (
      current.backend_port !== draft.backend_port ||
      current.frontend_port !== draft.frontend_port ||
      current.public_api_base !== draft.public_api_base ||
      JSON.stringify(current.cors_origins) !==
        JSON.stringify(splitOrigins(corsText))
    );
  }, [corsText, draft, payload]);

  // Flush through the global Apply (top toolbar) instead of a local button.
  // Refs keep the registered ``save`` closure reading the latest draft.
  const draftRef = useRef(draft);
  draftRef.current = draft;
  const corsRef = useRef(corsText);
  corsRef.current = corsText;
  const save = useCallback(async () => {
    const current = draftRef.current;
    if (!current) return;
    setError(null);
    try {
      const response = await fetch('/api/v1/settings/network', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...current,
          cors_origins: splitOrigins(corsRef.current),
        }),
      });
      const data = (await response.json().catch(() => ({}))) as
        | NetworkSettingsPayload
        | { detail?: string };
      if (!response.ok) {
        throw new Error(
          'detail' in data && data.detail
            ? data.detail
            : '保存网络设置失败。',
        );
      }
      const next = data as NetworkSettingsPayload;
      setPayload(next);
      setDraft(normalizeDraft(next));
      setCorsText((next.settings.cors_origins || []).join('\n'));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    registerExtension('network', { dirty, save });
    return () => registerExtension('network', null);
  }, [dirty, save, registerExtension]);

  return (
    <div data-tour="tour-network">
      <SettingsPageHeader
        title="网络"
        description="配置 Docker、局域网和反向代理部署中浏览器访问后端的 API 地址与 CORS 来源。"
      />

      <p style={{ marginBottom: 28, fontSize: 12, color: 'rgba(0, 0, 0, 0.45)' }}>
        网络改动重启后生效。
      </p>

      <ChatResponseTimeoutSection />

      {loading && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 13,
            color: 'rgba(0, 0, 0, 0.45)',
          }}
        >
          <Spin indicator={<LoadingOutlined spin />} />
          正在加载网络设置...
        </div>
      )}

      {!loading && error && (
        <div
          style={{
            borderRadius: 12,
            border: '1px solid rgba(255, 77, 79, 0.3)',
            background: 'rgba(255, 77, 79, 0.1)',
            padding: '12px 16px',
            fontSize: 13,
            color: '#cf1322',
          }}
        >
          {error}
        </div>
      )}

      {!loading && payload && draft && (
        <>
          <Row gutter={[12, 12]} style={{ marginBottom: 28 }}>
            <Col xs={24} md={12} xl={6}>
              <DetailTile
                label="浏览器 API"
                value={payload.effective.browser_api_base}
                tone="ok"
              />
            </Col>
            <Col xs={24} md={12} xl={6}>
              <DetailTile
                label="CORS 模式"
                value={
                  payload.effective.cors_mode === 'permissive'
                    ? '未启用认证时自动放行'
                    : '需要显式来源'
                }
                tone={
                  payload.effective.cors_mode === 'permissive' ? 'ok' : 'warn'
                }
              />
            </Col>
            <Col xs={24} md={12} xl={6}>
              <DetailTile
                label="认证 Cookie"
                value={`${payload.auth.cookie_samesite}${
                  payload.auth.cookie_secure ? ' + Secure' : ''
                }`}
                tone={
                  !payload.auth.enabled || payload.auth.cross_site_cookie_ready
                    ? 'ok'
                    : 'warn'
                }
              />
            </Col>
            <Col xs={24} md={12} xl={6}>
              <DetailTile label="重启" value="保存后需要重启" tone="warn" />
            </Col>
          </Row>

          <SettingSection
            title="运行端口"
            description="这些端口在启动时读取。Docker 端口映射右侧必须与容器内端口一致。"
          >
            <SettingRow
              title="后端端口"
              description="FastAPI 监听这个端口。"
              control={
                <InputNumber
                  min={1}
                  max={65535}
                  value={draft.backend_port}
                  onChange={(v) =>
                    setDraft((current) =>
                      current
                        ? { ...current, backend_port: typeof v === 'number' ? v : current.backend_port }
                        : current,
                    )
                  }
                  style={{ width: 112 }}
                />
              }
            />
            <SettingRow
              title="前端端口"
              description="Next.js 在这个端口提供 Web UI。"
              control={
                <InputNumber
                  min={1}
                  max={65535}
                  value={draft.frontend_port}
                  onChange={(v) =>
                    setDraft((current) =>
                      current
                        ? { ...current, frontend_port: typeof v === 'number' ? v : current.frontend_port }
                        : current,
                    )
                  }
                  style={{ width: 112 }}
                />
              }
            />
          </SettingSection>

          <SettingSection
            title="浏览器 API base"
            description="当浏览器不能通过 localhost 访问后端时填写，例如远程 Docker 或反向代理部署。"
          >
            <SettingRow
              title="公共 API base"
              description="本机 Docker 留空即可。远程部署填写浏览器可访问的后端 URL，可包含代理路径。"
              control={
                <Input
                  style={{ width: 360, maxWidth: '48vw' }}
                  placeholder={apiBasePlaceholder}
                  value={draft.public_api_base}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? { ...current, public_api_base: event.target.value }
                        : current,
                    )
                  }
                />
              }
            />
          </SettingSection>

          <SettingSection
            title="CORS 来源"
            description="仅认证跨域部署需要填写。这里填前端页面来源，不是 API URL。"
          >
            <div style={{ padding: '16px 0' }}>
              <Input.TextArea
                style={{
                  minHeight: 112,
                  resize: 'vertical',
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
                  fontSize: 12.5,
                  lineHeight: 1.625,
                }}
                placeholder={corsPlaceholder}
                value={corsText}
                onChange={(event) => setCorsText(event.target.value)}
              />
              <p
                style={{
                  marginTop: 8,
                  fontSize: 11.5,
                  lineHeight: 1.625,
                  color: 'rgba(0, 0, 0, 0.45)',
                }}
              >
                支持逗号、分号和换行分隔。裸 host:port 会按 http://host:port 保存。
              </p>
            </div>
          </SettingSection>

          {payload.auth.enabled && !payload.auth.cookie_secure && (
            <div
              style={{
                borderRadius: 12,
                border: '1px solid rgba(250, 173, 20, 0.3)',
                background: 'rgba(250, 173, 20, 0.1)',
                padding: '12px 16px',
                fontSize: 12.5,
                lineHeight: 1.625,
                color: '#d48806',
              }}
            >
              认证已启用，但安全 Cookie 未开启。跨站 HTTPS 部署应设置 auth.cookie_secure=true 并重启，使 SameSite=None Cookie 在现代浏览器中生效。
            </div>
          )}
        </>
      )}
    </div>
  );
}
