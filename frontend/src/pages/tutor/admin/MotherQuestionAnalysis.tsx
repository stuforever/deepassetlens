/**
 * 错题分析页（复刻自原仓 web/app/(workspace)/mother-questions/analysis/page.tsx，1:1）。
 * 技术栈替换：next/navigation → react-router-dom；next/dynamic 懒加载（ssr:false）→ 静态 import；
 * lucide-react → @ant-design/icons；i18n key → 中文直出（原仓 zh/app.json 原文）；
 * fetch(apiUrl("/api/v1/...")) → fetch('/api/v1/...')（路径/参数逐字一致）。
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeftOutlined, BarChartOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import MotherQuestionAnalysisCharts from './MotherQuestionAnalysisCharts';
import type {
  ComprehensiveStats,
  WeakPointsResponse,
  TrendsResponse,
  ErrorPatternsResponse,
  ReviewPlanResponse,
  SubjectStatsResponse,
  RetentionResponse,
} from './MotherQuestionAnalysisCharts';

export default function MotherQuestionAnalysis() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<ComprehensiveStats | null>(null);
  const [weak, setWeak] = useState<WeakPointsResponse | null>(null);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [errorPatterns, setErrorPatterns] = useState<ErrorPatternsResponse | null>(null);
  const [reviewPlan, setReviewPlan] = useState<ReviewPlanResponse | null>(null);
  const [subjectStats, setSubjectStats] = useState<SubjectStatsResponse | null>(null);
  const [retentionData, setRetentionData] = useState<RetentionResponse | null>(null);

  useEffect(() => {
    fetch('/api/v1/mother-questions/analysis/comprehensive-stats').then((r) => r.json()).then(setStats);
    fetch('/api/v1/mother-questions/analysis/weak-points').then((r) => r.json()).then(setWeak);
    fetch('/api/v1/mother-questions/analysis/trends?days=30').then((r) => r.json()).then(setTrends);
    fetch('/api/v1/mother-questions/analysis/error-patterns').then((r) => r.json()).then(setErrorPatterns);
    fetch('/api/v1/mother-questions/reviews/plan').then((r) => r.json()).then(setReviewPlan);
    fetch('/api/v1/mother-questions/analysis/by-subject').then((r) => r.json()).then(setSubjectStats);
    fetch('/api/v1/mother-questions/analysis/retention').then((r) => r.json()).then(setRetentionData);
  }, []);

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 24 }} data-testid="mq-analysis-page">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined style={{ fontSize: 20 }} />}
          onClick={() => navigate('/e/tutor/admin/mother-questions')}
          data-testid="mq-back-btn"
        />
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: 8 }} data-testid="mq-analysis-title">
          <BarChartOutlined style={{ fontSize: 24, color: '#1677ff' }} /> 母题库分析
        </h1>
      </div>

      <MotherQuestionAnalysisCharts
        stats={stats}
        weak={weak}
        trends={trends}
        errorPatterns={errorPatterns}
        reviewPlan={reviewPlan}
        subjectStats={subjectStats}
        retentionData={retentionData}
      />
    </div>
  );
}
