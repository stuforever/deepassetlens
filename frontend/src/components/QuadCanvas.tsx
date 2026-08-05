import React, { useEffect, useState, useRef, useLayoutEffect, useMemo, useCallback } from 'react';
import { Select, Spin, Empty, Popover } from 'antd';
import { conceptApi } from '../services/api';
import { tokens } from '../theme/tokens';
// 注意：SVG stroke 属性不支持 CSS var(--*)，需用 tokens 实际色值。

const COL_W = 176;        // 概念列宽
const ENT_W = 210;        // 实体列宽
const HALF_W = COL_W * 2; // 左/右半宽

const COLORS: Record<string, string> = {
  L1: '#5B8FF9', L2: '#5AD8A6', L3: tokens.colors.ai, L4: '#F6BD16',
};

const EMPTY: any[] = []; // 稳定空数组，避免 || [] 每次新引用导致 useEffect/useLayoutEffect 循环

// 概念列容器（模块级，避免重渲染 remount 丢 ref）
const ColWrap: React.FC<{ title: string; color: string; children: React.ReactNode }> = ({ title, color, children }) => (
  <div style={{ width: COL_W, flexShrink: 0, display: 'flex', flexDirection: 'column', borderRight: '1px solid var(--color-border)', minWidth: 0 }}>
    <div style={{ padding: '6px 10px', fontSize: 12, fontWeight: 600, color, borderBottom: '1px solid var(--color-border)', background: 'var(--bg-subtle)', whiteSpace: 'nowrap' }}>{title}</div>
    <div style={{ flex: 1, overflowY: 'auto', padding: '4px 8px' }}>{children}</div>
  </div>
);

// 实体列容器（带 onScroll 触发连线重算）
const EntCol: React.FC<{ title: string; color: string; onScroll?: () => void; children: React.ReactNode }> = ({ title, color, onScroll, children }) => (
  <div style={{ width: ENT_W, flexShrink: 0, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
    <div style={{ padding: '6px 10px', fontSize: 12, fontWeight: 600, color, borderBottom: '1px solid var(--color-border)', background: 'var(--bg-subtle)', whiteSpace: 'nowrap' }}>{title}</div>
    <div onScroll={onScroll} style={{ flex: 1, overflowY: 'auto', padding: '4px 8px' }}>{children}</div>
  </div>
);

type Line = { m: string; a: string; y1: number; y2: number; x2: number };

const QuadCanvas: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [l1Filter, setL1Filter] = useState<string | undefined>();
  const [l0Filter, setL0Filter] = useState<string | undefined>();
  const [selL1, setSelL1] = useState<string | undefined>();
  const [selL2, setSelL2] = useState<string | undefined>();
  const [selL3, setSelL3] = useState<string | undefined>();
  const [selL4, setSelL4] = useState<string | undefined>();
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [hoverEnt, setHoverEnt] = useState<string | null>(null);
  const [lines, setLines] = useState<Line[]>([]);

  const l2xRefs = useRef<Map<string, HTMLElement>>(new Map());
  const l4xRefs = useRef<Map<string, HTMLElement>>(new Map());
  const wrapRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await conceptApi.getGraphMatrix();
      setData(res.data.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };
  useEffect(() => { fetchData(); }, []);

  const columns: any[] = data?.columns || EMPTY;
  const domains: any[] = data?.domains || EMPTY;
  const rows: any[] = data?.rows || EMPTY;

  const l1List = useMemo(() => columns.filter((c: any) => c.level === 1 && (!l1Filter || c.id === l1Filter)), [columns, l1Filter]);
  const l2List = useMemo(() => columns.filter((c: any) => c.level === 2 && c.parent_id === selL1), [columns, selL1]);
  const l2xEntities = useMemo(() => (columns.find((c: any) => c.id === selL2)?.entities) || EMPTY, [columns, selL2]);
  const l3List = useMemo(() => rows.filter((r: any) => r.level === 3 && (!l0Filter || r.parent_id === l0Filter)), [rows, l0Filter]);
  const l4List = useMemo(() => rows.filter((r: any) => r.level === 4 && r.parent_id === selL3), [rows, selL3]);
  const l4xEntities = useMemo(() => (rows.find((r: any) => r.id === selL4)?.entities) || EMPTY, [rows, selL4]);

  // 默认选中首个（数据/筛选变化时自动续接）
  useEffect(() => { if (l1List.length && !l1List.some((c: any) => c.id === selL1)) setSelL1(l1List[0].id); }, [l1List, selL1]);
  useEffect(() => {
    if (l2List.length && !l2List.some((c: any) => c.id === selL2)) setSelL2(l2List[0].id);
    else if (!l2List.length && selL2) setSelL2(undefined);
  }, [l2List, selL2]);
  useEffect(() => { if (l3List.length && !l3List.some((r: any) => r.id === selL3)) setSelL3(l3List[0].id); }, [l3List, selL3]);
  useEffect(() => {
    if (l4List.length && !l4List.some((r: any) => r.id === selL4)) setSelL4(l4List[0].id);
    else if (!l4List.length && selL4) setSelL4(undefined);
  }, [l4List, selL4]);

  // 连线坐标计算：m(L2X)右中 -> a(L4X)左中，相对 SVG 容器；宽度读 ref 存入 line，避免 wrapW state 循环
  const computeLines = useCallback(() => {
    const wrap = wrapRef.current;
    if (!wrap) { setLines([]); return; }
    const wr = wrap.getBoundingClientRect();
    const w = wr.width;
    const next: Line[] = [];
    l2xEntities.forEach((m: any) => {
      const mEl = l2xRefs.current.get(String(m.id));
      if (!mEl) return;
      const mr = mEl.getBoundingClientRect();
      l4xEntities.forEach((a: any) => {
        const linkMap = a.linked_entity_map || {};
        if (!linkMap[m.id]) return;
        const aEl = l4xRefs.current.get(String(a.id));
        if (!aEl) return;
        const ar = aEl.getBoundingClientRect();
        next.push({
          m: String(m.id), a: String(a.id), x2: w,
          y1: mr.top + mr.height / 2 - wr.top,
          y2: ar.top + ar.height / 2 - wr.top,
        });
      });
    });
    setLines(next);
  }, [l2xEntities, l4xEntities]);

  useLayoutEffect(() => { computeLines(); }, [computeLines, leftCollapsed, rightCollapsed]);

  const scheduleCompute = () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => computeLines());
  };

  if (loading && !data) return <div style={{ padding: 100, textAlign: 'center' }}><Spin size="large" /></div>;
  if (!data) return <Empty description="暂无数据" />;

  const l1Options = columns.filter((c: any) => c.level === 1).map((c: any) => ({ label: c.name, value: c.id }));
  const l0Options = domains.map((d: any) => ({ label: d.name, value: d.id }));

  // 概念节点
  const renderConcept = (item: any, level: string, selected: boolean, onClick: () => void) => {
    const color = COLORS[level];
    return (
      <div
        key={item.id}
        onClick={onClick}
        style={{
          padding: '6px 10px', margin: '4px 0', borderRadius: 6, cursor: 'pointer', fontSize: 13,
          background: selected ? color + '1a' : 'var(--bg-content)',
          border: `1px solid ${selected ? color : 'var(--border-color)'}`,
          boxShadow: `inset 3px 0 0 ${color}` + (selected ? `, 0 0 0 1px ${color}55` : ''),
          transition: 'background .2s, box-shadow .2s',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = selected ? color + '26' : 'var(--bg-hover)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = selected ? color + '1a' : 'var(--bg-content)'; }}
      >
        {item.name}
      </div>
    );
  };

  // 实体节点
  const renderEntity = (item: any, kind: 'master' | 'activity') => {
    const color = kind === 'master' ? '#fa8c16' : '#13c2c2';
    const bg = kind === 'master' ? '#fff7e6' : '#e6fffb';
    const refCb = (el: HTMLElement | null) => {
      const map = kind === 'master' ? l2xRefs.current : l4xRefs.current;
      if (el) map.set(String(item.id), el); else map.delete(String(item.id));
    };
    return (
      <div
        key={item.id}
        ref={refCb}
        onMouseEnter={() => setHoverEnt(String(item.id))}
        onMouseLeave={() => setHoverEnt(null)}
        style={{
          padding: '6px 10px', margin: '4px 0', borderRadius: 6, cursor: 'pointer',
          background: bg, border: `1px solid ${color}66`, fontSize: 12, lineHeight: 1.3,
          transition: 'background .2s, box-shadow .2s',
        }}
      >
        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{item.name}</div>
        <div style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>{item.code}</div>
      </div>
    );
  };

  const emptyHint = (txt: string) => <div style={{ color: 'var(--border-strong)', fontSize: 12, padding: '12px 8px', textAlign: 'center' }}>{txt}</div>;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-content)' }}>
      {/* 顶部筛选 */}
      <div style={{ padding: '8px 12px', display: 'flex', gap: 12, alignItems: 'center', borderBottom: '1px solid var(--color-border)', flexShrink: 0 }}>
        <Select allowClear placeholder="筛选主数据L1" value={l1Filter} onChange={setL1Filter} options={l1Options} style={{ width: 180 }} />
        <Select allowClear placeholder="筛选业务域" value={l0Filter} onChange={setL0Filter} options={l0Options} style={{ width: 160 }} />
        <span style={{ color: 'var(--text-tertiary)', fontSize: 12, flex: 1 }}>左半 L1→L2→L2X，右半 L3→L4→L4X，中间为打点关系；点击节点逐级展开，悬停实体高亮连线</span>
        <Popover trigger="click" placement="bottomRight" content={
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 2 }}>概念层级</div>
            {([['L1', '#5B8FF9'], ['L2', '#5AD8A6'], ['L3', tokens.colors.ai], ['L4', '#F6BD16']] as const).map(([l, c]) => (
              <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ width: 12, height: 12, borderRadius: 3, background: c, border: '1px solid var(--border-color)' }} />
                {l}
              </div>
            ))}
            <div style={{ fontWeight: 600, margin: '4px 0 2px' }}>实体类型</div>
            {([['主数据实体', '#fa8c16', '#fff7e6'], ['业务活动实体', '#13c2c2', '#e6fffb']] as const).map(([l, c, bg]) => (
              <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ width: 12, height: 12, borderRadius: 3, background: bg, border: `1px solid ${c}` }} />
                {l}
              </div>
            ))}
          </div>
        }>
          <span style={{ cursor: 'pointer', color: 'var(--text-tertiary)', fontSize: 12, padding: '2px 8px', border: '1px solid var(--border-color)', borderRadius: 4 }}>
            图例
          </span>
        </Popover>
      </div>
      {/* 六列 */}
      <div style={{ flex: 1, display: 'flex', minHeight: 0, overflow: 'hidden' }}>
        {/* 左半 L1+L2 */}
        <div style={{ width: leftCollapsed ? 0 : HALF_W, overflow: 'hidden', transition: 'width .3s ease', display: 'flex', flexShrink: 0 }}>
          <ColWrap title="L1 主数据分组" color={COLORS.L1}>
            {l1List.length ? l1List.map((c: any) => renderConcept(c, 'L1', selL1 === c.id, () => setSelL1(c.id))) : emptyHint('无 L1')}
          </ColWrap>
          <ColWrap title="L2 主数据" color={COLORS.L2}>
            {l2List.length ? l2List.map((c: any) => renderConcept(c, 'L2', selL2 === c.id, () => setSelL2(c.id))) : emptyHint('请选择 L1')}
          </ColWrap>
        </div>
        {/* 左折叠按钮 */}
        <div onClick={() => setLeftCollapsed(v => !v)} title={leftCollapsed ? '展开左半' : '折叠左半'} style={{ width: 18, cursor: 'pointer', background: 'var(--bg-subtle)', borderRight: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', flexShrink: 0, fontSize: 10 }}>
          {leftCollapsed ? '▶' : '◀'}
        </div>
        {/* 中间核心 L2X + SVG + L4X */}
        <div style={{ flex: 1, display: 'flex', minHeight: 0, minWidth: 0 }}>
          <EntCol title="L2X 主数据实体" color="#fa8c16" onScroll={scheduleCompute}>
            {l2xEntities.length ? l2xEntities.map((e: any) => renderEntity(e, 'master')) : emptyHint('请选择 L2')}
          </EntCol>
          <div ref={wrapRef} style={{ flex: 1, minWidth: 80, position: 'relative' }}>
            <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
              {lines.map((l, i) => {
                const active = !hoverEnt || hoverEnt === l.m || hoverEnt === l.a;
                const dx = l.x2 / 2;
                return (
                  <path
                    key={i}
                    d={`M 0 ${l.y1} C ${dx} ${l.y1}, ${l.x2 - dx} ${l.y2}, ${l.x2} ${l.y2}`}
                    stroke={active ? '#fa541c' : tokens.colors.primaryBg}
                    strokeWidth={active && hoverEnt ? 2 : 1.2}
                    fill="none"
                    opacity={active ? 0.85 : 0.1}
                    style={{ transition: 'opacity .2s, stroke .2s' }}
                  />
                );
              })}
            </svg>
            {lines.length === 0 && <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', color: 'var(--border-color)', fontSize: 12 }}>打点关系</div>}
          </div>
          <EntCol title="L4X 业务活动实体" color="#13c2c2" onScroll={scheduleCompute}>
            {l4xEntities.length ? l4xEntities.map((e: any) => renderEntity(e, 'activity')) : emptyHint('请选择 L4')}
          </EntCol>
        </div>
        {/* 右折叠按钮 */}
        <div onClick={() => setRightCollapsed(v => !v)} title={rightCollapsed ? '展开右半' : '折叠右半'} style={{ width: 18, cursor: 'pointer', background: 'var(--bg-subtle)', borderLeft: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', flexShrink: 0, fontSize: 10 }}>
          {rightCollapsed ? '◀' : '▶'}
        </div>
        {/* 右半 L4+L3 */}
        <div style={{ width: rightCollapsed ? 0 : HALF_W, overflow: 'hidden', transition: 'width .3s ease', display: 'flex', flexShrink: 0 }}>
          <ColWrap title="L4 业务活动" color={COLORS.L4}>
            {l4List.length ? l4List.map((r: any) => renderConcept(r, 'L4', selL4 === r.id, () => setSelL4(r.id))) : emptyHint('请选择 L3')}
          </ColWrap>
          <ColWrap title="L3 业务活动分组" color={COLORS.L3}>
            {l3List.length ? l3List.map((r: any) => renderConcept(r, 'L3', selL3 === r.id, () => setSelL3(r.id))) : emptyHint('无 L3')}
          </ColWrap>
        </div>
      </div>
    </div>
  );
};

export default QuadCanvas;
