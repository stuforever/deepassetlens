/**
 * H5 二维码分享页（design §二 + Q1-Q4 第九篇升级）。原仓 app/h5/share/page.tsx 1:1 移植。
 *
 * - Q1：512px PNG 保存（Canvas.toDataURL）+ A5 打印卡片（@media print）
 * - Q2：设置拉取带 ?u=（儿童不回明文访问码，h5_links.py L135-150 遮蔽）；
 *        家长（管理员）侧访问码开关；儿童在门禁处「向家长索取」
 * - Q4：内网地址黄条警示（192.168/10./172.16-31/localhost）+ 公网已配置绿标
 *
 * 等价替换清单：
 * - "use client" 删除；next/link → react-router-dom Link；next/navigation useSearchParams +
 *   Suspense 结构保留（react-router 下 Suspense 非必需，保留原组件分层）；
 * - qrcode.react（QRCodeSVG/QRCodeCanvas）→ h5shared/QrCode 的 QrSvg/QrCanvas
 *   （内联实现，不加包，见 QrCode.tsx 头注）；
 * - lucide → @ant-design/icons：ChevronLeft→LeftOutlined、Copy→CopyOutlined、Check→CheckOutlined、
 *   Link2→LinkOutlined、Smartphone→MobileOutlined、Download→DownloadOutlined、
 *   Printer→PrinterOutlined、ShieldCheck→SafetyOutlined、AlertTriangle→WarningOutlined；
 * - Tailwind → 内联样式逐项对位；`hidden print:block` → .dsh-print-only 打印类；
 *   styled-jsx `<style jsx global>` → 普通 <style>（CSS 内容逐字）；
 * - withU/isIntranetUrl ← h5shared（h5Utils/h5Version）；
 * - 路由前缀映射：原 /h5 → /e/tutor-h5（targetPath 同步映射）。
 */
import { useState, Suspense, useEffect, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  LeftOutlined, CopyOutlined, CheckOutlined, LinkOutlined, MobileOutlined,
  DownloadOutlined, PrinterOutlined, SafetyOutlined, WarningOutlined,
} from "@ant-design/icons";
import { withU } from "./h5shared/h5Utils";
import { isIntranetUrl } from "./h5shared/h5Version";
import { QrSvg, QrCanvas } from "./h5shared/QrCode";
import { H5Shell } from "./h5shared/H5Shell";

function H5ShareContent() {
  const [searchParams] = useSearchParams();
  const u = searchParams.get("u") || searchParams.get("openid") || "";
  const [publicBase, setPublicBase] = useState("");
  const [accessCode, setAccessCode] = useState("");
  const [hasCode, setHasCode] = useState(false);
  const [copied, setCopied] = useState(false);
  const [codeBusy, setCodeBusy] = useState(false);
  const canvasWrapRef = useRef<HTMLDivElement>(null);

  // P3-B + Q2：公网地址优先级 后端设置 > localStorage > 当前 origin。
  // 带 u（儿童视角）时后端只回 public_base + has_access_code（不泄明文）；
  // 无 u（家长/管理员视角）回全量，二维码可嵌入访问码。
  useEffect(() => {
    if (typeof window !== "undefined") {
      let local = "";
      try {
        local = localStorage.getItem("h5_public_base") || "";
      } catch {
        /* ignore */
      }
      setPublicBase(local || window.location.origin);
      const uq = u ? `?u=${encodeURIComponent(u)}` : "";
      void fetch(`/api/v1/h5-settings${uq}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => {
          if (!d) return;
          if (d.public_base) setPublicBase(d.public_base);
          if (typeof d.access_code === "string") {
            setAccessCode(d.access_code);
            setHasCode(Boolean(d.access_code));
          }
          if (typeof d.has_access_code === "boolean") setHasCode(d.has_access_code);
        })
        .catch(() => {
          /* 离线兜底用 local */
        });
    }
  }, [u]);

  const targetPath = "/e/tutor-h5";
  const basePath = withU(targetPath, u);
  const codeQuery = accessCode
    ? `${basePath.includes("?") ? "&" : "?"}code=${encodeURIComponent(accessCode)}`
    : "";
  const shareUrl = (publicBase || "").replace(/\/$/, "") + basePath + codeQuery;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  };

  // Q1：512px PNG 保存
  const savePng = () => {
    const canvas = canvasWrapRef.current?.querySelector("canvas");
    if (!canvas) return;
    try {
      const url = (canvas as HTMLCanvasElement).toDataURL("image/png");
      const a = document.createElement("a");
      a.href = url;
      a.download = `deeptutor-h5-share${u ? `-${u}` : ""}.png`;
      a.click();
    } catch {
      /* ignore */
    }
  };

  // Q2：家长（管理员，无 u）侧访问码开关——PUT 需不带 u
  const toggleAccessCode = async (on: boolean) => {
    if (u || codeBusy) return;
    setCodeBusy(true);
    try {
      const next = on
        ? accessCode || String(Math.floor(100000 + Math.random() * 900000))
        : "";
      const res = await fetch("/api/v1/h5-settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_code: next }),
      });
      if (res.ok) {
        setAccessCode(next);
        setHasCode(Boolean(next));
      }
    } catch {
      /* ignore */
    } finally {
      setCodeBusy(false);
    }
  };

  // Q4：内网警示 / 公网绿标
  const isIntranet = isIntranetUrl(shareUrl);
  const publicConfigured = Boolean(publicBase) && !isIntranetUrl(publicBase);

  return (
    <H5Shell active="me">
      {/* 顶栏 */}
      <div style={{ background: "linear-gradient(to right, #f59e0b, #ea580c)", color: "#fff", padding: "16px 16px 20px", borderRadius: "0 0 24px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Link to={withU("/e/tutor-h5/me", u)} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 14, color: "#fef3c7", textDecoration: "none" }}>
            <LeftOutlined style={{ fontSize: 16 }} /> 返回
          </Link>
          <div style={{ fontSize: 18, fontWeight: 700 }}>🔗 分享</div>
          <div style={{ width: 56 }} />
        </div>
        <div style={{ marginTop: 8, fontSize: 14, color: "#fef3c7" }}>生成二维码，邀请家人朋友一起使用</div>
      </div>

      <div style={{ padding: "0 16px", marginTop: 16, display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Q4：内网/公网提示条 */}
        {isIntranet ? (
          <div
            style={{ padding: "12px 16px", borderRadius: 16, background: "#fff1f2", border: "1px solid #fecdd3", color: "#be123c", fontSize: 14, display: "flex", alignItems: "flex-start", gap: 8 }}
            data-testid="intranet-warn"
          >
            <WarningOutlined style={{ fontSize: 16, marginTop: 2, flexShrink: 0 }} />
            <span>
              当前是内网地址（{publicBase.replace(/^https?:\/\//, "").split(":")[0]}…），外部网络的手机扫码可能打不开。
              请在下方填入公网域名（内网穿透，如 ngrok / frp）。
            </span>
          </div>
        ) : publicConfigured ? (
          <div
            style={{ padding: "10px 16px", borderRadius: 16, background: "#ecfdf5", border: "1px solid #a7f3d0", color: "#047857", fontSize: 14, display: "flex", alignItems: "center", gap: 8 }}
            data-testid="public-ok"
          >
            <SafetyOutlined style={{ fontSize: 16, flexShrink: 0 }} /> 公网地址已配置，外部扫码可直达 ✓
          </div>
        ) : null}

        {/* 公网地址配置 */}
        <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0", padding: 16 }}>
          <h3 style={{ fontWeight: 600, fontSize: 14, marginBottom: 8, marginTop: 0, display: "flex", alignItems: "center", gap: 4 }}>
            <LinkOutlined style={{ fontSize: 16, color: "#f59e0b" }} /> 访问地址
          </h3>
          <input
            value={publicBase}
            onChange={(e) => {
              setPublicBase(e.target.value);
              try {
                localStorage.setItem("h5_public_base", e.target.value);
              } catch {
                /* ignore */
              }
            }}
            placeholder="https://你的公网地址"
            style={{ width: "100%", padding: "8px 12px", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 14, background: "transparent", boxSizing: "border-box" }}
          />
          <p style={{ fontSize: 12, color: "#94a3b8", marginTop: 8, marginBottom: 0 }}>
            默认使用当前访问地址。若需要别人在外部网络访问，请填入内网穿透后的公网域名（如 ngrok / frp）。
          </p>
        </div>

        {/* Q2：家长侧访问码开关（仅管理员视角展示；儿童视角只读提示） */}
        {!u ? (
          <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0", padding: 16 }} data-testid="code-toggle-card">
            <h3 style={{ fontWeight: 600, fontSize: 14, marginBottom: 8, marginTop: 0, display: "flex", alignItems: "center", gap: 4 }}>
              <SafetyOutlined style={{ fontSize: 16, color: "#6366f1" }} /> 访问码门禁
            </h3>
            <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "4px 0", cursor: "pointer" }}>
              <span style={{ fontSize: 14, color: "#334155" }}>开启后，扫码需输入访问码</span>
              <input
                type="checkbox"
                checked={hasCode}
                disabled={codeBusy}
                onChange={(e) => void toggleAccessCode(e.target.checked)}
                style={{ accentColor: "#4f46e5", width: 20, height: 20 }}
                data-testid="code-toggle"
              />
            </label>
            {hasCode && (
              <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
                访问码：{accessCode || "（已启用，孩子扫码时需输入）"}
              </div>
            )}
          </div>
        ) : (
          hasCode && (
            <div style={{ padding: "10px 16px", borderRadius: 16, background: "#eef2ff", border: "1px solid #c7d2fe", color: "#4338ca", fontSize: 12 }}>
              🔐 该链接已启用访问码门禁（二维码未含明文码）。孩子首次打开时由家长在旁输入。
            </div>
          )
        )}

        {/* 二维码 */}
        <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0", padding: 16, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{ padding: 16, background: "#fff", borderRadius: 16, border: "1px solid #e2e8f0" }}>
            <QrSvg value={shareUrl} size={200} level="M" />
          </div>
          {/* Q1：512px 离屏画布（PNG 导出 + 打印复用） */}
          <div ref={canvasWrapRef} className="dsh-print-only" data-testid="qr-canvas-wrap">
            <QrCanvas value={shareUrl} size={512} level="M" />
          </div>
          <div style={{ marginTop: 12, fontSize: 14, fontWeight: 500, color: "#334155" }}>
            扫码打开 H5 学习助手
            {u && <span style={{ color: "#94a3b8" }}>（用户：{u}）</span>}
          </div>
          <div style={{ marginTop: 4, fontSize: 12, color: "#94a3b8", maxWidth: 240, textAlign: "center", wordBreak: "break-all" }}>{shareUrl}</div>
          <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <button
              onClick={copy}
              style={{ display: "flex", alignItems: "center", gap: 4, padding: "8px 16px", borderRadius: 12, background: "#f59e0b", color: "#fff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer" }}
            >
              {copied ? <CheckOutlined style={{ fontSize: 16 }} /> : <CopyOutlined style={{ fontSize: 16 }} />}
              {copied ? "已复制" : "复制链接"}
            </button>
            <button
              onClick={savePng}
              data-testid="save-png-btn"
              style={{ display: "flex", alignItems: "center", gap: 4, padding: "8px 16px", borderRadius: 12, border: "1px solid #fcd34d", color: "#d97706", fontSize: 14, fontWeight: 500, background: "none", cursor: "pointer" }}
            >
              <DownloadOutlined style={{ fontSize: 16 }} /> 保存 PNG
            </button>
            <button
              onClick={() => window.print()}
              data-testid="print-btn"
              style={{ display: "flex", alignItems: "center", gap: 4, padding: "8px 16px", borderRadius: 12, border: "1px solid #e2e8f0", color: "#475569", fontSize: 14, fontWeight: 500, background: "none", cursor: "pointer" }}
            >
              <PrinterOutlined style={{ fontSize: 16 }} /> 打印卡片
            </button>
          </div>
        </div>

        {/* 使用说明 */}
        <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0", padding: 16 }}>
          <h3 style={{ fontWeight: 600, fontSize: 14, marginBottom: 8, marginTop: 0, display: "flex", alignItems: "center", gap: 4 }}>
            <MobileOutlined style={{ fontSize: 16, color: "#f59e0b" }} /> 别人如何用
          </h3>
          <ul style={{ fontSize: 12, color: "#64748b", display: "flex", flexDirection: "column", gap: 6, listStyle: "none", margin: 0, padding: 0 }}>
            <li>1. 手机扫码打开后即可学习 / 拍错题 / 看学情</li>
            <li>2. 每个使用者可在链接后加 ?u=名字 区分（如 /h5?u=小明）</li>
            <li>3. 分享到家庭群 / 班级群，各自记录各自的学情</li>
          </ul>
        </div>
      </div>

      {/* Q1：A5 打印卡片（屏幕隐藏；打印时仅显示此卡） */}
      <div className="print-card dsh-print-only">
        <div style={{ textAlign: "center", padding: "24px 12px" }}>
          <h1 style={{ fontSize: 22, margin: "0 0 4px" }}>DeepTutor 学习助手</h1>
          <p style={{ color: "#64748b", fontSize: 13, margin: "0 0 16px" }}>
            手机扫码，随时提问、拍错题、看学情{u ? `（用户：${u}）` : ""}
          </p>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}>
            <QrCanvas value={shareUrl} size={280} level="M" />
          </div>
          <p style={{ fontSize: 11, color: "#94a3b8", wordBreak: "break-all", margin: 0 }}>{shareUrl}</p>
        </div>
      </div>

      {/* 原 styled-jsx `<style jsx global>` 与 `hidden print:block` 的等价实现：
          打印规则逐字保留 + .dsh-print-only 控制离屏画布/打印卡的显隐 */}
      <style>{`
        .dsh-print-only { display: none; }
        @media print {
          body * {
            visibility: hidden !important;
          }
          .print-card,
          .print-card * {
            visibility: visible !important;
          }
          .print-card {
            position: absolute;
            inset: 0;
            width: 148mm;
            min-height: 200mm;
            margin: auto;
            background: #fff;
          }
          .dsh-print-only { display: block; }
        }
      `}</style>
    </H5Shell>
  );
}

export default function H5Share() {
  return (
    <Suspense fallback={<div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}><LeftOutlined style={{ fontSize: 16 }} /> 加载中…</div>}>
      <H5ShareContent />
    </Suspense>
  );
}
