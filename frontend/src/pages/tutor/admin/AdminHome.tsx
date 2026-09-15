/**
 * 附件四 A-1：tutor 后台首页骨架（/e/tutor/admin 占位）。
 * A-2 填实体：卡配置编辑面（enabled/连接/tools/knowledge_sources/suggestions——写路径
 * 全走①CRUD api.ts L592-604，后端零新增）；A-3 扩四区（学情跨用户/题库/教材/调度）。
 */
import React, { useEffect, useState } from 'react';
import { Card, Descriptions, Tag, Typography } from 'antd';
import { PageShell } from '../../../components/shell';
import { expertsApi } from '../../../services/api';
import type { ExpertCard } from '../../../services/api';

const { Text } = Typography;

const TutorAdminHome: React.FC = () => {
  const [card, setCard] = useState<ExpertCard | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await expertsApi.get('tutor');
        setCard((res.data as ExpertCard) || null);
      } catch { /* A-2 实体化时补错误面 */ }
    })();
  }, []);

  return (
    <PageShell title="tutor 后台" description="专家域内维护（卡配置+域数据）——§10.2 双入口：建在平台，管在专家">
      <div style={{ maxWidth: 860, margin: '0 auto' }}>
        <Card title="专家卡（只读总览——编辑面 A-2 交付）" style={{ borderRadius: 12 }}>
          {card ? (
            <Descriptions column={2} size="small">
              <Descriptions.Item label="名称">{card.name}</Descriptions.Item>
              <Descriptions.Item label="enabled">
                <Tag color={card.enabled ? 'green' : 'red'}>{card.enabled ? '启用' : '关停'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="tools">{(card.tools || []).length} 件</Descriptions.Item>
              <Descriptions.Item label="knowledge_sources">{(card.knowledge_sources || []).join('、')}</Descriptions.Item>
              <Descriptions.Item label="suggestions" span={2}>
                {(card.suggestions || []).length > 0
                  ? (card.suggestions || []).join(' / ')
                  : <Text type="secondary">（未配置）</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="version">{card.version}</Descriptions.Item>
              <Descriptions.Item label="槽配置">六槽+surface（编辑走②管理面——不重复造）</Descriptions.Item>
            </Descriptions>
          ) : (
            <Text type="secondary">卡加载中…</Text>
          )}
        </Card>
      </div>
    </PageShell>
  );
};

export default TutorAdminHome;
