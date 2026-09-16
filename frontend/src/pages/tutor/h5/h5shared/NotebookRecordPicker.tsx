/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/notebook/NotebookRecordPicker.tsx，88 行）。
 * 替换点：删除 "use client"；lucide Layers→AppstoreOutlined；PickerShell/
 * PickerHeader/NotebookSelector/useNotebookSelection→本目录批9 件；Tailwind→内联
 * 样式（token 见 dtStyle.ts；surface-card→card 白底、backdropClass 原为
 * bg-[var(--background)]/65 → rgba(255,255,255,0.65)）；t() 译文命中 zh/app.json
 * 直出（"Select Notebook Records"→选择笔记本记录、"Choose records across one or
 * more notebooks to ground the next request."→从一个或多个笔记本中选择记录，作为
 * 下一轮请求的依据。；actionLabel 默认值传原键，由 NotebookSelector 内部按
 * "Use Selected Records ({n})"→使用所选记录（{n}）渲染）。交互逐字未改。
 */
import { useEffect } from "react";
import { AppstoreOutlined } from "@ant-design/icons";
import PickerShell from "./PickerShell";
import PickerHeader from "./PickerHeader";
import NotebookSelector from "./NotebookSelector";
import { useNotebookSelection } from "./useNotebookSelection";
import type { SelectedRecord } from "./notebook-selection-types";
import { DT } from "./dtStyle";

interface NotebookRecordPickerProps {
  open: boolean;
  onClose: () => void;
  onApply: (records: SelectedRecord[]) => void;
  actionLabel?: string;
}

export default function NotebookRecordPicker({
  open,
  onClose,
  onApply,
  actionLabel = "Use Selected Records ({n})",
}: NotebookRecordPickerProps) {
  const {
    notebooks,
    expandedNotebooks,
    notebookRecordsMap,
    selectedRecords,
    loadingNotebooks,
    loadingRecordsFor,
    fetchNotebooks,
    toggleNotebookExpanded,
    toggleRecordSelection,
    selectAllFromNotebook,
    deselectAllFromNotebook,
    clearAllSelections,
  } = useNotebookSelection();

  useEffect(() => {
    if (!open) return;
    void fetchNotebooks();
  }, [fetchNotebooks, open]);

  return (
    <PickerShell
      open={open}
      onClose={onClose}
      labelledBy="notebook-picker-title"
      backdropClass="rgba(255,255,255,0.65)"
    >
      <div
        style={{
          width: "100%",
          maxWidth: 896,
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
          icon={AppstoreOutlined}
          titleId="notebook-picker-title"
          title={"选择笔记本记录"}
          subtitle={
            "从一个或多个笔记本中选择记录，作为下一轮请求的依据。"
          }
          onClose={onClose}
        />
        <div style={{ background: "rgba(255,255,255,0.4)", padding: 20 }}>
          <NotebookSelector
            notebooks={notebooks}
            expandedNotebooks={expandedNotebooks}
            notebookRecordsMap={notebookRecordsMap}
            selectedRecords={selectedRecords}
            loadingNotebooks={loadingNotebooks}
            loadingRecordsFor={loadingRecordsFor}
            isLoading={false}
            onToggleExpanded={toggleNotebookExpanded}
            onToggleRecord={toggleRecordSelection}
            onSelectAll={selectAllFromNotebook}
            onDeselectAll={deselectAllFromNotebook}
            onClearAll={clearAllSelections}
            onCreateSession={() => {
              onApply(Array.from(selectedRecords.values()) as SelectedRecord[]);
              onClose();
            }}
            actionLabel={actionLabel}
          />
        </div>
      </div>
    </PickerShell>
  );
}

// 具名再导出：批9 SA-A FollowupChatComposer 以 lazy(() => import(...).then((m) => ({ default: m.NotebookRecordPicker }))) 消费（桌面原件仅 default 导出，此为批内契约对齐，非新逻辑）。
export { NotebookRecordPicker };
