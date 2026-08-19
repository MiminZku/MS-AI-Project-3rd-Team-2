import React from "react";
import Card from "../Card";
import { mockAnalysisReport } from "../../mock/analysis";

export const AnalysisDashboardPreview: React.FC = () => {
  const { summaryCards, keyTopics, quotes, satisfactionData } = mockAnalysisReport;

  // Donut chart calculations for sentiment breakdown (from keyTopics or predefined)
  // Positive: 18 (topic-1) + 8 (topic-4) = 26
  // Neutral: 6 (topic-5) = 6
  // Negative: 12 (topic-2) + 9 (topic-3) = 21
  // Total: 53
  const totalTopicHits = 53;
  const positivePct = Math.round((26 / totalTopicHits) * 100);
  const neutralPct = Math.round((6 / totalTopicHits) * 100);
  const negativePct = 100 - positivePct - neutralPct;

  // Donut SVG parameters
  const radius = 50;
  const circumference = 2 * Math.PI * radius; // ~314.16
  const strokeWidth = 14;

  const posStrokeDash = (positivePct / 100) * circumference;
  const neuStrokeDash = (neutralPct / 100) * circumference;
  const negStrokeDash = (negativePct / 100) * circumference;

  return (
    <Card variant="default" padding="lg" className="analysis-dashboard-preview">
      <h3 className="report-block-title" style={{ marginBottom: "var(--space-6)" }}>
        조사 결과 분석 대시보드
      </h3>

      {/* Summary Cards Row */}
      <div className="report-summary-cards">
        {summaryCards.map((card, idx) => (
          <div key={idx} className="report-summary-card">
            <h4 className="summary-card-title">{card.title}</h4>
            <p className="summary-card-content">{card.content}</p>
          </div>
        ))}
      </div>

      {/* Grid: SVG Charts & Key Topics */}
      <div className="report-dashboard-grid">
        {/* Charts block */}
        <div className="charts-block">
          <h4 className="dashboard-sub-title">핵심 메트릭 분석</h4>
          
          <div className="charts-flex-container">
            {/* SVG Donut Chart (Sentiment) */}
            <div className="donut-chart-container">
              <span className="chart-label">감정 분포도</span>
              <svg width="150" height="150" viewBox="0 0 150 150">
                <circle cx="75" cy="75" r={radius} fill="transparent" stroke="#e8e8ed" strokeWidth={strokeWidth} />
                
                {/* Positive (Blue/Green Accent) */}
                <circle
                  cx="75"
                  cy="75"
                  r={radius}
                  fill="transparent"
                  stroke="var(--color-accent)"
                  strokeWidth={strokeWidth}
                  strokeDasharray={`${posStrokeDash} ${circumference}`}
                  transform="rotate(-90 75 75)"
                />
                
                {/* Negative (Red Muted) */}
                <circle
                  cx="75"
                  cy="75"
                  r={radius}
                  fill="transparent"
                  stroke="#ff5f56"
                  strokeWidth={strokeWidth}
                  strokeDasharray={`${negStrokeDash} ${circumference}`}
                  strokeDashoffset={-posStrokeDash}
                  transform="rotate(-90 75 75)"
                />

                {/* Neutral (Gray) */}
                <circle
                  cx="75"
                  cy="75"
                  r={radius}
                  fill="transparent"
                  stroke="#a0a0a0"
                  strokeWidth={strokeWidth}
                  strokeDasharray={`${neuStrokeDash} ${circumference}`}
                  strokeDashoffset={-(posStrokeDash + negStrokeDash)}
                  transform="rotate(-90 75 75)"
                />
                
                {/* Center text */}
                <text x="75" y="80" textAnchor="middle" fontSize="16" fontWeight="bold" fill="var(--color-text)">
                  {positivePct}%
                </text>
                <text x="75" y="98" textAnchor="middle" fontSize="10" fill="var(--color-text-muted)">
                  긍정적 답변
                </text>
              </svg>
              <div className="chart-legend">
                <span className="legend-item"><span className="legend-dot positive"></span>긍정 {positivePct}%</span>
                <span className="legend-item"><span className="legend-dot negative"></span>부정 {negativePct}%</span>
                <span className="legend-item"><span className="legend-dot neutral"></span>중립 {neutralPct}%</span>
              </div>
            </div>

            {/* SVG Bar Chart (Satisfaction) */}
            <div className="bar-chart-container">
              <span className="chart-label">요소별 만족도 점수 (100점 만점)</span>
              <svg width="240" height="150" viewBox="0 0 240 150">
                {satisfactionData.map((data, idx) => {
                  const barHeight = (data.score / 100) * 110;
                  const xPos = 10 + idx * 46;
                  const yPos = 120 - barHeight;
                  return (
                    <g key={idx}>
                      {/* Bar */}
                      <rect
                        x={xPos}
                        y={yPos}
                        width="24"
                        height={barHeight}
                        fill={data.score >= 80 ? "var(--color-accent)" : data.score >= 60 ? "#86868b" : "#ff5f56"}
                        rx="4"
                      />
                      {/* Score label */}
                      <text x={xPos + 12} y={yPos - 6} textAnchor="middle" fontSize="9" fontWeight="bold" fill="var(--color-text)">
                        {data.score}
                      </text>
                      {/* Category label */}
                      <text x={xPos + 12} y="136" textAnchor="middle" fontSize="8" fill="var(--color-text-muted)">
                        {data.category}
                      </text>
                    </g>
                  );
                })}
                {/* Base line */}
                <line x1="5" y1="120" x2="235" y2="120" stroke="var(--color-border)" strokeWidth="1" />
              </svg>
            </div>
          </div>
        </div>

        {/* Topics List */}
        <div className="topics-block">
          <h4 className="dashboard-sub-title">주요 언급 주제 태그 (언급 빈도)</h4>
          <div className="topic-tags-list">
            {keyTopics.map((topic) => (
              <div key={topic.id} className={`topic-tag-card sentiment-${topic.sentiment}`}>
                <span className="topic-name">{topic.topic}</span>
                <span className="topic-count">{topic.count}회 언급</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Respondent Highlight Quotes */}
      <div className="report-quotes-block" style={{ marginTop: "var(--space-6)" }}>
        <h4 className="dashboard-sub-title" style={{ marginBottom: "var(--space-4)" }}>
          핵심 응답자 인용문 (Highlight Quotes)
        </h4>
        <div className="quotes-grid">
          {quotes.map((quote) => (
            <div key={quote.id} className={`quote-card sentiment-${quote.sentiment}`}>
              <div className="quote-icon">“</div>
              <p className="quote-text">{quote.quote}</p>
              <div className="quote-meta">
                <span className="quote-speaker">{quote.speaker}</span>
                <span className="quote-time">{quote.timestamp} 발화</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
};

export default AnalysisDashboardPreview;
