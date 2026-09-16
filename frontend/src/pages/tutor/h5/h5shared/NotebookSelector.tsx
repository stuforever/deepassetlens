/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/notebook/NotebookSelector.tsx，252 行）。
 * 替换点：删除 "use client"；lucide Loader2/ChevronRight/ChevronDown/Check/
 * NotebookPen→LoadingOutlined(spin)/RightOutlined/DownOutlined/CheckOutlined/
 * HighlightOutlined（同 space-items 的 NotebookPen 映射）；notebook-selection-types
 * →./notebook-selection-types（getTypeColor 返回内联样式对象，消费侧对位）；
 * Tailwind→内联样式（token 见 dtStyle.ts）；line-clamp-2→WebkitLineClamp；
 * t() 译文：zh/app.json 命中直出（"Select Source (Cross-Notebook)"→选择来源
 * （跨笔记本）、"Clear"→清空、"No notebooks with records found"→未找到包含记录的
 * 笔记本、"Save a chat result first to populate a notebook."→请先保存一次聊天结果
 * 以填充笔记本。、"No records"→暂无记录、"Select All"→全选（原键 "Select all"）、
 * "Deselect"→取消选择、"Generating..."→生成中…、"Use Selected Records ({n})"→
 * 使用所选记录（{n}））。结构/交互逐字未改。
 */
import {
  LoadingOutlined,
  RightOutlined,
  DownOutlined,
  CheckOutlined,
  HighlightOutlined,
} from "@ant-design/icons";
import {
  Notebook,
  NotebookRecord,
  SelectedRecord,
  getTypeColor,
} from "./notebook-selection-types";
import { DT, ellipsis } from "./dtStyle";

interface NotebookSelectorProps {
  notebooks: Notebook[];
  expandedNotebooks: Set<string>;
  notebookRecordsMap: Map<string, NotebookRecord[]>;
  selectedRecords: Map<string, SelectedRecord>;
  loadingNotebooks: boolean;
  loadingRecordsFor: Set<string>;
  isLoading: boolean;
  onToggleExpanded: (notebookId: string) => void;
  onToggleRecord: (
    record: NotebookRecord,
    notebookId: string,
    notebookName: string,
  ) => void;
  onSelectAll: (notebookId: string, notebookName: string) => void;
  onDeselectAll: (notebookId: string) => void;
  onClearAll: () => void;
  onCreateSession: () => void;
  actionLabel?: string;
}

export default function NotebookSelector({
  notebooks,
  expandedNotebooks,
  notebookRecordsMap,
  selectedRecords,
  loadingNotebooks,
  loadingRecordsFor,
  isLoading,
  onToggleExpanded,
  onToggleRecord,
  onSelectAll,
  onDeselectAll,
  onClearAll,
  onCreateSession,
  actionLabel,
}: NotebookSelectorProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        borderRadius: 16,
        border: `1px solid ${DT.border}`,
        background: DT.card,
        boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: `1px solid ${DT.border}`,
          background: DT.card,
          padding: "14px 16px",
        }}
      >
        <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 600, color: DT.foreground }}>
          <HighlightOutlined style={{ fontSize: 14, color: DT.mutedForeground }} />
          选择来源（跨笔记本）
        </h2>
        {selectedRecords.size > 0 && (
          <button
            onClick={onClearAll}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = DT.muted;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
            style={{
              borderRadius: 6,
              padding: "4px 8px",
              fontSize: 12,
              border: "none",
              cursor: "pointer",
              background: "transparent",
              color: DT.mutedForeground,
              transition: "background-color 150ms, color 150ms",
            }}
          >
            清空 ({selectedRecords.size})
          </button>
        )}
      </div>

      <div style={{ maxHeight: 460, flex: 1, overflowY: "auto", padding: 8 }}>
        {loadingNotebooks ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 0" }}>
            <LoadingOutlined spin style={{ fontSize: 20, color: DT.mutedForeground }} />
          </div>
        ) : notebooks.length === 0 ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              padding: "40px 16px",
              textAlign: "center",
              fontSize: 14,
              color: DT.mutedForeground,
            }}
          >
            <HighlightOutlined style={{ fontSize: 20, color: DT.mutedForegroundAlpha(0.6) }} />
            <span>未找到包含记录的笔记本</span>
            <span style={{ fontSize: 11, color: DT.mutedForegroundAlpha(0.8) }}>
              请先保存一次聊天结果以填充笔记本。
            </span>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", rowGap: 8 }}>
            {notebooks.map((notebook) => {
              const isExpanded = expandedNotebooks.has(notebook.id);
              const records = notebookRecordsMap.get(notebook.id) || [];
              const isLoadingRecords = loadingRecordsFor.has(notebook.id);
              const selectedFromThis = records.filter((r) =>
                selectedRecords.has(r.id),
              ).length;

              return (
                <div
                  key={notebook.id}
                  style={{
                    overflow: "hidden",
                    borderRadius: 12,
                    border: `1px solid ${DT.border}`,
                    background: "rgba(255,255,255,0.6)",
                  }}
                >
                  {/* Notebook Header */}
                  <button
                    type="button"
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = DT.mutedAlpha(0.5);
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "transparent";
                    }}
                    style={{
                      display: "flex",
                      width: "100%",
                      cursor: "pointer",
                      alignItems: "center",
                      gap: 8,
                      padding: "10px 12px",
                      textAlign: "left",
                      border: "none",
                      background: "transparent",
                      font: "inherit",
                      transition: "background-color 150ms",
                    }}
                    onClick={() => onToggleExpanded(notebook.id)}
                  >
                    {isExpanded ? (
                      <DownOutlined style={{ fontSize: 14, color: DT.mutedForeground }} />
                    ) : (
                      <RightOutlined style={{ fontSize: 14, color: DT.mutedForeground }} />
                    )}
                    <span
                      style={{
                        height: 8,
                        width: 8,
                        flexShrink: 0,
                        borderRadius: 999,
                        backgroundColor: notebook.color || DT.primary,
                      }}
                    />
                    <span style={{ flex: 1, ...ellipsis, fontSize: 13, fontWeight: 500, color: DT.foreground }}>
                      {notebook.name}
                    </span>
                    <span style={{ fontSize: 11, fontVariantNumeric: "tabular-nums", color: DT.mutedForeground }}>
                      {selectedFromThis > 0 && (
                        <span style={{ fontWeight: 500, color: DT.primary }}>
                          {selectedFromThis}/
                        </span>
                      )}
                      {notebook.record_count}
                    </span>
                  </button>

                  {/* Records List */}
                  {isExpanded && (
                    <div
                      style={{
                        borderTop: `1px solid ${DT.border}`,
                        background: "rgba(255,255,255,0.3)",
                        padding: "8px 12px 12px",
                      }}
                    >
                      {isLoadingRecords ? (
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "16px 0" }}>
                          <LoadingOutlined spin style={{ fontSize: 16, color: DT.mutedForeground }} />
                        </div>
                      ) : records.length === 0 ? (
                        <div style={{ padding: "12px 0", textAlign: "center", fontSize: 12, color: DT.mutedForeground }}>
                          暂无记录
                        </div>
                      ) : (
                        <>
                          <div style={{ marginBottom: 8, display: "flex", gap: 12, fontSize: 11 }}>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onSelectAll(notebook.id, notebook.name);
                              }}
                              style={{
                                border: "none",
                                cursor: "pointer",
                                background: "transparent",
                                padding: 0,
                                fontSize: 11,
                                color: DT.primary,
                                transition: "opacity 150ms",
                              }}
                            >
                              全选
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onDeselectAll(notebook.id);
                              }}
                              style={{
                                border: "none",
                                cursor: "pointer",
                                background: "transparent",
                                padding: 0,
                                fontSize: 11,
                                color: DT.mutedForeground,
                                transition: "color 150ms",
                              }}
                            >
                              取消选择
                            </button>
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", rowGap: 6 }}>
                            {records.map((record) => {
                              const isSelected = selectedRecords.has(record.id);
                              return (
                                <div
                                  key={record.id}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onToggleRecord(
                                      record,
                                      notebook.id,
                                      notebook.name,
                                    );
                                  }}
                                  onMouseEnter={(e) => {
                                    if (!isSelected) {
                                      e.currentTarget.style.borderColor = DT.border;
                                      e.currentTarget.style.background = DT.mutedAlpha(0.4);
                                    }
                                  }}
                                  onMouseLeave={(e) => {
                                    if (!isSelected) {
                                      e.currentTarget.style.borderColor = "transparent";
                                      e.currentTarget.style.background = "transparent";
                                    }
                                  }}
                                  style={{
                                    cursor: "pointer",
                                    borderRadius: 8,
                                    border: `1px solid ${isSelected ? DT.primaryAlpha(0.4) : "transparent"}`,
                                    background: isSelected ? DT.primaryAlpha(0.08) : "transparent",
                                    padding: 10,
                                    transition: "border-color 150ms, background-color 150ms",
                                  }}
                                >
                                  <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                                    <div
                                      style={{
                                        marginTop: 2,
                                        display: "flex",
                                        height: 16,
                                        width: 16,
                                        flexShrink: 0,
                                        alignItems: "center",
                                        justifyContent: "center",
                                        borderRadius: 4,
                                        border: `1px solid ${isSelected ? DT.primary : DT.border}`,
                                        background: isSelected ? DT.primary : "transparent",
                                        color: DT.primaryForeground,
                                        transition: "background-color 150ms, border-color 150ms",
                                      }}
                                    >
                                      {isSelected && (
                                        <CheckOutlined style={{ fontSize: 10 }} />
                                      )}
                                    </div>
                                    <div style={{ minWidth: 0, flex: 1 }}>
                                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                        <span
                                          style={{
                                            flexShrink: 0,
                                            borderRadius: 4,
                                            border: "1px solid",
                                            padding: "2px 6px",
                                            fontSize: 10,
                                            fontWeight: 700,
                                            textTransform: "uppercase",
                                            ...getTypeColor(record.type),
                                          }}
                                        >
                                          {record.type}
                                        </span>
                                        <span style={{ ...ellipsis, fontSize: 12, color: DT.foreground }}>
                                          {record.title}
                                        </span>
                                      </div>
                                      {record.summary && (
                                        <p
                                          style={{
                                            margin: "6px 0 0",
                                            fontSize: 11,
                                            lineHeight: "20px",
                                            color: DT.mutedForeground,
                                            display: "-webkit-box",
                                            WebkitLineClamp: 2,
                                            WebkitBoxOrient: "vertical",
                                            overflow: "hidden",
                                          }}
                                        >
                                          {record.summary}
                                        </p>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Apply Button */}
      <div style={{ borderTop: `1px solid ${DT.border}`, background: DT.card, padding: 16 }}>
        <button
          onClick={onCreateSession}
          disabled={isLoading || selectedRecords.size === 0}
          style={{
            display: "flex",
            width: "100%",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            borderRadius: 12,
            border: "none",
            cursor: isLoading || selectedRecords.size === 0 ? "not-allowed" : "pointer",
            padding: "10px 16px",
            fontSize: 13,
            fontWeight: 500,
            background: DT.primary,
            color: DT.primaryForeground,
            opacity: isLoading || selectedRecords.size === 0 ? 0.4 : 1,
            transition: "opacity 150ms",
            font: "inherit",
          }}
        >
          {isLoading ? (
            <>
              <LoadingOutlined spin style={{ fontSize: 16 }} />
              生成中…
            </>
          ) : (
            (actionLabel || "使用所选记录（{n}）").replace(
              "{n}",
              String(selectedRecords.size),
            )
          )}
        </button>
      </div>
    </div>
  );
}
