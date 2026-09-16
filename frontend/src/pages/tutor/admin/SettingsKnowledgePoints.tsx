/**
 * 知识点管理（1:1 复刻自原仓 web/app/(utility)/settings/curriculum/knowledge-points/page.tsx）：
 * 按学科/学段管理知识树——工具栏（学科/学段筛选、从教材提取、学段归类、难度标注、
 * 数学图形标注、预置）、知识点树（难度★/学段/章节引用计数）、详情编辑器
 * （名称/学段/难度、关系图谱、关联章节、总结/讲解、实例、公式与推导、
 * 可拖拽图形、相关知识点出入向关系）。全功能保留，未裁剪。
 * cytoscape → SVG 力导向（KpRelationGraph）；MarkdownRenderer → LiteMarkdown；
 * MathWidget 资产注入逻辑 1:1；notify → antd message。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Col, Input, Row, Select, message } from 'antd';
import {
  AppstoreOutlined, DeleteOutlined, DragOutlined, ExperimentOutlined,
  LinkOutlined, LoadingOutlined, PlusOutlined, RightOutlined, RobotOutlined,
  SaveOutlined, StarOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import { SettingsPageHeader } from './SettingsPageHeader';
import { MarkdownField } from './MarkdownField';
import { MathWidget } from './MathWidget';
import { KpRelationGraph } from './KpRelationGraph';
import LiteMarkdown from './dtMarkdown';

const SUBJECTS: [string, string][] = [
  ['math', '数学'],
  ['chinese', '语文'],
  ['english', '英语'],
];
const GRADES = ['', '小学', '初中'];
const RELATIONS = ['前置知识', '后置知识', '相关', '包含'];
const SUBJECT_LABEL: Record<string, string> = {
  math: '数学',
  chinese: '语文',
  english: '英语',
};

interface KpNodeData {
  id: string;
  name: string;
  subject: string;
  grade: string | null;
  difficulty?: number | null;
  children?: KpNodeData[];
}
interface RelatedOut {
  kp_id: string;
  relation: string;
  name: string;
  subject: string;
}
interface RelatedIn {
  kp_id: string;
  relation: string;
  name: string;
  subject: string;
}
interface KpDetail {
  id: string;
  name: string;
  parent_id: string | null;
  subject: string;
  grade: string | null;
  difficulty: number | null;
  description: string | null;
  explanation: string | null;
  examples: { title: string; content: string }[];
  related: { kp_id: string; relation: string }[];
  formula: { name: string; latex: string; derivation: string } | null;
  figure: { type: string; config?: Record<string, unknown> } | null;
  related_out: RelatedOut[];
  related_in: RelatedIn[];
  chapters: { chapter_id: string; name: string; textbook_name: string }[];
}

const cardStyle: React.CSSProperties = { border: '1px solid #f0f0f0', borderRadius: 8, background: '#fff' };
const muted = 'rgba(0,0,0,0.45)';

export default function SettingsKnowledgePoints() {
  const [subject, setSubject] = useState('');
  const [grade, setGrade] = useState('');
  const [tree, setTree] = useState<KpNodeData[]>([]);
  const [flat, setFlat] = useState<KpNodeData[]>([]);
  const [refMap, setRefMap] = useState<Record<string, number>>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [diffing, setDiffing] = useState(false);
  const [figuring, setFiguring] = useState(false);

  const load = useCallback(async () => {
    const qs = `subject=${subject}${grade ? `&grade=${grade}` : ''}`;
    const [tr, ls] = await Promise.all([
      fetch(`/api/v1/curriculum/knowledge-points/tree?${qs}`).then((r) => r.json()),
      fetch(`/api/v1/curriculum/knowledge-points?${qs}`).then((r) => r.json()),
    ]);
    setTree(tr.tree || []);
    setFlat(ls.items || []);
  }, [subject, grade]);

  // 引用计数（全部教材章节的 kp_ids）
  useEffect(() => {
    let cancelled = false;
    fetch('/api/v1/curriculum/textbooks')
      .then((r) => r.json())
      .then(async (d) => {
        const tbs = d.items || [];
        const all: Array<{ kp_ids?: string[] }> = [];
        for (const t of tbs) {
          const r = await fetch(`/api/v1/curriculum/textbooks/${t.id}/chapters`).then((x) => x.json());
          (r.items || []).forEach((c: { kp_ids?: string[] }) => all.push(c));
        }
        if (cancelled) return;
        const map: Record<string, number> = {};
        all.forEach((c) => (c.kp_ids || []).forEach((kid: string) => (map[kid] = (map[kid] || 0) + 1)));
        setRefMap(map);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  const extractFromTextbooks = async () => {
    if (!window.confirm('用 LLM 从教材章节+原文自动提取「学科知识体系」知识点树，并自动关联所有章节？\n（将重建知识点目录，可能需要几分钟）')) return;
    setExtracting(true);
    message.info('LLM 提取中，请耐心等待（可能 2-5 分钟）...');
    try {
      const r = await fetch('/api/v1/curriculum/knowledge-points/extract-from-textbooks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      if (r.ok) {
        const d = await r.json();
        message.success(`已提取 ${d.rebuilt} 个知识点，关联 ${d.linked_chapters} 章`);
        await load();
      } else {
        const e = await r.text();
        message.error(`提取失败: ${e.slice(0, 80)}`);
      }
    } catch (e) {
      message.error('提取请求失败');
    }
    setExtracting(false);
  };

  const assignGrades = async () => {
    if (!window.confirm('按教材年级自动给知识点归类学段（小学/初中）？父节点按子节点继承。')) return;
    setAssigning(true);
    message.info('归类中...');
    try {
      const r = await fetch('/api/v1/curriculum/knowledge-points/assign-grades', { method: 'POST' });
      if (r.ok) {
        const d = await r.json();
        message.success(`已归类 ${d.updated} 个知识点`);
        await load();
      } else message.error('归类失败');
    } catch {
      message.error('归类请求失败');
    }
    setAssigning(false);
  };

  const seed = async () => {
    if (!window.confirm('预置小学1-6年级数学知识点体系？')) return;
    message.info('正在预置...');
    const r = await fetch('/api/v1/mother-questions/knowledge-points/seed', { method: 'POST' });
    if (r.ok) {
      const d = await r.json();
      message.success(`已预置 ${d.created} 个知识点`);
      await load();
    } else message.error('预置失败');
  };

  const assignDifficulty = async () => {
    if (!window.confirm('用 LLM 为所有学科知识点标注难度 1-5（用于树内易→难排序）？约需 1-3 分钟。')) return;
    setDiffing(true);
    message.info('LLM 标注难度中，请耐心等待...');
    try {
      const r = await fetch('/api/v1/curriculum/knowledge-points/assign-difficulty', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      if (r.ok) {
        const d = await r.json();
        message.success(`已标注 ${d.matched} 个知识点难度`);
        await load();
      } else message.error('难度标注失败');
    } catch {
      message.error('难度标注请求失败');
    }
    setDiffing(false);
  };

  const assignFigures = async () => {
    if (!window.confirm('按规则为数学知识点自动标注可拖拽图形（数轴/方程天平/几何画板）？')) return;
    setFiguring(true);
    message.info('标注图形中...');
    try {
      const r = await fetch('/api/v1/curriculum/knowledge-points/assign-figures', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject: 'math' }),
      });
      if (r.ok) {
        const d = await r.json();
        message.success(`已标注 ${d.updated} 个数学知识点图形`);
        await load();
        if (subject === '' || subject === 'math') setSelectedId(null);
      } else message.error('图形标注失败');
    } catch {
      message.error('图形标注请求失败');
    }
    setFiguring(false);
  };

  return (
    <div>
      <SettingsPageHeader
        title="知识点管理"
        description="按学科/学段管理知识树。每个知识点可维护：总结、讲解（Markdown+公式）、实例、数学公式与推导过程、以及与其他知识点的关系（形成关系图谱）。自主学习「知识点总结」直接引用这里的内容。"
      />
      {/* 工具栏 */}
      <div style={{ marginBottom: 16, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
        <Select
          style={{ width: 120 }}
          value={subject}
          onChange={(v) => {
            setSubject(v);
            setSelectedId(null);
          }}
          options={[{ value: '', label: '全部学科' }, ...SUBJECTS.map(([v, l]) => ({ value: v, label: l }))]}
        />
        <Select
          style={{ width: 120 }}
          value={grade}
          onChange={(v) => {
            setGrade(v);
            setSelectedId(null);
          }}
          options={[
            { value: '', label: '全部学段' },
            { value: '小学', label: '小学' },
            { value: '初中', label: '初中' },
          ]}
        />
        <Button size="small" onClick={extractFromTextbooks} disabled={extracting} icon={extracting ? <LoadingOutlined spin /> : <ThunderboltOutlined />}>
          {extracting ? '提取中...' : '从教材提取'}
        </Button>
        <Button size="small" onClick={assignGrades} disabled={assigning} icon={assigning ? <LoadingOutlined spin /> : <ThunderboltOutlined />}>
          学段归类
        </Button>
        <Button size="small" onClick={assignDifficulty} disabled={diffing} icon={diffing ? <LoadingOutlined spin /> : <StarOutlined />}>
          难度标注
        </Button>
        <Button size="small" onClick={assignFigures} disabled={figuring} icon={figuring ? <LoadingOutlined spin /> : <DragOutlined />}>
          数学图形标注
        </Button>
        <Button size="small" onClick={seed} icon={<ThunderboltOutlined />}>
          预置
        </Button>
      </div>

      <Row gutter={20}>
        {/* 知识树 */}
        <Col xs={24} lg={10}>
          <section style={cardStyle}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
              <AppstoreOutlined style={{ color: '#f59e0b' }} />
              <h2 style={{ margin: 0, fontWeight: 600, fontSize: 14 }}>知识点树</h2>
              <span style={{ fontSize: 12, color: muted, marginLeft: 'auto' }}>{flat.length} 个</span>
            </div>
            <div style={{ padding: 12, maxHeight: '70vh', overflowY: 'auto' }}>
              {tree.length === 0 ? (
                <p style={{ fontSize: 14, color: muted }}>暂无知识点，可「从教材提取」或手动添加。</p>
              ) : (
                tree.map((n) => (
                  <KpNode
                    key={n.id}
                    node={n}
                    depth={0}
                    selectedId={selectedId}
                    refMap={refMap}
                    onSelect={setSelectedId}
                  />
                ))
              )}
            </div>
          </section>
        </Col>

        {/* 详情编辑器 */}
        <Col xs={24} lg={14}>
          <section style={cardStyle}>
            {selectedId ? (
              <DetailEditor
                key={selectedId}
                kpId={selectedId}
                subject={subject}
                flat={flat}
                onChanged={() => load()}
                onJump={setSelectedId}
              />
            ) : (
              <div style={{ height: 256, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, fontSize: 14, color: muted }}>
                <AppstoreOutlined style={{ fontSize: 32, opacity: 0.4 }} />
                在左侧选择一个知识点，编辑 总结 / 讲解 / 实例 / 公式 / 关系
              </div>
            )}
          </section>
        </Col>
      </Row>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 树节点
// ---------------------------------------------------------------------------
function KpNode({
  node,
  depth,
  selectedId,
  refMap,
  onSelect,
}: {
  node: KpNodeData;
  depth: number;
  selectedId: string | null;
  refMap: Record<string, number>;
  onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState(depth < 1);
  const hasChildren = (node.children || []).length > 0;
  const refCount = refMap[node.id] || 0;
  const active = selectedId === node.id;
  return (
    <div>
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0',
          borderRadius: 4, cursor: 'pointer',
          background: active ? 'rgba(22,119,255,0.1)' : 'transparent',
          paddingLeft: depth * 16,
        }}
        onMouseEnter={(e) => {
          if (!active) e.currentTarget.style.background = 'rgba(0,0,0,0.03)';
        }}
        onMouseLeave={(e) => {
          if (!active) e.currentTarget.style.background = 'transparent';
        }}
        onClick={() => onSelect(node.id)}
      >
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setOpen(!open);
            }}
            style={{
              padding: 2, border: 'none', background: 'transparent', cursor: 'pointer',
              borderRadius: 2, lineHeight: 0, transition: 'transform 0.2s',
              transform: open ? 'rotate(90deg)' : 'none',
            }}
          >
            <RightOutlined style={{ fontSize: 11, color: 'rgba(0,0,0,0.45)' }} />
          </button>
        ) : (
          <span style={{ width: 16, display: 'inline-block' }} />
        )}
        <span style={{ fontSize: 14 }}>{node.name}</span>
        {node.difficulty ? (
          <span style={{ fontSize: 10, color: '#f59e0b' }} title={`难度 ${node.difficulty}/5`}>
            {'★'.repeat(Math.min(5, node.difficulty))}
          </span>
        ) : null}
        {node.grade && (
          <span style={{ fontSize: 10, padding: '1px 4px', borderRadius: 2, background: '#f5f5f5', color: muted }}>{node.grade}</span>
        )}
        {refCount > 0 && (
          <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 999, background: 'rgba(22,119,255,0.1)', color: '#1677ff' }}>📎 {refCount}</span>
        )}
      </div>
      {open && node.children?.map((c) => (
        <KpNode key={c.id} node={c} depth={depth + 1} selectedId={selectedId} refMap={refMap} onSelect={onSelect} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 详情编辑器
// ---------------------------------------------------------------------------
function DetailEditor({
  kpId,
  subject,
  flat,
  onChanged,
  onJump,
}: {
  kpId: string;
  subject: string;
  flat: KpNodeData[];
  onChanged: () => void;
  onJump: (id: string) => void;
}) {
  const [detail, setDetail] = useState<KpDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [relPick, setRelPick] = useState('');
  const [relType, setRelType] = useState('相关');

  const loadDetail = useCallback(async () => {
    setLoading(true);
    try {
      const d = await fetch(`/api/v1/curriculum/knowledge-points/${kpId}`).then((r) => r.json());
      setDetail(d);
    } catch {
      setDetail(null);
    }
    setLoading(false);
  }, [kpId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const patch = (p: Partial<KpDetail>) => {
    setDetail((d) => (d ? { ...d, ...p } : d));
  };

  const save = async () => {
    if (!detail) return;
    setSaving(true);
    try {
      const r = await fetch(`/api/v1/curriculum/knowledge-points/${kpId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: detail.name,
          grade: detail.grade || null,
          difficulty: detail.difficulty || null,
          description: detail.description || null,
          explanation: detail.explanation || null,
          examples: detail.examples || [],
          formula: detail.formula || null,
          figure: detail.figure || null,
          related: detail.related || [],
        }),
      });
      if (r.ok) {
        message.success('已保存');
        await loadDetail();
        onChanged();
      } else message.error('保存失败');
    } catch {
      message.error('保存请求失败');
    }
    setSaving(false);
  };

  const enrich = async () => {
    if (!detail) return;
    if (!window.confirm(`用 LLM 为「${detail.name}」补全 总结/讲解/实例${detail.subject === 'math' ? '/公式推导' : ''}/相关知识点？`)) return;
    setEnriching(true);
    message.info('LLM 生成中，约 10-60 秒...');
    try {
      const r = await fetch(`/api/v1/curriculum/knowledge-points/${kpId}/enrich`, { method: 'POST' });
      if (r.ok) {
        message.success('已补全');
        await loadDetail();
        onChanged();
      } else {
        const e = await r.text();
        message.error(`补全失败: ${e.slice(0, 100)}`);
      }
    } catch {
      message.error('补全请求失败');
    }
    setEnriching(false);
  };

  // 可拖拽图形：类型 + 配置 JSON
  const [figType, setFigType] = useState('numberline');
  const [figConfig, setFigConfig] = useState('{}');
  const [figError, setFigError] = useState<string | null>(null);
  const applyFigConfig = (type: string, raw: string) => {
    setFigType(type);
    setFigConfig(raw);
    try {
      const config = JSON.parse(raw || '{}');
      setFigError(null);
      patch({ figure: type ? { type, config } : null });
    } catch {
      setFigError('配置 JSON 解析失败（请检查括号/引号）');
    }
  };
  useEffect(() => {
    if (detail?.figure) {
      setFigType(detail.figure.type || 'numberline');
      setFigConfig(JSON.stringify(detail.figure.config || {}, null, 2));
    } else {
      setFigType('numberline');
      setFigConfig('{}');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kpId]);

  const addRelated = () => {
    if (!relPick || !detail) return;
    if (detail.related.some((r) => r.kp_id === relPick)) {
      message.info('已存在该关联');
      return;
    }
    patch({ related: [...detail.related, { kp_id: relPick, relation: relType }] });
    setRelPick('');
  };
  const removeRelated = (kid: string) => {
    if (!detail) return;
    patch({ related: detail.related.filter((r) => r.kp_id !== kid) });
  };

  const graph = useMemo(() => {
    if (!detail) return { nodes: [] as { id: string; name: string; subject?: string }[], edges: [] as { source: string; target: string; relation: string }[] };
    const nodes: { id: string; name: string; subject?: string }[] = [{ id: detail.id, name: detail.name, subject: detail.subject }];
    const edges: { source: string; target: string; relation: string }[] = [];
    const seen = new Set<string>([detail.id]);
    const addNode = (n: { kp_id: string; name: string; subject: string }) => {
      if (!seen.has(n.kp_id) && n.name) {
        seen.add(n.kp_id);
        nodes.push({ id: n.kp_id, name: n.name, subject: n.subject });
      }
    };
    detail.related_out.forEach((r) => {
      addNode(r);
      edges.push({ source: detail.id, target: r.kp_id, relation: r.relation });
    });
    detail.related_in.forEach((r) => {
      addNode(r);
      edges.push({ source: r.kp_id, target: detail.id, relation: r.relation });
    });
    return { nodes, edges };
  }, [detail]);

  if (loading) {
    return (
      <div style={{ height: 256, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, color: muted }}>
        <LoadingOutlined spin style={{ marginRight: 8 }} /> 加载中...
      </div>
    );
  }
  if (!detail) {
    return <div style={{ padding: 24, fontSize: 14, color: muted }}>加载失败</div>;
  }

  return (
    <div>
      {/* 头部 */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <Input
          style={{ flex: 1, minWidth: 160, fontWeight: 500 }}
          value={detail.name}
          onChange={(e) => patch({ name: e.target.value })}
        />
        <span style={{ fontSize: 12, color: muted }}>{SUBJECT_LABEL[detail.subject] || detail.subject}</span>
        <Select
          style={{ width: 128 }}
          value={detail.grade || ''}
          onChange={(v) => patch({ grade: v || null })}
          options={GRADES.map((g) => ({ value: g, label: g || '（未定学段）' }))}
        />
        <span title="难度：树内按难度易→难排序">
          <Select
            style={{ width: 120 }}
            value={detail.difficulty ? String(detail.difficulty) : ''}
            onChange={(v) => patch({ difficulty: v ? Number(v) : null })}
            options={[
              { value: '', label: '难度?' },
              ...[1, 2, 3, 4, 5].map((d) => ({ value: String(d), label: `${'★'.repeat(d)} 难度 ${d}` })),
            ]}
          />
        </span>
        <Button
          size="small"
          onClick={enrich}
          disabled={enriching}
          icon={enriching ? <LoadingOutlined spin /> : <RobotOutlined />}
        >
          AI 补全详情
        </Button>
        <Button
          type="primary"
          size="small"
          onClick={save}
          disabled={saving}
          icon={<SaveOutlined />}
        >
          {saving ? '保存中...' : '保存'}
        </Button>
      </div>

      <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 20, maxHeight: '70vh', overflowY: 'auto' }}>
        {/* 关系图谱 */}
        {(graph.nodes.length > 1 || (detail.related_out.length + detail.related_in.length) > 0) && (
          <div>
            <h3 style={{ fontSize: 12, fontWeight: 500, color: muted, margin: '0 0 8px' }}>关系图谱（点击节点跳转）</h3>
            <KpRelationGraph
              nodes={graph.nodes}
              edges={graph.edges}
              onNodeClick={(id) => id !== detail.id && onJump(id)}
              height={240}
            />
          </div>
        )}

        {/* 关联章节 */}
        {detail.chapters.length > 0 && (
          <div>
            <h3 style={{ fontSize: 12, fontWeight: 500, color: muted, margin: '0 0 6px' }}>关联章节</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {detail.chapters.map((c) => (
                <span key={c.chapter_id} style={{ fontSize: 11, padding: '4px 8px', borderRadius: 4, background: '#f5f5f5' }}>
                  {c.textbook_name} · {c.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 总结 */}
        <MarkdownField
          label="总结（一句话/一段，自主学习中默认展示）"
          value={detail.description || ''}
          onChange={(v) => patch({ description: v })}
          placeholder="用一两句话概括该知识点的核心..."
        />

        {/* 讲解 */}
        <MarkdownField
          label="讲解（Markdown，可含 $...$ 公式）"
          value={detail.explanation || ''}
          onChange={(v) => patch({ explanation: v })}
          rows={6}
          placeholder={'# 定义\n...\n\n# 关键点\n- ...\n\n公式用 $...$ 或 $$...$$ 包裹'}
        />

        {/* 实例 */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <label style={{ fontSize: 12, fontWeight: 500, color: muted }}>实例（例题/典型例子）</label>
            <Button
              type="text"
              size="small"
              icon={<PlusOutlined />}
              onClick={() => patch({ examples: [...(detail.examples || []), { title: '', content: '' }] })}
              style={{ fontSize: 11, color: '#1677ff' }}
            >
              添加实例
            </Button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(detail.examples || []).length === 0 && (
              <p style={{ fontSize: 12, color: muted }}>暂无实例，可手动添加或点「AI 补全详情」。</p>
            )}
            {(detail.examples || []).map((ex, i) => (
              <div key={i} style={{ borderRadius: 6, border: '1px solid #f0f0f0', padding: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Input
                    style={{ flex: 1, fontSize: 12, fontWeight: 500 }}
                    placeholder="实例标题（如：例1 温度零上零下）"
                    value={ex.title}
                    onChange={(e) => {
                      const arr = [...(detail.examples || [])];
                      arr[i] = { ...arr[i], title: e.target.value };
                      patch({ examples: arr });
                    }}
                  />
                  <Button
                    type="text"
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => patch({ examples: (detail.examples || []).filter((_, j) => j !== i) })}
                  />
                </div>
                <Input.TextArea
                  rows={2}
                  style={{ fontSize: 12 }}
                  placeholder="实例内容（可含公式）"
                  value={ex.content}
                  onChange={(e) => {
                    const arr = [...(detail.examples || [])];
                    arr[i] = { ...arr[i], content: e.target.value };
                    patch({ examples: arr });
                  }}
                />
              </div>
            ))}
          </div>
        </div>

        {/* 公式（数学） */}
        {(detail.subject === 'math' || detail.formula) && (
          <div style={{ borderRadius: 6, border: '1px solid #f0f0f0', padding: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <label style={{ fontSize: 12, fontWeight: 500, color: muted, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <ExperimentOutlined /> 公式与推导
              </label>
              {detail.formula && (
                <Button
                  type="text"
                  size="small"
                  danger
                  onClick={() => patch({ formula: null })}
                  style={{ fontSize: 11 }}
                >
                  清除公式
                </Button>
              )}
            </div>
            <Input
              placeholder="公式名（如：有理数的加法法则）"
              value={detail.formula?.name || ''}
              onChange={(e) =>
                patch({
                  formula: { name: e.target.value, latex: detail.formula?.latex || '', derivation: detail.formula?.derivation || '' },
                })
              }
            />
            <div>
              <label style={{ fontSize: 11, color: muted }}>LaTeX 公式</label>
              <Input.TextArea
                style={{ marginTop: 4, fontFamily: 'SFMono-Regular, Consolas, Menlo, monospace', fontSize: 14 }}
                rows={2}
                placeholder={'如: a + (-b) = a - b'}
                value={detail.formula?.latex || ''}
                onChange={(e) =>
                  patch({
                    formula: { name: detail.formula?.name || '', latex: e.target.value, derivation: detail.formula?.derivation || '' },
                  })
                }
              />
              {detail.formula?.latex && (
                <div style={{ marginTop: 4, padding: '8px 12px', borderRadius: 6, background: 'rgba(0,0,0,0.02)', overflowX: 'auto' }}>
                  <LiteMarkdown content={`$$${detail.formula.latex}$$`} />
                </div>
              )}
            </div>
            <MarkdownField
              label="推导过程（Markdown，可含公式与步骤）"
              value={detail.formula?.derivation || ''}
              onChange={(v) =>
                patch({
                  formula: { name: detail.formula?.name || '', latex: detail.formula?.latex || '', derivation: v },
                })
              }
              rows={5}
              placeholder={'推导过程，分步说明：\n1. ...\n2. ...\n\n关键变换用 $...$ 表示'}
            />
          </div>
        )}

        {/* 可拖拽图形（数学图形化） */}
        {detail.subject === 'math' && (
          <div style={{ borderRadius: 6, border: '1px solid #f0f0f0', padding: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <label style={{ fontSize: 12, fontWeight: 500, color: muted, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <DragOutlined /> 可拖拽图形（数学图形化）
              </label>
              {detail.figure && (
                <Button
                  type="text"
                  size="small"
                  danger
                  onClick={() => {
                    patch({ figure: null });
                    setFigConfig('{}');
                  }}
                  style={{ fontSize: 11 }}
                >
                  清除图形
                </Button>
              )}
            </div>
            <Select
              value={figType}
              onChange={(v) => applyFigConfig(v, figConfig)}
              options={[
                { value: '', label: '（无）' },
                { value: 'numberline', label: '🧮 数轴拖一拖' },
                { value: 'balance', label: '⚖️ 方程天平' },
                { value: 'geoboard', label: '📐 几何画板' },
              ]}
            />
            <div>
              <label style={{ fontSize: 11, color: muted }}>配置 JSON（可选，修改后预览实时更新）</label>
              <Input.TextArea
                style={{ marginTop: 4, fontFamily: 'SFMono-Regular, Consolas, Menlo, monospace', fontSize: 12 }}
                rows={4}
                value={figConfig}
                onChange={(e) => applyFigConfig(figType, e.target.value)}
                placeholder={'{"min": -10, "max": 10, "modes": ["find","compare","free"], "targets": [3,-5,0]}'}
              />
            </div>
            {figError && <p style={{ fontSize: 11, color: '#f43f5e' }}>{figError}</p>}
            {detail.figure ? (
              <MathWidget figure={detail.figure} />
            ) : (
              <p style={{ fontSize: 12, color: muted }}>
                选择上方图形类型后，这里会显示可拖拽的实时预览（也可用工具栏「数学图形标注」自动按规则标注）。
              </p>
            )}
          </div>
        )}

        {/* 相关知识点 */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <label style={{ fontSize: 12, fontWeight: 500, color: muted, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <LinkOutlined /> 相关知识点（关系图谱边）
            </label>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
            {(detail.related_out || []).map((r) => (
              <span
                key={r.kp_id}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11,
                  padding: '4px 8px', borderRadius: 999, border: '1px solid #f0f0f0', background: 'rgba(0,0,0,0.02)',
                }}
              >
                <a style={{ color: '#1677ff' }} onClick={() => onJump(r.kp_id)}>
                  {r.name}
                </a>
                <span style={{ color: muted }}>{r.relation}</span>
                <a style={{ color: 'rgba(244,63,94,0.7)' }} onClick={() => removeRelated(r.kp_id)}>
                  <DeleteOutlined style={{ fontSize: 12 }} />
                </a>
              </span>
            ))}
            {(detail.related_out || []).length === 0 && (
              <span style={{ fontSize: 12, color: muted }}>暂无出向关系</span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Select
              style={{ flex: 1 }}
              value={relPick}
              onChange={(v) => setRelPick(v)}
              options={[
                { value: '', label: '选择知识点...' },
                ...flat
                  .filter((f) => f.id !== detail.id && f.subject === detail.subject)
                  .map((f) => ({ value: f.id, label: f.name })),
              ]}
            />
            <Select
              style={{ width: 110 }}
              value={relType}
              onChange={(v) => setRelType(v)}
              options={RELATIONS.map((r) => ({ value: r, label: r }))}
            />
            <Button size="small" onClick={addRelated} icon={<PlusOutlined />}>
              添加
            </Button>
          </div>
          {detail.related_in.length > 0 && (
            <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              <span style={{ fontSize: 11, color: muted, alignSelf: 'center' }}>被引用为：</span>
              {detail.related_in.map((r) => (
                <a
                  key={r.kp_id}
                  onClick={() => onJump(r.kp_id)}
                  style={{ fontSize: 11, padding: '4px 8px', borderRadius: 999, border: '1px solid #f0f0f0', color: '#1677ff' }}
                >
                  {r.name}（{r.relation}）
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
