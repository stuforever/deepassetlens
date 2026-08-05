/**
 * GraphManager - 图谱画布统一外壳。
 * 顶部 44px CanvasToolbar（模式 Segmented：力导向/四区/矩阵）+ 聚焦实体 Tabs + 画布区。
 * 画布区按 canvasMode 切换 TreeCanvas/QuadCanvas/ForceCanvas/Neo4jForceCanvas/MatrixCanvas。
 * AppTabs 对画布页 padding:0，本组件自撑满。
 */
import React, { useEffect, useState } from 'react';
import { Tabs, Segmented, Popover, Button } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import TreeCanvas from '../components/TreeCanvas';
import ForceCanvas from '../components/ForceCanvas';
import Neo4jForceCanvas from '../components/Neo4jForceCanvas';
import MatrixCanvas from '../components/MatrixCanvas';
import QuadCanvas from '../components/QuadCanvas';
import { useStore } from '../store/useStore';
import { CanvasToolbar, StatusTag } from '../components/shell';
import { tokens } from '../theme/tokens';

type Props = {
  onOpenTarget?: (menuKey: string) => void;
};

const GraphManager: React.FC<Props> = () => {
  const { canvasMode, setCanvasMode } = useStore();

  type GraphTab = {
    key: string;
    label: string;
    focusEntity: { code: string; name?: string } | null;
  };

  const [tabs, setTabs] = useState<GraphTab[]>([
    { key: 'overview', label: '全景图谱', focusEntity: null },
  ]);
  const [activeTabKey, setActiveTabKey] = useState('overview');

  const addTab = (entityCode: string, entityName?: string) => {
    const key = `entity-${entityCode}`;
    setTabs((prev) => {
      const exists = prev.find((t) => t.key === key);
      if (exists) {
        setActiveTabKey(key);
        return prev;
      }
      const newTabs = [...prev, { key, label: entityName || entityCode, focusEntity: { code: entityCode, name: entityName } }];
      const limited = newTabs.length > 10 ? newTabs.slice(newTabs.length - 10) : newTabs;
      setActiveTabKey(key);
      return limited;
    });
  };

  const removeTab = (targetKey: string) => {
    setTabs((prev) => {
      const filtered = prev.filter((t) => t.key !== targetKey);
      if (filtered.length === 0) {
        setActiveTabKey('overview');
        return [{ key: 'overview', label: '全景图谱', focusEntity: null }];
      }
      if (activeTabKey === targetKey) {
        setActiveTabKey(filtered[filtered.length - 1].key);
      }
      return filtered;
    });
  };

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      if (detail.menu === 'graph' && detail.entityCode) {
        addTab(detail.entityCode, detail.entityName);
      }
    };
    window.addEventListener('navigate', handler);
    const raw = localStorage.getItem('graph_focus_entity');
    if (raw) {
      try {
        const obj = JSON.parse(raw);
        if (obj && obj.entityCode) {
          addTab(obj.entityCode, obj.entityName);
          localStorage.removeItem('graph_focus_entity');
        }
      } catch {}
    }
    return () => window.removeEventListener('navigate', handler);
  }, []);

  const activeTab = tabs.find((t) => t.key === activeTabKey) || tabs[0];
  const focusEntity = activeTab?.focusEntity || null;

  // Segmented 覆盖全部 5 种模式
  const segmentedValue = canvasMode;

  // 图例内容
  const legendContent = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12, maxWidth: 280 }}>
      <div style={{ fontWeight: 600, marginBottom: 2 }}>概念层级</div>
      {([
        ['L1 业务域', '#5B8FF9'],
        ['L2 主数据', '#5AD8A6'],
        ['L3 业务活动', tokens.colors.ai],
        ['L4 业务数据', '#F6BD16'],
      ] as const).map(([l, c]) => (
        <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 12, height: 12, borderRadius: 3, background: c, border: `1px solid ${tokens.colors.border}` }} />
          {l}
        </div>
      ))}
      <div style={{ fontWeight: 600, margin: '4px 0 2px' }}>实体类型</div>
      {([
        ['主数据实体', '#fa8c16', '#fff7e6'],
        ['业务活动实体', '#13c2c2', '#e6fffb'],
      ] as const).map(([l, c, bg]) => (
        <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 12, height: 12, borderRadius: 3, background: bg, border: `1px solid ${c}` }} />
          {l}
        </div>
      ))}
      <div style={{ fontWeight: 600, margin: '4px 0 2px' }}>关系类型</div>
      {([
        ['跨链', tokens.colors.ai],
        ['主-主', tokens.colors.primary],
        ['主-活动', tokens.colors.error],
        ['其他', tokens.colors.warning],
      ] as const).map(([l, c]) => (
        <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 16, height: 3, background: c }} />
          {l}
        </div>
      ))}
    </div>
  );

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: tokens.colors.bgContent }}>
      <CanvasToolbar
        left={
          <Segmented
            size="small"
            value={segmentedValue}
            options={[
              { label: '力导向', value: 'force' },
              { label: '树形', value: 'tree' },
              { label: '四区', value: 'quad' },
              { label: '矩阵', value: 'matrix' },
              { label: 'Neo4j', value: 'neo4j' },
            ]}
            onChange={(v) => setCanvasMode(v as typeof canvasMode)}
          />
        }
        right={
          <>
            <Popover trigger="click" placement="bottomRight" content={legendContent} title="图例">
              <Button size="small" type="text" icon={<InfoCircleOutlined />}>图例</Button>
            </Popover>
          </>
        }
      />
      <Tabs
        type="editable-card"
        hideAdd
        activeKey={activeTabKey}
        onChange={(k) => setActiveTabKey(k)}
        onEdit={(targetKey, action) => {
          if (action === 'remove' && targetKey !== 'overview') removeTab(targetKey as string);
        }}
        size="small"
        style={{ paddingLeft: tokens.space.s4, paddingRight: tokens.space.s4, flexShrink: 0 }}
        items={tabs.map((tab) => ({
          key: tab.key,
          label: tab.focusEntity ? (
            <span>
              <StatusTag preset="warning" style={{ marginRight: 4, fontSize: 10 }}>实体</StatusTag>
              {tab.label}
            </span>
          ) : (
            <span>{tab.label}</span>
          ),
          closable: tab.key !== 'overview',
        }))}
      />
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {focusEntity ? (
          <div
            style={{
              padding: `${tokens.space.s2}px ${tokens.space.s4}px`,
              background: tokens.colors.primaryBg,
              borderBottom: `1px solid ${tokens.colors.primary}40`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexShrink: 0,
            }}
          >
            <span>
              <StatusTag preset="info">聚焦实体</StatusTag>
              <span style={{ fontWeight: tokens.fontWeight.semibold, color: tokens.colors.primary }}>
                {focusEntity.name || focusEntity.code}
              </span>
              <span style={{ color: tokens.colors.textSecondary, marginLeft: tokens.space.s2, fontSize: tokens.fontSize.caption }}>
                ({focusEntity.code})
              </span>
            </span>
          </div>
        ) : null}
        <div style={{ flex: 1, minHeight: 0 }}>
          {canvasMode === 'tree' ? (
            <TreeCanvas focusEntity={focusEntity} />
          ) : canvasMode === 'quad' ? (
            <QuadCanvas />
          ) : canvasMode === 'force' ? (
            <ForceCanvas />
          ) : canvasMode === 'neo4j' ? (
            <Neo4jForceCanvas />
          ) : (
            <MatrixCanvas />
          )}
        </div>
      </div>
    </div>
  );
};

export default GraphManager;
