/**
 * 复刻自 DeepTutor 原仓 web/components/partners/PartnerChannels.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；t() → 文件内查表直出（zh/app.json 原译文）；Tailwind 类
 * 逐项换内联样式（hover 用事件直写；amber-500/40、amber-500/10、emerald-500 以
 * rgba/hex 字面值承载；dark:text-amber-300 亮色主题取 amber-700 #b45309）；响应式
 * md:grid-cols-[180px_1fr] 直接取桌面两列。apiFetch/apiUrl → ../../lib/api（批5 已
 * 1:1 落盘，等价直通）。
 * lucide-react→antd 图标登记：Loader2 → LoadingOutlined(spin)；Save → SaveOutlined。
 *
 * Channel configuration panel — Partners channel-config logic preserved:
 * schema-driven form for any channel (built-in or plugin), secret masking
 * with explicit reveal, delivery flags, and live listener reload on save.
 */

import { useCallback, useEffect, useState } from "react";
import { LoadingOutlined, SaveOutlined } from "@ant-design/icons";
import { apiFetch, apiUrl } from "../../lib/api";
import {
  getChannelSchemas,
  type ChannelsSchemaResponse,
} from "../../lib/partners-api";
import {
  SchemaField,
  defaultFor,
  type JsonSchema,
} from "./schema-form";
import ChannelIcon from "./ChannelIcon";

const ZH_MESSAGES: Record<string, string> = {
  "Channels saved": "频道已保存",
  "Invalid channel configuration": "频道配置无效",
  "Save failed": "保存失败",
  "Channel listeners failed to restart:": "频道监听器重启失败：",
  "Config is saved on disk; stop and start the partner to apply.":
    "配置已保存到磁盘；停止并重新启动伙伴以生效。",
  Enabled: "已启用",
  "Select a channel.": "请选择一个频道。",
  "This channel is not available on the server.": "该频道在此服务器上不可用。",
  Save: "保存",
};

function t(key: string, vars?: Record<string, string | number>): string {
  let text = ZH_MESSAGES[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.split(`{{${name}}}`).join(String(value));
    }
  }
  return text;
}

const LEGACY_GLOBAL_DELIVERY_KEYS = new Set([
  "send_progress",
  "send_tool_hints",
  "sendProgress",
  "sendToolHints",
]);

function stripLegacyGlobalDelivery(channels: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(channels).filter(
      ([key]) => !LEGACY_GLOBAL_DELIVERY_KEYS.has(key),
    ),
  );
}

export default function PartnerChannels({
  partnerId,
  onToast,
}: {
  partnerId: string;
  onToast: (msg: string) => void;
}) {
  const [schemaCatalog, setSchemaCatalog] =
    useState<ChannelsSchemaResponse | null>(null);
  const [channels, setChannels] = useState<Record<string, unknown>>({});
  const [activeChannel, setActiveChannel] = useState<string | null>(null);
  const [reloadError, setReloadError] = useState<string | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hoveredChannel, setHoveredChannel] = useState<string | null>(null);
  /** dot-paths of secrets the user has explicitly toggled to plaintext. */
  const [revealed, setRevealed] = useState<Set<string>>(new Set());

  useEffect(() => {
    void (async () => {
      try {
        setSchemaCatalog(await getChannelSchemas());
      } catch {
        /* leave catalog null → renders fallback message */
      }
    })();
  }, []);

  const loadDetail = useCallback(async () => {
    setLoadingDetail(true);
    try {
      // Edit form needs raw secrets to populate fields. Default GET masks them.
      const res = await apiFetch(
        apiUrl(`/api/v1/partners/${partnerId}?include_secrets=true`),
      );
      if (!res.ok) return;
      const data = await res.json();
      const raw = (data.channels ?? {}) as Record<string, unknown>;
      setChannels(stripLegacyGlobalDelivery(raw));
      setReloadError(
        typeof data.last_reload_error === "string"
          ? data.last_reload_error
          : null,
      );
    } finally {
      setLoadingDetail(false);
    }
  }, [partnerId]);

  useEffect(() => {
    setRevealed(new Set());
    void loadDetail();
  }, [loadDetail]);

  // Default active channel: prefer one already enabled.
  useEffect(() => {
    if (activeChannel || !schemaCatalog) return;
    const names = Object.keys(schemaCatalog.channels);
    const enabled = names.find((n) => {
      const cfg = channels[n];
      return (
        cfg &&
        typeof cfg === "object" &&
        (cfg as Record<string, unknown>).enabled === true
      );
    });
    setActiveChannel(enabled ?? names[0] ?? null);
  }, [schemaCatalog, channels, activeChannel]);

  const toggleSecret = useCallback((path: string) => {
    setRevealed((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  const setActiveChannelConfig = (next: unknown) => {
    if (!activeChannel) return;
    setChannels((prev) => ({ ...prev, [activeChannel]: next }));
  };

  const save = async () => {
    setSaving(true);
    try {
      const res = await apiFetch(apiUrl(`/api/v1/partners/${partnerId}`), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channels: stripLegacyGlobalDelivery(channels) }),
      });
      if (res.ok) {
        onToast(t("Channels saved"));
        await loadDetail();
      } else if (res.status === 422) {
        const err = (await res.json().catch(() => ({}))) as {
          detail?: { message?: string } | string;
        };
        const detail = err.detail;
        onToast(
          typeof detail === "string"
            ? detail
            : (detail?.message ?? t("Invalid channel configuration")),
        );
      } else {
        const err = (await res.json().catch(() => ({}))) as { detail?: string };
        onToast(err.detail ?? t("Save failed"));
      }
    } catch (error) {
      onToast(error instanceof Error ? error.message : t("Save failed"));
    } finally {
      setSaving(false);
    }
  };

  if (loadingDetail || !schemaCatalog) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: "40px 0" }}>
        <LoadingOutlined
          spin
          style={{
            fontSize: 20,
            color: "var(--muted-foreground, #64748b)",
          }}
        />
      </div>
    );
  }

  const channelEntries = Object.entries(schemaCatalog.channels).sort(
    ([, a], [, b]) => a.display_name.localeCompare(b.display_name),
  );
  const activeEntry = activeChannel
    ? schemaCatalog.channels[activeChannel]
    : undefined;
  const activeValue =
    activeChannel &&
    channels[activeChannel] &&
    typeof channels[activeChannel] === "object"
      ? (channels[activeChannel] as Record<string, unknown>)
      : (activeEntry?.default_config ?? {});
  const activeSecretSet = new Set(activeEntry?.secret_fields ?? []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {reloadError && (
        <div
          style={{
            borderRadius: 8,
            border: "1px solid rgba(245, 158, 11, 0.4)",
            background: "rgba(245, 158, 11, 0.1)",
            padding: "8px 12px",
            fontSize: 12,
            color: "#b45309",
          }}
        >
          <strong style={{ fontWeight: 500 }}>
            {t("Channel listeners failed to restart:")}
          </strong>{" "}
          <span
            style={{
              fontFamily:
                'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
            }}
          >
            {reloadError}
          </span>{" "}
          <span style={{ opacity: 0.8 }}>
            {t("Config is saved on disk; stop and start the partner to apply.")}
          </span>
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button
          type="button"
          onClick={() => void save()}
          disabled={saving}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            borderRadius: 8,
            border: "none",
            background: "var(--primary, #2563eb)",
            padding: "6px 12px",
            fontSize: 12,
            fontWeight: 500,
            color: "var(--primary-foreground, #ffffff)",
            cursor: "pointer",
            opacity: saving ? 0.4 : 1,
          }}
        >
          {saving ? (
            <LoadingOutlined spin style={{ fontSize: 14 }} />
          ) : (
            <SaveOutlined style={{ fontSize: 14 }} />
          )}
          {t("Save")}
        </button>
      </div>

      {/* Channel master-detail */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "180px minmax(0, 1fr)",
          gap: 16,
        }}
      >
        <aside
          style={{
            height: "fit-content",
            borderRadius: 12,
            border: "1px solid var(--border, #e2e8f0)",
            padding: 8,
          }}
        >
          <ul style={{ display: "flex", flexDirection: "column", gap: 2, listStyle: "none", margin: 0, padding: 0 }}>
            {channelEntries.map(([name, entry]) => {
              const cfg = channels[name] as Record<string, unknown> | undefined;
              const enabled = cfg?.enabled === true;
              const isActive = activeChannel === name;
              const unavailable = entry.available === false;
              const hovered = hoveredChannel === name;
              return (
                <li key={name}>
                  <button
                    type="button"
                    onClick={() => setActiveChannel(name)}
                    onMouseEnter={() => setHoveredChannel(name)}
                    onMouseLeave={() => setHoveredChannel(null)}
                    title={unavailable ? entry.unavailable_reason : undefined}
                    style={{
                      display: "flex",
                      width: "100%",
                      alignItems: "center",
                      gap: 8,
                      borderRadius: 6,
                      padding: "6px 10px",
                      textAlign: "left",
                      fontSize: 13,
                      border: "none",
                      background: isActive
                        ? "var(--muted, #f1f5f9)"
                        : "transparent",
                      fontWeight: isActive ? 500 : 400,
                      color: isActive
                        ? "var(--foreground, #0f172a)"
                        : hovered
                          ? "var(--foreground, #0f172a)"
                          : "var(--muted-foreground, #64748b)",
                      opacity: unavailable ? 0.45 : 1,
                      cursor: "pointer",
                      transition: "color 150ms, background-color 150ms",
                    }}
                  >
                    <ChannelIcon name={name} size={15} />
                    <span
                      style={{
                        minWidth: 0,
                        flex: 1,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {entry.display_name}
                    </span>
                    {enabled && (
                      <span
                        aria-label={t("Enabled")}
                        title={t("Enabled")}
                        style={{
                          height: 6,
                          width: 6,
                          flexShrink: 0,
                          borderRadius: 9999,
                          background: "#10b981",
                          display: "block",
                        }}
                      />
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        <section
          style={{
            borderRadius: 12,
            border: "1px solid var(--border, #e2e8f0)",
            padding: 16,
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          {!activeEntry ? (
            <p
              style={{
                fontSize: 13,
                color: "var(--muted-foreground, #64748b)",
                margin: 0,
              }}
            >
              {t("Select a channel.")}
            </p>
          ) : (
            <>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <h3
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    fontSize: 14,
                    fontWeight: 500,
                    color: "var(--foreground, #0f172a)",
                    margin: 0,
                  }}
                >
                  <ChannelIcon name={activeEntry.name} size={18} />
                  {activeEntry.display_name}
                </h3>
                <code
                  style={{
                    fontSize: 11,
                    color: "var(--muted-foreground, #64748b)",
                  }}
                >
                  {activeEntry.name}
                </code>
              </div>
              {activeEntry.available === false || !activeEntry.json_schema ? (
                <div
                  style={{
                    borderRadius: 8,
                    border: "1px solid rgba(245, 158, 11, 0.4)",
                    background: "rgba(245, 158, 11, 0.1)",
                    padding: "8px 12px",
                    fontSize: 12,
                    color: "#b45309",
                  }}
                >
                  <strong style={{ fontWeight: 500 }}>
                    {t("This channel is not available on the server.")}
                  </strong>{" "}
                  {activeEntry.unavailable_reason && (
                    <span
                      style={{
                        fontFamily:
                          'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                      }}
                    >
                      {activeEntry.unavailable_reason}
                    </span>
                  )}
                </div>
              ) : (
                <>
                  {(activeEntry.json_schema as JsonSchema).description && (
                    <p
                      style={{
                        fontSize: 11,
                        color: "var(--muted-foreground, #64748b)",
                        margin: 0,
                      }}
                    >
                      {(activeEntry.json_schema as JsonSchema).description}
                    </p>
                  )}
                  {Object.entries(
                    (activeEntry.json_schema as JsonSchema).properties ?? {},
                  ).map(([k, child]) => (
                    <SchemaField
                      key={k}
                      fieldKey={k}
                      schema={child}
                      value={activeValue[k] ?? defaultFor(child)}
                      onChange={(next) =>
                        setActiveChannelConfig({ ...activeValue, [k]: next })
                      }
                      secretFields={activeSecretSet}
                      path={k}
                      showSecretFor={revealed}
                      toggleSecret={toggleSecret}
                    />
                  ))}
                </>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
