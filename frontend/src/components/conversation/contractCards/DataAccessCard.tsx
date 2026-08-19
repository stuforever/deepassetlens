/**
 * DataAccessCard - 数据访问边界（设计 §6）
 * 允许工具（绿）/ 禁止工具（红）/ 本次允许 SQL 模板（折叠技术日志）。
 */
import React from 'react';
import { Collapse, Space, Tag, Typography } from 'antd';
import { SafetyOutlined } from '@ant-design/icons';
import ContractCardShell from './ContractCardShell';

const { Text } = Typography;

type Props = {
  allowedTools?: string[];
  forbiddenTools?: string[];
  templateIds?: string[];
};

const DataAccessCard: React.FC<Props> = ({ allowedTools = [], forbiddenTools = [], templateIds = [] }) => (
  <ContractCardShell
    icon={<SafetyOutlined />}
    title="数据访问边界"
    subtitle={`允许 ${allowedTools.length} · 禁止 ${forbiddenTools.length}`}
  >
    <Space direction="vertical" size={6} style={{ width: '100%' }}>
      <div>
        <Text type="secondary" style={{ fontSize: 12 }}>允许工具：</Text>
        <div style={{ marginTop: 4 }}>
          <Space size={[4, 4]} wrap>
            {allowedTools.map((t) => <Tag key={t} color="green" style={{ fontSize: 11 }}>{t}</Tag>)}
          </Space>
        </div>
      </div>
      {forbiddenTools.length > 0 ? (
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>禁止工具：</Text>
          <div style={{ marginTop: 4 }}>
            <Space size={[4, 4]} wrap>
              {forbiddenTools.map((t) => <Tag key={t} color="red" style={{ fontSize: 11 }}>{t}</Tag>)}
            </Space>
          </div>
        </div>
      ) : null}
      {templateIds.length > 0 ? (
        <Collapse
          size="small"
          ghost
          style={{ fontSize: 12 }}
          items={[{
            key: 'tpl',
            label: <Text type="secondary" style={{ fontSize: 12 }}>本次允许 SQL 模板（{templateIds.length}）</Text>,
            children: (
              <div style={{ fontSize: 12 }}>
                {templateIds.map((t) => <div key={t} style={{ padding: '2px 0', wordBreak: 'break-all' }}>{t}</div>)}
              </div>
            ),
          }]}
        />
      ) : null}
    </Space>
  </ContractCardShell>
);

export default DataAccessCard;
