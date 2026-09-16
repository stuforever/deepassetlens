/**
 * S2（M23）：H5PickerSheet —— 基于 H5Sheet 的单列选择弹层——原仓 1:1 移植。
 * 等价替换：lucide Search/Check → SearchOutlined/CheckOutlined；Tailwind → 内联样式。
 * 设计约定：
 *  - 选项 > 10 项时自动出现搜索框（过滤）
 *  - 当前选中项高亮 + ✓
 *  - 点选即关（mobile 拇指流）
 *  - 44px 触点行
 */
import React, { useMemo, useState } from "react";
import { SearchOutlined, CheckOutlined } from "@ant-design/icons";
import { H5Sheet } from "./H5Sheet";

export function H5PickerSheet({
  open,
  onClose,
  title,
  options,
  value,
  onChange,
  searchPlaceholder = "搜索…",
  emptyText = "没有可选项",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  options: Array<{ value: string; label: string }>;
  value?: string;
  onChange: (value: string) => void;
  searchPlaceholder?: string;
  emptyText?: string;
}) {
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return options;
    return options.filter((o) => o.label.toLowerCase().includes(needle));
  }, [q, options]);

  const showSearch = options.length > 10;

  const pick = (v: string) => {
    onChange(v);
    setQ("");
    onClose();
  };

  return (
    <H5Sheet open={open} onClose={onClose} title={title}>
      <div style={{ padding: "0 20px 16px" }}>
        {showSearch && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, background: "#f1f5f9", borderRadius: 12, padding: "0 12px", marginBottom: 8 }}>
            <SearchOutlined style={{ fontSize: 16, color: "#94a3b8", flexShrink: 0 }} />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={searchPlaceholder}
              style={{ width: "100%", minHeight: 44, background: "transparent", fontSize: 14, outline: "none", border: "none" }}
            />
          </div>
        )}
        {filtered.length === 0 ? (
          <div style={{ textAlign: "center", padding: "32px 0", color: "#94a3b8", fontSize: 14 }}>{emptyText}</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {filtered.map((o) => {
              const active = String(o.value) === String(value);
              return (
                <button
                  key={String(o.value)}
                  onClick={() => pick(String(o.value))}
                  data-testid="picker-option"
                  style={{
                    width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
                    minHeight: 44, padding: "10px 12px", borderRadius: 12, fontSize: 14, textAlign: "left",
                    background: active ? "#eef2ff" : "transparent",
                    color: active ? "#4338ca" : "inherit",
                    fontWeight: active ? 500 : 400,
                    border: "none", cursor: "pointer",
                  }}
                >
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{o.label}</span>
                  {active && <CheckOutlined style={{ fontSize: 14, color: "#4f46e5", flexShrink: 0, marginLeft: 8 }} />}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </H5Sheet>
  );
}
