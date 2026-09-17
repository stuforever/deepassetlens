/**
 * 章节管理（1:1 复刻自原仓 web/app/(utility)/settings/curriculum/chapters/page.tsx）：
 * 章节体系权威源——按教材列章节（页码/知识点关联数）、LLM 自动建章节、
 * 手动新增（父章/顺序/起止页）、删除、知识点树多选关联（KpTreePicker 弹层）。
 * notify → antd message；confirm → window.confirm；apiUrl → 相对路径 fetch。
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Button, Col, Input, InputNumber, Row, Select, message } from 'antd';
import {
  ApartmentOutlined, DeleteOutlined, FileUnknownOutlined,
  LinkOutlined, PlusOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import { SettingsPageHeader } from '../../components/settings/shared';
import { KpTreePicker } from '../tutor/admin/KpTreePicker';

interface Textbook {
  id: string;
  name: string;
}
interface Chapter {
  id: string;
  name: string;
  order: number;
  kp_ids: string[];
  page_start: number | null;
  page_end: number | null;
}

const cardStyle: React.CSSProperties = {
  border: '1px solid #f0f0f0',
  borderRadius: 8,
  background: '#fff',
};
const cardHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '12px 16px',
  borderBottom: '1px solid #f0f0f0',
};

export default function ChaptersPage() {
  const [textbooks, setTextbooks] = useState<Textbook[]>([]);
  const [tbId, setTbId] = useState('');
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [name, setName] = useState('');
  const [parentId, setParentId] = useState('');
  const [order, setOrder] = useState(0);
  const [pageStart, setPageStart] = useState<number | null>(null);
  const [pageEnd, setPageEnd] = useState<number | null>(null);
  const [pickerFor, setPickerFor] = useState<{ chapter: Chapter; selected: string[] } | null>(null);
  const [kpTree, setKpTree] = useState<any[]>([]);

  const loadChapters = useCallback(async (tid: string) => {
    const d = await fetch(`/api/v1/curriculum/textbooks/${tid}/chapters`).then((r) => r.json());
    setChapters(d.items || []);
  }, []);

  useEffect(() => {
    fetch('/api/v1/curriculum/textbooks')
      .then((r) => r.json())
      .then((d) => setTextbooks(d.items || []))
      .catch(() => {});
  }, []);

  const openPicker = async (chapter: Chapter) => {
    const [tr] = await Promise.all([
      fetch('/api/v1/curriculum/knowledge-points/tree').then((r) => r.json()),
    ]);
    setKpTree(tr.tree || []);
    setPickerFor({ chapter, selected: [...(chapter.kp_ids || [])] });
  };

  const savePicker = async () => {
    if (!pickerFor) return;
    const { chapter, selected } = pickerFor;
    const r = await fetch(`/api/v1/curriculum/chapters/${chapter.id}/kps`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kp_ids: selected }),
    });
    if (r.ok) {
      message.success(`已关联 ${selected.length} 个知识点`);
      setPickerFor(null);
      await loadChapters(tbId);
    } else message.error('关联失败');
  };

  const add = async () => {
    if (!tbId || !name) {
      message.error('选教材+名称必填');
      return;
    }
    await fetch('/api/v1/curriculum/chapters', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        textbook_id: tbId,
        parent_id: parentId || null,
        name,
        order,
        page_start: pageStart != null ? Number(pageStart) : null,
        page_end: pageEnd != null ? Number(pageEnd) : null,
      }),
    });
    setName('');
    setParentId('');
    setPageStart(null);
    setPageEnd(null);
    message.success('已添加');
    await loadChapters(tbId);
  };

  const del = async (id: string) => {
    if (!window.confirm('删除此章节及子章节？')) return;
    await fetch(`/api/v1/curriculum/chapters/${id}`, { method: 'DELETE' });
    message.success('已删除');
    await loadChapters(tbId);
  };

  const autoBuildChapters = async () => {
    if (!tbId) {
      message.error('先选教材');
      return;
    }
    if (!window.confirm('用 LLM 自动为该教材构建章节？')) return;
    message.info('LLM 分析中...');
    const r = await fetch(`/api/v1/mother-questions/chapters/auto-build/${tbId}`, {
      method: 'POST',
    });
    if (r.ok) {
      const d = await r.json();
      message.success(`已创建 ${d.created || 0} 个章节`);
      await loadChapters(tbId);
    } else message.error('自动建章节失败');
  };

  const showTb = tbId ? textbooks.find((t) => t.id === tbId) : null;

  return (
    <div>
      <SettingsPageHeader
        title="章节管理"
        description="这里是章节体系的权威源——自主学习左侧的章节树直接来源于此。每个章节可设教材页码（支撑「原文」展示）并关联知识点。"
      />
      <Row gutter={20}>
        {/* 章节列表 */}
        <Col xs={24} lg={12}>
          <section style={cardStyle}>
            <div style={cardHeaderStyle}>
              <ApartmentOutlined style={{ color: '#fa8c16' }} />
              <Select
                style={{ flex: 1 }}
                value={tbId}
                onChange={(v) => {
                  setTbId(v);
                  void loadChapters(v);
                }}
                options={[
                  { value: '', label: '选择教材' },
                  ...textbooks.map((t) => ({ value: t.id, label: t.name })),
                ]}
              />
              {tbId && (
                <Button
                  onClick={autoBuildChapters}
                  icon={<ThunderboltOutlined />}
                  style={{ flexShrink: 0 }}
                >
                  自动建章节
                </Button>
              )}
            </div>
            <div style={{ padding: 12, maxHeight: '62vh', overflowY: 'auto' }}>
              {!tbId ? (
                <p style={{ color: 'rgba(0, 0, 0, 0.45)', margin: 0 }}>请先选教材</p>
              ) : chapters.length === 0 ? (
                <p style={{ color: 'rgba(0, 0, 0, 0.45)', margin: 0 }}>
                  {showTb?.name || ''} 暂无章节，可手动新增或用「自动建章节」。
                </p>
              ) : (
                <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                  {chapters.map((c) => (
                    <li
                      key={c.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: 8,
                        borderRadius: 6,
                        border: '1px solid #f0f0f0',
                        fontSize: 14,
                        marginBottom: 4,
                      }}
                    >
                      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {c.order}. {c.name}
                        {c.page_start != null && (
                          <span style={{ marginLeft: 8, fontSize: 10, color: 'rgba(0, 0, 0, 0.45)' }}>
                            P{c.page_start}
                            {c.page_end != null ? `-${c.page_end}` : ''}
                          </span>
                        )}
                        {(c.kp_ids || []).length > 0 && (
                          <span
                            style={{
                              marginLeft: 8,
                              fontSize: 10,
                              padding: '2px 6px',
                              borderRadius: 999,
                              background: 'rgba(22, 119, 255, 0.1)',
                              color: '#1677ff',
                            }}
                          >
                            {(c.kp_ids || []).length} 知识点
                          </span>
                        )}
                      </span>
                      <Button
                        type="text"
                        size="small"
                        onClick={() => void openPicker(c)}
                        title="关联知识点"
                        icon={<LinkOutlined style={{ color: '#1677ff' }} />}
                      />
                      <Button
                        type="text"
                        size="small"
                        danger
                        onClick={() => void del(c.id)}
                        style={{ marginLeft: 4 }}
                        icon={<DeleteOutlined />}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </Col>

        {/* 新增章节 */}
        <Col xs={24} lg={12}>
          <section style={{ ...cardStyle, height: 'fit-content' }}>
            <div style={cardHeaderStyle}>
              <FileUnknownOutlined style={{ color: '#fa8c16' }} />
              <h2 style={{ margin: 0, fontWeight: 600, fontSize: 14 }}>新增章节</h2>
            </div>
            <div style={{ padding: 16 }}>
              {tbId ? (
                <>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="章节名称"
                  />
                  <div style={{ marginTop: 12 }}>
                    <Select
                      style={{ width: '100%' }}
                      value={parentId}
                      onChange={setParentId}
                      options={[
                        { value: '', label: '（顶级章）' },
                        ...chapters.map((c) => ({ value: c.id, label: c.name })),
                      ]}
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginTop: 12 }}>
                    <InputNumber
                      placeholder="顺序"
                      value={order}
                      onChange={(v) => setOrder(typeof v === 'number' ? v : 0)}
                      style={{ width: '100%' }}
                    />
                    <InputNumber
                      placeholder="起始页"
                      value={pageStart}
                      onChange={(v) => setPageStart(typeof v === 'number' ? v : null)}
                      style={{ width: '100%' }}
                    />
                    <InputNumber
                      placeholder="结束页"
                      value={pageEnd}
                      onChange={(v) => setPageEnd(typeof v === 'number' ? v : null)}
                      style={{ width: '100%' }}
                    />
                  </div>
                  <Button
                    type="primary"
                    onClick={() => void add()}
                    icon={<PlusOutlined />}
                    style={{ marginTop: 12 }}
                  >
                    添加
                  </Button>
                  <p style={{ fontSize: 11, color: 'rgba(0, 0, 0, 0.45)', marginTop: 12, marginBottom: 0 }}>
                    起始/结束页对应教材 PDF 拆页的页码（P1 起），用于自主学习「原文」按章展示。
                  </p>
                </>
              ) : (
                <p style={{ color: 'rgba(0, 0, 0, 0.45)', margin: 0 }}>先选教材</p>
              )}
            </div>
          </section>
        </Col>
      </Row>

      {pickerFor && (
        <KpTreePicker
          tree={kpTree}
          selected={pickerFor.selected}
          onChange={(ids) => setPickerFor({ ...pickerFor, selected: ids })}
          onClose={() => setPickerFor(null)}
          onSave={() => void savePicker()}
          title={`关联知识点 - ${pickerFor.chapter.name}`}
        />
      )}
    </div>
  );
}
