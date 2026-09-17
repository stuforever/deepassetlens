/**
 * 文件树列表（IA批4 复刻——源 DeepTutor web/components/knowledge/KbDocumentList.tsx 1:1，antd 重建）。
 * 区块：头部（标题+计数徽标+新建文件夹/刷新/收起）/ 内联新建文件夹表单 / 文件夹树
 * （展开收起 · 拖拽移动 · 文件行 hover 动作：移动到…菜单 + 删除行内确认）/ 折叠态 44px 窄条 /
 * 错误条+重试 / 加载骨架 / 空态。
 * docIconFor：源 lib/doc-attachments 的等价实现（tupu 侧 doc-attachments 已裁剪该表，
 * 按 task 规约用 antd 图标：pdf→FilePdfOutlined / 图片→FileImageOutlined / docx→FileWordOutlined /
 * xlsx→FileExcelOutlined / md→FileMarkdownOutlined / 其它→FileTextOutlined）。
 * 文案基线：dt_baseline/fieldlists/knowledge.md §3（"Delete?"/"Confirm delete"/"Delete file" 保留英文原文；
 * formatRelative 相对时间为源内硬编码英文，不经 i18n）。
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ComponentType, CSSProperties, ReactNode } from 'react';
import { Button, Input } from 'antd';
import {
  ArrowRightOutlined,
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
  DownOutlined,
  FileExcelOutlined,
  FileImageOutlined,
  FileMarkdownOutlined,
  FilePdfOutlined,
  FileTextOutlined,
  FileWordOutlined,
  FolderAddOutlined,
  FolderOutlined,
  LoadingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ReloadOutlined,
  RightOutlined,
} from '@ant-design/icons';
import {
  createKbFolder,
  deleteKbFile,
  invalidateClientCache,
  listKnowledgeBaseFiles,
  moveKbFile,
  type KnowledgeBaseFile,
} from './knowledge-api';
import { extOf, formatBytes } from '../../pages/tutor/admin/doc-attachments';

const COLOR_BORDER = '#e5e7eb';
const COLOR_MUTED_BG = '#f3f4f6';
const COLOR_MUTED_FG = '#6b7280';
const COLOR_FG = '#1f2937';
const COLOR_PRIMARY = '#1677ff';

/** 源 DocIconSpec 等价：tint 为具体色值（原 tailwind text-* 类换算）。 */
export interface DocIconSpec {
  Icon: ComponentType<{ style?: CSSProperties }>;
  tint: string;
  label: string;
}

const IMAGE_EXTS = new Set([
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.webp',
  '.bmp',
  '.svg',
]);
const EXCEL_EXTS = new Set(['.xlsx', '.xls', '.csv']);
const WORD_EXTS = new Set(['.docx', '.doc']);
const MARKDOWN_EXTS = new Set(['.md', '.markdown']);

/** 按扩展名选 antd 图标（源 docIconFor 的 antd 等价实现）。 */
export function docIconFor(filename: string): DocIconSpec {
  const ext = extOf(filename);
  if (ext === '.pdf') {
    return { Icon: FilePdfOutlined, tint: 'rgba(239,68,68,0.8)', label: 'PDF' };
  }
  if (WORD_EXTS.has(ext)) {
    return { Icon: FileWordOutlined, tint: 'rgba(59,130,246,0.8)', label: 'DOCX' };
  }
  if (EXCEL_EXTS.has(ext)) {
    return { Icon: FileExcelOutlined, tint: 'rgba(16,185,129,0.8)', label: 'XLSX' };
  }
  if (IMAGE_EXTS.has(ext)) {
    return {
      Icon: FileImageOutlined,
      tint: 'rgba(20,184,166,0.8)',
      label: ext.slice(1).toUpperCase(),
    };
  }
  if (MARKDOWN_EXTS.has(ext)) {
    return { Icon: FileMarkdownOutlined, tint: 'rgba(139,92,246,0.8)', label: 'MD' };
  }
  const label = ext ? ext.slice(1).toUpperCase() : 'FILE';
  return { Icon: FileTextOutlined, tint: 'rgba(0,0,0,0.45)', label };
}

interface KbDocumentListProps {
  kbName: string;
  /** 刷新触发器：bump 该 prop 强制重新拉取（如上传后）。 */
  refreshKey?: number;
  selectedFile: string | null;
  onSelect: (file: KnowledgeBaseFile | null) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

interface TreeNode {
  name: string; // 段标签
  path: string; // 相对 raw/ 的完整 POSIX 路径
  type: 'file' | 'folder';
  file?: KnowledgeBaseFile;
  children: TreeNode[];
}

function parentOf(path: string): string {
  const idx = path.lastIndexOf('/');
  return idx === -1 ? '' : path.slice(0, idx);
}

function buildTree(entries: KnowledgeBaseFile[]): {
  root: TreeNode[];
  folderPaths: string[];
} {
  const folders = new Map<string, TreeNode>();
  const root: TreeNode[] = [];
  const folderPaths: string[] = [];

  const ensureFolder = (path: string): TreeNode => {
    const existing = folders.get(path);
    if (existing) return existing;
    const node: TreeNode = {
      name: path.slice(path.lastIndexOf('/') + 1),
      path,
      type: 'folder',
      children: [],
    };
    folders.set(path, node);
    folderPaths.push(path);
    const parent = parentOf(path);
    if (parent) ensureFolder(parent).children.push(node);
    else root.push(node);
    return node;
  };

  // 先建文件夹，文件的父级一定存在，空文件夹也能显示。
  for (const entry of entries) {
    if (entry.type === 'folder') ensureFolder(entry.name);
  }
  for (const entry of entries) {
    if (entry.type === 'folder') continue;
    const node: TreeNode = {
      name: entry.name.slice(entry.name.lastIndexOf('/') + 1),
      path: entry.name,
      type: 'file',
      file: entry,
      children: [],
    };
    const parent = parentOf(entry.name);
    if (parent) ensureFolder(parent).children.push(node);
    else root.push(node);
  }

  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
      return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
    });
    nodes.forEach((n) => n.children.length && sortNodes(n.children));
  };
  sortNodes(root);
  folderPaths.sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
  return { root, folderPaths };
}

const iconBtnStyle: CSSProperties = {
  display: 'flex',
  height: 24,
  width: 24,
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: 6,
  padding: 0,
  border: 0,
  background: 'transparent',
  cursor: 'pointer',
};

const menuItemStyle: CSSProperties = {
  display: 'block',
  width: '100%',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  padding: '6px 10px',
  textAlign: 'left',
  fontSize: 12,
  color: COLOR_FG,
  background: 'transparent',
  border: 0,
  cursor: 'pointer',
};

/** hover/骨架动画所需的最小样式（替代源 tailwind hover:/group-hover:/animate-pulse 语义）。 */
const ListStyles = () => (
  <style>{`
.kbdl-ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 1px; }
.kbdl-row { transition: background-color .15s ease, box-shadow .15s ease; }
.kbdl-row-hoverable:hover { background: rgba(243,244,246,0.5); }
.kbdl-row-active { background: rgba(22,119,255,0.1); }
.kbdl-row-drag { opacity: 0.5; }
.kbdl-row.kbdl-drop { background: rgba(22,119,255,0.15); box-shadow: inset 0 0 0 1px rgba(22,119,255,0.4); }
.kbdl-actions { opacity: 0; transition: opacity .15s ease; }
.kbdl-row:hover .kbdl-actions { opacity: 1; }
.kbdl-icon-btn { color: #6b7280; }
.kbdl-icon-btn:hover { background: #f3f4f6; color: #1f2937; }
.kbdl-icon-btn:disabled { opacity: 0.4; cursor: default; }
.kbdl-icon-btn:disabled:hover { background: transparent; color: #6b7280; }
.kbdl-danger-hover:hover { background: #fef2f2; color: #dc2626; }
.kbdl-menu-item:hover { background: rgba(243,244,246,0.6); }
.kbdl-pulse { animation: kbdl-pulse 1.6s ease-in-out infinite; }
@keyframes kbdl-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
`}</style>
);

export default function KbDocumentList({
  kbName,
  refreshKey = 0,
  selectedFile,
  onSelect,
  collapsed,
  onToggleCollapsed,
}: KbDocumentListProps) {
  const [files, setFiles] = useState<KnowledgeBaseFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [newFolderOpen, setNewFolderOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [moveMenuFor, setMoveMenuFor] = useState<string | null>(null);
  const [confirmDeleteFor, setConfirmDeleteFor] = useState<string | null>(null);
  const [dragPath, setDragPath] = useState<string | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    async (force = false) => {
      setLoading(true);
      setError(null);
      try {
        if (force) invalidateClientCache(`knowledge:files:${kbName}`);
        const next = await listKnowledgeBaseFiles(kbName, { force });
        setFiles(next);
        // 默认展开全部文件夹，文件无需逐层翻找即可见。
        setExpanded(
          new Set(next.filter((e) => e.type === 'folder').map((e) => e.name)),
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    },
    [kbName],
  );

  useEffect(() => {
    void load(refreshKey > 0);
  }, [load, refreshKey]);

  const { root, folderPaths } = useMemo(() => buildTree(files), [files]);
  const fileEntries = useMemo(
    () => files.filter((e) => e.type !== 'folder'),
    [files],
  );

  const toggleFolder = (path: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });

  const handleCreateFolder = async () => {
    const name = newFolderName.trim();
    if (!name) return;
    setBusy(true);
    try {
      await createKbFolder(kbName, name);
      setNewFolderName('');
      setNewFolderOpen(false);
      await load(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const handleMove = async (source: string, destFolder: string) => {
    setMoveMenuFor(null);
    setDropTarget(null);
    setDragPath(null);
    if (parentOf(source) === destFolder) return; // 已在该目录
    setBusy(true);
    try {
      await moveKbFile(kbName, source, destFolder);
      const basename = source.slice(source.lastIndexOf('/') + 1);
      const newPath = destFolder ? `${destFolder}/${basename}` : basename;
      await load(true);
      // 若移动的是当前预览文件，保持预览指向移动后的文件。
      if (selectedFile === source) {
        const moved = files.find((f) => f.name === source);
        onSelect({
          ...(moved ?? { name: newPath }),
          name: newPath,
          type: 'file',
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (path: string) => {
    setConfirmDeleteFor(null);
    setBusy(true);
    try {
      await deleteKbFile(kbName, path);
      // 若删除的是当前预览文件，清空预览。
      if (selectedFile === path) onSelect(null);
      await load(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  if (collapsed) {
    return (
      <aside
        style={{
          display: 'flex',
          height: '100%',
          width: 44,
          flexShrink: 0,
          flexDirection: 'column',
          alignItems: 'center',
          gap: 4,
          borderRight: `1px solid ${COLOR_BORDER}`,
          background: 'rgba(255,255,255,0.4)',
          padding: '8px 0',
        }}
      >
        <ListStyles />
        <button
          type="button"
          onClick={onToggleCollapsed}
          title="展开"
          aria-label="展开"
          className="kbdl-icon-btn"
          style={{ ...iconBtnStyle, height: 28, width: 28 }}
        >
          <MenuUnfoldOutlined style={{ fontSize: 13 }} />
        </button>
        <div
          style={{
            margin: '4px 0',
            height: 1,
            width: 24,
            background: 'rgba(229,231,235,0.6)',
          }}
        />
        <div
          style={{
            display: 'flex',
            width: '100%',
            flex: 1,
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
            overflowY: 'auto',
            paddingBottom: 8,
          }}
        >
          {fileEntries.map((file) => {
            const spec = docIconFor(file.name);
            const Icon = spec.Icon;
            const active = selectedFile === file.name;
            return (
              <button
                key={file.name}
                type="button"
                onClick={() => onSelect(file)}
                title={file.name}
                aria-label={file.name}
                className="kbdl-icon-btn"
                style={{
                  ...iconBtnStyle,
                  position: 'relative',
                  height: 32,
                  width: 32,
                  background: active ? 'rgba(22,119,255,0.12)' : undefined,
                  boxShadow: active
                    ? 'inset 0 0 0 1px rgba(22,119,255,0.4)'
                    : undefined,
                }}
              >
                {active && (
                  <span
                    style={{
                      position: 'absolute',
                      left: -4,
                      top: '50%',
                      height: 16,
                      width: 2.5,
                      transform: 'translateY(-50%)',
                      borderRadius: 999,
                      background: COLOR_PRIMARY,
                    }}
                  />
                )}
                <Icon style={{ fontSize: 13, color: spec.tint }} />
              </button>
            );
          })}
        </div>
      </aside>
    );
  }

  const renderNode = (node: TreeNode, depth: number): ReactNode => {
    const indent = { paddingLeft: `${depth * 12 + 8}px` };
    if (node.type === 'folder') {
      const open = expanded.has(node.path);
      const isDrop = dropTarget === node.path;
      return (
        <li key={`d:${node.path}`}>
          <div
            onClick={() => toggleFolder(node.path)}
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setDropTarget(node.path);
            }}
            onDragLeave={() =>
              setDropTarget((cur) => (cur === node.path ? null : cur))
            }
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              const src = e.dataTransfer.getData('text/plain');
              if (src) void handleMove(src, node.path);
            }}
            style={{
              ...indent,
              display: 'flex',
              cursor: 'pointer',
              alignItems: 'center',
              gap: 4,
              borderRadius: 6,
              paddingTop: 6,
              paddingBottom: 6,
              paddingRight: 8,
            }}
            className={`kbdl-row kbdl-row-hoverable ${isDrop ? 'kbdl-drop' : ''}`}
          >
            {open ? (
              <DownOutlined
                style={{ fontSize: 12, flexShrink: 0, color: COLOR_MUTED_FG }}
              />
            ) : (
              <RightOutlined
                style={{ fontSize: 12, flexShrink: 0, color: COLOR_MUTED_FG }}
              />
            )}
            <FolderOutlined
              style={{ fontSize: 14, flexShrink: 0, color: COLOR_MUTED_FG }}
            />
            <span
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontSize: 12,
                fontWeight: 500,
                color: COLOR_FG,
              }}
            >
              {node.name}
            </span>
          </div>
          {open && node.children.length > 0 && (
            <ul className="kbdl-ul">
              {node.children.map((child) => renderNode(child, depth + 1))}
            </ul>
          )}
        </li>
      );
    }

    const spec = docIconFor(node.name);
    const Icon = spec.Icon;
    const active = selectedFile === node.path;
    const file = node.file!;
    return (
      <li key={`f:${node.path}`} style={{ position: 'relative' }}>
        <div
          draggable
          onDragStart={(e) => {
            e.dataTransfer.setData('text/plain', node.path);
            e.dataTransfer.effectAllowed = 'move';
            setDragPath(node.path);
          }}
          onDragEnd={() => setDragPath(null)}
          style={{
            ...indent,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            borderRadius: 6,
            paddingTop: 6,
            paddingBottom: 6,
            paddingRight: 4,
          }}
          className={`kbdl-row ${
            active ? 'kbdl-row-active' : 'kbdl-row-hoverable'
          } ${dragPath === node.path ? 'kbdl-row-drag' : ''}`}
        >
          <button
            type="button"
            onClick={() => onSelect(file)}
            title={node.path}
            style={{
              display: 'flex',
              minWidth: 0,
              flex: 1,
              alignItems: 'center',
              gap: 8,
              textAlign: 'left',
              border: 0,
              background: 'transparent',
              padding: 0,
              cursor: 'pointer',
            }}
          >
            <Icon
              style={{ fontSize: 13, flexShrink: 0, color: spec.tint }}
            />
            <div style={{ minWidth: 0, flex: 1 }}>
              <div
                style={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  fontSize: 12,
                  fontWeight: 500,
                  color: COLOR_FG,
                }}
              >
                {node.name}
              </div>
              <div
                style={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  fontSize: 10,
                  color: COLOR_MUTED_FG,
                }}
              >
                {file.size ? formatBytes(file.size) : ''}
                {file.modified ? ` · ${formatRelative(file.modified)}` : ''}
              </div>
            </div>
          </button>
          {confirmDeleteFor === node.path ? (
            <div
              style={{
                display: 'flex',
                flexShrink: 0,
                alignItems: 'center',
                gap: 2,
                paddingRight: 2,
              }}
            >
              <span
                style={{
                  padding: '0 2px',
                  fontSize: 10,
                  fontWeight: 500,
                  color: '#dc2626',
                }}
              >
                {/* zh 未收录 → 运行时回退英文（保留原文） */}
                Delete?
              </span>
              <button
                type="button"
                onClick={() => void handleDelete(node.path)}
                disabled={busy}
                className="kbdl-danger-hover"
                title="Confirm delete"
                aria-label="Confirm delete"
                style={{
                  ...iconBtnStyle,
                  height: 22,
                  width: 22,
                  color: '#dc2626',
                }}
              >
                <CheckOutlined style={{ fontSize: 14 }} />
              </button>
              <button
                type="button"
                onClick={() => setConfirmDeleteFor(null)}
                className="kbdl-icon-btn"
                title="取消"
                aria-label="取消"
                style={{ ...iconBtnStyle, height: 22, width: 22 }}
              >
                <CloseOutlined style={{ fontSize: 14 }} />
              </button>
            </div>
          ) : (
            <div
              className="kbdl-actions"
              style={{ display: 'flex', flexShrink: 0, alignItems: 'center' }}
            >
              <button
                type="button"
                onClick={() => {
                  setConfirmDeleteFor(null);
                  setMoveMenuFor((cur) =>
                    cur === node.path ? null : node.path,
                  );
                }}
                className="kbdl-icon-btn"
                title="移动到…"
                aria-label="移动到…"
                style={{ ...iconBtnStyle, height: 22, width: 22 }}
              >
                <ArrowRightOutlined style={{ fontSize: 14 }} />
              </button>
              <button
                type="button"
                onClick={() => {
                  setMoveMenuFor(null);
                  setConfirmDeleteFor(node.path);
                }}
                className="kbdl-icon-btn kbdl-danger-hover"
                title="Delete file"
                aria-label="Delete file"
                style={{ ...iconBtnStyle, height: 22, width: 22 }}
              >
                <DeleteOutlined style={{ fontSize: 14 }} />
              </button>
            </div>
          )}
        </div>

        {moveMenuFor === node.path && (
          <>
            <div
              style={{ position: 'fixed', inset: 0, zIndex: 10 }}
              onClick={() => setMoveMenuFor(null)}
            />
            <div
              style={{
                position: 'absolute',
                right: 4,
                top: 32,
                zIndex: 20,
                maxHeight: 240,
                width: 176,
                overflowY: 'auto',
                borderRadius: 8,
                border: `1px solid ${COLOR_BORDER}`,
                background: '#ffffff',
                padding: '4px 0',
                boxShadow:
                  '0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)',
              }}
            >
              <div
                style={{
                  padding: '4px 10px',
                  fontSize: 10,
                  textTransform: 'uppercase',
                  letterSpacing: 0.5,
                  color: COLOR_MUTED_FG,
                }}
              >
                移动到
              </div>
              {parentOf(node.path) !== '' && (
                <button
                  type="button"
                  onClick={() => void handleMove(node.path, '')}
                  className="kbdl-menu-item"
                  style={menuItemStyle}
                >
                  / 根目录
                </button>
              )}
              {folderPaths
                .filter((p) => p !== parentOf(node.path))
                .map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => void handleMove(node.path, p)}
                    className="kbdl-menu-item"
                    style={menuItemStyle}
                  >
                    {p}
                  </button>
                ))}
              {folderPaths.length === 0 && parentOf(node.path) === '' && (
                <div
                  style={{
                    padding: '6px 10px',
                    fontSize: 11,
                    color: COLOR_MUTED_FG,
                  }}
                >
                  暂无文件夹
                </div>
              )}
            </div>
          </>
        )}
      </li>
    );
  };

  return (
    <aside
      style={{
        display: 'flex',
        height: '100%',
        width: 220,
        flexShrink: 0,
        flexDirection: 'column',
        borderRight: `1px solid ${COLOR_BORDER}`,
        background: 'rgba(255,255,255,0.4)',
      }}
    >
      <ListStyles />
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 4,
          padding: '10px 10px 6px',
        }}
      >
        <div style={{ display: 'flex', minWidth: 0, alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 12, fontWeight: 500, color: COLOR_FG }}>
            文件
          </span>
          <span
            style={{
              borderRadius: 999,
              background: COLOR_MUTED_BG,
              padding: '0 6px',
              fontSize: 10,
              lineHeight: '16px',
              color: COLOR_MUTED_FG,
            }}
          >
            {fileEntries.length}
          </span>
        </div>
        <div style={{ display: 'flex', flexShrink: 0, alignItems: 'center', gap: 2 }}>
          <button
            type="button"
            onClick={() => {
              setNewFolderOpen((v) => !v);
              setNewFolderName('');
            }}
            className="kbdl-icon-btn"
            title="新建文件夹"
            aria-label="新建文件夹"
            style={iconBtnStyle}
          >
            <FolderAddOutlined style={{ fontSize: 13 }} />
          </button>
          <button
            type="button"
            onClick={() => void load(true)}
            className="kbdl-icon-btn"
            title="刷新"
            aria-label="刷新"
            disabled={loading || busy}
            style={iconBtnStyle}
          >
            {loading ? (
              <LoadingOutlined spin style={{ fontSize: 12 }} />
            ) : (
              <ReloadOutlined style={{ fontSize: 12 }} />
            )}
          </button>
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="kbdl-icon-btn"
            title="收起"
            aria-label="收起"
            style={iconBtnStyle}
          >
            <MenuFoldOutlined style={{ fontSize: 12 }} />
          </button>
        </div>
      </div>

      {newFolderOpen && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0 10px 6px' }}>
          <Input
            size="small"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void handleCreateFolder();
              if (e.key === 'Escape') setNewFolderOpen(false);
            }}
            autoFocus
            placeholder="文件夹名称"
            style={{ minWidth: 0, flex: 1, fontSize: 12 }}
          />
          <Button
            size="small"
            type="primary"
            onClick={() => void handleCreateFolder()}
            disabled={busy || !newFolderName.trim()}
            style={{ flexShrink: 0, fontSize: 11, height: 24, padding: '0 8px' }}
          >
            添加
          </Button>
        </div>
      )}

      <div
        style={{ flex: 1, overflowY: 'auto', padding: '0 6px 10px' }}
        onDragOver={(e) => {
          e.preventDefault();
          setDropTarget('');
        }}
        onDrop={(e) => {
          e.preventDefault();
          const src = e.dataTransfer.getData('text/plain');
          if (src) void handleMove(src, '');
        }}
      >
        {error ? (
          <div
            style={{
              borderRadius: 6,
              border: '1px solid #fecaca',
              background: '#fef2f2',
              padding: '8px 10px',
              fontSize: 11,
              color: '#b91c1c',
            }}
          >
            {error}
            <button
              type="button"
              onClick={() => void load(true)}
              style={{
                marginLeft: 4,
                textDecoration: 'underline',
                border: 0,
                background: 'transparent',
                color: 'inherit',
                cursor: 'pointer',
                padding: 0,
                fontSize: 11,
              }}
            >
              重试
            </button>
          </div>
        ) : loading && !files.length ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="kbdl-pulse"
                style={{
                  height: 32,
                  borderRadius: 6,
                  background: 'rgba(243,244,246,0.4)',
                }}
              />
            ))}
          </div>
        ) : fileEntries.length === 0 && folderPaths.length === 0 ? (
          <div
            style={{
              padding: '24px 8px',
              textAlign: 'center',
              fontSize: 11,
              color: COLOR_MUTED_FG,
            }}
          >
            <div style={{ marginBottom: 6 }}>
              <FolderOutlined style={{ fontSize: 14, opacity: 0.5 }} />
            </div>
            暂无文件。请使用「添加文档」标签页添加。
          </div>
        ) : (
          <ul className="kbdl-ul">{root.map((n) => renderNode(n, 0))}</ul>
        )}
      </div>
    </aside>
  );
}

function formatRelative(unixSeconds: number): string {
  const ts = unixSeconds * 1000;
  const diff = Date.now() - ts;
  if (diff < 60_000) return 'just now';
  if (diff < 60 * 60_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 24 * 60 * 60_000)
    return `${Math.floor(diff / (60 * 60_000))}h ago`;
  if (diff < 30 * 24 * 60 * 60_000)
    return `${Math.floor(diff / (24 * 60 * 60_000))}d ago`;
  return new Date(ts).toLocaleDateString();
}
