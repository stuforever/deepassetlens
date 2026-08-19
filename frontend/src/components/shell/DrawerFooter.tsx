/**
 * DrawerFooter - B4 管理页规范化：抽屉底部 sticky 操作条。
 * 用于 antd Drawer 的 footer 槽位（footer={<DrawerFooter>...</DrawerFooter>}），
 * antd Drawer footer 渲染在 body 之外、始终可见（内容超长内部滚动时操作按钮不丢失）。
 * 左 extra 可放辅助信息（如"共 N 条"），右侧放取消/确定。
 */
import React from 'react';
import { Space } from 'antd';

const DrawerFooter: React.FC<{ children: React.ReactNode; extra?: React.ReactNode }> = ({ children, extra }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, width: '100%' }}>
    <div style={{ flex: 1, minWidth: 0 }}>{extra}</div>
    <Space>{children}</Space>
  </div>
);

export default React.memo(DrawerFooter);
