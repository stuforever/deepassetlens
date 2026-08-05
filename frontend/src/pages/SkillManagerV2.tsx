import React, { useCallback, useEffect, useState } from 'react';
import {
  Button, Space, Modal, Form, Input, Select, Tag, message,
  Tooltip, Empty, Spin, Input as AntInput, Popconfirm,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, EditOutlined, SaveOutlined,
  CheckCircleOutlined, ClockCircleOutlined, CloseCircleOutlined,
  CodeOutlined, ApiOutlined, DatabaseOutlined, GlobalOutlined,
  ExperimentOutlined, FileTextOutlined, RobotOutlined,
  SearchOutlined, EyeOutlined, FolderOutlined,
} from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { skillV2Api, SkillDTO } from '../services/skillV2Api';
import { PageShell, StatusTag, type StatusPreset } from '../components/shell';
import { tokens } from '../theme/tokens';

const { TextArea } = AntInput;

// ── 静态映射 ──────────────────────────────────────────────
// 技能类型语义色（领域专属，无对应设计 token）
const SKILL_TYPE_COLORS = {
  claude: '#6366f1',
  natural: '#10b981',
  python: '#3b82f6',
  sql: '#f59e0b',
  http: '#8b5cf6',
  mixed: '#ec4899',
} as const;

const SKILL_TYPE_MAP: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  claude: { label: 'Claude技能', icon: <RobotOutlined />, color: SKILL_TYPE_COLORS.claude },
  natural: { label: '自然语言', icon: <ExperimentOutlined />, color: SKILL_TYPE_COLORS.natural },
  python: { label: 'Python', icon: <CodeOutlined />, color: SKILL_TYPE_COLORS.python },
  sql: { label: 'SQL', icon: <DatabaseOutlined />, color: SKILL_TYPE_COLORS.sql },
  http: { label: 'HTTP', icon: <GlobalOutlined />, color: SKILL_TYPE_COLORS.http },
  mixed: { label: '混合', icon: <ApiOutlined />, color: SKILL_TYPE_COLORS.mixed },
};

const STATUS_MAP: Record<string, { label: string; preset: StatusPreset; icon: React.ReactNode }> = {
  draft: { label: '草稿', preset: 'default', icon: <ClockCircleOutlined /> },
  published: { label: '已发布', preset: 'success', icon: <CheckCircleOutlined /> },
  disabled: { label: '已禁用', preset: 'error', icon: <CloseCircleOutlined /> },
};

// ── 组件 ──────────────────────────────────────────────────
const SkillManagerV2: React.FC = () => {
  const [skills, setSkills] = useState<SkillDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<SkillDTO | null>(null);

  // 搜索 & 筛选
  const [searchText, setSearchText] = useState('');
  const [filterTypes, setFilterTypes] = useState<string[]>([]);

  // SKILL.md 编辑
  const [mdContent, setMdContent] = useState('');
  const [mdLoading, setMdLoading] = useState(false);
  const [mdDirty, setMdDirty] = useState(false);

  // 文件树
  const [fileList, setFileList] = useState<any[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [fileContent, setFileContent] = useState('');
  const [fileDirty, setFileDirty] = useState(false);

  // 创建技能
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [createForm] = Form.useForm();

  // 重命名
  const [renameModalVisible, setRenameModalVisible] = useState(false);
  const [renameForm] = Form.useForm();

  // ── 加载技能列表 ──
  const loadSkills = useCallback(async () => {
    setLoading(true);
    try {
      const res = await skillV2Api.listSkills();
      const list = (res.data?.data || []).filter((s: SkillDTO) => s.skill_code !== 'query_entity_pipeline');
      setSkills(list);
      // 自动选中第一条技能，避免右侧大面积空白
      if (list.length > 0) {
        setSelectedSkill(prev => prev ?? list[0]);
      }
    } catch (e) {
      message.error('加载技能列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadSkills(); }, [loadSkills]);

  // ── 选中技能时加载 SKILL.md ──
  const handleSelectSkill = useCallback(async (skill: SkillDTO) => {
    setSelectedSkill(skill);
    setMdDirty(false);
    setMdLoading(true);
    setSelectedFile('');
    setFileContent('');
    setFileDirty(false);
    try {
      const res = await skillV2Api.readSkillFile(skill.skill_id, 'SKILL.md');
      setMdContent(res.data?.data?.content || '');
    } catch {
      setMdContent('');
    } finally {
      setMdLoading(false);
    }
    // 加载文件树
    try {
      const fres = await skillV2Api.listSkillFiles(skill.skill_id);
      setFileList(fres.data?.data || []);
    } catch {
      setFileList([]);
    }
  }, []);

  // ── 保存 SKILL.md ──
  const handleSaveMd = async () => {
    if (!selectedSkill) return;
    try {
      await skillV2Api.writeSkillFile(selectedSkill.skill_id, 'SKILL.md', mdContent);
      setMdDirty(false);
      message.success('SKILL.md 已保存');
    } catch {
      message.error('保存失败');
    }
  };

  // ── 保存其他文件 ──
  const handleSaveFile = async () => {
    if (!selectedSkill || !selectedFile) return;
    try {
      await skillV2Api.writeSkillFile(selectedSkill.skill_id, selectedFile, fileContent);
      setFileDirty(false);
      message.success(`${selectedFile} 已保存`);
    } catch {
      message.error('保存失败');
    }
  };

  // ── 读取文件 ──
  const handleReadFile = async (path: string) => {
    if (!selectedSkill) return;
    setSelectedFile(path);
    setFileDirty(false);
    try {
      const res = await skillV2Api.readSkillFile(selectedSkill.skill_id, path);
      setFileContent(res.data?.data?.content || '');
    } catch {
      setFileContent('');
    }
  };

  // ── 创建技能 ──
  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      const res = await skillV2Api.createSkill({ ...values, skill_type: values.skill_type || 'claude' });
      const sid = res.data?.data?.skill_id;
      message.success('技能创建成功');
      setCreateModalVisible(false);
      createForm.resetFields();
      await loadSkills();
      // 自动选中新技能
      if (sid) {
        const newSkill = (await skillV2Api.getSkill(sid)).data?.data;
        if (newSkill) handleSelectSkill(newSkill);
      }
    } catch (e: any) {
      if (e?.errorFields) return; // 表单校验失败
      message.error('创建失败');
    }
  };

  // ── 删除技能 ──
  const handleDelete = async (skill: SkillDTO) => {
    try {
      await skillV2Api.deleteSkill(skill.skill_id);
      message.success('技能已删除');
      if (selectedSkill?.skill_id === skill.skill_id) setSelectedSkill(null);
      await loadSkills();
    } catch {
      message.error('删除失败');
    }
  };

  // ── 发布/取消发布 ──
  const handlePublish = async (skill: SkillDTO) => {
    try {
      await skillV2Api.publishSkill(skill.skill_id);
      message.success('技能已发布');
      await loadSkills();
      if (selectedSkill?.skill_id === skill.skill_id) {
        const updated = (await skillV2Api.getSkill(skill.skill_id)).data?.data;
        if (updated) setSelectedSkill(updated);
      }
    } catch {
      message.error('发布失败');
    }
  };

  const handleUnpublish = async (skill: SkillDTO) => {
    try {
      await skillV2Api.unpublishSkill(skill.skill_id);
      message.success('已取消发布');
      await loadSkills();
      if (selectedSkill?.skill_id === skill.skill_id) {
        const updated = (await skillV2Api.getSkill(skill.skill_id)).data?.data;
        if (updated) setSelectedSkill(updated);
      }
    } catch {
      message.error('取消发布失败');
    }
  };

  // ── 重命名 ──
  const handleRename = async () => {
    try {
      const values = await renameForm.validateFields();
      if (!selectedSkill) return;
      await skillV2Api.updateSkill(selectedSkill.skill_id, { name: values.name });
      message.success('重命名成功');
      setRenameModalVisible(false);
      await loadSkills();
      const updated = (await skillV2Api.getSkill(selectedSkill.skill_id)).data?.data;
      if (updated) setSelectedSkill(updated);
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error('重命名失败');
    }
  };

  // ── 筛选后的技能列表 ──
  const filteredSkills = skills.filter(s => {
    const matchSearch = !searchText ||
      s.name.toLowerCase().includes(searchText.toLowerCase()) ||
      s.skill_code.toLowerCase().includes(searchText.toLowerCase()) ||
      (s.description || '').toLowerCase().includes(searchText.toLowerCase());
    const matchType = filterTypes.length === 0 || filterTypes.includes(s.skill_type);
    return matchSearch && matchType;
  });

  // ── 文件图标 ──
  const getFileIcon = (path: string) => {
    if (path.endsWith('.md')) return <FileTextOutlined style={{ color: SKILL_TYPE_COLORS.claude }} />;
    if (path.endsWith('.py')) return <CodeOutlined style={{ color: SKILL_TYPE_COLORS.python }} />;
    if (path.endsWith('.json')) return <ApiOutlined style={{ color: SKILL_TYPE_COLORS.sql }} />;
    if (path.endsWith('.txt')) return <FileTextOutlined style={{ color: SKILL_TYPE_COLORS.natural }} />;
    return <FileTextOutlined />;
  };

  // ── 渲染 ──────────────────────────────────────────────
  return (
    <PageShell
      title="技能管理"
      description={`${filteredSkills.length} 个技能`}
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>创建技能</Button>}
    >
      {/* 主体：左右分栏 */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* 左侧栏 */}
        <div style={{
          width: 300, borderRight: `1px solid ${tokens.colors.border}`, display: 'flex',
          flexDirection: 'column', flexShrink: 0, background: tokens.colors.bgSubtle,
        }}>
          {/* 搜索框 */}
          <div style={{ padding: '12px 12px 8px' }}>
            <AntInput
              prefix={<SearchOutlined style={{ color: tokens.colors.textTertiary }} />}
              placeholder="搜索技能名称、代码、描述..."
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              allowClear
              size="middle"
            />
          </div>

          {/* 类型筛选 */}
          <div style={{ padding: '0 12px 8px', display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {Object.entries(SKILL_TYPE_MAP).map(([k, v]) => (
              <Tag
                key={k}
                style={{
                  cursor: 'pointer', margin: 0, padding: '2px 8px',
                  background: filterTypes.includes(k) ? v.color : tokens.colors.bgContent,
                  color: filterTypes.includes(k) ? tokens.colors.textInverse : v.color,
                  borderColor: v.color, fontSize: 12,
                }}
                onClick={() => {
                  setFilterTypes(prev =>
                    prev.includes(k) ? prev.filter(t => t !== k) : [...prev, k]
                  );
                }}
              >
                {v.icon} {v.label}
              </Tag>
            ))}
          </div>

          {/* 技能列表 */}
          <div style={{ flex: 1, overflow: 'auto', padding: '0 8px 8px' }}>
            <Spin spinning={loading} size="small">
              {filteredSkills.length === 0 ? (
                <Empty description="无匹配技能" style={{ marginTop: 40 }} />
              ) : (
                filteredSkills.map(skill => {
                  const typeInfo = SKILL_TYPE_MAP[skill.skill_type] || SKILL_TYPE_MAP.claude;
                  const statusInfo = STATUS_MAP[skill.status] || STATUS_MAP.draft;
                  const isSelected = selectedSkill?.skill_id === skill.skill_id;
                  return (
                    <div
                      key={skill.skill_id}
                      onClick={() => handleSelectSkill(skill)}
                      style={{
                        padding: '10px 12px', marginBottom: 4, borderRadius: 8, cursor: 'pointer',
                        background: isSelected ? tokens.colors.primaryBg : tokens.colors.bgContent,
                        border: isSelected ? `1px solid ${tokens.colors.primary}` : `1px solid ${tokens.colors.border}`,
                        transition: 'all 0.2s',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: tokens.colors.textPrimary, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {typeInfo.icon} {skill.name}
                        </span>
                        <StatusTag preset={statusInfo.preset} style={{ margin: 0, fontSize: 11 }}>{statusInfo.label}</StatusTag>
                      </div>
                      <div style={{ fontSize: 11, color: tokens.colors.textTertiary, marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {skill.skill_code}
                      </div>
                      {skill.description && (
                        <div style={{ fontSize: 11, color: tokens.colors.textTertiary, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {skill.description.slice(0, 50)}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </Spin>
          </div>
        </div>

        {/* 右侧编辑区 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {!selectedSkill ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Empty
                description="选择左侧技能或创建新技能"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            </div>
          ) : (
            <>
              {/* 右侧顶栏：技能信息 + 操作 */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '10px 20px', borderBottom: `1px solid ${tokens.colors.border}`, flexShrink: 0,
              }}>
                <Space size={12}>
                  <span style={{ fontSize: 15, fontWeight: 600 }}>{selectedSkill.name}</span>
                  <Tag color={SKILL_TYPE_MAP[selectedSkill.skill_type]?.color}>
                    {SKILL_TYPE_MAP[selectedSkill.skill_type]?.icon} {SKILL_TYPE_MAP[selectedSkill.skill_type]?.label}
                  </Tag>
                  <StatusTag preset={STATUS_MAP[selectedSkill.status]?.preset} icon={STATUS_MAP[selectedSkill.status]?.icon}>
                    {STATUS_MAP[selectedSkill.status]?.label}
                  </StatusTag>
                  <span style={{ fontSize: 12, color: tokens.colors.textTertiary }}>{selectedSkill.skill_code}</span>
                </Space>
                <Space>
                  <Button
                    icon={<SaveOutlined />}
                    type={mdDirty ? 'primary' : 'default'}
                    onClick={handleSaveMd}
                    disabled={!mdDirty}
                  >
                    保存
                  </Button>
                  <Button icon={<EditOutlined />} onClick={() => { renameForm.setFieldsValue({ name: selectedSkill.name }); setRenameModalVisible(true); }}>
                    重命名
                  </Button>
                  {selectedSkill.status === 'published' ? (
                    <Popconfirm title="确定取消发布？" onConfirm={() => handleUnpublish(selectedSkill)}>
                      <Button>取消发布</Button>
                    </Popconfirm>
                  ) : (
                    <Popconfirm title="确定发布？" onConfirm={() => handlePublish(selectedSkill)}>
                      <Button type="primary" ghost>发布</Button>
                    </Popconfirm>
                  )}
                  <Popconfirm title="确定删除此技能？" onConfirm={() => handleDelete(selectedSkill)}>
                    <Button danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              </div>

              {/* 编辑器 + 预览 */}
              <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                {/* SKILL.md 编辑器 */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: `1px solid ${tokens.colors.border}`, minHeight: 0 }}>
                  <div style={{ padding: '6px 12px', background: tokens.colors.bgSubtle, borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12, color: tokens.colors.textTertiary, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
                    <span><FileTextOutlined /> SKILL.md 编辑器</span>
                    {mdDirty && <StatusTag preset="warning" style={{ fontSize: 11 }}>未保存</StatusTag>}
                  </div>
                    <Editor
                      height="100%"
                      language="markdown"
                      theme="vs"
                      loading={<Spin />}
                      value={mdContent}
                      onChange={(val) => { setMdContent(val || ''); setMdDirty(true); }}
                      options={{
                        minimap: { enabled: false },
                        fontSize: 13,
                        wordWrap: 'on',
                        lineNumbers: 'on',
                        scrollBeyondLastLine: false,
                        padding: { top: 12 },
                      }}
                    />
                </div>

                {/* Markdown 预览 */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <div style={{ padding: '6px 12px', background: tokens.colors.bgSubtle, borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12, color: tokens.colors.textTertiary }}>
                    <EyeOutlined /> 预览
                  </div>
                  <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px' }}>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h1: ({ children }) => <h1 style={{ fontSize: 20, fontWeight: 700, margin: '16px 0 8px', color: tokens.colors.textPrimary }}>{children}</h1>,
                        h2: ({ children }) => <h2 style={{ fontSize: 16, fontWeight: 600, margin: '14px 0 6px', color: tokens.colors.textSecondary, borderBottom: `1px solid ${tokens.colors.border}`, paddingBottom: 4 }}>{children}</h2>,
                        h3: ({ children }) => <h3 style={{ fontSize: 14, fontWeight: 600, margin: '12px 0 4px', color: tokens.colors.textSecondary }}>{children}</h3>,
                        p: ({ children }) => <p style={{ fontSize: 13, lineHeight: 1.7, color: tokens.colors.textSecondary, margin: '6px 0' }}>{children}</p>,
                        li: ({ children }) => <li style={{ fontSize: 13, lineHeight: 1.7, color: tokens.colors.textSecondary, marginLeft: 8 }}>{children}</li>,
                        code: ({ children, className }) => {
                          const isBlock = className?.includes('language-');
                          if (isBlock) {
                            // 代码块深色主题（VS Code dark 风格，无对应设计 token）
                            return <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: 12, borderRadius: 6, fontSize: 12, overflow: 'auto', margin: '8px 0' }}><code>{children}</code></pre>;
                          }
                          return <code style={{ background: tokens.colors.bgSubtle, color: tokens.colors.primary, padding: '2px 6px', borderRadius: 4, fontSize: 12 }}>{children}</code>;
                        },
                        table: ({ children }) => <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, margin: '8px 0' }}>{children}</table>,
                        th: ({ children }) => <th style={{ border: `1px solid ${tokens.colors.border}`, padding: '6px 10px', background: tokens.colors.bgSubtle, fontWeight: 600, textAlign: 'left' }}>{children}</th>,
                        td: ({ children }) => <td style={{ border: `1px solid ${tokens.colors.border}`, padding: '6px 10px' }}>{children}</td>,
                        strong: ({ children }) => <strong style={{ color: tokens.colors.textPrimary, fontWeight: 600 }}>{children}</strong>,
                        hr: () => <hr style={{ border: 'none', borderTop: `1px solid ${tokens.colors.border}`, margin: '12px 0' }} />,
                      }}
                    >
                      {mdContent}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>

              {/* 底部文件树（可折叠的其他文件） */}
              {fileList.filter(f => !f.is_dir && f.path !== 'SKILL.md').length > 0 && (
                <div style={{
                  borderTop: `1px solid ${tokens.colors.border}`, padding: '8px 20px', background: tokens.colors.bgSubtle,
                  maxHeight: 200, overflow: 'auto', flexShrink: 0,
                }}>
                  <div style={{ fontSize: 12, color: tokens.colors.textTertiary, marginBottom: 6 }}>
                    <FolderOutlined /> 其他文件
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {fileList.filter(f => !f.is_dir && f.path !== 'SKILL.md').map(f => (
                      <Tag
                        key={f.path}
                        style={{ cursor: 'pointer', fontSize: 12 }}
                        color={selectedFile === f.path ? 'blue' : 'default'}
                        onClick={() => handleReadFile(f.path)}
                      >
                        {getFileIcon(f.path)} {f.path}
                      </Tag>
                    ))}
                  </div>
                  {selectedFile && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontSize: 12, color: tokens.colors.textTertiary }}>编辑: {selectedFile}</span>
                        <Button size="small" icon={<SaveOutlined />} onClick={handleSaveFile} disabled={!fileDirty}>
                          保存
                        </Button>
                      </div>
                      <Editor
                        height="120px"
                        language={selectedFile.endsWith('.py') ? 'python' : selectedFile.endsWith('.json') ? 'json' : 'plaintext'}
                        theme="vs"
                        value={fileContent}
                        onChange={(val) => { setFileContent(val || ''); setFileDirty(true); }}
                        options={{ minimap: { enabled: false }, fontSize: 12, wordWrap: 'on' }}
                      />
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* 创建技能弹窗 */}
      <Modal
        title="创建技能"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        onOk={() => createForm.submit()}
        width={480}
      >
        <Form form={createForm} onFinish={handleCreate} layout="vertical" initialValues={{ skill_type: 'claude' }}>
          <Form.Item name="name" label="技能名称" rules={[{ required: true, message: '请输入技能名称' }]}>
            <Input placeholder="如: 数据查询" />
          </Form.Item>
          <Form.Item name="skill_type" label="技能类型" rules={[{ required: true }]}>
            <Select>
              {Object.entries(SKILL_TYPE_MAP).map(([k, v]) => (
                <Select.Option key={k} value={k}>{v.icon} {v.label}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="技能功能描述（会写入 SKILL.md frontmatter 的 description 字段）" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 重命名弹窗 */}
      <Modal
        title="重命名技能"
        open={renameModalVisible}
        onCancel={() => setRenameModalVisible(false)}
        onOk={() => renameForm.submit()}
        width={400}
      >
        <Form form={renameForm} onFinish={handleRename} layout="vertical">
          <Form.Item name="name" label="技能名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </PageShell>
  );
};

export default SkillManagerV2;
