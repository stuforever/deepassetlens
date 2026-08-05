import React from 'react';
import ModelTreeManager from '../components/ModelTreeManager';

type Props = {
  onOpenTarget?: (menuKey: string) => void;
};

const ActivityManager: React.FC<Props> = ({ onOpenTarget }) => {
  return <ModelTreeManager mode="activity" pageTitle="业务活动建模" onOpenTarget={onOpenTarget} />;
};

export default ActivityManager;
