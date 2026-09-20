/**
 * 母题库主列表——1:1 移植自原仓 web/app/(workspace)/mother-questions/page.tsx
 * （Next.js+Tailwind → React+react-router+antd；区块顺序 统计行→筛选栏→高级筛选→
 * 卡片网格→分页、按钮文案、确认弹窗、空态、认领弹窗、导出弹窗逐字保留，i18n 直出中文）。
 * API 契约：/api/v1/mother-questions（列表/删除）、/claim、/dict、
 * /analysis/comprehensive-stats、/{id}/transfer-to-*、/export。
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { Button, Input, Modal, Select, message } from 'antd';
import {
  AppstoreOutlined, ArrowLeftOutlined, ArrowRightOutlined, BarChartOutlined, CameraOutlined,
  CheckCircleOutlined, DeleteOutlined, DownloadOutlined, EditOutlined, DownOutlined, UpOutlined,
  EllipsisOutlined, FileSearchOutlined, FileTextOutlined, FilterOutlined, PlusOutlined,
  ReloadOutlined, ScanOutlined, SearchOutlined, SendOutlined, UndoOutlined, VideoCameraOutlined,
} from '@ant-design/icons';
import { ExportModal } from './ExportModal';
import {
  GRADES, CATEGORIES, SUBJECTS, SUBJECT_COLORS, SUBJECT_DISPLAY, GRADE_DISPLAY,
  CATEGORY_DISPLAY, MASTERY_DISPLAY, MASTERY_COLOR,
} from './dtFields';

interface MotherQuestion {
  id: string; title: string; question_text: string;
  subject?: string;
  grade?: string; category?: string; difficulty: number;
  variant_count: number; video_count: number; mastery_status?: string; create_time: number;
  photo_url?: string; tags?: string[];
}
interface Stats { total: number; by_grade: Record<string, number>; by_category: Record<string, number>; avg_difficulty: number; by_status?: Record<string, number>; }
interface TextbookDict { id: string; name: string; grade?: string; }
interface ChapterDict { id: string; name: string; textbook_id: string; }

const MUTED = 'rgba(0,0,0,0.45)';
const PRIMARY = '#1677ff';
const cardBtnStyle: CSSProperties = {
  padding: 4, borderRadius: 4, background: 'transparent', border: 'none', cursor: 'pointer', lineHeight: 1,
};
const menuItemStyle: CSSProperties = {
  width: '100%', padding: '6px 12px', textAlign: 'left', height: 'auto',
  display: 'flex', alignItems: 'center', gap: 8,
};

function MotherQuestionsContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const searchParams = useSearchParams()[0];
  const [items, setItems] = useState<MotherQuestion[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [showExport, setShowExport] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [subject, setSubject] = useState('');
  const [grade, setGrade] = useState('');
  const [category, setCategory] = useState('');
  const [textbookId, setTextbookId] = useState('');
  const [chapterId, setChapterId] = useState('');
  const [tag, setTag] = useState('');
  const [sortBy, setSortBy] = useState('create_time');
  const [sortOrder, setSortOrder] = useState('desc');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [textbooks, setTextbooks] = useState<TextbookDict[]>([]);
  const [chapters, setChapters] = useState<ChapterDict[]>([]);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  // R2 认领给孩子（P2-C1 桌面入口）
  const [showClaim, setShowClaim] = useState(false);
  const [claimTargetU, setClaimTargetU] = useState('');
  const [claimAll, setClaimAll] = useState(true);
  const [claiming, setClaiming] = useState(false);

  // URL 同步筛选
  const syncUrl = useCallback((overrides: Record<string, string> = {}) => {
    const params = new URLSearchParams();
    const state = { keyword, subject, grade, category, textbookId, chapterId, tag, sortBy, sortOrder, page: String(page), ...overrides };
    Object.entries(state).forEach(([k, v]) => { if (v) params.set(k, v); });
    navigate(`${location.pathname}?${params.toString()}`, { replace: true });
  }, [keyword, subject, grade, category, textbookId, chapterId, tag, sortBy, sortOrder, page, location.pathname, navigate]);

  // R2 认领给孩子（P2-C1 桌面入口）：把母题复制到目标 H5 用户（仅 admin）
  const submitClaim = useCallback(async () => {
    const target = claimTargetU.trim();
    if (!target) {
      message.error('请输入孩子名字');
      return;
    }
    setClaiming(true);
    try {
      const res = await fetch('/api/v1/mother-questions/claim', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_u: target,
          all: claimAll,
          mids: claimAll ? [] : items.map((m) => m.id),
          include_variants: true,
        }),
      });
      const data = await res.json().catch(() => null);
      if (res.ok && typeof data?.claimed === 'number') {
        message.success(`已复制 ${data.claimed} 道到「${target}」（跳过重复 ${data.skipped_dup ?? 0} 道）`);
        setShowClaim(false);
        setClaimTargetU('');
      } else {
        message.error(data?.detail || '认领失败');
      }
    } catch {
      message.error('认领失败（网络错误）');
    } finally {
      setClaiming(false);
    }
  }, [claimTargetU, claimAll, items]);

  // 从 URL 恢复筛选
  useEffect(() => {
    setKeyword(searchParams.get('keyword') || '');
    setSubject(searchParams.get('subject') || '');
    setGrade(searchParams.get('grade') || '');
    setCategory(searchParams.get('category') || '');
    setTextbookId(searchParams.get('textbookId') || '');
    setChapterId(searchParams.get('chapterId') || '');
    setTag(searchParams.get('tag') || '');
    setSortBy(searchParams.get('sortBy') || 'create_time');
    setSortOrder(searchParams.get('sortOrder') || 'desc');
    setPage(Number(searchParams.get('page')) || 1);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 加载字典
  useEffect(() => {
    fetch('/api/v1/mother-questions/dict')
      .then((r) => r.json())
      .then((d) => {
        setTextbooks(d.textbooks || []);
        setChapters((d.chapters || []).filter((c: ChapterDict) => !textbookId || c.textbook_id === textbookId));
      })
      .catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setChapters((prev) => prev.filter((c) => !textbookId || c.textbook_id === textbookId));
  }, [textbookId]);

  // 兼容旧的 ?photo=1 跳转：挂载即消费一次并置 redirecting 标记——避免与 syncUrl 的
  // replace 互相覆盖；故 redirect 进行中放行其导航、跳过 syncUrl。
  const photoRedirecting = useRef(false);
  useEffect(() => {
    if (searchParams.get('photo') === '1' && !photoRedirecting.current) {
      photoRedirecting.current = true;
      navigate('/e/sishu/admin/mother-questions/photo', { replace: true });
    }
  }, [searchParams, navigate]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (keyword) params.set('keyword', keyword);
      if (subject) params.set('subject', subject);
      if (grade) params.set('grade', grade);
      if (category) params.set('category', category);
      if (textbookId) params.set('textbook_id', textbookId);
      if (chapterId) params.set('chapter_id', chapterId);
      if (tag) params.set('tag', tag);
      params.set('sort_by', sortBy);
      params.set('sort_order', sortOrder);
      const res = await fetch(`/api/v1/mother-questions?${params}`);
      const data = await res.json();
      setItems(data.items || []); setTotal(data.total || 0);
      const sRes = await fetch('/api/v1/mother-questions/analysis/comprehensive-stats');
      if (sRes.ok) setStats(await sRes.json());
    } catch { message.error('加载失败'); }
    finally { setLoading(false); }
  }, [page, pageSize, keyword, subject, grade, category, textbookId, chapterId, tag, sortBy, sortOrder]);

  useEffect(() => {
    load();
    if (!photoRedirecting.current) syncUrl();
  }, [load, syncUrl]);

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 24 }} data-testid="mq-page">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 8 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8, margin: 0 }} data-testid="mq-title">
          <FileSearchOutlined style={{ fontSize: 24, color: PRIMARY }} /> 题库
          <span style={{ fontSize: 14, color: MUTED, fontWeight: 400 }}>（共 {total} 题）</span>
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={() => navigate('/e/sishu/admin/mother-questions/review')} data-testid="mq-review-btn" icon={<UndoOutlined />} style={{ background: '#f0fdf4', borderColor: '#bbf7d0', color: '#15803d' }}>复习</Button>
          <Button onClick={() => navigate('/e/sishu/admin/mother-questions/trash')} data-testid="mq-trash-btn" icon={<DeleteOutlined />}>回收站</Button>
          <Button onClick={() => setShowExport(true)} data-testid="mq-export-btn" icon={<FileTextOutlined />}>导出</Button>
          <Button onClick={() => setShowClaim(true)} data-testid="mq-claim-btn" icon={<SendOutlined />} style={{ background: '#f0f9ff', borderColor: '#bae6fd', color: '#0369a1' }}>认领给孩子</Button>
          <Button onClick={() => navigate('/e/sishu/admin/settings/curriculum')} data-testid="mq-settings-btn" icon={<AppstoreOutlined />}>设置管理</Button>
          <Button onClick={() => navigate('/e/sishu/admin/mother-questions/analysis')} data-testid="mq-analysis-btn" icon={<BarChartOutlined />}>分析</Button>
          <Button onClick={() => navigate('/e/sishu/admin/mother-questions/photo-center')} data-testid="mq-photo-center-btn" icon={<ScanOutlined />}>拍照中心</Button>
          <Button onClick={() => navigate('/e/sishu/admin/mother-questions/photo')} data-testid="mq-photo-btn" icon={<CameraOutlined />} style={{ background: '#faf5ff', borderColor: '#e9d5ff', color: '#7e22ce' }}>拍照录入</Button>
          <Button type="primary" onClick={() => navigate('/e/sishu/admin/mother-questions/new')} data-testid="mq-add-btn" icon={<PlusOutlined />}>新增母题</Button>
        </div>
      </div>

      {stats && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 24 }} data-testid="mq-stats">
          <StatCard label="母题总数" value={stats.total} testid="mq-stat-total" />
          <StatCard label="平均难度" value={stats.avg_difficulty} small testid="mq-stat-avg-difficulty" />
          <StatCard label={MASTERY_DISPLAY.not_mastered} value={stats.by_status?.not_mastered ?? 0} small testid="mq-stat-not-mastered" />
          <StatCard label={MASTERY_DISPLAY.reviewing} value={stats.by_status?.reviewing ?? 0} small testid="mq-stat-reviewing" />
          <StatCard label={MASTERY_DISPLAY.mastered} value={stats.by_status?.mastered ?? 0} small testid="mq-stat-mastered" />
        </div>
      )}

      {/* 筛选栏（可折叠） */}
      <div style={{ borderRadius: 8, border: '1px solid #d9d9d9', background: '#fff', marginBottom: 16 }} data-testid="mq-filter-bar">
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, padding: 12 }}>
          <Input
            prefix={<SearchOutlined style={{ color: MUTED }} />}
            style={{ flex: 1, minWidth: 200 }}
            placeholder="搜索标题/题干/解析/错因/标签"
            value={keyword}
            onChange={(e) => { setKeyword(e.target.value); setPage(1); }}
            data-testid="mq-search"
          />
          <Select
            style={{ width: 128 }}
            value={subject}
            onChange={(v) => { setSubject(v); setPage(1); }}
            data-testid="mq-filter-subject"
            options={[{ value: '', label: '全部科目' }, ...Object.entries(SUBJECTS).map(([k]) => ({ value: k, label: SUBJECT_DISPLAY[k] }))]}
          />
          <Select
            style={{ width: 128 }}
            value={grade}
            onChange={(v) => { setGrade(v); setPage(1); }}
            data-testid="mq-filter-grade"
            options={[{ value: '', label: '全部年级' }, ...GRADES.map((g) => ({ value: g, label: GRADE_DISPLAY[g] }))]}
          />
          <Select
            style={{ width: 128 }}
            value={category}
            onChange={(v) => { setCategory(v); setPage(1); }}
            data-testid="mq-filter-category"
            options={[{ value: '', label: '全部题型' }, ...CATEGORIES.map((c) => ({ value: c, label: CATEGORY_DISPLAY[c] }))]}
          />
          <Select
            style={{ width: 110 }}
            value={sortBy}
            onChange={(v) => setSortBy(v)}
            data-testid="mq-filter-sort-by"
            options={[
              { value: 'create_time', label: '按时间' },
              { value: 'difficulty', label: '按难度' },
              { value: 'title', label: '按标题' },
            ]}
          />
          <Select
            style={{ width: 90 }}
            value={sortOrder}
            onChange={(v) => setSortOrder(v)}
            data-testid="mq-filter-sort-order"
            options={[
              { value: 'desc', label: '降序' },
              { value: 'asc', label: '升序' },
            ]}
          />
          <Button onClick={() => setShowAdvanced(!showAdvanced)} data-testid="mq-advanced-btn" icon={showAdvanced ? <UpOutlined /> : <DownOutlined />}>高级</Button>
          <Button onClick={() => { load(); }} data-testid="mq-refresh-btn" icon={<ReloadOutlined />} />
        </div>
        {/* 高级筛选（折叠区） */}
        {showAdvanced && (
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, padding: '8px 12px 12px', borderTop: '1px solid #f0f0f0' }}>
            {textbooks.length > 0 && (
              <Select
                style={{ width: 180 }}
                value={textbookId}
                onChange={(v) => { setTextbookId(v); setChapterId(''); setPage(1); }}
                options={[{ value: '', label: '全部教材' }, ...textbooks.map((tb) => ({ value: tb.id, label: tb.name }))]}
              />
            )}
            {textbookId && chapters.filter((c) => c.textbook_id === textbookId).length > 0 && (
              <Select
                style={{ width: 180 }}
                value={chapterId}
                onChange={(v) => { setChapterId(v); setPage(1); }}
                options={[{ value: '', label: '全部章节' }, ...chapters.filter((c) => c.textbook_id === textbookId).map((c) => ({ value: c.id, label: c.name }))]}
              />
            )}
            <Input
              style={{ width: 128 }}
              placeholder="标签筛选"
              value={tag}
              onChange={(e) => { setTag(e.target.value); setPage(1); }}
            />
          </div>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '32px 0', color: MUTED }} data-testid="mq-loading">加载中…</div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '32px 0', color: MUTED }} data-testid="mq-empty">暂无母题</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 16 }} data-testid="mq-card-grid">
          {items.map((m) => (
            <MotherCard
              key={m.id}
              m={m}
              onOpen={() => navigate(`/e/sishu/admin/mother-questions/${m.id}`)}
              onEdit={() => navigate(`/e/sishu/admin/mother-questions/${m.id}?edit=1`)}
              onDelete={async () => {
                if (!window.confirm('确认删除？')) return;
                await fetch(`/api/v1/mother-questions/${m.id}`, { method: 'DELETE' });
                message.success('已删除'); load();
              }}
              onTransfer={async () => {
                const ep = m.mastery_status === 'mastered' ? 'transfer-to-active' : 'transfer-to-mastered';
                await fetch(`/api/v1/mother-questions/${m.id}/${ep}`, { method: 'POST' });
                message.success('已转换'); load();
              }}
              onExport={async () => {
                const r = await fetch('/api/v1/mother-questions/export', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids: [m.id], with_image: true }) });
                const blob = await r.blob(); const url = URL.createObjectURL(blob);
                const a = document.createElement('a'); a.href = url; a.download = `${m.title}.docx`; a.click(); URL.revokeObjectURL(url);
              }}
              openMenuId={openMenuId}
              setOpenMenuId={setOpenMenuId}
            />
          ))}
        </div>
      )}

      {/* 分页 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 24 }} data-testid="mq-pagination">
        <Button onClick={() => { setPage(Math.max(1, page - 1)); }} disabled={page <= 1} data-testid="mq-page-prev" icon={<ArrowLeftOutlined />} />
        <span style={{ fontSize: 14 }} data-testid="mq-page-indicator">{page} / {totalPages}</span>
        <Button onClick={() => { setPage(Math.min(totalPages, page + 1)); }} disabled={page >= totalPages} data-testid="mq-page-next" icon={<ArrowRightOutlined />} />
      </div>

      {showExport && <ExportModal onClose={() => setShowExport(false)} currentIds={items.map((m) => m.id)} />}

      {/* R2 认领给孩子（P2-C1） */}
      <Modal
        open={showClaim}
        onCancel={() => setShowClaim(false)}
        footer={null}
        width={448}
        data-testid="mq-claim-modal"
        closeIcon={<span data-testid="mq-claim-close">✕</span>}
        title={(
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 18, fontWeight: 600 }}>
            <SendOutlined style={{ color: '#0ea5e9' }} /> 认领给孩子
          </span>
        )}
      >
        <p style={{ fontSize: 14, color: MUTED, marginBottom: 12 }}>
          把题库中的母题复制到孩子的 H5 工作区（按 标题+题干 判重，重复自动跳过）。
        </p>
        <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>孩子名字（H5 用户）</label>
        <Input
          value={claimTargetU}
          onChange={(e) => setClaimTargetU(e.target.value)}
          placeholder="如：小明"
          maxLength={20}
          style={{ marginBottom: 12 }}
          data-testid="mq-claim-input"
        />
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, cursor: 'pointer' }}>
            <input type="radio" checked={claimAll} onChange={() => setClaimAll(true)} data-testid="mq-claim-all" /> 全部母题
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, cursor: 'pointer' }}>
            <input type="radio" checked={!claimAll} onChange={() => setClaimAll(false)} data-testid="mq-claim-current" /> 当前列表（{items.length} 道）
          </label>
        </div>
        <button
          onClick={() => void submitClaim()}
          disabled={claiming || !claimTargetU.trim()}
          style={{ width: '100%', padding: '10px 0', borderRadius: 12, background: '#0284c7', color: '#fff', fontSize: 14, fontWeight: 500, border: 'none', cursor: 'pointer', opacity: claiming || !claimTargetU.trim() ? 0.5 : 1 }}
          data-testid="mq-claim-confirm"
        >
          {claiming ? '认领中…' : '确认认领'}
        </button>
      </Modal>
    </div>
  );
}

function StatCard({ label, value, small, testid }: { label: string; value: ReactNode; small?: boolean; testid?: string }) {
  return (
    <div style={{ flex: '1 1 160px', padding: 12, borderRadius: 8, border: '1px solid #d9d9d9', background: '#fff' }} data-testid={testid}>
      <div style={{ fontSize: 12, color: MUTED, marginBottom: 4 }}>{label}</div>
      <div style={small ? { fontSize: 14, fontWeight: 500 } : { fontSize: 24, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function MotherCard({
  m, onOpen, onEdit, onDelete, onTransfer, onExport, openMenuId, setOpenMenuId,
}: {
  m: MotherQuestion; onOpen: () => void; onEdit: () => void; onDelete: () => void;
  onTransfer: () => void; onExport: () => void;
  openMenuId: string | null; setOpenMenuId: (id: string | null) => void;
}) {
  const [hovered, setHovered] = useState(false);
  const menuOpen = openMenuId === m.id;
  const subjColor = SUBJECT_COLORS[m.subject || 'other'] || SUBJECT_COLORS.other;
  return (
    <div
      onClick={onOpen}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ position: 'relative', padding: 16, borderRadius: 8, border: '1px solid #d9d9d9', borderLeft: `4px solid ${subjColor}`, background: '#fff', cursor: 'pointer', transition: 'box-shadow 0.2s', boxShadow: hovered ? '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)' : undefined }}
      data-testid={`mq-card-${m.id}`}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <span style={{ fontSize: 12, padding: '2px 6px', borderRadius: 4, color: '#fff', flexShrink: 0, backgroundColor: subjColor }}>{SUBJECT_DISPLAY[m.subject || 'other']}</span>
          <h3 style={{ fontWeight: 600, margin: 0, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical' }} data-testid={`mq-card-title-${m.id}`}>{m.title}</h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 4, background: '#f5f5f5', color: 'rgba(0,0,0,0.85)', whiteSpace: 'nowrap' }}>{"★".repeat(m.difficulty)}</span>
          <button
            onClick={(e) => { e.stopPropagation(); setOpenMenuId(menuOpen ? null : m.id); }}
            style={cardBtnStyle}
            data-testid={`mq-card-menu-${m.id}`}
          >
            <EllipsisOutlined style={{ fontSize: 16, color: 'rgba(0,0,0,0.65)' }} />
          </button>
        </div>
      </div>
      {menuOpen && (
        <div
          style={{ position: 'absolute', top: 40, right: 8, zIndex: 10, background: '#fff', border: '1px solid #d9d9d9', borderRadius: 8, boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', padding: '4px 0', width: 128 }}
          onClick={(e) => e.stopPropagation()}
          data-testid={`mq-card-menu-list-${m.id}`}
        >
          <Button type="text" onClick={() => { setOpenMenuId(null); onEdit(); }} data-testid={`mq-card-edit-${m.id}`} style={menuItemStyle}><EditOutlined style={{ fontSize: 12 }} /> 编辑</Button>
          <Button type="text" onClick={() => { setOpenMenuId(null); onTransfer(); }} data-testid={`mq-card-status-${m.id}`} style={menuItemStyle}><CheckCircleOutlined style={{ fontSize: 12 }} /> 转换状态</Button>
          <Button type="text" onClick={() => { setOpenMenuId(null); onExport(); }} data-testid={`mq-card-export-${m.id}`} style={menuItemStyle}><DownloadOutlined style={{ fontSize: 12 }} /> 导出</Button>
          <Button type="text" onClick={() => { setOpenMenuId(null); onDelete(); }} data-testid={`mq-card-delete-${m.id}`} style={{ ...menuItemStyle, color: '#e11d48' }}><DeleteOutlined style={{ fontSize: 12 }} /> 删除</Button>
        </div>
      )}
      <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
        {m.photo_url && (
          <img src={m.photo_url} alt="" style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 6, border: '1px solid #d9d9d9', flexShrink: 0 }} />
        )}
        <p style={{ fontSize: 14, color: MUTED, flex: 1, margin: 0, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' }}>{m.question_text}</p>
      </div>
      {m.tags && m.tags.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 8 }}>
          {m.tags.map((tg, i) => <span key={i} style={{ fontSize: 12, padding: '2px 6px', borderRadius: 4, background: 'rgba(22,119,255,0.1)', color: PRIMARY }}>{tg}</span>)}
        </div>
      )}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 12, color: MUTED }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {m.grade && <span>{GRADE_DISPLAY[m.grade] || m.grade}</span>}
          {m.category && <span>· {CATEGORY_DISPLAY[m.category] || m.category}</span>}
          {m.mastery_status && <span style={{ color: MASTERY_COLOR[m.mastery_status] }} data-testid={`mq-card-mastery-${m.id}`}>· {MASTERY_DISPLAY[m.mastery_status] || m.mastery_status}</span>}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <FilterOutlined style={{ fontSize: 12 }} /> {m.variant_count} 变式
          <VideoCameraOutlined style={{ fontSize: 12, marginLeft: 4 }} /> {m.video_count} 视频
        </span>
      </div>
    </div>
  );
}

export default function MotherQuestionsPage() {
  return <MotherQuestionsContent />;
}
