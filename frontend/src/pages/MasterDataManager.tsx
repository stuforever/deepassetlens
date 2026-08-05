import React from 'react';
import ModelTreeManager from '../components/ModelTreeManager';

type Props = {
  onOpenTarget?: (menuKey: string) => void;
};

const MasterDataManager: React.FC<Props> = ({ onOpenTarget }) => {
  return <ModelTreeManager mode="master" pageTitle="主数据建模" onOpenTarget={onOpenTarget} />;
};

export default MasterDataManager;
