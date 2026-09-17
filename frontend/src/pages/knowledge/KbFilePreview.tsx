/**
 * 文件预览右栏（IA批4 复刻——源 DeepTutor web/components/knowledge/KbFilePreview.tsx 1:1，antd 重建）。
 * 「文件」Tab 主从布局右栏的内联文件预览——头部（文件名+图标+动作组：文件列表开关/全屏/下载/复制链接）+
 * 体部按 previewKindFor 分发到 ./previewSupport 的渲染器（Pdf/Image/Svg/Markdown/Text/Docx/Xlsx/OfficeText/Fallback）。
 * 全屏 = fixed 覆盖层 + Esc 退出；复制链接 = navigator.clipboard + 1.5s 对勾反馈。
 * docIconFor/formatBytes：docIconFor 复用 KbDocumentList 的等价实现（tupu 侧 doc-attachments 已裁剪图标表）；
 * formatBytes 来自 ../../pages/tutor/admin/doc-attachments。
 */
import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import {
  CheckOutlined,
  CopyOutlined,
  DownloadOutlined,
  FileTextOutlined,
  FullscreenExitOutlined,
  FullscreenOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { apiUrl } from './knowledge-api';
import { formatBytes } from '../../pages/tutor/admin/doc-attachments';
import { docIconFor } from './KbDocumentList';
import {
  previewKindFor,
  resolveSourceUrl,
  type FilePreviewSource,
} from './previewSupport';
// 各 Preview 渲染组件（并行件：组件名=源 previewers 文件名去掉扩展名）
import PdfPreview from './previewers/PdfPreview';
import ImagePreview from './previewers/ImagePreview';
import SvgPreview from './previewers/SvgPreview';
import MarkdownPreview from './previewers/MarkdownPreview';
import TextPreview from './previewers/TextPreview';
import DocxPreview from './previewers/DocxPreview';
import XlsxPreview from './previewers/XlsxPreview';
import OfficeTextPreview from './previewers/OfficeTextPreview';
import FallbackPreview from './previewers/FallbackPreview';

const COLOR_BORDER = '#e5e7eb';
const COLOR_MUTED_BG = '#f3f4f6';
const COLOR_MUTED_FG = '#6b7280';
const COLOR_FG = '#1f2937';

interface KbFilePreviewProps {
  source: FilePreviewSource | null;
  /**
   * 可选插槽，渲染在面包屑/标题右侧——用于在预览头部内联展示元信息
   * （如文件数、修改时间），因为本组件是主从布局的右栏，其上没有独立头部。
   */
  metaSuffix?: ReactNode;
  /** 文件列表当前折叠态。提供时头部显示开关，用户无需去文件列表找开关即可加宽预览。 */
  fileListCollapsed?: boolean;
  onToggleFileList?: () => void;
}

const iconBtnStyle: CSSProperties = {
  display: 'flex',
  height: 28,
  width: 28,
  flexShrink: 0,
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: 6,
  padding: 0,
  border: 0,
  background: 'transparent',
  cursor: 'pointer',
  textDecoration: 'none',
};

/** hover 反馈（替代源 tailwind hover: 语义）。 */
const PreviewStyles = () => (
  <style>{`
.kbfp-icon-btn { color: #6b7280; }
.kbfp-icon-btn:hover { background: #f3f4f6; color: #1f2937; }
`}</style>
);

/**
 * 适配知识库主从布局的内联文件预览面板：头部（文件名+动作）在上，体部（渲染器）在下。
 * 无抽屉动画、无 portal，挂载时机由父级决定。
 */
export default function KbFilePreview({
  source,
  metaSuffix,
  fileListCollapsed,
  onToggleFileList,
}: KbFilePreviewProps) {
  const [copied, setCopied] = useState(false);
  // 主从布局限制内联面板高度；全屏让长 PDF 用满整个窗口。
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    if (!fullscreen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setFullscreen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [fullscreen]);

  const previewUrl = useMemo(
    () => (source ? resolveSourceUrl(source, apiUrl) : null),
    [source],
  );
  const extractedTextUrl = useMemo(() => {
    if (!source?.extractedTextUrl) return null;
    return source.extractedTextUrl.startsWith('http')
      ? source.extractedTextUrl
      : apiUrl(source.extractedTextUrl);
  }, [source]);
  const kind = useMemo(
    () => (source ? previewKindFor(source) : null),
    [source],
  );

  if (!source) {
    return (
      <div style={{ display: 'flex', height: '100%', flexDirection: 'column' }}>
        <PreviewStyles />
        {onToggleFileList && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              borderBottom: `1px solid ${COLOR_BORDER}`,
              background: 'rgba(255,255,255,0.4)',
              padding: '6px 12px',
            }}
          >
            <button
              type="button"
              onClick={onToggleFileList}
              className="kbfp-icon-btn"
              title={fileListCollapsed ? '显示文件列表' : '隐藏文件列表'}
              aria-label={fileListCollapsed ? '显示文件列表' : '隐藏文件列表'}
              style={iconBtnStyle}
            >
              {fileListCollapsed ? (
                <MenuUnfoldOutlined style={{ fontSize: 13 }} />
              ) : (
                <MenuFoldOutlined style={{ fontSize: 13 }} />
              )}
            </button>
          </div>
        )}
        <div
          style={{
            display: 'flex',
            flex: 1,
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            padding: '48px 24px',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              display: 'flex',
              height: 48,
              width: 48,
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 16,
              background: COLOR_MUTED_BG,
              color: COLOR_MUTED_FG,
            }}
          >
            <FileTextOutlined style={{ fontSize: 20 }} />
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500, color: COLOR_FG }}>
              请选择一个文件以预览
            </div>
            <p
              style={{
                margin: '4px auto 0',
                maxWidth: 320,
                fontSize: 11.5,
                lineHeight: 1.6,
                color: COLOR_MUTED_FG,
              }}
            >
              从左侧列表选择任意文档，可在此处直接预览，无需离开知识库。
            </p>
          </div>
        </div>
      </div>
    );
  }

  const spec = docIconFor(source.filename);
  const HeaderIcon = spec.Icon;
  const sizeLabel = source.size ? formatBytes(source.size) : '';

  const handleCopy = async () => {
    if (!previewUrl) return;
    try {
      await navigator.clipboard.writeText(previewUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // 剪贴板被拒绝；忽略
    }
  };

  return (
    <div
      style={
        fullscreen
          ? {
              position: 'fixed',
              inset: 0,
              zIndex: 50,
              display: 'flex',
              minHeight: 0,
              flexDirection: 'column',
              background: 'var(--background, #fff)',
            }
          : {
              margin: '0 auto',
              display: 'flex',
              height: '100%',
              width: '100%',
              minHeight: 0,
              maxWidth: 1024,
              flexDirection: 'column',
            }
      }
    >
      <PreviewStyles />
      {/* 头部 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          borderBottom: `1px solid ${COLOR_BORDER}`,
          background: 'rgba(255,255,255,0.8)',
          padding: '8px 12px',
        }}
      >
        {onToggleFileList && !fullscreen && (
          <button
            type="button"
            onClick={onToggleFileList}
            className="kbfp-icon-btn"
            title={fileListCollapsed ? '显示文件列表' : '隐藏文件列表'}
            aria-label={fileListCollapsed ? '显示文件列表' : '隐藏文件列表'}
            style={iconBtnStyle}
          >
            {fileListCollapsed ? (
              <MenuUnfoldOutlined style={{ fontSize: 13 }} />
            ) : (
              <MenuFoldOutlined style={{ fontSize: 13 }} />
            )}
          </button>
        )}
        <div
          style={{
            display: 'flex',
            height: 32,
            width: 32,
            flexShrink: 0,
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 6,
            background: 'rgba(243,244,246,0.6)',
          }}
        >
          <HeaderIcon style={{ fontSize: 15, color: spec.tint }} />
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div
            style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontSize: 12.5,
              fontWeight: 500,
              color: COLOR_FG,
            }}
          >
            {source.filename}
          </div>
          <div
            style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontSize: 10.5,
              textTransform: 'uppercase',
              letterSpacing: 0.5,
              color: COLOR_MUTED_FG,
            }}
          >
            {sizeLabel ? `${spec.label} · ${sizeLabel}` : spec.label}
          </div>
        </div>

        {metaSuffix && (
          <div style={{ flexShrink: 0, fontSize: 11, color: COLOR_MUTED_FG }}>
            {metaSuffix}
          </div>
        )}

        <button
          type="button"
          onClick={() => setFullscreen((value) => !value)}
          className="kbfp-icon-btn"
          title={fullscreen ? '退出全屏' : '全屏'}
          aria-label={fullscreen ? '退出全屏' : '全屏'}
          style={iconBtnStyle}
        >
          {fullscreen ? (
            <FullscreenExitOutlined style={{ fontSize: 13 }} />
          ) : (
            <FullscreenOutlined style={{ fontSize: 13 }} />
          )}
        </button>

        {previewUrl && (
          <>
            <a
              href={previewUrl}
              download={source.filename}
              className="kbfp-icon-btn"
              title="下载"
              aria-label="下载"
              style={iconBtnStyle}
            >
              <DownloadOutlined style={{ fontSize: 13 }} />
            </a>
            <button
              type="button"
              onClick={() => void handleCopy()}
              className="kbfp-icon-btn"
              title="复制链接"
              aria-label="复制链接"
              style={iconBtnStyle}
            >
              {copied ? (
                <CheckOutlined style={{ fontSize: 13, color: '#10b981' }} />
              ) : (
                <CopyOutlined style={{ fontSize: 13 }} />
              )}
            </button>
          </>
        )}
      </div>

      {/* 体部 */}
      <div style={{ position: 'relative', minHeight: 0, flex: 1, overflow: 'hidden' }}>
        {!previewUrl ? (
          <FallbackPreview
            filename={source.filename}
            url={null}
            reason="legacy"
          />
        ) : kind === 'office-text' ? (
          <OfficeTextPreview
            filename={source.filename}
            extractedText={source.extractedText}
            extractedTextUrl={extractedTextUrl}
            url={previewUrl}
          />
        ) : kind === 'pdf' ? (
          <PdfPreview url={previewUrl} filename={source.filename} />
        ) : kind === 'docx' ? (
          <DocxPreview url={previewUrl} />
        ) : kind === 'xlsx' ? (
          <XlsxPreview url={previewUrl} />
        ) : kind === 'image' ? (
          <ImagePreview url={previewUrl} filename={source.filename} />
        ) : kind === 'svg' ? (
          <SvgPreview url={previewUrl} filename={source.filename} />
        ) : kind === 'markdown' ? (
          <div style={{ height: '100%', overflowY: 'auto' }}>
            <MarkdownPreview url={previewUrl} />
          </div>
        ) : kind === 'code' || kind === 'text' ? (
          <div style={{ height: '100%', overflowY: 'auto' }}>
            <TextPreview url={previewUrl} filename={source.filename} />
          </div>
        ) : (
          <FallbackPreview filename={source.filename} url={previewUrl} />
        )}
      </div>
    </div>
  );
}
