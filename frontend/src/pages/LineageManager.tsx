import React from 'react';
import { Card, Empty } from 'antd';

const LineageManager: React.FC = () => {
  return (
    <Card title="智能溯源" style={{ height: '100%' }}>
      <Empty description="这里是全局智能溯源分析大盘，待开发..." />
    </Card>
  );
};

export default LineageManager;
