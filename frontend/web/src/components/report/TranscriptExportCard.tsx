import React, { useState } from "react";
import Card from "../Card";
import Button from "../Button";
import { mockTranscript } from "../../mock/transcript";

export const TranscriptExportCard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"ko" | "en">("ko");

  const handleDownload = (format: string) => {
    alert(`[데모 안내] ${format} 다운로드 기능은 실제 백엔드 연동 및 파일 생성 서버 구축 후 지원될 예정입니다.`);
  };

  return (
    <Card variant="default" padding="lg" className="transcript-export-card">
      <div className="card-header-actions">
        <h3 className="report-block-title">인터뷰 트랜스크립트 미리보기</h3>
        <div className="download-buttons">
          <Button variant="secondary" size="sm" onClick={() => handleDownload("Word")}>
            Word 다운로드
          </Button>
          <Button variant="secondary" size="sm" onClick={() => handleDownload("PDF")}>
            PDF 다운로드
          </Button>
        </div>
      </div>

      <div className="tab-buttons-container">
        <button
          className={`tab-btn ${activeTab === "ko" ? "active" : ""}`}
          onClick={() => setActiveTab("ko")}
        >
          원문 스크립트 (KO)
        </button>
        <button
          className={`tab-btn ${activeTab === "en" ? "active" : ""}`}
          onClick={() => setActiveTab("en")}
        >
          번역본 스크립트 (EN)
        </button>
      </div>

      <div className="transcript-scroll-area">
        {mockTranscript.map((turn) => (
          <div key={turn.id} className={`transcript-bubble ${turn.speaker}`}>
            <div className="bubble-meta">
              <span className="bubble-speaker">{turn.speakerName}</span>
              <span className="bubble-time">{turn.timestamp}</span>
            </div>
            <div className="bubble-text">
              {activeTab === "ko" ? turn.originalText : turn.translatedText}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};

export default TranscriptExportCard;
