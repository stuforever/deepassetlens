/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/PersonaPicker.tsx，206 行）。
 * 替换点：删除 "use client"；lucide Check/Loader2/Search/UserRound→CheckOutlined/
 * LoadingOutlined(spin)/SearchOutlined/UserOutlined；PickerShell/PickerHeader→本目录
 * 件；personas-api→./personasApi（SA-D 批件，listPersonas({force:true}) 契约一致）；
 * Tailwind→内联样式；t() 译文："Select Persona"/"No persona"/"Use Persona" 等
 * persona 相关键在 zh/app.json 无对应键，按 i18next 缺键回退行为直出原 key。
 * 交互（重开同步/force 拉取/搜索过滤）逐字未改。
 */
import { useEffect, useMemo, useState } from "react";
import {
  CheckOutlined,
  LoadingOutlined,
  SearchOutlined,
  UserOutlined,
} from "@ant-design/icons";
import PickerShell from "./PickerShell";
import PickerHeader from "./PickerHeader";
import { listPersonas, type PersonaInfo } from "./personasApi";
import { DT, ellipsis } from "./dtStyle";

interface PersonaPickerProps {
  open: boolean;
  initialPersona: string | null;
  onClose: () => void;
  onApply: (selection: string | null) => void;
}

export default function PersonaPicker({
  open,
  initialPersona,
  onClose,
  onApply,
}: PersonaPickerProps) {
  const [personas, setPersonas] = useState<PersonaInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(initialPersona);
  const [query, setQuery] = useState("");

  // Sync local state with the parent's current selection every time the
  // picker is reopened so the modal always starts from the latest choice.
  useEffect(() => {
    if (!open) return;
    setSelected(initialPersona);
    setQuery("");
  }, [open, initialPersona]);

  useEffect(() => {
    if (!open) return;
    let mounted = true;
    void (async () => {
      setLoading(true);
      try {
        const items = await listPersonas({ force: true });
        if (mounted) setPersonas(items);
      } catch {
        if (mounted) setPersonas([]);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [open]);

  const filteredPersonas = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return personas;
    return personas.filter((persona) => {
      const name = persona.name.toLowerCase();
      const desc = (persona.description || "").toLowerCase();
      return name.includes(keyword) || desc.includes(keyword);
    });
  }, [personas, query]);

  const handleApply = () => {
    onApply(selected);
    onClose();
  };

  return (
    <PickerShell
      open={open}
      onClose={onClose}
      labelledBy="persona-picker-title"
      backdropClass="rgba(255,255,255,0.65)"
    >
      <div
        style={{
          width: "100%",
          maxWidth: 768,
          overflow: "hidden",
          borderRadius: 16,
          border: `1px solid ${DT.border}`,
          background: DT.card,
          color: DT.foreground,
          boxShadow: "0 22px 70px rgba(0,0,0,0.18)",
          padding: 16,
        }}
      >
        <PickerHeader
          icon={UserOutlined}
          titleId="persona-picker-title"
          title={"Select Persona"}
          subtitle={
            "Choose a behavior persona to apply, or pick No persona to use the default."
          }
          onClose={onClose}
        />

        <div style={{ background: "rgba(255,255,255,0.4)", padding: 20 }}>
          <button
            type="button"
            onClick={() => setSelected(null)}
            onMouseEnter={(e) => {
              if (selected !== null) {
                e.currentTarget.style.background = DT.mutedAlpha(0.4);
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background =
                selected === null ? DT.primaryAlpha(0.08) : DT.card;
            }}
            style={{
              marginBottom: 12,
              display: "flex",
              width: "100%",
              alignItems: "flex-start",
              gap: 12,
              borderRadius: 16,
              border: `1px solid ${selected === null ? DT.primaryAlpha(0.4) : DT.border}`,
              background:
                selected === null ? DT.primaryAlpha(0.08) : DT.card,
              padding: "12px 16px",
              textAlign: "left",
              cursor: "pointer",
              transition: "background-color 150ms, border-color 150ms",
              font: "inherit",
            }}
          >
            <div
              style={{
                marginTop: 2,
                display: "flex",
                height: 20,
                width: 20,
                flexShrink: 0,
                alignItems: "center",
                justifyContent: "center",
                borderRadius: 999,
                border: `1px solid ${selected === null ? DT.primary : DT.border}`,
                background: selected === null ? DT.primary : "transparent",
                color: selected === null ? DT.primaryForeground : "transparent",
                transition: "background-color 150ms, border-color 150ms",
              }}
            >
              <CheckOutlined style={{ fontSize: 12 }} />
            </div>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 500, color: DT.foreground }}>
                No persona
              </div>
              <p style={{ margin: "2px 0 0", fontSize: 12, lineHeight: "20px", color: DT.mutedForeground }}>
                Use the default assistant behavior for this turn.
              </p>
            </div>
          </button>

          <div style={{ marginBottom: 16 }}>
            <div style={{ position: "relative", flex: 1 }}>
              <SearchOutlined
                style={{
                  pointerEvents: "none",
                  position: "absolute",
                  left: 12,
                  top: "50%",
                  fontSize: 16,
                  transform: "translateY(-50%)",
                  color: DT.mutedForeground,
                }}
              />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search personas by name or description"
                style={{
                  width: "100%",
                  borderRadius: 12,
                  border: `1px solid ${DT.border}`,
                  background: DT.card,
                  padding: "10px 12px 10px 36px",
                  fontSize: 13,
                  color: DT.foreground,
                  outline: "none",
                  transition: "border-color 150ms, box-shadow 150ms",
                  boxSizing: "border-box",
                }}
              />
            </div>
          </div>

          <div
            style={{
              maxHeight: "48vh",
              overflowY: "auto",
              borderRadius: 16,
              border: `1px solid ${DT.border}`,
              background: DT.card,
            }}
          >
            {loading ? (
              <div style={{ minHeight: 220, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <LoadingOutlined spin style={{ fontSize: 20, color: DT.mutedForeground }} />
              </div>
            ) : filteredPersonas.length ? (
              <div>
                {filteredPersonas.map((persona, idx) => {
                  const active = selected === persona.name;
                  return (
                    <button
                      key={persona.name}
                      onClick={() => setSelected(persona.name)}
                      onMouseEnter={(e) => {
                        if (!active) {
                          e.currentTarget.style.background = DT.mutedAlpha(0.4);
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = active
                          ? DT.primaryAlpha(0.08)
                          : "transparent";
                      }}
                      style={{
                        display: "flex",
                        width: "100%",
                        alignItems: "flex-start",
                        gap: 12,
                        padding: "12px 16px",
                        textAlign: "left",
                        border: "none",
                        cursor: "pointer",
                        background: active ? DT.primaryAlpha(0.08) : "transparent",
                        font: "inherit",
                        borderTop: idx > 0 ? `1px solid ${DT.border}` : undefined,
                      }}
                    >
                      <div
                        style={{
                          marginTop: 2,
                          display: "flex",
                          height: 20,
                          width: 20,
                          flexShrink: 0,
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: 999,
                          border: `1px solid ${active ? DT.primary : DT.border}`,
                          background: active ? DT.primary : "transparent",
                          color: active ? DT.primaryForeground : "transparent",
                          transition: "background-color 150ms, border-color 150ms",
                        }}
                      >
                        <CheckOutlined style={{ fontSize: 12 }} />
                      </div>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{ ...ellipsis, fontSize: 14, fontWeight: 500, color: DT.foreground }}>
                            {persona.name}
                          </span>
                          {persona.source === "admin" ? (
                            <span
                              style={{
                                borderRadius: 6,
                                background: DT.muted,
                                padding: "2px 6px",
                                fontSize: 10,
                                fontWeight: 500,
                                textTransform: "uppercase",
                                letterSpacing: "0.05em",
                                color: DT.mutedForeground,
                              }}
                            >
                              preset
                            </span>
                          ) : null}
                        </div>
                        {persona.description ? (
                          <p
                            style={{
                              margin: "4px 0 0",
                              fontSize: 12,
                              lineHeight: "20px",
                              color: DT.mutedForeground,
                              display: "-webkit-box",
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: "vertical",
                              overflow: "hidden",
                            }}
                          >
                            {persona.description}
                          </p>
                        ) : null}
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div style={{ padding: "56px 24px", textAlign: "center", fontSize: 13, color: DT.mutedForeground }}>
                {personas.length === 0
                  ? "No personas yet"
                  : "No matching personas found."}
              </div>
            )}
          </div>

          <div style={{ marginTop: 16, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
            <div style={{ fontSize: 12, color: DT.mutedForeground }}>
              {selected
                ? `Persona: ${selected}`
                : "No persona selected"}
            </div>
            <button
              onClick={handleApply}
              style={{
                borderRadius: 12,
                border: "none",
                cursor: "pointer",
                background: DT.primary,
                padding: "10px 16px",
                fontSize: 13,
                fontWeight: 500,
                color: DT.primaryForeground,
                transition: "opacity 150ms",
                font: "inherit",
              }}
            >
              {selected ? "Use Persona" : "Continue without persona"}
            </button>
          </div>
        </div>
      </div>
    </PickerShell>
  );
}

// 具名再导出：批9 SA-A FollowupChatComposer 以 lazy(() => import(...).then((m) => ({ default: m.PersonaPicker }))) 消费（桌面原件仅 default 导出，此为批内契约对齐，非新逻辑）。
export { PersonaPicker };
