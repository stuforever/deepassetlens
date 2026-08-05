import React, { useState, useEffect } from 'react';
import {
  Table, Button, Input, Select, Space, Tooltip,
  Typography, Switch, Modal, message, Popconfirm, Alert
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, EditOutlined, CopyOutlined,
  ArrowUpOutlined, ArrowDownOutlined, EyeOutlined, CodeOutlined
} from '@ant-design/icons';
import { StatusTag } from './shell';

const { Option } = Select;
const { Text } = Typography;

interface Param {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  description?: string;
  required: boolean;
  defaultValue?: any;
  example?: any;
}

interface ParamTableEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  title?: string;
  placeholder?: string;
  height?: number;
}

const ParamTableEditor: React.FC<ParamTableEditorProps> = ({
  value = '',
  onChange,
  title = '参数定义',
  placeholder = '添加参数...',
  height = 400
}) => {
  // 解析JSON Schema为参数数组
  const parseSchemaToParams = (schemaStr: string): Param[] => {
    try {
      if (!schemaStr.trim()) return [];
      const schema = JSON.parse(schemaStr);
      const properties = schema.properties || {};
      const required = schema.required || [];
      
      return Object.keys(properties).map((key, index) => {
        const prop = properties[key];
        return {
          id: `param-${index}`,
          name: key,
          type: prop.type || 'string',
          description: prop.description || '',
          required: required.includes(key),
          defaultValue: prop.default,
          example: prop.example
        };
      });
    } catch (e) {
      console.error('Failed to parse schema', e);
      return [];
    }
  };

  // 将参数数组转换为JSON Schema
  const convertParamsToSchema = (params: Param[]): string => {
    const schema: any = {
      type: 'object',
      properties: {},
      required: []
    };

    params.forEach(param => {
      schema.properties[param.name] = {
        type: param.type,
        description: param.description || undefined,
        default: param.defaultValue || undefined,
        example: param.example || undefined
      };

      if (param.required) {
        schema.required.push(param.name);
      }
    });

    return JSON.stringify(schema, null, 2);
  };

  const [params, setParams] = useState<Param[]>(parseSchemaToParams(value));
  const [editingParam, setEditingParam] = useState<Param | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [jsonPreview, setJsonPreview] = useState<string>('');
  const [validationError, setValidationError] = useState<string | null>(null);

  // 验证JSON Schema
  const validateJsonSchema = (schemaStr: string): string | null => {
    try {
      if (!schemaStr.trim()) return null;
      const schema = JSON.parse(schemaStr);
      
      // 基本验证：检查是否是对象
      if (typeof schema !== 'object' || schema === null) {
        return 'Schema必须是JSON对象';
      }
      
      // 检查是否有type属性
      if (schema.type !== 'object') {
        return 'Schema类型必须是"object"';
      }
      
      // 检查properties是否存在
      if (!schema.properties || typeof schema.properties !== 'object') {
        return 'Schema必须包含"properties"对象';
      }
      
      // 检查required是否为数组
      if (schema.required && !Array.isArray(schema.required)) {
        return '"required"必须是数组';
      }
      
      return null;
    } catch (e) {
      return '无效的JSON格式';
    }
  };

  // 当参数变化时更新JSON Schema
  useEffect(() => {
    const schemaStr = convertParamsToSchema(params);
    setJsonPreview(schemaStr);
    onChange?.(schemaStr);
    
    // 验证Schema
    const error = validateJsonSchema(schemaStr);
    setValidationError(error);
  }, [params, onChange]);

  // 初始化
  useEffect(() => {
    setParams(parseSchemaToParams(value));
  }, [value]);

  const handleAddParam = () => {
    const newParam: Param = {
      id: `param-${Date.now()}`,
      name: '',
      type: 'string',
      description: '',
      required: false,
      defaultValue: ''
    };
    setEditingParam(newParam);
    setIsEditing(true);
  };

  const handleEditParam = (param: Param) => {
    setEditingParam(param);
    setIsEditing(true);
  };

  const handleDeleteParam = (id: string) => {
    setParams(params.filter(p => p.id !== id));
    message.success('参数已删除');
  };

  const handleSaveParam = () => {
    if (!editingParam || !editingParam.name.trim()) {
      message.error('参数名称不能为空');
      return;
    }

    // 检查名称是否重复
    const isDuplicate = params.some(p => 
      p.id !== editingParam.id && p.name === editingParam.name
    );
    if (isDuplicate) {
      message.error('参数名称不能重复');
      return;
    }

    if (editingParam.id.startsWith('param-') && !editingParam.id.includes('Date')) {
      // 更新现有参数
      setParams(params.map(p => p.id === editingParam.id ? editingParam : p));
    } else {
      // 添加新参数
      setParams([...params, editingParam]);
    }

    setEditingParam(null);
    setIsEditing(false);
    message.success('参数已保存');
  };

  const handleMoveParam = (index: number, direction: 'up' | 'down') => {
    if (
      (direction === 'up' && index === 0) ||
      (direction === 'down' && index === params.length - 1)
    ) {
      return;
    }

    const newParams = [...params];
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    [newParams[index], newParams[newIndex]] = [newParams[newIndex], newParams[index]];
    setParams(newParams);
  };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(jsonPreview);
    message.success('JSON Schema 已复制到剪贴板');
  };

  const handleImportJson = () => {
    Modal.confirm({
      title: '导入 JSON Schema',
      content: (
        <div>
          <Input.TextArea
            placeholder="粘贴 JSON Schema..."
            rows={6}
            onChange={(e) => {
              try {
                const newParams = parseSchemaToParams(e.target.value);
                if (newParams.length > 0) {
                  setParams(newParams);
                }
              } catch (e) {
                // 忽略解析错误
              }
            }}
          />
        </div>
      ),
      onOk: () => {
        message.success('参数已导入');
      }
    });
  };

  const columns = [
    {
      title: '参数名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string, record: Param) => (
        <Space>
          <Text strong>{name}</Text>
          {record.required && <StatusTag preset="error">必填</StatusTag>}
        </Space>
      )
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => (
        <StatusTag preset={
          type === 'string' ? 'info' :
          type === 'number' ? 'success' :
          type === 'boolean' ? 'warning' :
          type === 'array' ? 'ai' : 'error'
        }>
          {type}
        </StatusTag>
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (desc: string) => desc || <Text type="secondary">无描述</Text>
    },
    {
      title: '默认值',
      dataIndex: 'defaultValue',
      key: 'defaultValue',
      width: 100,
      render: (value: any) => (
        <Text code style={{ fontSize: '12px' }}>
          {value !== undefined ? JSON.stringify(value) : '-'}
        </Text>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: Param, index: number) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditParam(record)}
            />
          </Tooltip>
          <Tooltip title="上移">
            <Button
              type="text"
              size="small"
              icon={<ArrowUpOutlined />}
              onClick={() => handleMoveParam(index, 'up')}
              disabled={index === 0}
            />
          </Tooltip>
          <Tooltip title="下移">
            <Button
              type="text"
              size="small"
              icon={<ArrowDownOutlined />}
              onClick={() => handleMoveParam(index, 'down')}
              disabled={index === params.length - 1}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个参数吗？"
            onConfirm={() => handleDeleteParam(record.id)}
          >
            <Tooltip title="删除">
              <Button
                type="text"
                danger
                size="small"
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height, gap: 16 }}>
      {/* 工具栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text strong>{title}</Text>
        <Space>
          <Tooltip title="导入 JSON Schema">
            <Button
              size="small"
              icon={<CodeOutlined />}
              onClick={handleImportJson}
            >
              导入
            </Button>
          </Tooltip>
          <Tooltip title="添加参数">
            <Button
              type="primary"
              size="small"
              icon={<PlusOutlined />}
              onClick={handleAddParam}
            >
              添加参数
            </Button>
          </Tooltip>
        </Space>
      </div>

      {/* 参数表格 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <Table
          size="small"
          columns={columns}
          dataSource={params}
          rowKey="id"
          pagination={false}
          scroll={{ y: 200 }}
          locale={{ emptyText: '暂无参数，点击上方按钮添加' }}
        />
      </div>

      {/* JSON Schema 预览 */}
      <div>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: 8 
        }}>
          <Space>
            <Text strong>JSON Schema 预览</Text>
            {validationError ? (
              <StatusTag preset="error" style={{ fontSize: '12px' }}>验证失败</StatusTag>
            ) : (
              <StatusTag preset="success" style={{ fontSize: '12px' }}>验证通过</StatusTag>
            )}
          </Space>
          <Button
            size="small"
            icon={<CopyOutlined />}
            onClick={handleCopyJson}
          >
            复制
          </Button>
        </div>
        {validationError && (
          <Alert
            message={validationError}
            type="error"
            showIcon
            style={{ marginBottom: 8, fontSize: '12px' }}
          />
        )}
        <pre style={{
          margin: 0,
          padding: '12px',
          backgroundColor: validationError ? 'var(--color-error-bg)' : 'var(--bg-subtle)',
          borderRadius: '4px',
          fontSize: '12px',
          border: validationError ? '1px solid var(--color-error-bg)' : '1px solid var(--border-color)',
          fontFamily: 'monospace',
          maxHeight: '200px',
          overflow: 'auto',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all'
        }}>
          {jsonPreview || '{}'}
        </pre>
      </div>

      {/* 编辑弹窗 */}
      <Modal
        title={editingParam?.id.startsWith('param-') && !editingParam?.id.includes('Date') ? '编辑参数' : '添加参数'}
        open={isEditing}
        onCancel={() => {
          setIsEditing(false);
          setEditingParam(null);
        }}
        onOk={handleSaveParam}
        width={600}
      >
        {editingParam && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>参数名称</Text>
              <Input
                value={editingParam.name}
                onChange={(e) => setEditingParam({ ...editingParam, name: e.target.value })}
                placeholder="例如：username、age、is_active"
              />
            </div>

            <div style={{ display: 'flex', gap: 16 }}>
              <div style={{ flex: 1 }}>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>类型</Text>
                <Select
                  value={editingParam.type}
                  onChange={(value) => setEditingParam({ ...editingParam, type: value })}
                  style={{ width: '100%' }}
                >
                  <Option value="string">字符串</Option>
                  <Option value="number">数字</Option>
                  <Option value="boolean">布尔值</Option>
                  <Option value="array">数组</Option>
                  <Option value="object">对象</Option>
                </Select>
              </div>
              <div style={{ flex: 1 }}>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>必填</Text>
                <div>
                  <Switch
                    checked={editingParam.required}
                    onChange={(checked) => setEditingParam({ ...editingParam, required: checked })}
                  />
                  <Text style={{ marginLeft: 8 }}>
                    {editingParam.required ? '是' : '否'}
                  </Text>
                </div>
              </div>
            </div>

            <div>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>描述</Text>
              <Input.TextArea
                value={editingParam.description}
                onChange={(e) => setEditingParam({ ...editingParam, description: e.target.value })}
                placeholder="参数描述..."
                rows={2}
              />
            </div>

            <div>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>默认值</Text>
              <Input.TextArea
                value={typeof editingParam.defaultValue === 'object' 
                  ? JSON.stringify(editingParam.defaultValue, null, 2)
                  : String(editingParam.defaultValue || '')
                }
                onChange={(e) => {
                  try {
                    const value = e.target.value;
                    if (value.trim() === '') {
                      setEditingParam({ ...editingParam, defaultValue: undefined });
                    } else if (editingParam.type === 'number') {
                      setEditingParam({ ...editingParam, defaultValue: Number(value) });
                    } else if (editingParam.type === 'boolean') {
                      setEditingParam({ ...editingParam, defaultValue: value === 'true' });
                    } else if (editingParam.type === 'array' || editingParam.type === 'object') {
                      setEditingParam({ ...editingParam, defaultValue: JSON.parse(value) });
                    } else {
                      setEditingParam({ ...editingParam, defaultValue: value });
                    }
                  } catch (e) {
                    // 保持原样
                  }
                }}
                placeholder={
                  editingParam.type === 'string' ? '字符串默认值' :
                  editingParam.type === 'number' ? '数字默认值，如：0、100' :
                  editingParam.type === 'boolean' ? 'true 或 false' :
                  editingParam.type === 'array' ? 'JSON数组，如：["item1", "item2"]' :
                  'JSON对象，如：{"key": "value"}'
                }
                rows={2}
              />
            </div>

            <div>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>示例值</Text>
              <Input.TextArea
                value={typeof editingParam.example === 'object' 
                  ? JSON.stringify(editingParam.example, null, 2)
                  : String(editingParam.example || '')
                }
                onChange={(e) => {
                  try {
                    const value = e.target.value;
                    if (value.trim() === '') {
                      setEditingParam({ ...editingParam, example: undefined });
                    } else if (editingParam.type === 'number') {
                      setEditingParam({ ...editingParam, example: Number(value) });
                    } else if (editingParam.type === 'boolean') {
                      setEditingParam({ ...editingParam, example: value === 'true' });
                    } else if (editingParam.type === 'array' || editingParam.type === 'object') {
                      setEditingParam({ ...editingParam, example: JSON.parse(value) });
                    } else {
                      setEditingParam({ ...editingParam, example: value });
                    }
                  } catch (e) {
                    // 保持原样
                  }
                }}
                placeholder="示例值，用于文档和测试"
                rows={2}
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ParamTableEditor;