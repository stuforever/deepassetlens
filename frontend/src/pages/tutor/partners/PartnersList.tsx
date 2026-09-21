/**
 * PartnersList 伙伴列表页——原仓 DeepTutor web/app/(workspace)/partners/page.tsx（252 行）
 * 1:1 移植（批6 6.3）。tupu 路由 /e/sishu/partners（navigation.tsx 既有占位 e:sishu:partners）。
 *
 * 页面区块（与源逐块对拍）：
 * 1. 页头：标题「伙伴」+ 副标题（管理员/非管理员双文案）+ 管理员「新建伙伴」主色入口（PlusOutlined）；
 * 2. 加载态：min-h 320 居中 LoadingOutlined(spin)；
 * 3. 空态：min-h 360 虚线圆角容器——TeamOutlined(HeartHandshake 就近) + 标题 + 说明
 *    + 管理员「创建第一个伙伴」入口（非管理员无入口）；
 * 4. 伙伴卡两列栅格（sm:grid-cols-2 → antd Row/Col）：PartnerAvatar(42) + 名称 +
 *    运行状态点（运行中=emerald/停止=border 色，busy 时换 LoadingOutlined）+ 描述两行截断
 *    + 频道 chips（ChannelIcon+名，空则「未接入频道」）。
 *
 * 等价替换清单：
 * - "use client" 删除；next/link → react-router-dom Link；next/navigation useRouter → useNavigate；
 * - 路由映射：/partners/new → /e/sishu/partners/new；/partners/[id] → /e/sishu/partners/detail?id=X
 *   （tupu 接线口径：详情经 ?id= 传参）；/home?agent=X → /e/sishu/chat?agent=X（NotebookPage
 *   「/home 即对话」先例）；/agents → /e/sishu/agents；
 * - lucide → @ant-design/icons：HeartHandshake→TeamOutlined（伙伴语义就近，与导航 e:sishu:partners
 *   同图标）、Loader2→LoadingOutlined(spin)、Plus→PlusOutlined；
 * - useTranslation t(键) → locales/zh/app.json 中文值逐字直用；"Stopped" 未收录键保留英文原文
 *   （i18next 缺键回退行为一致）；
 * - Tailwind → antd props + 内联样式（CSS 变量带 fallback，同 NotebookPage/MemoryWorkbench 先例）；
 *   hover:/dark:/sm:hidden 变体按先例省略，卡 hover 反馈用 antd Card hoverable 等价；
 * - grid-cols-1 sm:grid-cols-2 → antd Row/Col xs=24 sm=12；line-clamp-2 → -webkit-line-clamp；
 * - 卡元素 <button> → antd Card hoverable（onClick 内 busy 守卫等价 disabled 语义）；
 * - @/lib/subagents-api → 已移植 ../../../lib/subagents-api（IA批5 件）；@/lib/partners-api →
 *   ../../../lib/partners-api、@/hooks/useAuthStatus → ../../../hooks/useAuthStatus（并行批按名
 *   落盘，SubagentSettingsEditor 同规约）；@/components/partners/* → ../../../components/partners/*
 *   （并行批；pages/tutor/partners/ 距 src/ 三级，../../ 口径按深度校正）。
 * - 交互逐字未改：管理员进详情/非管理员自动连 subagent 进对话（重名顺延 "(2)"）、失败回落 /agents。
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Card, Col, Row } from "antd";
import {
  LoadingOutlined,
  PlusOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { listPartners, type PartnerInfo } from "../../../lib/partners-api";
import {
  connectSubagent,
  listConnectablePartners,
  listSubagentConnections,
  type ConnectablePartner,
} from "../../../lib/subagents-api";
import { useAuthStatus } from "../../../hooks/useAuthStatus";
import ChannelIcon from "../../../components/partners/ChannelIcon";
import PartnerAvatar from "../../../components/partners/PartnerAvatar";

// CSS 变量 + fallback（tupu 未注入 DeepTutor 变量时回落 antd 默认色阶，先例同 NotebookPage）
const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";
const MUTED = "var(--muted, #f5f5f5)";
const PRIMARY = "var(--primary, #1677ff)";
const PRIMARY_FG = "var(--primary-foreground, #ffffff)";
// bg-emerald-500
const EMERALD_500 = "#10b981";

function channelNames(partner: PartnerInfo): string[] {
  if (Array.isArray(partner.channels)) {
    // n: string 显式标注——PartnerInfo 类型来自并行批 lib/partners-api，就位前 TS 无法推断
    return partner.channels.filter(
      (n: string) => n !== "send_progress" && n !== "send_tool_hints",
    );
  }
  return [];
}

function asPartnerInfo(card: ConnectablePartner): PartnerInfo {
  // A non-admin only ever sees identity cards (no channel wiring); normalize
  // into the shape the card grid renders, with no channels.
  return {
    partner_id: card.partner_id,
    name: card.name,
    description: card.description || "",
    channels: [],
    emoji: card.emoji,
    color: card.color,
    avatar: card.avatar,
    language: card.language,
    running: Boolean(card.running),
    started_at: null,
  };
}

export default function PartnersList() {
  const navigate = useNavigate();
  // Partners are admin-managed: an admin sees & manages every partner, while a
  // non-admin sees only the partners assigned to them, read-only (creation and
  // editing stay admin-only). The list source differs accordingly.
  const { isAdmin, loading: authLoading } = useAuthStatus();
  const [partners, setPartners] = useState<PartnerInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  // Clicking a partner card. An admin drills into the management page; a
  // non-admin can't manage partners — for them a partner is consulted as a
  // connected agent, so we reuse (or create) that partner's subagent
  // connection and drop them straight into a fresh chat with it preselected.
  const openPartner = useCallback(
    async (partner: PartnerInfo) => {
      if (isAdmin) {
        // 源 router.push(`/partners/${id}`) → tupu 参数路由 /e/sishu/partners/:partnerId（IA批6）
        navigate(
          `/e/sishu/partners/${encodeURIComponent(partner.partner_id)}`,
        );
        return;
      }
      setBusyId(partner.partner_id);
      try {
        const conns = await listSubagentConnections();
        const existing = conns.find(
          (c) =>
            c.agent_kind === "partner" && c.partner_id === partner.partner_id,
        );
        let name = existing?.name;
        if (!name) {
          const taken = new Set(conns.map((c) => c.name));
          const base = partner.name?.trim() || partner.partner_id;
          let candidate = base;
          for (let i = 2; taken.has(candidate); i++)
            candidate = `${base} (${i})`;
          name = (
            await connectSubagent({
              name: candidate,
              agent_kind: "partner",
              partner_id: partner.partner_id,
            })
          ).name;
        }
        navigate(`/e/sishu/chat?agent=${encodeURIComponent(name)}`);
      } catch {
        // Couldn't auto-connect (e.g. the name clashes with an existing KB) —
        // fall back to My Agents, where the partner can be connected by hand.
        navigate("/e/sishu/agents");
      } finally {
        setBusyId(null);
      }
    },
    [isAdmin, navigate],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (isAdmin) {
        setPartners(await listPartners());
      } else {
        setPartners((await listConnectablePartners()).map(asPartnerInfo));
      }
    } catch {
      setPartners([]);
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    if (authLoading) return;
    void load();
  }, [authLoading, load]);

  return (
    <div
      style={{
        maxWidth: 896,
        margin: "0 auto",
        height: "100%",
        overflowY: "auto",
        padding: "32px 24px",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: 16,
          marginBottom: 28,
        }}
      >
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: 19,
              fontWeight: 600,
              letterSpacing: "-0.01em",
              color: FG,
            }}
          >
            伙伴
          </h1>
          <p
            style={{
              margin: "4px 0 0",
              fontSize: 12.5,
              color: MUTED_FG,
            }}
          >
            {isAdmin
              ? "每个伙伴都有自己的灵魂、资料库和频道——可以直接在飞书、Telegram 等 IM 里对话。"
              : "管理员分配给你的伙伴。点击任意一个即可开始与它对话。"}
          </p>
        </div>
        {isAdmin ? (
          <Link
            to="/e/sishu/partners/new"
            style={{
              display: "inline-flex",
              flexShrink: 0,
              alignItems: "center",
              gap: 6,
              borderRadius: 8,
              background: PRIMARY,
              padding: "8px 14px",
              fontSize: 12.5,
              fontWeight: 500,
              color: PRIMARY_FG,
              textDecoration: "none",
            }}
          >
            <PlusOutlined style={{ fontSize: 14 }} />
            新建伙伴
          </Link>
        ) : null}
      </header>

      {loading ? (
        <div
          style={{
            minHeight: 320,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <LoadingOutlined spin style={{ fontSize: 20, color: MUTED_FG }} />
        </div>
      ) : partners.length === 0 ? (
        <div
          style={{
            minHeight: 360,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 16,
            border: `1px dashed ${BORDER}`,
            textAlign: "center",
          }}
        >
          <TeamOutlined
            style={{ marginBottom: 12, fontSize: 32, color: MUTED_FG }}
          />
          <p
            style={{
              margin: 0,
              fontSize: 14,
              fontWeight: 500,
              color: FG,
            }}
          >
            {isAdmin ? "还没有伙伴" : "还没有分配给你的伙伴"}
          </p>
          <p
            style={{
              margin: "6px 0 0",
              maxWidth: 384,
              fontSize: 12.5,
              lineHeight: 1.625,
              color: MUTED_FG,
            }}
          >
            {isAdmin
              ? "创建一个伙伴，赋予它灵魂和一部分资料库，然后在这里或飞书、Telegram、Slack 等 IM 中与它对话。"
              : "管理员还没有给你分配任何伙伴。一旦分配，它们就会显示在这里。"}
          </p>
          {isAdmin ? (
            <Link
              to="/e/sishu/partners/new"
              style={{
                marginTop: 16,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                borderRadius: 8,
                background: PRIMARY,
                padding: "8px 14px",
                fontSize: 12.5,
                fontWeight: 500,
                color: PRIMARY_FG,
                textDecoration: "none",
              }}
            >
              <PlusOutlined style={{ fontSize: 14 }} />
              创建第一个伙伴
            </Link>
          ) : null}
        </div>
      ) : (
        <Row gutter={[12, 12]}>
          {partners.map((partner) => {
            const channels = channelNames(partner);
            const busy = busyId === partner.partner_id;
            return (
              <Col key={partner.partner_id} xs={24} sm={12}>
                <Card
                  hoverable
                  style={{
                    height: "100%",
                    borderRadius: 16,
                    borderColor: BORDER,
                    opacity: busy ? 0.6 : undefined,
                  }}
                  styles={{ body: {
                    height: "100%",
                    boxSizing: "border-box",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 12,
                    padding: 16,
                    cursor: busy ? "default" : "pointer",
                  } }}
                  onClick={() => {
                    if (!busy) void openPartner(partner);
                  }}
                >
                  <PartnerAvatar
                    name={partner.name}
                    emoji={partner.emoji}
                    color={partner.color}
                    image={partner.avatar}
                    size={42}
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
                      {busy ? (
                        <LoadingOutlined
                          spin
                          style={{ fontSize: 12, flexShrink: 0, color: MUTED_FG }}
                        />
                      ) : (
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
                      )}
                    </div>
                    {partner.description ? (
                      <p
                        style={{
                          margin: "2px 0 0",
                          fontSize: 12,
                          lineHeight: 1.625,
                          color: MUTED_FG,
                          display: "-webkit-box",
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                        }}
                      >
                        {partner.description}
                      </p>
                    ) : null}
                    <div
                      style={{
                        marginTop: 8,
                        display: "flex",
                        flexWrap: "wrap",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      {channels.length > 0 ? (
                        channels.map((channel) => (
                          <span
                            key={channel}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 4,
                              borderRadius: 999,
                              background: MUTED,
                              padding: "2px 8px",
                              fontSize: 11,
                              color: MUTED_FG,
                            }}
                          >
                            <ChannelIcon name={channel} size={11} />
                            {channel}
                          </span>
                        ))
                      ) : (
                        <span style={{ fontSize: 11, color: MUTED_FG }}>
                          未接入频道
                        </span>
                      )}
                    </div>
                  </div>
                </Card>
              </Col>
            );
          })}
        </Row>
      )}
    </div>
  );
}
