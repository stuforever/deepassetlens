/**
 * PlaceholderPage - 占位页（待开发）。
 * 用 EmptyState 统一渲染，保证导航结构完整、视觉统一。
 */
import React from 'react';
import { EmptyState } from '../components/shell';
import { tokens } from '../theme/tokens';

const PlaceholderPage: React.FC<{ title?: string }> = ({ title }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, padding: tokens.layout.contentPadding }}>
      <EmptyState
        title={`${title ?? '该功能'}开发中`}
        description="此模块尚未上线，后续版本将提供完整能力。"
      />
    </div>
  );
};

export default PlaceholderPage;
