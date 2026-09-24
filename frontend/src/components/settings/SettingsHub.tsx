/**
 * SettingsHub（UX3批4 瘦身）：设置首屏——搜索框 + ≤6 捷径 + StatusPanel。
 * 删六分类卡平铺（与左导航重复——SETTINGS_SECTIONS 单一事实源侧栏已够）；
 * apiBase 一行并入状态区。 navigate 用 useNavigate（KeepAlive 架构）。
 */
import React, { useCallback, useMemo, useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Input } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import SettingsStatusPanel from "./SettingsStatusPanel";
import {
  SETTINGS_CATEGORIES,
  type Lang,
} from "../../lib/settings-nav";
import { useSettings } from "./SettingsContext";

export default function SettingsHub() {
  const zh = true;
  const tr = useCallback((l: Lang) => (zh ? l.zh : l.en), [zh]);
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [apiBase, setApiBase] = useState("");

  useEffect(() => {
    fetch("/api/v1/settings")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        const base = d?.effective?.browser_api_base || d?.ui?.browser_api_base || "";
        if (base) setApiBase(base);
      })
      .catch(() => {});
  }, []);

  // 搜索：SETTINGS_CATEGORIES 全叶子扁平匹配
  const hits = useMemo(() => {
    const kw = q.trim().toLowerCase();
    if (!kw) return [];
    const out: { label: string; path: string }[] = [];
    for (const c of SETTINGS_CATEGORIES) {
      if ((c.label?.zh || c.label?.en || "").toLowerCase().includes(kw)) {
        out.push({ label: c.label?.zh || c.label?.en || c.key, path: c.href });
      }
      for (const child of c.children ?? []) {
        const lbl = (child as { label?: { zh?: string; en?: string } })?.label;
        const childLabel = typeof lbl === 'object' ? (lbl?.zh || lbl?.en || '') : String(lbl || '');
        const childPath = (child as { path?: string }).path || '';
        if (childLabel.toLowerCase().includes(kw) || childPath.toLowerCase().includes(kw)) {
          out.push({ label: childLabel || childPath, path: childPath });
        }
      }
    }
    return out.slice(0, 8);
  }, [q]);

  const SHORTCUTS = [
    { label: "LLM", path: "/settings/llm" },
    { label: "模型", path: "/settings/models" },
    { label: "MCP", path: "/settings/mcp" },
    { label: "网络", path: "/settings/network" },
    { label: "教学设置", path: "/e/sishu/admin/settings" },
    { label: "状态", path: "/settings/status" },
  ];

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
      <Input
        allowClear
        prefix={<SearchOutlined style={{ color: "#999" }} />}
        placeholder="搜索设置页…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        data-testid="settings-hub-search"
      />
      {hits.length > 0 && (
        <div data-testid="settings-hub-hits">
          {hits.slice(0, 8).map((h) => (
            <div
              key={h.path}
              role="button"
              tabIndex={0}
              onClick={() => navigate(h.path)}
              onKeyDown={(e) => { if (e.key === "Enter") navigate(h.path); }}
              style={{ padding: "8px 12px", cursor: "pointer", borderBottom: "1px solid #f0f0f0" }}
            >
              {h.label}
            </div>
          ))}
        </div>
      )}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }} data-testid="settings-hub-shortcuts">
        {SHORTCUTS.map((s) => (
          <Link
            key={s.path}
            to={s.path}
            data-testid={`settings-shortcut-${s.label}`}
            style={{ padding: "6px 14px", borderRadius: 999, border: "1px solid #e5e7eb", fontSize: 13, color: "#333", textDecoration: "none" }}
          >
            {s.label}
          </Link>
        ))}
      </div>
      <SettingsStatusPanel />
      {apiBase && (
        <div style={{ fontSize: 12, color: "#999" }} data-testid="settings-api-base">
          API 基址：{apiBase}
        </div>
      )}
    </div>
  );
}
