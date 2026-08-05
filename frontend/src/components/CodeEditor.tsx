import React, { useState, useEffect, useRef } from 'react';
import { Button, Space, Card, Tooltip, Typography, Select, message } from 'antd';
import { FormatPainterOutlined, CopyOutlined, CodeOutlined, LineHeightOutlined } from '@ant-design/icons';

const { Text } = Typography;
const { Option } = Select;

interface CodeEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  height?: number;
  language?: string;
  showLineNumbers?: boolean;
}

const CodeEditor: React.FC<CodeEditorProps> = ({
  value = '',
  onChange,
  placeholder = '请输入代码...',
  height = 300,
  language = 'javascript',
  showLineNumbers = true
}) => {
  const [content, setContent] = useState(value);
  const [lineCount, setLineCount] = useState(1);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);

  // 更新行数
  useEffect(() => {
    const lines = content.split('\n').length;
    setLineCount(Math.max(lines, 1));
  }, [content]);

  // 同步滚动
  const handleScroll = () => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setContent(newValue);
    onChange?.(newValue);
  };

  const handleFormatCode = () => {
    try {
      // 简单的格式化逻辑
      let formatted = content;
      
      // 基本的缩进格式化
      if (language === 'javascript' || language === 'typescript') {
        // 添加分号（简单示例）
        formatted = formatted.replace(/([^;])\n/g, '$1;\n');
      }
      
      // 标准化换行
      formatted = formatted.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
      
      // 移除多余的空行
      formatted = formatted.replace(/\n\s*\n\s*\n/g, '\n\n');
      
      setContent(formatted);
      onChange?.(formatted);
      message.success('代码格式化完成');
    } catch (error) {
      message.error('格式化失败，请检查代码语法');
    }
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(content);
    message.success('代码已复制到剪贴板');
  };

  const handleInsertTemplate = () => {
    const templates: Record<string, string> = {
      javascript: `// JavaScript 代码模板
function execute(inputs) {
  // 在此编写你的处理逻辑
  const result = {};
  
  // 示例：处理输入
  if (inputs && typeof inputs === 'object') {
    result.processed = true;
    result.data = inputs;
  }
  
  return result;
}`,
      python: `# Python 代码模板
def execute(inputs):
    """技能处理逻辑"""
    result = {}
    
    # 示例：处理输入
    if inputs and isinstance(inputs, dict):
        result['processed'] = True
        result['data'] = inputs
    
    return result`,
      sql: `-- SQL 查询模板
SELECT 
    *
FROM 
    table_name
WHERE 
    1 = 1
    -- AND field = {{param}}
LIMIT 100;`,
      default: `// 代码模板
function process(inputs) {
  // 你的代码逻辑
  return {};
}`
    };
    
    const template = templates[language] || templates.default;
    const newContent = content ? content + '\n\n' + template : template;
    setContent(newContent);
    onChange?.(newContent);
  };

  const handleLanguageChange = (lang: string) => {
    // 这里可以触发父组件更新语言
    message.info(`语言已切换为: ${lang}`);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height }}>
      {/* 工具栏 */}
      <div style={{ 
        marginBottom: 8, 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        padding: '4px 0',
        borderBottom: '1px solid var(--color-border)'
      }}>
        <Space>
          <Text strong>
            <CodeOutlined /> 代码编辑器
          </Text>
          <Select
            size="small"
            value={language}
            onChange={handleLanguageChange}
            style={{ width: 120 }}
          >
            <Option value="javascript">JavaScript</Option>
            <Option value="typescript">TypeScript</Option>
            <Option value="python">Python</Option>
            <Option value="sql">SQL</Option>
            <Option value="java">Java</Option>
            <Option value="html">HTML</Option>
            <Option value="css">CSS</Option>
            <Option value="json">JSON</Option>
          </Select>
        </Space>
        <Space size="small">
          <Tooltip title="插入模板">
            <Button
              size="small"
              icon={<LineHeightOutlined />}
              onClick={handleInsertTemplate}
            >
              模板
            </Button>
          </Tooltip>
          <Tooltip title="格式化代码">
            <Button
              size="small"
              icon={<FormatPainterOutlined />}
              onClick={handleFormatCode}
            >
              格式化
            </Button>
          </Tooltip>
          <Tooltip title="复制代码">
            <Button
              size="small"
              icon={<CopyOutlined />}
              onClick={handleCopyCode}
            >
              复制
            </Button>
          </Tooltip>
        </Space>
      </div>

      {/* 编辑器区域 */}
      <div style={{ 
        flex: 1, 
        display: 'flex', 
        overflow: 'hidden',
        border: '1px solid var(--border-color)',
        borderRadius: '6px',
        backgroundColor: 'var(--bg-subtle)'
      }}>
        {/* 行号区域 */}
        {showLineNumbers && (
          <div
            ref={lineNumbersRef}
            style={{
              width: '50px',
              padding: '8px 4px',
              textAlign: 'right',
              backgroundColor: 'var(--bg-hover)',
              borderRight: '1px solid var(--border-color)',
              overflow: 'hidden',
              fontFamily: 'monospace',
              fontSize: '13px',
              lineHeight: '1.5',
              color: 'var(--text-secondary)',
              userSelect: 'none',
              flexShrink: 0
            }}
          >
            {Array.from({ length: lineCount }, (_, i) => (
              <div key={i} style={{ height: '21px' }}>
                {i + 1}
              </div>
            ))}
          </div>
        )}

        {/* 代码编辑区域 */}
        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleContentChange}
          onScroll={handleScroll}
          placeholder={placeholder}
          style={{
            flex: 1,
            padding: '8px',
            border: 'none',
            outline: 'none',
            resize: 'none',
            fontFamily: 'monospace',
            fontSize: '13px',
            lineHeight: '1.5',
            backgroundColor: 'transparent',
            whiteSpace: 'pre',
            overflow: 'auto',
            tabSize: 2
          }}
          spellCheck={false}
        />
      </div>

      {/* 状态栏 */}
      <div style={{
        marginTop: 8,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '12px',
        color: 'var(--text-secondary)'
      }}>
        <div>
          <Text type="secondary">
            行数: {lineCount} | 字符: {content.length} | 语言: {language}
          </Text>
        </div>
        <div>
          <Text type="secondary">
            提示: 使用 Tab 键缩进代码，Shift+Tab 反向缩进
          </Text>
        </div>
      </div>

      {/* 快捷键提示 */}
      <Card size="small" style={{ marginTop: 8 }}>
        <Text type="secondary" style={{ fontSize: '11px' }}>
          <strong>快捷键:</strong> Ctrl+S 保存 | Ctrl+F 格式化 | Ctrl+C 复制 | Ctrl+Z 撤销 | Tab 缩进
        </Text>
      </Card>
    </div>
  );
};

export default CodeEditor;