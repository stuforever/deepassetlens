import React, { useState, useEffect } from 'react';
import { Modal, Row, Col, Card, List, Typography, Button, Space, message, Spin } from 'antd';
import { ArrowRightOutlined, DatabaseOutlined, LinkOutlined, SaveOutlined } from '@ant-design/icons';
import { useStore } from '../store/useStore';
import { mappingApi } from '../services/api';
import { StatusTag } from './shell';

const { Text } = Typography;

const MappingEditor: React.FC = () => {
  const { isMappingModalVisible, setMappingModalVisible, selectedNode } = useStore();
  const [loading, setLoading] = useState(false);
  const [selectedSource, setSelectedSource] = useState<any>(null);
  const [mappings, setMappings] = useState<Record<string, string>>({});

  useEffect(() => {
    if (isMappingModalVisible) {
      fetchSources();
    }
  }, [isMappingModalVisible]);

  const fetchSources = async () => {
    setLoading(true);
    try {
      const response = await mappingApi.getSources();
      if (response.data.length > 0) {
        setSelectedSource(response.data[0]);
      }
    } catch (error) {
      message.error('获取数据源失败');
    } finally {
      setLoading(false);
    }
  };

  const sourceFields = selectedSource?.column_metadata?.columns || [];

  // 模拟实体属性 (实际应从 selectedNode.properties_schema 获取)
  const targetAttrs = [
    { id: 'tgt1', name: 'id', type: 'string', desc: '唯一标识' },
    { id: 'tgt2', name: 'name', type: 'string', desc: '名称' },
    { id: 'tgt3', name: 'address', type: 'string', desc: '地址' },
    { id: 'tgt4', name: 'org_id', type: 'string', desc: '组织ID' },
  ];

  const handleDragStart = (e: React.DragEvent, fieldName: string) => {
    e.dataTransfer.setData('fieldName', fieldName);
  };

  const handleDrop = (e: React.DragEvent, attrName: string) => {
    e.preventDefault();
    const fieldName = e.dataTransfer.getData('fieldName');
    setMappings(prev => ({ ...prev, [attrName]: fieldName }));
  };

  const handleSave = async () => {
    if (!selectedSource || !selectedNode) return;
    
    try {
      await mappingApi.createMapping({
        entity_id: selectedNode.id,
        source_table_id: selectedSource.id,
        mapping_logic: mappings,
      });
      message.success('映射关系已成功保存到数据库');
      setMappingModalVisible(false);
    } catch (error) {
      message.error('保存失败');
    }
  };

  return (
    <Modal
      title={
        <Space>
          <LinkOutlined />
          <span>字段映射编辑器 - {selectedNode?.name || selectedNode?.label}</span>
        </Space>
      }
      open={isMappingModalVisible}
      onCancel={() => setMappingModalVisible(false)}
      width={1000}
      footer={[
        <Button key="cancel" onClick={() => setMappingModalVisible(false)}>取消</Button>,
        <Button key="save" type="primary" icon={<SaveOutlined />} onClick={handleSave}>保存映射</Button>
      ]}
    >
      <div style={{ padding: '20px', background: 'var(--bg-hover)', borderRadius: '8px' }}>
        <Row gutter={24}>
          <Col span={10}>
            <Card title={<Space><DatabaseOutlined /><span>源表: {selectedSource?.table_name || '未选择'}</span></Space>} size="small">
              <Spin spinning={loading}>
                <List
                  dataSource={sourceFields}
                  renderItem={(item: any) => (
                    <List.Item 
                      draggable 
                      onDragStart={(e) => handleDragStart(e, item.name)}
                      style={{ cursor: 'move', background: 'var(--bg-content)', marginBottom: '8px', padding: '8px 12px', border: '1px solid var(--border-color)', borderRadius: '4px' }}
                    >
                      <div>
                        <Text strong>{item.name}</Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: '12px' }}>{item.type} | {item.comment}</Text>
                      </div>
                    </List.Item>
                  )}
                />
              </Spin>
            </Card>
          </Col>
          
          <Col span={4} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ArrowRightOutlined style={{ fontSize: '32px', color: 'var(--color-primary)' }} />
          </Col>

          <Col span={10}>
            <Card title={<Space><DatabaseOutlined color="var(--color-warning)" /><span>目标实体: {selectedNode?.name || selectedNode?.label}</span></Space>} size="small">
              <List
                dataSource={targetAttrs}
                renderItem={item => (
                  <List.Item 
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => handleDrop(e, item.name)}
                    style={{ 
                      background: mappings[item.name] ? '#e6f7ff' : 'var(--bg-content)', 
                      marginBottom: '8px', 
                      padding: '8px 12px', 
                      border: mappings[item.name] ? '1px solid var(--color-primary-bg)' : '1px dashed var(--border-color)', 
                      borderRadius: '4px' 
                    }}
                  >
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text strong>{item.name}</Text>
                        <StatusTag preset="info">{item.type}</StatusTag>
                      </div>
                      {mappings[item.name] && (
                        <div style={{ marginTop: '8px', borderTop: '1px solid var(--color-primary-bg)', paddingTop: '4px' }}>
                          <Text type="success" style={{ fontSize: '12px' }}>
                            已映射: {mappings[item.name]}
                          </Text>
                        </div>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>
      </div>
    </Modal>
  );
};

export default MappingEditor;
