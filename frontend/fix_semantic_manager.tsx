import React, { useMemo, useState } from 'react';
import { Card, Table, Typography, Space, Button, message, Tabs, Tag, Input, Select, Modal, Form } from 'antd';
import { DownloadOutlined, PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { TERMS } from '../constants/standardTerms';

const { Text } = Typography;

const DEFAULT_STOP_WORDS = [
  '吗', '请', '帮', '我', '你', '了', '吧', '呢', '啊', '呀', '吧', '呢', '是否', '有没有', '请问', '一下', '帮我', '看看', '这个', '那个',
];

const DEFAULT_STANDARD_DICT = [
  { nonStandard: '用户', standard: '用电户' },
  { nonStandard: '客户', standard: '用电户' },
  { nonStandard: '户主', standard: '用电户' },
  { nonStandard: '电费', standard: '计费结算' },
  { nonStandard: '账单', standard: '计费结算' },
  { nonStandard: '算完', standard: '结算完成' },
  { nonStandard: '扣没扣', standard: '缴费状态' },
];

const SemanticManager = () => {
  const [activeTab, setActiveTab] = useState('basic');
  const [keyword, setKeyword] = useState('');
  const [semanticCategory, setSemanticCategory] = useState('all');
  const [stopWords, setStopWords] = useState<string[]>(DEFAULT_STOP_WORDS);
  const [standardDict, setStandardDict] = useState(DEFAULT_STANDARD_DICT);
  const [stopWordModalOpen, setStopWordModalOpen] = useState(false);
  const [dictModalOpen, setDictModalOpen] = useState(false);
  const [editingStopWord, setEditingStopWord] = useState<string | null>(null);
  const [editingDictItem, setEditingDictItem] = useState<any | null>(null);
  const [stopWordForm] = Form.useForm();
  const [dictForm] = Form.useForm();

  const baseSemanticRows = useMemo(
    () => [
      { id: '1', category: '平台术语', term: TERMS.mappingRule, standard: 'menu_mapping_rule', status: '已发布', owner: '平台组' },
      { id: '2', category: '平台术语', term: TERMS.mappingInfoView, standard: 'menu_mapping_info_view', status: '已发布', owner: '平台组' },
      { id: '3', category: '实体术语', term: TERMS.graphEntityEnName, standard: 'entity_code', status: '已发布', owner: '数据治理组' },
      { id: '4', category: '实体术语', term: TERMS.graphEntityCnName, standard: 'entity_name', status: '已发布', owner: '数据治理组' },
      { id: '5', category: '源端表术语', term: TERMS.sourceTableEnName, standard: 'source_table_en', status: '草稿', owner: '接入组' },
      { id: '6', category: '表字段术语', term: TERMS.sourceFieldEnName, standard: 'source_field_en', status: '草稿', owner: '接入组' },
      { id: '7', category: '业务规则术语', term: TERMS.extractionLogic, standard: 'field_rule_logic', status: '草稿', owner: '规则组' },
      { id: '8', category: '行业标准术语', term: '供电可靠率', standard: 'DLT-std-reliability', status: '草稿', owner: '标准组' },
      { id: '9', category: '场景应用术语', term: '业扩报装场景取数', standard: 'scene_yk_apply', status: '草稿', owner: '应用组' },
    ],
    []
  );
