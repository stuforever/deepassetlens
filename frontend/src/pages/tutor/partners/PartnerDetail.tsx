/**
 * PartnerDetail 伙伴详情页——原仓 DeepTutor web/app/(workspace)/partners/[partnerId]/page.tsx（412 行）
 * 1:1 移植（批6 6.3）。tupu 路由 /e/tutor/partners/detail?id=X（接线批注册）；
 * partnerId 来源：props { partnerId } 优先，否则 useSearchParams ?id=（tupu 无路径参数段，
 * 源 useParams<{partnerId}> 等价替换）。?tab= 深链保留。
 *
 * 页面区块（与源逐块对拍）：
 * 1. 顶栏：返回「伙伴」图标链接 + PartnerAvatar(32) + 名称+运行状态点 + 描述单行截断
 *    + 四 Tab 分段导航（聊天/配置/频道/Archive，Message/Setting/Api/Container Outlined）
 *    + chat|archive 时「保存到笔记本」「下载 Markdown」两枚图标按钮（无内容禁用）
 *    + 启停按钮（busy spin / 运行 BorderOutlined / 停止 CaretRightOutlined）+ 删除按钮；
 * 2. 加载态：h-full 居中 LoadingOutlined(spin)；
 * 3. 未找到态：「未找到该伙伴」+「返回伙伴」链接；
 * 4. 体：Chat 恒挂载（他 Tab 时 display:none——进行中的轮次/WebSocket/实时轨迹不因切 Tab 中断）；
 *    archive → PartnerArchives（Resume 回 chat 并换 sessionKey）；configure → PartnerConfigure；
 *    channels → PartnerChannels；
 * 5. SaveToNotebookModal（recordType "tutorbot"，导出消息按 user/assistant/system 过滤）；
 * 6. 底部居中 Toast（3.5s 自动消失）。
 *
 * 等价替换清单：
 * - "use client" 删除；next/link → react-router-dom Link；next/navigation 的 useParams/
 *   useSearchParams/useRouter → props ?id= / react-router useSearchParams / useNavigate；
 *   Next 专用 Suspense 包裹（仅 Next 流式约束所需）按 RR6 等价直接渲染，省略；
 * - 路由映射：/partners → /e/tutor/partners；
 * - lucide → @ant-design/icons：ArrowLeft→ArrowLeftOutlined、Archive→ContainerOutlined
 *   （MemorySection 先例）、BookmarkPlus→SaveOutlined（保存语义就近）、Download→DownloadOutlined、
 *   Loader2→LoadingOutlined(spin)、MessageCircle→MessageOutlined、Play→CaretRightOutlined
 *   （PageSpeechBar 先例）、Radio→ApiOutlined（频道接入语义就近）、Settings2→SettingOutlined、
 *   Square→BorderOutlined（H5WrongBook/PageSpeechBar 先例）、Trash2→DeleteOutlined；
 * - useTranslation t(键) → locales/zh/app.json 中文值逐字直用；"Stopped"/"Archive" 未收录键保留
 *   英文原文（i18next 缺键回退行为一致）；window.confirm 文案逐字保留（NotebookPage 先例）；
 * - Tailwind → antd props + 内联样式（CSS 变量带 fallback）；hover:/dark: 变体按先例省略
 *   （头部图标按钮 hover 变色、删除 hover 变红、链接 hover 下划线省略）；
 *   头部 Tab 导航 segmented → antd Segmented（muted 底+活动白底圆角，视觉等价）；
 * - @/lib/partners-api / chat-export / partner-session → ../../../lib/*（并行批按名落盘，
 *   SubagentSettingsEditor 同规约）；@/components/partners/*、@/components/notebook/
 *   SaveToNotebookModal → 并行批按名 import（pages/tutor/partners/ 距 src/ 三级，
 *   ../../ 口径按深度校正为 ../../../）。
 * - 交互逐字未改：启停+toast（伙伴已停止/伙伴已启动/操作失败）、删除确认→返回列表、
 *   导出标题取首条 user 消息前 80 字、Archive Resume 换会话并回 Chat、Chat 恒挂载语义。
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Button, Segmented } from "antd";
import {
  ApiOutlined,
  ArrowLeftOutlined,
  BorderOutlined,
  CaretRightOutlined,
  ContainerOutlined,
  DeleteOutlined,
  DownloadOutlined,
  LoadingOutlined,
  MessageOutlined,
  SaveOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import {
  destroyPartner,
  getPartner,
  startPartner,
  stopPartner,
  type PartnerInfo,
} from "../../../lib/partners-api";
import {
  downloadChatMarkdown,
  type ExportableMessage,
} from "../../../lib/chat-export";
import {
  loadPartnerSessionKey,
  persistPartnerSessionKey,
} from "../../../lib/partner-session";
import PartnerAvatar from "../../../components/partners/PartnerAvatar";
import PartnerChat from "../../../components/partners/PartnerChat";
import PartnerChannels from "../../../components/partners/PartnerChannels";
import PartnerConfigure from "../../../components/partners/PartnerConfigure";
import PartnerArchives from "../../../components/partners/PartnerArchives";
import SaveToNotebookModal, {
  type NotebookSaveMessage,
  type NotebookSavePayload,
} from "../../../components/notebook/SaveToNotebookModal";

// CSS 变量 + fallback（先例同 NotebookPage）
const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";
const MUTED = "var(--muted, #f5f5f5)";
const BACKGROUND = "var(--background, #ffffff)";
const PRIMARY = "var(--primary, #1677ff)";
// bg-emerald-500
const EMERALD_500 = "#10b981";

type Tab = "chat" | "configure" | "channels" | "archive";

export default function PartnerDetail({
  partnerId: partnerIdProp,
}: {
  partnerId?: string;
}) {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  // 源 useParams<{partnerId}> → tupu 等价（⑤R F1 先例）：KeepAlive 页签架构无 <Routes>，
  // useParams() 恒空——从 pathname 尾段解析（/:partnerId 路由段约定）；
  // props / ?id= 兼容兜底（接线期承接两式）。
  const tail = location.pathname.split("/").filter(Boolean).pop() || "";
  const partnerId = tail || partnerIdProp || searchParams.get("id") || "";

  const initialTab = (searchParams.get("tab") as Tab) || "chat";
  const [tab, setTab] = useState<Tab>(
    ["chat", "configure", "channels", "archive"].includes(initialTab)
      ? initialTab
      : "chat",
  );
  const [partner, setPartner] = useState<PartnerInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [lifecycleBusy, setLifecycleBusy] = useState(false);
  const [toast, setToast] = useState("");
  // Conversation transcripts lifted from the Chat / Archive tabs so the header
  // can export whichever surface is active.
  const [chatMessages, setChatMessages] = useState<ExportableMessage[]>([]);
  const [archiveMessages, setArchiveMessages] = useState<ExportableMessage[]>(
    [],
  );
  const [showSaveModal, setShowSaveModal] = useState(false);
  // The active web session key lives here so the Archive tab's Resume can
  // point the (always-mounted) Chat tab at a different conversation.
  const [sessionKey, setSessionKey] = useState("");
  useEffect(() => {
    setSessionKey(loadPartnerSessionKey(partnerId));
  }, [partnerId]);
  const changeSessionKey = useCallback(
    (key: string) => {
      persistPartnerSessionKey(partnerId, key);
      setSessionKey(key);
    },
    [partnerId],
  );

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timer);
  }, [toast]);

  const exportMessages = useMemo<ExportableMessage[]>(() => {
    if (tab === "chat") return chatMessages;
    if (tab === "archive") return archiveMessages;
    return [];
  }, [tab, chatMessages, archiveMessages]);

  const canExport = exportMessages.length > 0;

  const exportTitle = useMemo(() => {
    const firstUser = exportMessages
      .find((msg) => msg.role === "user")
      ?.content.trim();
    return firstUser?.slice(0, 80) || partner?.name || "Conversation";
  }, [exportMessages, partner?.name]);

  const savePayload = useMemo<NotebookSavePayload | null>(() => {
    if (!partner || !canExport) return null;
    return {
      recordType: "tutorbot",
      title: exportTitle,
      // The transcript / userQuery are rebuilt inside the modal from the
      // user's selected subset; these are just fallbacks.
      userQuery: "",
      output: "",
      metadata: {
        source: "partner",
        partner_id: partnerId,
        partner_name: partner.name,
      },
    };
  }, [partner, canExport, exportTitle, partnerId]);

  const saveMessages = useMemo<NotebookSaveMessage[]>(
    () =>
      exportMessages
        .filter(
          (msg) =>
            msg.role === "user" ||
            msg.role === "assistant" ||
            msg.role === "system",
        )
        .map((msg) => ({
          role: msg.role as NotebookSaveMessage["role"],
          content: msg.content,
        })),
    [exportMessages],
  );

  const handleDownload = useCallback(() => {
    if (!exportMessages.length) return;
    downloadChatMarkdown(exportMessages, { title: exportTitle });
  }, [exportMessages, exportTitle]);

  const load = useCallback(async () => {
    try {
      setPartner(await getPartner(partnerId));
    } catch {
      setPartner(null);
    } finally {
      setLoading(false);
    }
  }, [partnerId]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleRunning = async () => {
    if (!partner) return;
    setLifecycleBusy(true);
    try {
      if (partner.running) {
        await stopPartner(partnerId);
        setToast("伙伴已停止");
      } else {
        await startPartner(partnerId);
        setToast("伙伴已启动");
      }
      await load();
    } catch (e) {
      setToast(e instanceof Error ? e.message : "操作失败");
    } finally {
      setLifecycleBusy(false);
    }
  };

  const handleDestroy = async () => {
    if (
      !window.confirm(
        "删除该伙伴及其全部数据（工作区、会话、频道）？此操作不可撤销。",
      )
    )
      return;
    try {
      await destroyPartner(partnerId);
      navigate("/e/tutor/partners");
    } catch (e) {
      setToast(e instanceof Error ? e.message : "删除失败");
    }
  };

  if (loading) {
    return (
      <div
        style={{
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <LoadingOutlined spin style={{ fontSize: 20, color: MUTED_FG }} />
      </div>
    );
  }

  if (!partner) {
    return (
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
        }}
      >
        <p style={{ margin: 0, fontSize: 14, color: MUTED_FG }}>
          未找到该伙伴
        </p>
        <Link to="/e/tutor/partners" style={{ fontSize: 13, color: PRIMARY }}>
          返回伙伴
        </Link>
      </div>
    );
  }

  const tabs: { key: Tab; label: string; icon: typeof MessageOutlined }[] = [
    { key: "chat", label: "聊天", icon: MessageOutlined },
    { key: "configure", label: "配置", icon: SettingOutlined },
    { key: "channels", label: "频道", icon: ApiOutlined },
    { key: "archive", label: "Archive", icon: ContainerOutlined },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          borderBottom: `1px solid ${BORDER}`,
          padding: "12px 20px",
        }}
      >
        <Link
          to="/e/tutor/partners"
          aria-label="返回伙伴"
          style={{
            display: "inline-flex",
            borderRadius: 6,
            padding: 6,
            color: MUTED_FG,
          }}
        >
          <ArrowLeftOutlined style={{ fontSize: 16 }} />
        </Link>
        <PartnerAvatar
          name={partner.name}
          emoji={partner.emoji}
          color={partner.color}
          image={partner.avatar}
          size={32}
        />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                fontSize: 14,
                fontWeight: 500,
                color: FG,
              }}
            >
              {partner.name}
            </span>
            <span
              title={partner.running ? "运行中" : "Stopped"}
              style={{
                width: 6,
                height: 6,
                flexShrink: 0,
                borderRadius: "50%",
                background: partner.running ? EMERALD_500 : BORDER,
              }}
            />
          </div>
          {partner.description ? (
            <p
              style={{
                margin: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                fontSize: 11.5,
                color: MUTED_FG,
              }}
            >
              {partner.description}
            </p>
          ) : null}
        </div>

        <Segmented
          value={tab}
          onChange={(value) => setTab(value as Tab)}
          options={tabs.map(({ key, label, icon: Icon }) => ({
            value: key,
            label: (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <Icon style={{ fontSize: 14 }} />
                {label}
              </span>
            ),
          }))}
        />

        {(tab === "chat" || tab === "archive") && (
          <>
            <Button
              type="text"
              onClick={() => setShowSaveModal(true)}
              disabled={!canExport}
              title="保存到笔记本"
              aria-label="保存到笔记本"
              icon={<SaveOutlined style={{ fontSize: 16 }} />}
              style={{ color: MUTED_FG, padding: 6, borderRadius: 6 }}
            />
            <Button
              type="text"
              onClick={handleDownload}
              disabled={!canExport}
              title="将聊天记录下载为 Markdown 文件"
              aria-label="下载 Markdown"
              icon={<DownloadOutlined style={{ fontSize: 16 }} />}
              style={{ color: MUTED_FG, padding: 6, borderRadius: 6 }}
            />
          </>
        )}
        <Button
          type="text"
          onClick={() => void toggleRunning()}
          disabled={lifecycleBusy}
          title={partner.running ? "停止" : "开始"}
          icon={
            lifecycleBusy ? (
              <LoadingOutlined spin style={{ fontSize: 16 }} />
            ) : partner.running ? (
              <BorderOutlined style={{ fontSize: 16 }} />
            ) : (
              <CaretRightOutlined style={{ fontSize: 16 }} />
            )
          }
          style={{ color: MUTED_FG, padding: 6, borderRadius: 6 }}
        />
        <Button
          type="text"
          onClick={() => void handleDestroy()}
          title="删除伙伴"
          icon={<DeleteOutlined style={{ fontSize: 16 }} />}
          style={{ color: MUTED_FG, padding: 6, borderRadius: 6 }}
        />
      </div>

      {/* Body. Chat stays mounted (hidden off-tab) so an in-progress turn —
          its WebSocket and live trace — survives switching to another tab. */}
      <div style={{ minHeight: 0, flex: 1 }}>
        <div
          style={{
            height: tab === "chat" ? "100%" : undefined,
            display: tab === "chat" ? undefined : "none",
          }}
        >
          <div
            style={{
              maxWidth: 768,
              margin: "0 auto",
              height: "100%",
              padding: "0 20px",
            }}
          >
            <PartnerChat
              partnerId={partnerId}
              partnerName={partner.name}
              emoji={partner.emoji}
              color={partner.color}
              avatar={partner.avatar}
              running={partner.running}
              sessionKey={sessionKey}
              onSessionKeyChange={changeSessionKey}
              onToast={setToast}
              onMessagesChange={setChatMessages}
            />
          </div>
        </div>
        {tab === "archive" ? (
          <div
            style={{
              maxWidth: 1024,
              margin: "0 auto",
              height: "100%",
              overflow: "hidden",
              padding: "20px 20px",
            }}
          >
            <PartnerArchives
              partnerId={partnerId}
              onToast={setToast}
              onMessagesChange={setArchiveMessages}
              // key: string 显式标注——并行批组件就位前 TS 无法从 props 推断
              onResume={(key: string) => {
                changeSessionKey(key);
                setTab("chat");
              }}
            />
          </div>
        ) : tab === "configure" ? (
          <div
            style={{
              maxWidth: 768,
              margin: "0 auto",
              height: "100%",
              overflowY: "auto",
              padding: "20px 20px",
            }}
          >
            <PartnerConfigure
              partner={partner}
              onToast={setToast}
              onUpdated={() => void load()}
            />
          </div>
        ) : tab === "channels" ? (
          <div
            style={{
              maxWidth: 768,
              margin: "0 auto",
              height: "100%",
              overflowY: "auto",
              padding: "20px 20px",
            }}
          >
            <PartnerChannels partnerId={partnerId} onToast={setToast} />
          </div>
        ) : null}
      </div>

      <SaveToNotebookModal
        open={showSaveModal}
        payload={savePayload}
        messages={saveMessages}
        onClose={() => setShowSaveModal(false)}
        onSaved={() => {
          setShowSaveModal(false);
          setToast("已保存到笔记本。");
        }}
      />

      {toast && (
        <div
          style={{
            pointerEvents: "none",
            position: "fixed",
            bottom: 24,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 1000,
            borderRadius: 8,
            background: FG,
            color: BACKGROUND,
            padding: "8px 14px",
            fontSize: 12.5,
            boxShadow:
              "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)",
          }}
        >
          {toast}
        </div>
      )}
    </div>
  );
}
