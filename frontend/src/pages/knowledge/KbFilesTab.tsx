/**
 * 文件主从布局（IA批4 复刻——源 DeepTutor web/components/knowledge/KbFilesTab.tsx 1:1，antd 重建）。
 * 「文件」Tab 主从容器：左文件树（KbDocumentList）+ 右内联预览（KbFilePreview）；
 * 任务结束自动刷新列表；文件列表折叠态持久化。
 * useCollapsiblePanel：源 @/hooks/useCollapsiblePanel 的本地内联等价实现
 * （useState 折叠态 + localStorage `panel:{key}:collapsed` 持久化，不新建文件）。
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  knowledgeBaseFilePath,
  knowledgeBaseFilePreviewTextPath,
  type KnowledgeBaseFile,
} from './knowledge-api';
import type { KnowledgeBase } from './knowledge-helpers';
import type { TaskState } from './useKnowledgeProgress';
import type { FilePreviewSource } from './previewSupport';
import KbDocumentList from './KbDocumentList';
import KbFilePreview from './KbFilePreview';

interface KbFilesTabProps {
  kb: KnowledgeBase;
  task?: TaskState;
}

/** 源 useCollapsiblePanel 的内联等价实现：持久化、按 key 的面板折叠态。 */
function useCollapsiblePanel(storageKey: string, defaultCollapsed = false) {
  const [collapsed, setCollapsedState] = useState(defaultCollapsed);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(
        `panel:${storageKey}:collapsed`,
      );
      if (stored != null) {
        setCollapsedState(stored === '1');
      }
    } catch {
      // localStorage 不可用；保留默认值
    }
  }, [storageKey]);

  const setCollapsed = useCallback(
    (value: boolean | ((prev: boolean) => boolean)) => {
      setCollapsedState((prev) => {
        const next = typeof value === 'function' ? value(prev) : value;
        try {
          window.localStorage.setItem(
            `panel:${storageKey}:collapsed`,
            next ? '1' : '0',
          );
        } catch {
          // 配额 / 隐私模式；忽略
        }
        return next;
      });
    },
    [storageKey],
  );

  const toggle = useCallback(() => {
    setCollapsed((prev) => !prev);
  }, [setCollapsed]);

  return { collapsed, setCollapsed, toggle };
}

/**
 * 「文件」Tab 主从视图：左侧原始文档列表，右侧内联预览。
 * 列表可折叠成纯图标窄条，为预览内容让出横向空间。
 */
export default function KbFilesTab({ kb, task }: KbFilesTabProps) {
  const [selectedFile, setSelectedFile] = useState<KnowledgeBaseFile | null>(
    null,
  );
  const fileListPanel = useCollapsiblePanel('knowledge-file-list');

  // 上传/创建任务落定时 bump refreshKey，让新索引的文件自动出现。
  const taskExecuting = task?.executing === true;
  const [refreshKey, setRefreshKey] = useState(0);
  useEffect(() => {
    if (!taskExecuting) {
      setRefreshKey((n) => n + 1);
    }
  }, [taskExecuting]);

  const previewSource = useMemo<FilePreviewSource | null>(() => {
    if (!selectedFile) return null;
    return {
      filename: selectedFile.name,
      mimeType: selectedFile.mime_type ?? undefined,
      url: knowledgeBaseFilePath(kb.name, selectedFile.name),
      extractedTextUrl: knowledgeBaseFilePreviewTextPath(
        kb.name,
        selectedFile.name,
      ),
      size: selectedFile.size,
      id: `${kb.name}/${selectedFile.name}`,
    };
  }, [kb.name, selectedFile]);

  return (
    <div style={{ display: 'flex', height: '100%', minHeight: 0 }}>
      <KbDocumentList
        kbName={kb.name}
        refreshKey={refreshKey}
        selectedFile={selectedFile?.name ?? null}
        onSelect={setSelectedFile}
        collapsed={fileListPanel.collapsed}
        onToggleCollapsed={fileListPanel.toggle}
      />
      <div
        style={{
          display: 'flex',
          minHeight: 0,
          minWidth: 0,
          flex: 1,
          flexDirection: 'column',
        }}
      >
        <KbFilePreview
          source={previewSource}
          fileListCollapsed={fileListPanel.collapsed}
          onToggleFileList={fileListPanel.toggle}
        />
      </div>
    </div>
  );
}
