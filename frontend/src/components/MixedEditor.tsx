import React, { useState, useEffect } from 'react';
import { 
  Input, Button, Select, Space, Card, Tooltip, Typography, 
  Table, Tag, Modal, message, Row, Col, Divider, Form,
  InputNumber, Switch, Popconfirm
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, CopyOutlined, CodeOutlined,
  SaveOutlined, DownloadOutlined, UploadOutlined, PythonOutlined,
  CheckCircleOutlined, CloseCircleOutlined, SettingOutlined,
  EyeOutlined, EyeInvisibleOutlined, LinkOutlined
} from '@ant-design/icons';
import { StatusTag } from './shell';

const { TextArea } = Input;
const { Option } = Select;
const { Text, Title } = Typography;

interface Dependency {
  id: string;
  name: string;
  version: string;
  type: 'pip' | 'npm' | 'system' | 'custom';
  description?: string;
  enabled: boolean;
}

interface MixedEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  height?: number;
  language?: string;
}

const MixedEditor: React.FC<MixedEditorProps> = ({
  value = '',
  onChange,
  placeholder = '输入代码并管理依赖...',
  height = 500,
  language = 'python'
}) => {
  // 解析初始值
  const parseInitialValue = (val: string) => {
    try {
      if (val && val.trim()) {
        const parsed = JSON.parse(val);
        return {
          code: parsed.code || '',
          dependencies: parsed.dependencies || [],
          config: parsed.config || {}
        };
      }
    } catch (e) {
      // 如果不是JSON，可能是纯代码
    }
    return {
      code: value,
      dependencies: [
        { id: '1', name: 'requests', version: 'latest', type: 'pip', description: 'HTTP库', enabled: true },
        { id: '2', name: 'pandas', version: '>=1.0.0', type: 'pip', description: '数据分析', enabled: true }
      ],
      config: {
        timeout: 30,
        memory_limit: '512MB',
        retry_count: 3,
        environment: 'python3.8'
      }
    };
  };

  const [data, setData] = useState<any>(parseInitialValue(value));
  const [activeTab, setActiveTab] = useState('code');
  const [newDependency, setNewDependency] = useState({ name: '', version: 'latest', type: 'pip' as const });
  const [isInstalling, setIsInstalling] = useState(false);
  const [dependencySearch, setDependencySearch] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // 当数据变化时通知父组件
  useEffect(() => {
    if (onChange) {
      onChange(JSON.stringify(data, null, 2));
    }
  }, [data, onChange]);

  const handleCodeChange = (code: string) => {
    setData((prev: any) => ({ ...prev, code }));
  };

  const handleConfigChange = (key: string, value: any) => {
    setData((prev: any) => ({
      ...prev,
      config: { ...prev.config, [key]: value }
    }));
  };

  const handleAddDependency = () => {
    if (!newDependency.name.trim()) {
      message.error('请输入依赖包名称');
      return;
    }

    const newDep: Dependency = {
      id: Date.now().toString(),
      name: newDependency.name.trim(),
      version: newDependency.version.trim() || 'latest',
      type: newDependency.type,
      enabled: true
    };

    setData((prev: any) => ({
      ...prev,
      dependencies: [...prev.dependencies, newDep]
    }));

    setNewDependency({ name: '', version: 'latest', type: 'pip' });
    message.success('依赖已添加');
  };

  const handleRemoveDependency = (id: string) => {
    setData((prev: any) => ({
      ...prev,
      dependencies: prev.dependencies.filter((dep: Dependency) => dep.id !== id)
    }));
    message.success('依赖已移除');
  };

  const handleToggleDependency = (id: string, enabled: boolean) => {
    setData((prev: any) => ({
      ...prev,
      dependencies: prev.dependencies.map((dep: Dependency) =>
        dep.id === id ? { ...dep, enabled } : dep
      )
    }));
  };

  const handleInstallDependencies = async () => {
    setIsInstalling(true);
    try {
      // 模拟安装过程
      const enabledDeps = data.dependencies.filter((dep: Dependency) => dep.enabled);
      
      for (const dep of enabledDeps) {
        // 模拟安装每个依赖
        await new Promise(resolve => setTimeout(resolve, 500));
        console.log(`Installing ${dep.name}${dep.version !== 'latest' ? `==${dep.version}` : ''}`);
      }
      
      message.success(`成功安装 ${enabledDeps.length} 个依赖包`);
    } catch (error: any) {
      message.error('安装失败: ' + error.message);
    } finally {
      setIsInstalling(false);
    }
  };

  const handleGenerateRequirements = () => {
    const enabledDeps = data.dependencies.filter((dep: Dependency) => dep.enabled);
    const requirements = enabledDeps
      .map((dep: Dependency) => `${dep.name}${dep.version !== 'latest' ? `==${dep.version}` : ''}`)
      .join('\n');
    
    navigator.clipboard.writeText(requirements);
    message.success('requirements.txt 已复制到剪贴板');
  };

  const handleImportRequirements = () => {
    Modal.confirm({
      title: '导入 requirements.txt',
      content: (
        <div>
          <TextArea
            placeholder="粘贴 requirements.txt 内容，每行一个依赖包"
            rows={6}
            onChange={(e) => {
              const content = e.target.value;
              const lines = content.split('\n').filter(line => line.trim());
              const deps: Dependency[] = lines.map((line, index) => {
                const [name, version] = line.split(/[=<>!]/).map(s => s.trim());
                return {
                  id: `imported-${index}`,
                  name: name || line.trim(),
                  version: version || 'latest',
                  type: 'pip',
                  enabled: true
                };
              });
              
              if (deps.length > 0) {
                setData((prev: any) => ({
                  ...prev,
                  dependencies: [...prev.dependencies, ...deps]
                }));
              }
            }}
          />
        </div>
      ),
      onOk: () => {
        message.success('依赖已导入');
      }
    });
  };

  const handleSaveTemplate = () => {
    const templateName = prompt('请输入模板名称:');
    if (templateName) {
      const templates = JSON.parse(localStorage.getItem('mixed_editor_templates') || '[]');
      templates.push({
        name: templateName,
        data,
        timestamp: new Date().toISOString()
      });
      localStorage.setItem('mixed_editor_templates', JSON.stringify(templates));
      message.success('模板保存成功');
    }
  };

  const filteredDependencies = data.dependencies.filter((dep: Dependency) =>
    dep.name.toLowerCase().includes(dependencySearch.toLowerCase()) ||
    dep.description?.toLowerCase().includes(dependencySearch.toLowerCase())
  );

  const getDependencyTypePreset = (type: string): 'info' | 'success' | 'warning' | 'ai' | 'default' => {
    const presets: Record<string, 'info' | 'success' | 'warning' | 'ai' | 'default'> = {
      'pip': 'info',
      'npm': 'success',
      'system': 'warning',
      'custom': 'ai'
    };
    return presets[type] || 'default';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height, gap: 16 }}>
      {/* 顶部工具栏 */}
      <Card size="small">
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space>
              <PythonOutlined />
              <Text strong>混合编辑器 (代码 + 依赖管理)</Text>
              <StatusTag preset="warning">Beta</StatusTag>
            </Space>
          </Col>
          <Col>
            <Space>
              <Tooltip title="保存模板">
                <Button size="small" icon={<SaveOutlined />} onClick={handleSaveTemplate}>
                  保存模板
                </Button>
              </Tooltip>
              <Tooltip title="生成 requirements.txt">
                <Button size="small" icon={<DownloadOutlined />} onClick={handleGenerateRequirements}>
                  生成依赖文件
                </Button>
              </Tooltip>
              <Tooltip title="导入依赖">
                <Button size="small" icon={<UploadOutlined />} onClick={handleImportRequirements}>
                  导入依赖
                </Button>
              </Tooltip>
            </Space>
          </Col>
        </Row>
      </Card>

      <Row gutter={16} style={{ flex: 1, minHeight: 0 }}>
        {/* 左侧：代码编辑器 */}
        <Col span={16}>
          <Card 
            title="代码编辑器" 
            size="small"
            style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
            bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0 }}
          >
            <TextArea
              value={data.code}
              onChange={(e) => handleCodeChange(e.target.value)}
              placeholder={placeholder}
              style={{
                flex: 1,
                fontFamily: 'monospace',
                fontSize: '13px',
                lineHeight: 1.5,
                border: 'none',
                resize: 'none',
                padding: '12px'
              }}
              spellCheck={false}
            />
            <div style={{ 
              padding: '8px 12px', 
              borderTop: '1px solid var(--color-border)',
              backgroundColor: 'var(--bg-subtle)',
              fontSize: '12px',
              color: 'var(--text-secondary)'
            }}>
              <Space>
                <Text type="secondary">语言: {language}</Text>
                <Divider type="vertical" />
                <Text type="secondary">行数: {data.code.split('\n').length}</Text>
                <Divider type="vertical" />
                <Text type="secondary">字符: {data.code.length}</Text>
              </Space>
            </div>
          </Card>
        </Col>

        {/* 右侧：依赖管理 */}
        <Col span={8}>
          <Card 
            title={
              <Space>
                <SettingOutlined />
                <span>依赖包管理</span>
                <Button 
                  size="small" 
                  type="primary" 
                  loading={isInstalling}
                  onClick={handleInstallDependencies}
                >
                  安装依赖
                </Button>
              </Space>
            }
            size="small"
            style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
            bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0 }}
          >
            {/* 依赖搜索和添加 */}
            <div style={{ padding: '12px', borderBottom: '1px solid var(--color-border)' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Input
                  placeholder="搜索依赖包..."
                  value={dependencySearch}
                  onChange={(e) => setDependencySearch(e.target.value)}
                  allowClear
                />
                <Space.Compact style={{ width: '100%' }}>
                  <Input
                    placeholder="包名，如: numpy"
                    value={newDependency.name}
                    onChange={(e) => setNewDependency(prev => ({ ...prev, name: e.target.value }))}
                  />
                  <Input
                    placeholder="版本"
                    value={newDependency.version}
                    onChange={(e) => setNewDependency(prev => ({ ...prev, version: e.target.value }))}
                    style={{ width: '100px' }}
                  />
                  <Select
                    value={newDependency.type}
                    onChange={(value) => setNewDependency(prev => ({ ...prev, type: value }))}
                    style={{ width: '90px' }}
                  >
                    <Option value="pip">pip</Option>
                    <Option value="npm">npm</Option>
                    <Option value="system">系统</Option>
                    <Option value="custom">自定义</Option>
                  </Select>
                  <Button type="primary" icon={<PlusOutlined />} onClick={handleAddDependency}>
                    添加
                  </Button>
                </Space.Compact>
              </Space>
            </div>

            {/* 依赖列表 */}
            <div style={{ flex: 1, overflow: 'auto', padding: '8px' }}>
              {filteredDependencies.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-tertiary)' }}>
                  <Text type="secondary">暂无依赖包</Text>
                </div>
              ) : (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {filteredDependencies.map((dep: Dependency) => (
                    <Card 
                      key={dep.id} 
                      size="small"
                      style={{ 
                        backgroundColor: dep.enabled ? 'var(--bg-content)' : 'var(--bg-subtle)',
                        borderColor: dep.enabled ? 'var(--border-color)' : 'var(--color-border)'
                      }}
                    >
                      <Row gutter={8} align="middle">
                        <Col flex="auto">
                          <Space direction="vertical" size={2} style={{ width: '100%' }}>
                            <Space>
                              <Text strong>{dep.name}</Text>
                              <StatusTag preset={getDependencyTypePreset(dep.type)} style={{ fontSize: '12px' }}>
                                {dep.type}
                              </StatusTag>
                              <Tag style={{ fontSize: '12px' }}>{dep.version}</Tag>
                            </Space>
                            {dep.description && (
                              <Text type="secondary" style={{ fontSize: '12px' }}>
                                {dep.description}
                              </Text>
                            )}
                          </Space>
                        </Col>
                        <Col>
                          <Space>
                            <Switch
                              size="small"
                              checked={dep.enabled}
                              onChange={(checked) => handleToggleDependency(dep.id, checked)}
                            />
                            <Popconfirm
                              title="确定要删除这个依赖吗？"
                              onConfirm={() => handleRemoveDependency(dep.id)}
                            >
                              <Button
                                type="text"
                                danger
                                size="small"
                                icon={<DeleteOutlined />}
                              />
                            </Popconfirm>
                          </Space>
                        </Col>
                      </Row>
                    </Card>
                  ))}
                </Space>
              )}
            </div>

            {/* 统计信息 */}
            <div style={{ 
              padding: '8px 12px', 
              borderTop: '1px solid var(--color-border)',
              backgroundColor: 'var(--bg-subtle)',
              fontSize: '12px'
            }}>
              <Row justify="space-between">
                <Col>
                  <Text type="secondary">
                    总计: {data.dependencies.length} 个依赖
                  </Text>
                </Col>
                <Col>
                  <Text type="secondary">
                    启用: {data.dependencies.filter((d: Dependency) => d.enabled).length} 个
                  </Text>
                </Col>
              </Row>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 高级配置 */}
      <Card 
        title={
          <Space>
            <SettingOutlined />
            <span>运行环境配置</span>
            <Button 
              type="link" 
              size="small"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              {showAdvanced ? '隐藏高级配置' : '显示高级配置'}
            </Button>
          </Space>
        }
        size="small"
      >
        {showAdvanced && (
          <Row gutter={16}>
            <Col span={8}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text strong style={{ fontSize: '12px', display: 'block', marginBottom: 4 }}>
                    超时时间 (秒)
                  </Text>
                  <InputNumber
                    value={data.config.timeout}
                    onChange={(value) => handleConfigChange('timeout', value)}
                    min={1}
                    max={300}
                    style={{ width: '100%' }}
                  />
                </div>
                <div>
                  <Text strong style={{ fontSize: '12px', display: 'block', marginBottom: 4 }}>
                    内存限制
                  </Text>
                  <Select
                    value={data.config.memory_limit}
                    onChange={(value) => handleConfigChange('memory_limit', value)}
                    style={{ width: '100%' }}
                  >
                    <Option value="256MB">256MB</Option>
                    <Option value="512MB">512MB</Option>
                    <Option value="1GB">1GB</Option>
                    <Option value="2GB">2GB</Option>
                    <Option value="4GB">4GB</Option>
                  </Select>
                </div>
              </Space>
            </Col>
            <Col span={8}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text strong style={{ fontSize: '12px', display: 'block', marginBottom: 4 }}>
                    重试次数
                  </Text>
                  <InputNumber
                    value={data.config.retry_count}
                    onChange={(value) => handleConfigChange('retry_count', value)}
                    min={0}
                    max={10}
                    style={{ width: '100%' }}
                  />
                </div>
                <div>
                  <Text strong style={{ fontSize: '12px', display: 'block', marginBottom: 4 }}>
                    运行环境
                  </Text>
                  <Select
                    value={data.config.environment}
                    onChange={(value) => handleConfigChange('environment', value)}
                    style={{ width: '100%' }}
                  >
                    <Option value="python3.8">Python 3.8</Option>
                    <Option value="python3.9">Python 3.9</Option>
                    <Option value="python3.10">Python 3.10</Option>
                    <Option value="node16">Node.js 16</Option>
                    <Option value="node18">Node.js 18</Option>
                  </Select>
                </div>
              </Space>
            </Col>
            <Col span={8}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text strong style={{ fontSize: '12px', display: 'block', marginBottom: 4 }}>
                    输出格式
                  </Text>
                  <Select
                    defaultValue="json"
                    style={{ width: '100%' }}
                  >
                    <Option value="json">JSON</Option>
                    <Option value="text">文本</Option>
                    <Option value="html">HTML</Option>
                    <Option value="xml">XML</Option>
                  </Select>
                </div>
                <div>
                  <Text strong style={{ fontSize: '12px', display: 'block', marginBottom: 4 }}>
                    日志级别
                  </Text>
                  <Select
                    defaultValue="info"
                    style={{ width: '100%' }}
                  >
                    <Option value="debug">Debug</Option>
                    <Option value="info">Info</Option>
                    <Option value="warning">Warning</Option>
                    <Option value="error">Error</Option>
                  </Select>
                </div>
              </Space>
            </Col>
          </Row>
        )}
        
        {!showAdvanced && (
          <Row gutter={16}>
            <Col span={24}>
              <Space>
                <Tag>超时: {data.config.timeout}秒</Tag>
                <Tag>内存: {data.config.memory_limit}</Tag>
                <Tag>重试: {data.config.retry_count}次</Tag>
                <Tag>环境: {data.config.environment}</Tag>
              </Space>
            </Col>
          </Row>
        )}
      </Card>
    </div>
  );
};

export default MixedEditor;