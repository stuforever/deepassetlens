/**
 * 批①b（v4§二.2）：八问答模板前端常量——每专家 8 条（第 8 条=自定义空模板）。
 * 内容照抄总册 §二.2 两列原文（含 {占位符}）。
 * 交互铁律：点击=回填 composer 并聚焦，**任何情况下不直发**（调用方遵守）。
 * 模板配置存前端常量，不发后端。
 */
import React from 'react';
import {
  BarChartOutlined, UnorderedListOutlined, SwapOutlined, PieChartOutlined,
  AlertOutlined, FileTextOutlined, ApartmentOutlined, EditOutlined,
  BookOutlined, FormOutlined, CheckSquareOutlined, RocketOutlined,
  LineChartOutlined, CustomerServiceOutlined, QuestionCircleOutlined,
} from '@ant-design/icons';

export interface ChatTemplate {
  icon: React.ReactNode;
  title: string;
  /** 问答文案（含 {占位符}——回填后用户自行改写） */
  text: string;
}

export const chatTemplates: Record<'wenshu' | 'sishu', ChatTemplate[]> = {
  wenshu: [
    { icon: <BarChartOutlined />, title: '数据概览', text: '{主题}有多少？分布如何？' },
    { icon: <UnorderedListOutlined />, title: '明细查询', text: '查{实体}的{条件}明细' },
    { icon: <SwapOutlined />, title: '对比分析', text: '{A}和{B}对比' },
    { icon: <PieChartOutlined />, title: '趋势/占比', text: '{指标}按{维度}的占比' },
    { icon: <AlertOutlined />, title: '异常排查', text: '{实体}有什么异常？' },
    { icon: <FileTextOutlined />, title: '指标解读', text: '{指标}含义与口径' },
    { icon: <ApartmentOutlined />, title: '血缘追溯', text: '{资产}从哪来？' },
    { icon: <EditOutlined />, title: '自定义', text: '' },
  ],
  sishu: [
    { icon: <BookOutlined />, title: '课文讲解', text: '讲一讲{课文}' },
    { icon: <FormOutlined />, title: '出题练习', text: '围绕{知识点}出 5 道题' },
    { icon: <CheckSquareOutlined />, title: '错题讲解', text: '分析我的错题' },
    { icon: <RocketOutlined />, title: '学习计划', text: '给我安排{主题}学习路径' },
    { icon: <LineChartOutlined />, title: '学情解读', text: '我最近学得怎么样？' },
    { icon: <CustomerServiceOutlined />, title: '阅读伴读', text: '陪我读{篇目}' },
    { icon: <QuestionCircleOutlined />, title: '知识问答', text: '{知识点}是什么意思？' },
    { icon: <EditOutlined />, title: '自定义', text: '' },
  ],
};
