import React, { useState, useEffect } from 'react';
import { Input, Button, Space, Card, Tooltip, Typography } from 'antd';
import { PlusOutlined, CopyOutlined, BulbOutlined } from '@ant-design/icons';
import { StatusTag } from './shell';

const { TextArea } = Input;
const { Text } = Typography;

interface PromptEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  height?: number;
  variables?: string[];
}

const PromptEditor: React.FC<PromptEditorProps> = ({
  value = '',
  onChange,
  placeholder = '请输入提示词内容...',
  height = 300,
  variables = []
}) => {
  const [content, setContent] = useState(value);
  const [detectedVariables, setDetectedVariables] = useState<string[]>([]);
  const [customVariables, setCustomVariables] = useState<string[]>([]);

  // 检测内容中的变量
  useEffect(() => {
    const variablePattern = /\{\{([^}]+)\}\}/g;
    const matches = Array.from(content.matchAll(variablePattern));
    const foundVars = matches.map(match => match[1].trim());
    const uniqueVars = Array.from(new Set(foundVars));
    setDetectedVariables(uniqueVars);
  }, [content]);

  // 合并所有变量
  const allVariables = Array.from(new Set([...variables, ...detectedVariables, ...customVariables]));

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setContent(newValue);
    onChange?.(newValue);
  };

  const handleInsertVariable = (variable: string) => {
    const newContent = content + ` {{${variable}}}`;
    setContent(newContent);
    onChange?.(newContent);
  };

  const handleAddCustomVariable = () => {
    const variableName = prompt('请输入变量名（无需包含花括号）:');
    if (variableName && variableName.trim()) {
      const trimmedName = variableName.trim();
      setCustomVariables(prev => [...prev, trimmedName]);
      handleInsertVariable(trimmedName);
    }
  };

  const handleCopyVariable = (variable: string) => {
    navigator.clipboard.writeText(`{{${variable}}}`);
  };

  const handleExtractVariables = () => {
    const extracted = prompt('请输入要提取的变量名（用逗号分隔）:');
    if (extracted) {
      const vars = extracted.split(',').map(v => v.trim()).filter(v => v);
      setCustomVariables(prev => [...prev, ...vars.filter(v => !prev.includes(v))]);
    }
  };

  return (
    <div style={{ display: 'flex', gap: 16, height }}>
      {/* 左侧编辑器 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text strong>提示词编辑器</Text>
          <Space size="small">
            <Tooltip title="提取变量">
              <Button
                size="small"
                icon={<BulbOutlined />}
                onClick={handleExtractVariables}
              >
                提取变量
              </Button>
            </Tooltip>
            <Tooltip title="添加自定义变量">
              <Button
                size="small"
                icon={<PlusOutlined />}
                onClick={handleAddCustomVariable}
              >
                添加变量
              </Button>
            </Tooltip>
          </Space>
        </div>
        <TextArea
          value={content}
          onChange={handleContentChange}
          placeholder={placeholder}
          style={{
            flex: 1,
            fontFamily: 'monospace',
            fontSize: '13px',
            lineHeight: 1.6,
            resize: 'none'
          }}
        />
        <div style={{ marginTop: 8, fontSize: '12px', color: 'var(--text-secondary)' }}>
          提示：使用双花括号 <code>{'{{变量名}}'}</code> 来标记变量，变量会自动在右侧面板中检测和显示。
        </div>
      </div>

      {/* 右侧变量面板 */}
      <Card
        title="变量面板"
        size="small"
        style={{ width: 280, display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, overflow: 'auto' }}
      >
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            点击变量可快速插入到编辑器中
          </Text>
        </div>

        {/* 检测到的变量 */}
        {detectedVariables.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ fontSize: '12px', display: 'block', marginBottom: 8 }}>
              检测到的变量 ({detectedVariables.length})
            </Text>
            <Space wrap size={[4, 4]} style={{ marginBottom: 8 }}>
              {detectedVariables.map(variable => (
                <Tooltip key={variable} title="点击插入">
                  <span
                    style={{ cursor: 'pointer', userSelect: 'none' }}
                    onClick={() => handleInsertVariable(variable)}
                  >
                    <StatusTag preset="info">{variable}</StatusTag>
                  </span>
                </Tooltip>
              ))}
            </Space>
          </div>
        )}

        {/* 预定义变量 */}
        {variables.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ fontSize: '12px', display: 'block', marginBottom: 8 }}>
              预定义变量 ({variables.length})
            </Text>
            <Space wrap size={[4, 4]} style={{ marginBottom: 8 }}>
              {variables.map(variable => (
                <Tooltip key={variable} title="点击插入">
                  <span
                    style={{ cursor: 'pointer', userSelect: 'none' }}
                    onClick={() => handleInsertVariable(variable)}
                  >
                    <StatusTag preset="success">{variable}</StatusTag>
                  </span>
                </Tooltip>
              ))}
            </Space>
          </div>
        )}

        {/* 自定义变量 */}
        {customVariables.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ fontSize: '12px', display: 'block', marginBottom: 8 }}>
              自定义变量 ({customVariables.length})
            </Text>
            <Space wrap size={[4, 4]}>
              {customVariables.map(variable => (
                <Tooltip key={variable} title="点击插入">
                  <span
                    style={{ cursor: 'pointer', userSelect: 'none' }}
                    onClick={() => handleInsertVariable(variable)}
                  >
                    <StatusTag preset="warning">{variable}</StatusTag>
                  </span>
                </Tooltip>
              ))}
            </Space>
          </div>
        )}

        {/* 变量操作 */}
        <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: '1px solid var(--color-border)' }}>
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Button
              block
              size="small"
              icon={<PlusOutlined />}
              onClick={handleAddCustomVariable}
            >
              添加新变量
            </Button>
            {allVariables.length > 0 && (
              <Button
                block
                size="small"
                icon={<CopyOutlined />}
                onClick={() => {
                  const allVarText = allVariables.map(v => `{{${v}}}`).join('\n');
                  navigator.clipboard.writeText(allVarText);
                }}
              >
                复制所有变量
              </Button>
            )}
          </Space>
        </div>
      </Card>
    </div>
  );
};

export default PromptEditor;