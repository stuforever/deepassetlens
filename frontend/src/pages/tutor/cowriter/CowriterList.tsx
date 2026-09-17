/**
 * CowriterList —— 智能写作（Co-Writer）文档列表页（桌面 workspace）。
 * 1:1 复刻自原仓 DeepTutor web/app/(workspace)/co-writer/page.tsx（266 行，批6 6.3）。
 * 复刻来源：Next.js("use client") + Tailwind + react-i18next + lucide-react + next/navigation
 * 替换点：
 *  - "use client" 删除；useRouter(next/navigation) → useNavigate/useLocation(react-router-dom)；
 *    源 router.push(`/co-writer/${doc.id}`) → navigate(`${pathname}?doc=<id>`)（任务指定 tupu 侧
 *    编辑页由同路径 ?doc=<id> 承接；pathname 动态取当前挂载路径，"列表→编辑"语义等价）；
 *  - react-i18next → 中文直出（译文逐键取自原仓 web/locales/zh/app.json：
 *    Co-Writer→智能写作、New draft→新建草稿、From template→从模板创建、Start from template→
 *    从模板开始、No drafts yet→暂无草稿、Untitled draft→未命名草稿、Updated→最近更新、
 *    ago→前、Delete draft→删除草稿、Click again to confirm→再次点击确认、Empty draft→空白草稿）；
 *  - lucide-react → @ant-design/icons 语义就近：FileText→FileTextOutlined、PenLine→EditOutlined、
 *    Plus→PlusOutlined、Trash2→DeleteOutlined、Loader2→LoadingOutlined(spin)；
 *  - import 契约：源 @/lib/co-writer-api / @/lib/co-writer-events / ./sampleTemplate →
 *    并行批已落盘移植件 './co-writer-api'、'./co-writer-events'、'./sampleTemplate'
 *    （逐字 1:1，导出契约已逐项核对一致；endpoint /api/v1/co_writer，fetch 相对路径，
 *    tupu 由 setupProxy 转发 28000）；
 *  - Tailwind → antd 组件 + 内联样式 + <style> 注入（网格断点 sm:2/xl:3、卡片 hover 边框、
 *    删除钮 group-hover 显隐无法用内联 style 表达，语义注入 <style>）；颜色映射沿用
 *    BookLibrary 登记口径：border→#e4e4e7、muted→#f4f4f5、muted-foreground→#6b7280、
 *    foreground→rgba(0,0,0,0.88)、primary→#1677ff、ring/hover→#1677ff、rose 按 tailwind 标准值；
 *  - next/image：本页无图片。
 * 不变：relativeTime 单位算法、文档列表卡（图标/标题/相对时间/预览 line-clamp-4）、
 *       两次点击删除确认（pending 态 rose 高亮 + title 提示）、新建（空白/模板）成功后进编辑、
 *       加载态/空态（双按钮）/错误条、卡片 role="button"+tabIndex+Enter/空格键盘语义。
 */
import { useCallback, useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  LoadingOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import {
  createCoWriterDocument,
  deleteCoWriterDocument,
  listCoWriterDocuments,
  type CoWriterDocumentSummary,
} from "./co-writer-api";
import { notifyCoWriterChanged } from "./co-writer-events";
import { CO_WRITER_SAMPLE_TEMPLATE } from "./sampleTemplate";

/* ── 页面（源 page.tsx 逐区块移植）────────────────────────────────────────── */

function relativeTime(seconds: number): string {
  if (!seconds || Number.isNaN(seconds)) return "";
  const diff = Date.now() / 1000 - seconds;
  // Compact locale-neutral units; the card wraps this as "Updated {x} ago".
  if (diff < 60) return "1m";
  const mins = Math.floor(diff / 60);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo`;
  return `${Math.floor(months / 12)}y`;
}

/** -webkit-line-clamp 截断（line-clamp-4）。 */
function clampLines(n: number): CSSProperties {
  return {
    display: "-webkit-box",
    WebkitLineClamp: n,
    WebkitBoxOrient: "vertical",
    overflow: "hidden",
  };
}

/** 网格断点（grid-cols-1 sm:grid-cols-2 xl:grid-cols-3）与卡片悬停态、删除钮 group-hover 显隐。 */
const CW_CSS = `
.cw-grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
@media (min-width: 640px) { .cw-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (min-width: 1280px) { .cw-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
.cw-card { position: relative; display: flex; flex-direction: column; height: 176px; padding: 16px; border: 1px solid #e4e4e7; border-radius: 16px; cursor: pointer; text-align: left; transition: border-color 0.15s; outline: none; }
.cw-card:hover, .cw-card:focus-visible { border-color: #1677ff; }
.cw-del { flex-shrink: 0; border: none; background: transparent; border-radius: 6px; padding: 4px; line-height: 0; cursor: pointer; color: rgba(107, 114, 128, 0.6); opacity: 0; transition: opacity 0.15s, background-color 0.15s, color 0.15s; }
.cw-card:hover .cw-del { opacity: 1; }
.cw-del:hover:not(:disabled) { background: rgba(244, 63, 94, 0.1); color: #e11d48; }
.cw-del[data-pending="1"] { background: rgba(244, 63, 94, 0.15); color: #e11d48; opacity: 1; }
.cw-del:disabled { opacity: 0.5; cursor: default; }
`;

export default function CoWriterHomePage() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<CoWriterDocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  // 源 router.push(`/co-writer/${doc.id}`) 的 tupu 等价：参数路由 /e/tutor/co-writer/:docId
  // （IA批6 expertPages 注册，KeepAlive 路径切换才换渲染——?doc= 仅改查询不触发路由，已实测）。
  const goEdit = useCallback(
    (docId: string) => {
      navigate(`/e/tutor/co-writer/${encodeURIComponent(docId)}`);
    },
    [navigate],
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const docs = await listCoWriterDocuments();
      setDocuments(docs);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleCreate = useCallback(
    async (withTemplate: boolean) => {
      if (creating) return;
      setCreating(true);
      setError("");
      try {
        const document = await createCoWriterDocument({
          content: withTemplate ? CO_WRITER_SAMPLE_TEMPLATE : "",
        });
        notifyCoWriterChanged();
        goEdit(document.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setCreating(false);
      }
    },
    [creating, goEdit],
  );

  const handleDelete = useCallback(
    async (docId: string) => {
      if (deletingId) return;
      setDeletingId(docId);
      setError("");
      try {
        await deleteCoWriterDocument(docId);
        setDocuments((prev) => prev.filter((doc) => doc.id !== docId));
        setPendingDeleteId(null);
        notifyCoWriterChanged();
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setDeletingId(null);
      }
    },
    [deletingId],
  );

  const renderEmpty = () => (
    <div
      style={{
        minHeight: 360,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 16,
        border: "1px dashed #e4e4e7",
        padding: "0 32px",
        textAlign: "center",
      }}
    >
      <EditOutlined
        style={{ fontSize: 30, marginBottom: 12, color: "#6b7280" }}
      />
      <p style={{ margin: 0, fontSize: 14, fontWeight: 500, color: "rgba(0,0,0,0.88)" }}>
        暂无草稿
      </p>
      <p
        style={{
          marginTop: 6,
          maxWidth: 384,
          fontSize: 12.5,
          lineHeight: 1.625,
          color: "#6b7280",
        }}
      >
        新建一个 Markdown 草稿开始写作。
      </p>
      <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <Button
          type="primary"
          onClick={() => handleCreate(false)}
          disabled={creating}
          icon={creating ? <LoadingOutlined spin /> : <PlusOutlined />}
          style={{ fontSize: 12.5, height: "auto", padding: "8px 14px", borderRadius: 8 }}
        >
          新建草稿
        </Button>
        <Button
          onClick={() => handleCreate(true)}
          disabled={creating}
          icon={<FileTextOutlined />}
          style={{ fontSize: 12.5, height: "auto", padding: "8px 14px", borderRadius: 8 }}
        >
          从模板开始
        </Button>
      </div>
    </div>
  );

  return (
    <div style={{ height: "100%", overflowY: "auto", background: "#fff" }}>
      <style>{CW_CSS}</style>
      <div style={{ maxWidth: 1024, margin: "0 auto", padding: "32px 24px" }}>
        <header
          style={{
            marginBottom: 28,
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            gap: 16,
          }}
        >
          <div>
            <h1
              style={{
                margin: 0,
                fontSize: 19,
                fontWeight: 600,
                letterSpacing: "-0.025em",
                color: "rgba(0,0,0,0.88)",
              }}
            >
              智能写作
            </h1>
            <p style={{ marginTop: 4, fontSize: 12.5, color: "#6b7280" }}>
              管理你的 Markdown 草稿与项目。
            </p>
          </div>
          <div style={{ display: "flex", flexShrink: 0, alignItems: "center", gap: 8 }}>
            <Button
              onClick={() => handleCreate(true)}
              disabled={creating}
              icon={<FileTextOutlined />}
              style={{ fontSize: 12.5, height: "auto", padding: "8px 14px", borderRadius: 8 }}
            >
              从模板创建
            </Button>
            <Button
              type="primary"
              onClick={() => handleCreate(false)}
              disabled={creating}
              icon={creating ? <LoadingOutlined spin /> : <PlusOutlined />}
              style={{ fontSize: 12.5, height: "auto", padding: "8px 14px", borderRadius: 8 }}
            >
              新建草稿
            </Button>
          </div>
        </header>

        {error ? (
          <div
            style={{
              marginBottom: 16,
              borderRadius: 8,
              border: "1px solid rgba(253, 164, 175, 0.3)",
              background: "rgba(255, 241, 242, 0.4)",
              padding: "8px 12px",
              fontSize: 12,
              color: "#be123c",
            }}
          >
            {error}
          </div>
        ) : null}

        {loading ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              padding: "80px 0",
              fontSize: 12.5,
              color: "#6b7280",
            }}
          >
            <LoadingOutlined spin style={{ fontSize: 16 }} />
            正在加载草稿…
          </div>
        ) : documents.length === 0 ? (
          renderEmpty()
        ) : (
          <div className="cw-grid">
            {documents.map((doc) => {
              const isPendingDelete = pendingDeleteId === doc.id;
              const isDeleting = deletingId === doc.id;
              return (
                <div
                  key={doc.id}
                  role="button"
                  tabIndex={0}
                  className="cw-card"
                  onClick={() => goEdit(doc.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      goEdit(doc.id);
                    }
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      gap: 8,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 8, minWidth: 0 }}>
                      <FileTextOutlined
                        style={{ fontSize: 15, marginTop: 2, flexShrink: 0, color: "#6b7280" }}
                      />
                      <div style={{ minWidth: 0 }}>
                        <div
                          title={doc.title || "未命名草稿"}
                          style={{
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            fontSize: 14,
                            fontWeight: 500,
                            color: "rgba(0,0,0,0.88)",
                          }}
                        >
                          {doc.title || "未命名草稿"}
                        </div>
                        <div
                          style={{
                            marginTop: 2,
                            fontSize: 11,
                            color: "rgba(107, 114, 128, 0.7)",
                          }}
                        >
                          最近更新 {relativeTime(doc.updated_at)}{" "}
                          前
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="cw-del"
                      data-pending={isPendingDelete ? "1" : "0"}
                      onClick={(event) => {
                        event.stopPropagation();
                        if (isPendingDelete) {
                          void handleDelete(doc.id);
                        } else {
                          setPendingDeleteId(doc.id);
                        }
                      }}
                      disabled={isDeleting}
                      title={isPendingDelete ? "再次点击确认" : "删除草稿"}
                    >
                      {isDeleting ? (
                        <LoadingOutlined spin style={{ fontSize: 13 }} />
                      ) : (
                        <DeleteOutlined style={{ fontSize: 13 }} />
                      )}
                    </button>
                  </div>
                  <p
                    style={{
                      ...clampLines(4),
                      marginTop: 10,
                      flex: 1,
                      fontSize: 12,
                      lineHeight: 1.625,
                      color: "#6b7280",
                    }}
                  >
                    {doc.preview || "空白草稿"}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
