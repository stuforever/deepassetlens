/**
 * 知识点树多选器（1:1 复刻自原仓 web/components/curriculum/KpTreePicker.tsx，
 * 章节关联用：三态复选（全选/半选/未选）、行点击切换整棵子树、遮罩弹层
 * → antd Modal 承载，底部「已选 N 个知识点 / 保存关联」布局照原样）。
 */
import React from 'react';
import { Button, Modal } from 'antd';
import { CloseOutlined } from '@ant-design/icons';

/** 知识点树节点（来自 curriculum 知识点 API，字段以使用到的为准）。 */
interface KpTreeNode {
  id: string;
  name: string;
  difficulty?: number;
  grade?: string;
  children?: KpTreeNode[];
}

export function KpTreePicker({
  tree,
  selected,
  onChange,
  onClose,
  onSave,
  title,
}: {
  tree: KpTreeNode[];
  selected: string[];
  onChange: (ids: string[]) => void;
  onClose: () => void;
  onSave: () => void;
  title: string;
}) {
  // 计算节点是否被选/半选
  const collectIds = (node: KpTreeNode): string[] => {
    const ids = [node.id];
    (node.children || []).forEach((c) => ids.push(...collectIds(c)));
    return ids;
  };
  const toggleNode = (node: KpTreeNode, checked: boolean) => {
    const ids = collectIds(node);
    const set = new Set(selected);
    ids.forEach((id) => (checked ? set.add(id) : set.delete(id)));
    onChange(Array.from(set));
  };
  const state = (node: KpTreeNode): 'checked' | 'half' | 'none' => {
    const ids = collectIds(node);
    const count = ids.filter((id) => selected.includes(id)).length;
    if (count === 0) return 'none';
    if (count === ids.length) return 'checked';
    return 'half';
  };
  const render = (node: KpTreeNode, depth: number): React.ReactNode => {
    const st = state(node);
    const boxStyle: React.CSSProperties =
      st === 'checked'
        ? { background: '#1677ff', border: '1px solid #1677ff', color: '#fff' }
        : st === 'half'
          ? { background: 'rgba(22,119,255,0.4)', border: '1px solid #1677ff', color: '#fff' }
          : { border: '1px solid rgba(0,0,0,0.25)', color: 'transparent' };
    return (
      <div key={node.id}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '4px 0',
            borderRadius: 4,
            cursor: 'pointer',
            paddingLeft: depth * 18,
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(0,0,0,0.03)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          onClick={() => toggleNode(node, st !== 'checked')}
        >
          <span
            style={{
              display: 'inline-flex',
              width: 16,
              height: 16,
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 2,
              fontSize: 10,
              lineHeight: 1,
              flexShrink: 0,
              ...boxStyle,
            }}
          >
            {st === 'checked' ? '✓' : st === 'half' ? '–' : ''}
          </span>
          <span style={{ fontSize: 14 }}>{node.name}</span>
          {node.difficulty ? (
            <span style={{ fontSize: 10, color: '#f59e0b' }} title={`难度 ${node.difficulty}/5`}>
              {'★'.repeat(Math.min(5, node.difficulty))}
            </span>
          ) : null}
          {node.grade && (
            <span style={{ fontSize: 10, padding: '1px 4px', borderRadius: 2, background: '#f5f5f5', color: 'rgba(0,0,0,0.45)' }}>
              {node.grade}
            </span>
          )}
        </div>
        {node.children?.map((c) => render(c, depth + 1))}
      </div>
    );
  };
  return (
    <Modal
      open
      title={title}
      onCancel={onClose}
      width={512}
      closeIcon={<CloseOutlined />}
      footer={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }}>已选 {selected.length} 个知识点</span>
          <Button type="primary" onClick={onSave}>
            保存关联
          </Button>
        </div>
      }
      styles={{ body: { maxHeight: '60vh', overflowY: 'auto' } }}
    >
      <div style={{ padding: '4px 0' }}>
        {tree.length === 0 ? (
          <p style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>
            暂无知识点，请先在「知识点管理」建树或自动提取
          </p>
        ) : (
          tree.map((n) => render(n, 0))
        )}
      </div>
    </Modal>
  );
}

export default KpTreePicker;
