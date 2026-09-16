/**
 * 教学设置（原仓 curriculum 设置页组）——tupu 合页外壳。
 * 原仓为三个路由页（(utility)/settings/curriculum/{textbooks,chapters,knowledge-points}）+
 * 磁贴入口页（SettingsSectionGrid categoryKey="curriculum"），此处按 tupu 形态合一为
 * 单个 antd Tabs 设置页；tab 顺序 = 原仓设置侧栏顺序（lib/settings-nav.ts CURRICULUM_CHILDREN：
 * 课本管理 → 章节管理 → 知识点管理），三页内容 1:1 复刻于同目录子组件。
 * ⑤R 批8（8.2）：追加第 4 tab「专家卡配置」——A-2 卡配置编辑面落位（唯一交棒开放裁定默认在此），
 * 复用共享件 ExpertCardConfigEditor（与 tutor 后台首页同一编辑面，零新逻辑）。
 */
import React, { useState } from 'react';
import { Tabs } from 'antd';
import SettingsTextbooks from './SettingsTextbooks';
import SettingsChapters from './SettingsChapters';
import SettingsKnowledgePoints from './SettingsKnowledgePoints';
import ExpertCardConfigEditor from './ExpertCardConfigEditor';
import { CurriculumTabContext } from './dtCurriculumTab';

export default function SettingsAdmin() {
  const [activeKey, setActiveKey] = useState('textbooks');
  return (
    <CurriculumTabContext.Provider value={{ goToTab: setActiveKey }}>
      <Tabs
        activeKey={activeKey}
        onChange={setActiveKey}
        items={[
          { key: 'textbooks', label: '课本管理', children: <SettingsTextbooks /> },
          { key: 'chapters', label: '章节管理', children: <SettingsChapters /> },
          { key: 'knowledge-points', label: '知识点管理', children: <SettingsKnowledgePoints /> },
          { key: 'expert-card', label: '专家卡配置', children: <ExpertCardConfigEditor /> },
        ]}
      />
    </CurriculumTabContext.Provider>
  );
}
