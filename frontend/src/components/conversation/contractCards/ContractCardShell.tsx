/**
 * 受控契约卡片共享外壳：统一 圆角卡片 + 图标 + 标题 + 默认展开。
 * 业务卡默认展开；技术日志（SQL/参数/原始返回/模板指纹）由调用方用折叠块。
 */
import React from 'react';
import { Card, Typography } from 'antd';

const { Text } = Typography;

type Props = {
  icon: React.ReactNode;
  title: string;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
};

const ContractCardShell: React.FC<Props> = ({ icon, title, subtitle, children }) => (
  <Card
    size="small"
    style={{ borderColor: 'var(--color-border)', boxShadow: 'none', marginBottom: 8 }}
    styles={{ body: { paddingTop: 8, paddingBottom: 8 } }}
    title={
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: 14 }}>{icon}</span>
        <span style={{ fontSize: 13, fontWeight: 600 }}>{title}</span>
        {subtitle ? (
          <Text type="secondary" style={{ fontSize: 11, marginLeft: 6 }}>{subtitle}</Text>
        ) : null}
      </span>
    }
  >
    {children}
  </Card>
);

export default ContractCardShell;
