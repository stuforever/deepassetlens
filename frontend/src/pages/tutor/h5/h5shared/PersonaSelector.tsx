/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/home/PersonaSelector.tsx，276 行）。
 * 替换点：删除 "use client"；lucide Check/ChevronDown/Search/Sparkles/UserRound→
 * CheckOutlined/DownOutlined/SearchOutlined/StarOutlined/UserOutlined；personas-api
 * → ./personasApi（批8/SA-D 同源契约）；Tailwind→内联样式（token 见 dtStyle.ts）；
 * hover→onMouseEnter/Leave 直写 style；t() 译文：命中 zh/app.json 的 "Default"→默认；
 * "Select persona"/"Search personas..."/"No persona — the assistant's standard
 * behavior"/"Preset"/"No personas match this search." 在 zh/app.json 无对应键，
 * 按 i18next 缺键回退行为直出原 key。状态机/受控 open/搜索过滤逐字未改。
 */
import { useEffect, useMemo, useRef, useState } from "react";
import {
  CheckOutlined,
  DownOutlined,
  SearchOutlined,
  StarOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useLingerExpand } from "./use-linger-expand";
import { listPersonas, type PersonaInfo } from "./personasApi";
import { DT, ellipsis } from "./dtStyle";

/**
 * Session persona switcher (composer toolbar).
 *
 * Mirrors ModelSelector's chip + dropdown pattern. The selection is a
 * SESSION-level preference: it applies to every following message in the
 * current chat until changed (persisted via session.preferences.persona).
 * "Default" (value "") means no persona — the assistant's base behavior.
 *
 * Open state is optionally controlled (`open`/`onOpenChange`) so the
 * `/persona` slash command and the @space menu entry can pop the same
 * dropdown programmatically.
 */
export default function PersonaSelector({
  value,
  onChange,
  open: openProp,
  onOpenChange,
  placement = "top",
}: {
  /** Active persona name; "" = Default (no persona). */
  value: string;
  onChange: (persona: string) => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  placement?: "top" | "bottom";
}) {
  const [openState, setOpenState] = useState(false);
  const open = openProp ?? openState;
  const { expanded, linger, triggerProps: lingerProps } = useLingerExpand(open);
  const setOpen = (next: boolean) => {
    setOpenState(next);
    onOpenChange?.(next);
    // Closing (selection or outside click) keeps the label expanded for a
    // beat so the change registers before the chip collapses.
    if (!next) linger();
  };
  const rootRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const [personas, setPersonas] = useState<PersonaInfo[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [query, setQuery] = useState("");

  // Load (cached) persona list when the dropdown first opens.
  useEffect(() => {
    if (!open || loaded) return;
    let cancelled = false;
    void listPersonas()
      .then((items) => {
        if (!cancelled) {
          setPersonas(items);
          setLoaded(true);
        }
      })
      .catch(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [open, loaded]);

  // Focus the search box and clear stale queries on open.
  useEffect(() => {
    if (!open) return;
    setQuery("");
    requestAnimationFrame(() => searchRef.current?.focus());
  }, [open]);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const handler = (event: MouseEvent) => {
      const target = event.target as Node;
      if (rootRef.current && !rootRef.current.contains(target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return personas;
    return personas.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q),
    );
  }, [personas, query]);

  const defaultLabel = "默认";
  const label = value || defaultLabel;
  const menuPosition = placement === "bottom" ? "top" : "bottom";

  const pick = (persona: string) => {
    onChange(persona);
    setOpen(false);
  };

  const showDefaultRow =
    !query.trim() ||
    defaultLabel.toLowerCase().includes(query.trim().toLowerCase());

  return (
    <div ref={rootRef} style={{ position: "relative" }}>
      {/* Resting state is just the small figure icon; hovering (or opening
          the menu) slides the persona name out with a max-width animation
          and lingers ~1.2s after leave/selection before collapsing. A
          non-default persona tints the icon primary so the active state
          stays visible even when collapsed. */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-label={"Select persona"}
        aria-expanded={open}
        {...lingerProps}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = DT.mutedAlpha(0.55);
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent";
        }}
        style={{
          display: "inline-flex",
          height: 32,
          flexShrink: 0,
          alignItems: "center",
          borderRadius: 8,
          padding: "0 8px",
          fontSize: 14,
          fontWeight: 500,
          border: "none",
          cursor: "pointer",
          background: open ? DT.muted : "transparent",
          color: open
            ? DT.foreground
            : value
              ? DT.primary
              : DT.mutedForeground,
          transition: "background-color 150ms, color 150ms, transform 150ms",
        }}
      >
        <UserOutlined style={{ fontSize: 16, flexShrink: 0 }} />
        <span
          style={{
            display: "flex",
            minWidth: 0,
            alignItems: "center",
            gap: 4,
            overflow: "hidden",
            whiteSpace: "nowrap",
            marginLeft: expanded ? 6 : 0,
            maxWidth: expanded ? 140 : 0,
            opacity: expanded ? 1 : 0,
            transition:
              "max-width 300ms ease-out, opacity 300ms ease-out, margin-left 300ms ease-out",
          }}
        >
          <span style={ellipsis}>{label}</span>
          <DownOutlined
            style={{
              fontSize: 13,
              flexShrink: 0,
              transition: "transform 200ms",
              transform: open ? "rotate(180deg)" : undefined,
            }}
          />
        </span>
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            right: 0,
            zIndex: 50,
            [menuPosition === "top" ? "bottom" : "top"]: "100%",
            marginBottom: menuPosition === "top" ? 6 : undefined,
            marginTop: menuPosition === "bottom" ? 6 : undefined,
            width: "min(280px, calc(100vw - 32px))",
            overflow: "hidden",
            borderRadius: 12,
            border: `1px solid ${DT.border}`,
            background: DT.popover,
            boxShadow:
              "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)",
          } as React.CSSProperties}
        >
          <div style={{ borderBottom: `1px solid ${DT.borderAlpha(0.5)}`, padding: 8 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                borderRadius: 8,
                border: `1px solid ${DT.borderAlpha(0.6)}`,
                background: DT.background,
                padding: "4px 8px",
              }}
            >
              <SearchOutlined
                style={{ fontSize: 12, flexShrink: 0, color: DT.mutedForeground }}
              />
              <input
                ref={searchRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Escape") {
                    e.preventDefault();
                    setOpen(false);
                  }
                }}
                placeholder={"Search personas..."}
                style={{
                  width: "100%",
                  background: "transparent",
                  fontSize: 12,
                  color: DT.foreground,
                  outline: "none",
                  border: "none",
                }}
              />
            </div>
          </div>
          <div style={{ maxHeight: 280, overflowY: "auto", padding: "4px 0" }}>
            {showDefaultRow && (
              <button
                type="button"
                onClick={() => pick("")}
                onMouseEnter={(e) => {
                  if (value) {
                    e.currentTarget.style.background = DT.mutedAlpha(0.45);
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = !value
                    ? DT.primaryAlpha(0.06)
                    : "transparent";
                }}
                style={{
                  display: "flex",
                  width: "100%",
                  alignItems: "center",
                  gap: 10,
                  padding: "6px 12px",
                  textAlign: "left",
                  border: "none",
                  cursor: "pointer",
                  background: !value ? DT.primaryAlpha(0.06) : "transparent",
                  font: "inherit",
                }}
              >
                <StarOutlined
                  style={{
                    fontSize: 15,
                    flexShrink: 0,
                    color: !value ? DT.primary : DT.mutedForeground,
                  }}
                />
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ ...ellipsis, fontSize: 12.5, fontWeight: 500, lineHeight: 1.375, color: DT.foreground }}>
                    {defaultLabel}
                  </div>
                  <div style={{ ...ellipsis, fontSize: 11, lineHeight: 1.375, color: DT.mutedForeground }}>
                    {"No persona — the assistant's standard behavior"}
                  </div>
                </div>
                {!value && (
                  <CheckOutlined
                    style={{ fontSize: 14, flexShrink: 0, color: DT.primary }}
                  />
                )}
              </button>
            )}
            {filtered.map((persona) => {
              const selected = persona.name === value;
              const baseBg = selected ? DT.primaryAlpha(0.06) : "transparent";
              return (
                <button
                  key={persona.name}
                  type="button"
                  onClick={() => pick(persona.name)}
                  onMouseEnter={(e) => {
                    if (!selected) {
                      e.currentTarget.style.background = DT.mutedAlpha(0.45);
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = baseBg;
                  }}
                  style={{
                    display: "flex",
                    width: "100%",
                    alignItems: "center",
                    gap: 10,
                    padding: "6px 12px",
                    textAlign: "left",
                    border: "none",
                    cursor: "pointer",
                    background: baseBg,
                    font: "inherit",
                  }}
                >
                  <UserOutlined
                    style={{
                      fontSize: 15,
                      flexShrink: 0,
                      color: selected ? DT.primary : DT.mutedForeground,
                    }}
                  />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ display: "flex", minWidth: 0, alignItems: "center", gap: 6 }}>
                      <span style={{ ...ellipsis, fontSize: 12.5, fontWeight: 500, lineHeight: 1.375, color: DT.foreground }}>
                        {persona.name}
                      </span>
                      {persona.source === "admin" && (
                        <span
                          style={{
                            flexShrink: 0,
                            borderRadius: 999,
                            background: DT.muted,
                            padding: "1px 6px",
                            fontSize: 9,
                            fontWeight: 600,
                            textTransform: "uppercase",
                            letterSpacing: "0.05em",
                            color: DT.mutedForeground,
                          }}
                        >
                          Preset
                        </span>
                      )}
                    </div>
                    {persona.description ? (
                      <div style={{ ...ellipsis, fontSize: 11, lineHeight: 1.375, color: DT.mutedForeground }}>
                        {persona.description}
                      </div>
                    ) : null}
                  </div>
                  {selected && (
                    <CheckOutlined
                      style={{ fontSize: 14, flexShrink: 0, color: DT.primary }}
                    />
                  )}
                </button>
              );
            })}
            {loaded && filtered.length === 0 && !showDefaultRow && (
              <div style={{ padding: "16px 12px", textAlign: "center", fontSize: 12, color: DT.mutedForeground }}>
                No personas match this search.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
