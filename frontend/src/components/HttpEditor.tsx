import React, { useState, useEffect } from 'react';
import {
  Input, Button, Select, Space, Card, Tooltip, Typography,
  Table, Form, InputNumber, Switch, Divider, Tabs,
  Modal, message, Row, Col
} from 'antd';
import { StatusTag } from './shell';
import { 
  GlobalOutlined, SendOutlined, PlusOutlined, DeleteOutlined, 
  CopyOutlined, SaveOutlined, HistoryOutlined, CodeOutlined,
  EyeOutlined, EyeInvisibleOutlined, ApiOutlined 
} from '@ant-design/icons';

const { TextArea } = Input;
const { Option } = Select;
const { Text, Title } = Typography;
const { TabPane } = Tabs;

interface HttpHeader {
  key: string;
  value: string;
  enabled: boolean;
}

interface HttpParam {
  key: string;
  value: string;
  enabled: boolean;
}

interface HttpEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  height?: number;
}

const HttpEditor: React.FC<HttpEditorProps> = ({
  value = '',
  onChange,
  placeholder = '配置HTTP请求...',
  height = 400
}) => {
  // 解析初始值
  const parseInitialValue = (val: string) => {
    try {
      if (val && val.trim()) {
        return JSON.parse(val);
      }
    } catch (e) {
      // 如果不是JSON，使用默认值
    }
    return {
      method: 'GET',
      url: '',
      headers: [
        { key: 'Content-Type', value: 'application/json', enabled: true },
        { key: 'Accept', value: 'application/json', enabled: true }
      ],
      params: [],
      body: '',
      auth: { type: 'none', username: '', password: '', token: '' }
    };
  };

  const [config, setConfig] = useState<any>(parseInitialValue(value));
  const [activeTab, setActiveTab] = useState('headers');
  const [response, setResponse] = useState<any>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [showPassword, setShowPassword] = useState(false);

  // 当配置变化时通知父组件
  useEffect(() => {
    if (onChange) {
      onChange(JSON.stringify(config, null, 2));
    }
  }, [config, onChange]);

  // 初始化历史记录
  useEffect(() => {
    const savedHistory = localStorage.getItem('http_editor_history');
    if (savedHistory) {
      try {
        setHistory(JSON.parse(savedHistory));
      } catch (e) {
        console.error('Failed to parse history', e);
      }
    }
  }, []);

  const handleConfigChange = (key: string, value: any) => {
    setConfig((prev: any) => ({
      ...prev,
      [key]: value
    }));
  };

  const handleHeaderChange = (index: number, field: string, value: any) => {
    const newHeaders = [...config.headers];
    newHeaders[index] = { ...newHeaders[index], [field]: value };
    handleConfigChange('headers', newHeaders);
  };

  const handleParamChange = (index: number, field: string, value: any) => {
    const newParams = [...config.params];
    newParams[index] = { ...newParams[index], [field]: value };
    handleConfigChange('params', newParams);
  };

  const addHeader = () => {
    const newHeaders = [...config.headers, { key: '', value: '', enabled: true }];
    handleConfigChange('headers', newHeaders);
  };

  const removeHeader = (index: number) => {
    const newHeaders = config.headers.filter((_: any, i: number) => i !== index);
    handleConfigChange('headers', newHeaders);
  };

  const addParam = () => {
    const newParams = [...config.params, { key: '', value: '', enabled: true }];
    handleConfigChange('params', newParams);
  };

  const removeParam = (index: number) => {
    const newParams = config.params.filter((_: any, i: number) => i !== index);
    handleConfigChange('params', newParams);
  };

  const handleTestRequest = async () => {
    if (!config.url) {
      message.error('请输入URL');
      return;
    }

    setIsTesting(true);
    try {
      // 构建请求URL（包含查询参数）
      let url = config.url;
      const enabledParams = config.params.filter((p: any) => p.enabled && p.key);
      if (enabledParams.length > 0) {
        const queryString = enabledParams
          .map((p: any) => `${encodeURIComponent(p.key)}=${encodeURIComponent(p.value)}`)
          .join('&');
        url += (url.includes('?') ? '&' : '?') + queryString;
      }

      // 构建请求头
      const headers: Record<string, string> = {};
      config.headers
        .filter((h: any) => h.enabled && h.key)
        .forEach((h: any) => {
          headers[h.key] = h.value;
        });

      // 构建请求体
      let body: any = null;
      if (config.method !== 'GET' && config.method !== 'HEAD') {
        const contentType = headers['Content-Type'] || '';
        if (contentType.includes('application/json') && config.body) {
          try {
            body = JSON.parse(config.body);
          } catch (e) {
            body = config.body;
          }
        } else {
          body = config.body;
        }
      }

      // 添加认证信息
      if (config.auth.type === 'basic' && config.auth.username && config.auth.password) {
        const token = btoa(`${config.auth.username}:${config.auth.password}`);
        headers['Authorization'] = `Basic ${token}`;
      } else if (config.auth.type === 'bearer' && config.auth.token) {
        headers['Authorization'] = `Bearer ${config.auth.token}`;
      }

      // 发送请求
      const response = await fetch(url, {
        method: config.method,
        headers,
        body: body ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined
      });

      const responseData = {
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries()),
        body: await response.text()
      };

      setResponse(responseData);

      // 保存到历史记录
      const historyItem = {
        id: Date.now(),
        method: config.method,
        url: config.url,
        timestamp: new Date().toISOString(),
        status: response.status
      };
      const newHistory = [historyItem, ...history.slice(0, 9)];
      setHistory(newHistory);
      localStorage.setItem('http_editor_history', JSON.stringify(newHistory));

      message.success('请求成功');
    } catch (error: any) {
      setResponse({
        status: 0,
        statusText: 'Error',
        body: error.message
      });
      message.error('请求失败: ' + error.message);
    } finally {
      setIsTesting(false);
    }
  };

  const handleLoadFromHistory = (item: any) => {
    Modal.confirm({
      title: '加载历史记录',
      content: `确定要加载 ${item.method} ${item.url} 吗？`,
      onOk: () => {
        // 这里应该从更完整的历史记录中加载完整配置
        handleConfigChange('method', item.method);
        handleConfigChange('url', item.url);
        message.success('已加载历史记录');
      }
    });
  };

  const handleCopyResponse = () => {
    if (response) {
      navigator.clipboard.writeText(JSON.stringify(response, null, 2));
      message.success('响应已复制到剪贴板');
    }
  };

  const handleSaveTemplate = () => {
    const templateName = prompt('请输入模板名称:');
    if (templateName) {
      const templates = JSON.parse(localStorage.getItem('http_templates') || '[]');
      templates.push({
        name: templateName,
        config,
        timestamp: new Date().toISOString()
      });
      localStorage.setItem('http_templates', JSON.stringify(templates));
      message.success('模板保存成功');
    }
  };

  const handleBodyTypeChange = (type: string) => {
    // 根据类型设置默认Content-Type
    const contentTypeMap: Record<string, string> = {
      'json': 'application/json',
      'form': 'application/x-www-form-urlencoded',
      'text': 'text/plain',
      'xml': 'application/xml'
    };

    if (contentTypeMap[type]) {
      const headers = [...config.headers];
      const contentTypeIndex = headers.findIndex((h: any) => 
        h.key.toLowerCase() === 'content-type'
      );
      
      if (contentTypeIndex >= 0) {
        headers[contentTypeIndex].value = contentTypeMap[type];
      } else {
        headers.push({ key: 'Content-Type', value: contentTypeMap[type], enabled: true });
      }
      handleConfigChange('headers', headers);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height, gap: 16 }}>
      {/* 请求配置区域 */}
      <Card 
        title={
          <Space>
            <ApiOutlined />
            <Text strong>HTTP 请求配置</Text>
          </Space>
        }
        size="small"
        extra={
          <Space>
            <Tooltip title="保存为模板">
              <Button size="small" icon={<SaveOutlined />} onClick={handleSaveTemplate}>
                保存模板
              </Button>
            </Tooltip>
            <Tooltip title="历史记录">
              <Button 
                size="small" 
                icon={<HistoryOutlined />}
                onClick={() => {
                  Modal.info({
                    title: '请求历史',
                    content: (
                      <div style={{ maxHeight: '300px', overflow: 'auto' }}>
                        {history.length === 0 ? (
                          <Text type="secondary">暂无历史记录</Text>
                        ) : (
                          history.map((item) => (
                            <Card 
                              key={item.id} 
                              size="small" 
                              style={{ marginBottom: 8, cursor: 'pointer' }}
                              onClick={() => handleLoadFromHistory(item)}
                            >
                              <Space>
                                <StatusTag preset={
                                  item.status >= 200 && item.status < 300 ? 'success' :
                                  item.status >= 400 ? 'error' : 'default'
                                }>
                                  {item.method}
                                </StatusTag>
                                <Text ellipsis style={{ flex: 1 }}>{item.url}</Text>
                                <Text type="secondary" style={{ fontSize: '12px' }}>
                                  {new Date(item.timestamp).toLocaleTimeString()}
                                </Text>
                              </Space>
                            </Card>
                          ))
                        )}
                      </div>
                    ),
                    width: 600
                  });
                }}
              >
                历史
              </Button>
            </Tooltip>
          </Space>
        }
      >
        {/* 请求行 */}
        <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
          <Select 
            value={config.method}
            onChange={(value) => handleConfigChange('method', value)}
            style={{ width: '120px' }}
          >
            <Option value="GET">GET</Option>
            <Option value="POST">POST</Option>
            <Option value="PUT">PUT</Option>
            <Option value="DELETE">DELETE</Option>
            <Option value="PATCH">PATCH</Option>
            <Option value="HEAD">HEAD</Option>
            <Option value="OPTIONS">OPTIONS</Option>
          </Select>
          <Input
            value={config.url}
            onChange={(e) => handleConfigChange('url', e.target.value)}
            placeholder="输入请求URL，例如: https://api.example.com/endpoint"
            addonBefore={<GlobalOutlined />}
          />
          <Button 
            type="primary" 
            icon={<SendOutlined />} 
            loading={isTesting}
            onClick={handleTestRequest}
          >
            发送
          </Button>
        </Space.Compact>

        {/* 标签页 */}
        <Tabs activeKey={activeTab} onChange={setActiveTab} size="small">
          <TabPane tab="请求头 (Headers)" key="headers">
            <Table
              size="small"
              dataSource={config.headers}
              pagination={false}
              scroll={{ y: 150 }}
              columns={[
                {
                  title: '启用',
                  dataIndex: 'enabled',
                  width: 60,
                  render: (enabled: boolean, record: any, index: number) => (
                    <Switch 
                      size="small" 
                      checked={enabled}
                      onChange={(checked) => handleHeaderChange(index, 'enabled', checked)}
                    />
                  )
                },
                {
                  title: '键',
                  dataIndex: 'key',
                  render: (key: string, record: any, index: number) => (
                    <Input
                      value={key}
                      onChange={(e) => handleHeaderChange(index, 'key', e.target.value)}
                      placeholder="Header名称"
                      size="small"
                    />
                  )
                },
                {
                  title: '值',
                  dataIndex: 'value',
                  render: (value: string, record: any, index: number) => (
                    <Input
                      value={value}
                      onChange={(e) => handleHeaderChange(index, 'value', e.target.value)}
                      placeholder="Header值"
                      size="small"
                    />
                  )
                },
                {
                  title: '操作',
                  width: 60,
                  render: (_: any, record: any, index: number) => (
                    <Button
                      type="text"
                      danger
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={() => removeHeader(index)}
                    />
                  )
                }
              ]}
              footer={() => (
                <Button block icon={<PlusOutlined />} onClick={addHeader}>
                  添加请求头
                </Button>
              )}
            />
          </TabPane>

          <TabPane tab="查询参数 (Params)" key="params">
            <Table
              size="small"
              dataSource={config.params}
              pagination={false}
              scroll={{ y: 150 }}
              columns={[
                {
                  title: '启用',
                  dataIndex: 'enabled',
                  width: 60,
                  render: (enabled: boolean, record: any, index: number) => (
                    <Switch 
                      size="small" 
                      checked={enabled}
                      onChange={(checked) => handleParamChange(index, 'enabled', checked)}
                    />
                  )
                },
                {
                  title: '键',
                  dataIndex: 'key',
                  render: (key: string, record: any, index: number) => (
                    <Input
                      value={key}
                      onChange={(e) => handleParamChange(index, 'key', e.target.value)}
                      placeholder="参数名"
                      size="small"
                    />
                  )
                },
                {
                  title: '值',
                  dataIndex: 'value',
                  render: (value: string, record: any, index: number) => (
                    <Input
                      value={value}
                      onChange={(e) => handleParamChange(index, 'value', e.target.value)}
                      placeholder="参数值"
                      size="small"
                    />
                  )
                },
                {
                  title: '操作',
                  width: 60,
                  render: (_: any, record: any, index: number) => (
                    <Button
                      type="text"
                      danger
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={() => removeParam(index)}
                    />
                  )
                }
              ]}
              footer={() => (
                <Button block icon={<PlusOutlined />} onClick={addParam}>
                  添加查询参数
                </Button>
              )}
            />
          </TabPane>

          <TabPane tab="认证 (Auth)" key="auth">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Select
                value={config.auth.type}
                onChange={(value) => handleConfigChange('auth', { ...config.auth, type: value })}
                style={{ width: '100%' }}
              >
                <Option value="none">无认证</Option>
                <Option value="basic">Basic Auth</Option>
                <Option value="bearer">Bearer Token</Option>
                <Option value="apiKey">API Key</Option>
              </Select>

              {config.auth.type === 'basic' && (
                <>
                  <Input
                    value={config.auth.username}
                    onChange={(e) => handleConfigChange('auth', { ...config.auth, username: e.target.value })}
                    placeholder="用户名"
                    addonBefore="用户名"
                  />
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    value={config.auth.password}
                    onChange={(e) => handleConfigChange('auth', { ...config.auth, password: e.target.value })}
                    placeholder="密码"
                    addonBefore="密码"
                    addonAfter={
                      <Tooltip title={showPassword ? '隐藏密码' : '显示密码'}>
                        <Button
                          type="text"
                          size="small"
                          icon={showPassword ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                          onClick={() => setShowPassword(!showPassword)}
                        />
                      </Tooltip>
                    }
                  />
                </>
              )}

              {config.auth.type === 'bearer' && (
                <Input
                  value={config.auth.token}
                  onChange={(e) => handleConfigChange('auth', { ...config.auth, token: e.target.value })}
                  placeholder="Bearer Token"
                  addonBefore="Token"
                />
              )}

              {config.auth.type === 'apiKey' && (
                <>
                  <Input
                    value={config.auth.key}
                    onChange={(e) => handleConfigChange('auth', { ...config.auth, key: e.target.value })}
                    placeholder="API Key名称"
                    addonBefore="Key"
                  />
                  <Input
                    value={config.auth.value}
                    onChange={(e) => handleConfigChange('auth', { ...config.auth, value: e.target.value })}
                    placeholder="API Key值"
                    addonBefore="Value"
                  />
                  <Select
                    value={config.auth.location || 'header'}
                    onChange={(value) => handleConfigChange('auth', { ...config.auth, location: value })}
                    placeholder="位置"
                  >
                    <Option value="header">请求头</Option>
                    <Option value="query">查询参数</Option>
                  </Select>
                </>
              )}
            </Space>
          </TabPane>
        </Tabs>
      </Card>

      {/* 请求体区域 */}
      <Card 
        title="请求体 (Body)" 
        size="small"
        extra={
          <Space size="small">
            <Select
              size="small"
              defaultValue="json"
              onChange={handleBodyTypeChange}
              style={{ width: 100 }}
            >
              <Option value="json">JSON</Option>
              <Option value="form">Form</Option>
              <Option value="text">Text</Option>
              <Option value="xml">XML</Option>
            </Select>
          </Space>
        }
      >
        <TextArea
          value={config.body}
          onChange={(e) => handleConfigChange('body', e.target.value)}
          placeholder={
            config.method === 'GET' || config.method === 'HEAD' 
              ? 'GET和HEAD请求不支持请求体' 
              : '输入请求体内容 (JSON/XML/文本)...'
          }
          rows={6}
          style={{ fontFamily: 'monospace' }}
          disabled={config.method === 'GET' || config.method === 'HEAD'}
        />
      </Card>

      {/* 响应区域 */}
      {response && (
        <Card 
          title={
            <Space>
              <Text strong>响应结果</Text>
              <StatusTag preset={response.status >= 200 && response.status < 300 ? 'success' : 'error'}>
                {response.status} {response.statusText}
              </StatusTag>
            </Space>
          }
          size="small"
          extra={
            <Button 
              size="small" 
              icon={<CopyOutlined />} 
              onClick={handleCopyResponse}
            >
              复制响应
            </Button>
          }
        >
          <Tabs size="small">
            <TabPane tab="响应体" key="body">
              <div style={{ 
                backgroundColor: 'var(--bg-subtle)', 
                padding: '12px', 
                borderRadius: '4px',
                maxHeight: '200px',
                overflow: 'auto',
                fontFamily: 'monospace',
                fontSize: '12px'
              }}>
                <pre style={{ margin: 0 }}>
                  {typeof response.body === 'string' 
                    ? response.body 
                    : JSON.stringify(response.body, null, 2)}
                </pre>
              </div>
            </TabPane>
            <TabPane tab="响应头" key="headers">
              <div style={{ 
                backgroundColor: 'var(--bg-subtle)', 
                padding: '12px', 
                borderRadius: '4px',
                maxHeight: '200px',
                overflow: 'auto',
                fontFamily: 'monospace',
                fontSize: '12px'
              }}>
                <pre style={{ margin: 0 }}>
                  {JSON.stringify(response.headers, null, 2)}
                </pre>
              </div>
            </TabPane>
          </Tabs>
        </Card>
      )}
    </div>
  );
};

export default HttpEditor;