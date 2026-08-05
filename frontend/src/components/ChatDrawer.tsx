import React, { useState } from 'react';
import { Drawer, Input, Button, List, Typography, Space, Empty, Spin } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined, CodeOutlined } from '@ant-design/icons';
import { chatApi } from '../services/api';
import { StatusTag } from './shell';

const { Text, Paragraph } = Typography;

interface Message {
  role: 'user' | 'assistant';
  content: string;
  cypher?: string;
  results?: any[];
}

interface ChatDrawerProps {
  visible: boolean;
  onClose: () => void;
}

const ChatDrawer: React.FC<ChatDrawerProps> = ({ visible, onClose }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: '您好！我是 数据智能分析组件 智能助手。您可以问我关于图谱结构的问题，例如：“找一下属于用电客户分类下的所有实体”。' }
  ]);

  const handleSend = async () => {
    if (!query.trim()) return;

    const userMsg: Message = { role: 'user', content: query };
    setMessages(prev => [...prev, userMsg]);
    setQuery('');
    setLoading(true);

    try {
      const res = await chatApi.ask(query);
      const assistantMsg: Message = {
        role: 'assistant',
        content: res.data.answer,
        cypher: res.data.cypher,
        results: res.data.results
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: '抱歉，我现在无法处理您的请求，请检查后端服务。' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Drawer
      title={
        <Space>
          <RobotOutlined />
          <span>智能问数 (Text-to-Cypher)</span>
        </Space>
      }
      placement="right"
      width={450}
      onClose={onClose}
      open={visible}
      footer={
        <div style={{ display: 'flex', gap: '8px', padding: '10px 0' }}>
          <Input 
            placeholder="输入您的问询..." 
            value={query} 
            onChange={e => setQuery(e.target.value)}
            onPressEnter={handleSend}
            disabled={loading}
          />
          <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading}>发送</Button>
        </div>
      }
    >
      <List
        dataSource={messages}
        renderItem={(msg) => (
          <List.Item style={{ borderBottom: 'none', padding: '12px 0' }}>
            <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px', gap: '8px' }}>
                {msg.role === 'user' ? <UserOutlined style={{ color: 'var(--color-primary)' }} /> : <RobotOutlined style={{ color: 'var(--color-success)' }} />}
                <Text strong>{msg.role === 'user' ? '我' : '智能助手'}</Text>
              </div>
              <div style={{ 
                background: msg.role === 'user' ? '#e6f7ff' : 'var(--color-success-bg)', 
                padding: '12px', 
                borderRadius: '8px',
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '90%'
              }}>
                <Paragraph style={{ margin: 0 }}>{msg.content}</Paragraph>
                
                {msg.cypher && (
                  <div style={{ marginTop: '12px' }}>
                    <Text type="secondary" style={{ fontSize: '12px' }}><CodeOutlined /> 生成的 Cypher:</Text>
                    <div style={{ 
                      background: 'var(--bg-content)', 
                      padding: '8px', 
                      borderRadius: '4px', 
                      fontSize: '11px',
                      fontFamily: 'monospace',
                      marginTop: '4px',
                      border: '1px solid var(--border-color)'
                    }}>
                      {msg.cypher}
                    </div>
                  </div>
                )}

                {msg.results && msg.results.length > 0 && (
                  <div style={{ marginTop: '12px' }}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>查询结果 ({msg.results.length}):</Text>
                    <div style={{ background: 'var(--bg-content)', borderRadius: '4px', marginTop: '4px', border: '1px solid var(--border-color)', padding: '4px' }}>
                      <List
                        size="small"
                        dataSource={msg.results}
                        renderItem={(item: any) => (
                          <List.Item style={{ fontSize: '11px', padding: '4px 8px' }}>
                            {Object.entries(item).map(([k, v]: any) => (
                              <div key={k}><StatusTag preset="info">{k}</StatusTag>: {v}</div>
                            ))}
                          </List.Item>
                        )}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </List.Item>
        )}
      />
      {loading && (
        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <Spin tip="思考中..." />
        </div>
      )}
    </Drawer>
  );
};

export default ChatDrawer;
