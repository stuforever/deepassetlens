/**
 * 母题库分析图表面（复刻自原仓 web/app/(workspace)/mother-questions/analysis/AnalysisCharts.tsx，1:1）。
 * 技术栈替换（tupu 未装 recharts，按纪律等价呈现并记录）：
 *   recharts BarChart → MiniBars 最简 CSS 柱状图；layout="vertical" → MiniBars horizontal 横向条形图；
 *   PieChart → MiniDonut（conic-gradient 环形图）；AreaChart（录入趋势）→ MiniBars 柱状图；
 *   堆叠 BarChart（已掌握/复习中）→ MiniStacked 横向堆叠条形图；
 *   lucide-react 图标 → @ant-design/icons；next/navigation → react-router-dom；
 *   i18n key → 中文直出（原仓 zh/app.json 原文）。
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AimOutlined, AppstoreOutlined, LineChartOutlined, RiseOutlined } from '@ant-design/icons';
import { Col, Row } from 'antd';
import { MASTERY_DISPLAY, SUBJECT_COLORS, SUBJECT_DISPLAY } from './dtFields';

const PIE_COLORS = ["#f43f5e", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ec4899"];
const MUTED = '#6b7280';
const PRIMARY = '#1677ff';

/** 母题库分析各接口响应类型（字段以使用到的为准；与原仓逐字一致）。 */
export interface ComprehensiveStats {
  total: number;
  avg_difficulty: number;
  by_grade: Record<string, number>;
  by_category: Record<string, number>;
  by_difficulty: Record<string, number>;
  by_status: Record<string, number>;
}

export interface WeakPointsResponse {
  weak_points?: { knowledge_point_id: string | null; mother_count: number }[];
}

export interface TrendsResponse {
  trends?: { date: string; count: number }[];
}

export interface ErrorPatternsResponse {
  patterns?: { reason: string; count: number }[];
}

export interface ReviewPlanResponse {
  plan?: { title: string; difficulty: number; mastery_status: string }[];
}

export interface SubjectStatsResponse {
  items?: {
    subject: string;
    count: number;
    mastered: number;
    reviewing: number;
    avg_difficulty: number;
  }[];
  total_subjects?: number;
}

export interface RetentionResponse {
  avg_retention: number | null;
  reviewed_count: number;
  total_count: number;
  distribution: Record<string, number>;
  lowest_retention: {
    id: string;
    title: string;
    retention: number | null;
    stability: number | null;
    reps: number;
    lapses: number;
    state: string;
  }[];
}

/** 最简 CSS 柱状图（→ recharts BarChart；horizontal 时为横向条形图，→ layout="vertical" 的 BarChart）。 */
function MiniBars({ data, color, horizontal = false, height = 160 }: {
  data: { name: string; count: number }[];
  color: string;
  horizontal?: boolean;
  height?: number;
}) {
  const max = Math.max(...data.map((d) => d.count), 1);
  if (horizontal) {
    return (
      <div style={{ height, display: 'flex', flexDirection: 'column', justifyContent: 'space-around' }}>
        {data.map((d, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }} title={`${d.name}: ${d.count}`}>
            <span style={{ width: 60, flexShrink: 0, fontSize: 11, color: MUTED, textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.name}</span>
            <div style={{ flex: 1, height: 14, background: '#f5f5f5', borderRadius: '0 4px 4px 0', overflow: 'hidden' }}>
              <div style={{ width: `${(d.count / max) * 100}%`, height: '100%', background: color, borderRadius: '0 4px 4px 0' }} />
            </div>
          </div>
        ))}
      </div>
    );
  }
  return (
    <div style={{ height }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: height - 20, borderBottom: '1px solid #f0f0f0' }}>
        {data.map((d, i) => (
          <div key={i} style={{ flex: 1, height: '100%', display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }} title={`${d.name}: ${d.count}`}>
            <div style={{ width: '60%', minWidth: 12, height: `${Math.max(2, (d.count / max) * 100)}%`, background: color, borderRadius: '4px 4px 0 0' }} />
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        {data.map((d, i) => (
          <div key={i} style={{ flex: 1, fontSize: 11, color: MUTED, textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.name}</div>
        ))}
      </div>
    </div>
  );
}

/** 最简 CSS 环形图（→ recharts PieChart，conic-gradient 扇区 + 图例）。 */
function MiniDonut({ data, size = 160 }: { data: { name: string; count: number; color: string }[]; size?: number }) {
  const total = data.reduce((s, d) => s + d.count, 0) || 1;
  let acc = 0;
  const stops = data
    .map((d) => {
      const start = (acc / total) * 360;
      acc += d.count;
      const end = (acc / total) * 360;
      return `${d.color} ${start}deg ${end}deg`;
    })
    .join(', ');
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16, height: 250 }}>
      <div style={{ width: size, height: size, borderRadius: '50%', background: `conic-gradient(${stops})`, position: 'relative', flexShrink: 0 }}>
        <div style={{ position: 'absolute', top: '25%', right: '25%', bottom: '25%', left: '25%', background: '#fff', borderRadius: '50%' }} />
      </div>
      <div style={{ fontSize: 12, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {data.map((d, i) => (
          <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: d.color, flexShrink: 0 }} />
            {d.name}（{d.count}）
          </span>
        ))}
      </div>
    </div>
  );
}

/** 最简 CSS 横向堆叠条形图（→ recharts 堆叠 BarChart：mastered #10b981 + reviewing #f59e0b，含图例）。 */
function MiniStacked({ data, height = 250 }: { data: { name: string; mastered: number; reviewing: number }[]; height?: number }) {
  const max = Math.max(...data.map((d) => d.mastered + d.reviewing), 1);
  return (
    <div style={{ height }}>
      <div style={{ height: height - 24, display: 'flex', flexDirection: 'column', justifyContent: 'space-around' }}>
        {data.map((d, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }} title={`${d.name}: ${d.mastered} / ${d.reviewing}`}>
            <span style={{ width: 48, flexShrink: 0, fontSize: 11, color: MUTED, textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.name}</span>
            <div style={{ flex: 1, height: 14, background: '#f5f5f5', borderRadius: 4, overflow: 'hidden', display: 'flex' }}>
              <div style={{ width: `${(d.mastered / max) * 100}%`, background: '#10b981' }} />
              <div style={{ width: `${(d.reviewing / max) * 100}%`, background: '#f59e0b', borderRadius: '0 4px 4px 0' }} />
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', gap: 16, fontSize: 11, color: MUTED }}>
        <span><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: '#10b981', marginRight: 4 }} />已掌握</span>
        <span><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: '#f59e0b', marginRight: 4 }} />复习中</span>
      </div>
    </div>
  );
}

interface AnalysisChartsProps {
  stats: ComprehensiveStats | null;
  weak: WeakPointsResponse | null;
  trends: TrendsResponse | null;
  errorPatterns: ErrorPatternsResponse | null;
  reviewPlan: ReviewPlanResponse | null;
  subjectStats: SubjectStatsResponse | null;
  retentionData: RetentionResponse | null;
}

export default function MotherQuestionAnalysisCharts({
  stats,
  weak,
  trends,
  errorPatterns,
  reviewPlan,
  subjectStats,
  retentionData,
}: AnalysisChartsProps) {
  const navigate = useNavigate();

  // 数据转换（与原仓逐字一致）
  const gradeData = stats ? Object.entries(stats.by_grade || {}).map(([k, v]) => ({ name: k, count: v })) : [];
  const categoryData = stats ? Object.entries(stats.by_category || {}).map(([k, v]) => ({ name: k, count: v })) : [];
  const difficultyData = stats ? Object.entries(stats.by_difficulty || {}).map(([k, v]) => ({ name: "★".repeat(Number(k)), count: v })) : [];
  const statusData = stats ? Object.entries(stats.by_status || {}).map(([k, v]) => ({
    name: MASTERY_DISPLAY[k] || k, count: v,
  })) : [];
  const weakData = weak?.weak_points?.map((w) => ({ name: w.knowledge_point_id?.slice(0, 8) || '未挂载', count: w.mother_count })) || [];
  const trendData = trends?.trends?.map((t) => ({ date: t.date.slice(5), count: t.count })) || [];
  const patternData = errorPatterns?.patterns?.map((p) => ({ name: p.reason, count: p.count })) || [];
  const subjectData = subjectStats?.items?.map((s) => ({
    name: SUBJECT_DISPLAY[s.subject] || s.subject,
    count: s.count,
    mastered: s.mastered,
    reviewing: s.reviewing,
    avg_difficulty: s.avg_difficulty,
    color: SUBJECT_COLORS[s.subject] || "#6b7280",
  })) || [];
  const retentionDistribution = retentionData
    ? Object.entries(retentionData.distribution || {}).map(([k, v]) => ({ name: k, count: v }))
    : [];

  const cardStyle: React.CSSProperties = { padding: 16, borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff' };
  const h2Style: React.CSSProperties = { fontWeight: 600, margin: '0 0 12px' };

  return (
    <Row gutter={[24, 24]}>
      {/* 综合统计 */}
      <Col xs={24} lg={12}>
        <section style={cardStyle}>
          <h2 style={h2Style}>综合统计</h2>
          {stats ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ fontSize: 14, color: MUTED }}>母题总数</span>
                <span style={{ fontSize: 24, fontWeight: 700 }}>{stats.total}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: 16 }}>
                <span style={{ fontSize: 14, color: MUTED }}>平均难度</span>
                <span style={{ fontSize: 20, fontWeight: 600 }}>{stats.avg_difficulty}</span>
              </div>
              {gradeData.length > 0 && (
                <div style={{ height: 160, marginTop: 16 }}>
                  <div style={{ fontSize: 12, color: MUTED, marginBottom: 4 }}>年级分布</div>
                  <MiniBars data={gradeData} color="#3b82f6" height={140} />
                </div>
              )}
              {categoryData.length > 0 && (
                <div style={{ height: 160, marginTop: 16 }}>
                  <div style={{ fontSize: 12, color: MUTED, marginBottom: 4 }}>题型分布</div>
                  <MiniBars data={categoryData} color="#8b5cf6" height={140} />
                </div>
              )}
            </div>
          ) : (
            <div style={{ fontSize: 14, color: MUTED }}>加载中…</div>
          )}
        </section>
      </Col>

      {/* 掌握状态饼图 */}
      <Col xs={24} lg={12}>
        <section style={cardStyle}>
          <h2 style={h2Style}>掌握状态分布</h2>
          {statusData.length > 0 ? (
            <MiniDonut data={statusData.map((d, i) => ({ ...d, color: PIE_COLORS[i % PIE_COLORS.length] }))} />
          ) : (
            <p style={{ fontSize: 14, color: MUTED }}>暂无数据</p>
          )}
          {difficultyData.length > 0 && (
            <div style={{ height: 160, marginTop: 16 }}>
              <div style={{ fontSize: 12, color: MUTED, marginBottom: 4 }}>难度分布</div>
              <MiniBars data={difficultyData} color="#f59e0b" height={140} />
            </div>
          )}
        </section>
      </Col>

      {/* 薄弱知识点 */}
      <Col xs={24} lg={12}>
        <section style={cardStyle}>
          <h2 style={{ ...h2Style, display: 'flex', alignItems: 'center', gap: 8 }}>
            <AimOutlined style={{ color: '#f43f5e' }} /> 薄弱知识点（母题积累最多）
          </h2>
          {weakData.length > 0 ? (
            <MiniBars data={weakData} color="#f43f5e" horizontal height={250} />
          ) : (
            <p style={{ fontSize: 14, color: MUTED }}>暂无数据</p>
          )}
        </section>
      </Col>

      {/* 录入趋势 */}
      <Col xs={24} lg={12}>
        <section style={cardStyle}>
          <h2 style={{ ...h2Style, display: 'flex', alignItems: 'center', gap: 8 }}>
            <RiseOutlined style={{ color: PRIMARY }} /> 近 30 天录入趋势
          </h2>
          {trendData.length > 0 ? (
            <MiniBars data={trendData.map((t) => ({ name: t.date, count: t.count }))} color="#3b82f6" height={250} />
          ) : (
            <p style={{ fontSize: 14, color: MUTED }}>暂无数据</p>
          )}
        </section>
      </Col>

      {/* 错误模式 */}
      <Col xs={24} lg={24}>
        <section style={cardStyle}>
          <h2 style={{ ...h2Style, display: 'flex', alignItems: 'center', gap: 8 }}><AimOutlined style={{ color: '#f43f5e' }} /> 错误模式分析</h2>
          {patternData.length > 0 ? (
            <MiniBars data={patternData} color="#f43f5e" height={200} />
          ) : (
            <p style={{ fontSize: 14, color: MUTED }}>暂无数据（母题需填写错因 wrong_reason）</p>
          )}
        </section>
      </Col>

      {/* 复习计划 */}
      <Col xs={24} lg={24}>
        <section style={cardStyle}>
          <h2 style={{ ...h2Style, display: 'flex', alignItems: 'center', gap: 8 }}><RiseOutlined style={{ color: PRIMARY }} /> 复习计划（到期母题）</h2>
          {reviewPlan?.plan?.length ? (
            <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>{reviewPlan.plan.map((p, i) => (
              <li key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, borderBottom: '1px solid #f0f0f0', paddingBottom: 4 }}>
                <span style={{ flex: 1 }}>{p.title}</span>
                <span style={{ fontSize: 12, color: MUTED }}>难度{p.difficulty}</span>
                <span style={{ padding: '2px 8px', borderRadius: 4, background: '#fef3c7', color: '#b45309', fontSize: 12 }}>{p.mastery_status}</span>
              </li>
            ))}</ul>
          ) : <p style={{ fontSize: 14, color: MUTED }}>暂无到期复习</p>}
        </section>
      </Col>

      {/* 科目分布 */}
      <Col xs={24} lg={24}>
        <section style={cardStyle}>
          <h2 style={{ ...h2Style, display: 'flex', alignItems: 'center', gap: 8 }}>
            <AppstoreOutlined style={{ color: PRIMARY }} /> 科目分布
            {subjectStats?.total_subjects != null && (
              <span style={{ fontSize: 12, color: MUTED }}>共 {subjectStats.total_subjects} 个科目</span>
            )}
          </h2>
          {subjectData.length > 0 ? (
            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <div style={{ height: 260 }}>
                  <div style={{ fontSize: 12, color: MUTED, marginBottom: 4 }}>各科目母题数量</div>
                  <MiniDonut data={subjectData.map((s) => ({ name: s.name, count: s.count, color: s.color }))} size={150} />
                </div>
              </Col>
              <Col xs={24} md={12}>
                <div style={{ height: 260 }}>
                  <div style={{ fontSize: 12, color: MUTED, marginBottom: 4 }}>已掌握 / 复习中 数量</div>
                  <MiniStacked data={subjectData} height={230} />
                </div>
              </Col>
            </Row>
          ) : (
            <p style={{ fontSize: 14, color: MUTED }}>暂无数据</p>
          )}
        </section>
      </Col>

      {/* 保留率分析 */}
      <Col xs={24} lg={24}>
        <section style={cardStyle}>
          <h2 style={{ ...h2Style, display: 'flex', alignItems: 'center', gap: 8 }}>
            <LineChartOutlined style={{ color: PRIMARY }} /> 保留率分析
          </h2>
          {retentionData ? (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: 12, color: MUTED }}>平均保留率</span>
                  <span style={{ fontSize: 30, fontWeight: 700, color: PRIMARY }}>
                    {retentionData.avg_retention != null ? `${Number(retentionData.avg_retention).toFixed(1)}%` : "-"}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: 12, color: MUTED }}>已复习母题</span>
                  <span style={{ fontSize: 24, fontWeight: 600 }}>
                    {retentionData.reviewed_count ?? 0} / {retentionData.total_count ?? 0}
                  </span>
                </div>
              </div>
              {retentionDistribution.length > 0 && (
                <div style={{ height: 200, marginTop: 16 }}>
                  <div style={{ fontSize: 12, color: MUTED, marginBottom: 4 }}>保留率分布</div>
                  <MiniBars data={retentionDistribution} color="#3b82f6" height={180} />
                </div>
              )}
              {(retentionData.lowest_retention?.length ?? 0) > 0 && (
                <div>
                  <div style={{ fontSize: 12, color: MUTED, marginBottom: 4 }}>保留率最低的 10 道母题</div>
                  <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                    {retentionData.lowest_retention.map((q) => (
                      <li key={q.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, borderBottom: '1px solid #f0f0f0', paddingBottom: 4 }}>
                        <button
                          onClick={() => navigate(`/e/sishu/admin/mother-questions/${q.id}`)}
                          onMouseEnter={(e) => { e.currentTarget.style.color = PRIMARY; e.currentTarget.style.textDecoration = 'underline'; }}
                          onMouseLeave={(e) => { e.currentTarget.style.color = 'inherit'; e.currentTarget.style.textDecoration = 'none'; }}
                          style={{ flex: 1, textAlign: 'left', cursor: 'pointer', border: 'none', background: 'none', padding: 0, color: 'inherit', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 14 }}
                        >
                          {q.title}
                        </button>
                        <span style={{ fontSize: 12, color: MUTED, flexShrink: 0 }}>
                          保留率 {q.retention != null ? Number(q.retention).toFixed(1) : "-"}%
                        </span>
                        <span style={{ fontSize: 12, color: MUTED, flexShrink: 0 }}>稳定度 {q.stability ?? "-"}</span>
                        <span style={{ fontSize: 12, color: MUTED, flexShrink: 0 }}>复习 {q.reps ?? 0} 次</span>
                        <span style={{ fontSize: 12, color: MUTED, flexShrink: 0 }}>遗忘 {q.lapses ?? 0} 次</span>
                        <span style={{ padding: '2px 8px', borderRadius: 4, background: '#f3f4f6', fontSize: 12, flexShrink: 0 }}>{q.state}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p style={{ fontSize: 14, color: MUTED }}>加载中…</p>
          )}
        </section>
      </Col>
    </Row>
  );
}
