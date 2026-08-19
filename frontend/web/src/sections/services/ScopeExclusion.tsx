import React from "react";
import Card from "../../components/Card";

export const ScopeExclusion: React.FC = () => {
  return (
    <section className="scope-exclusion-section section-padding">
      <div className="container">
        <Card variant="flat" padding="lg" className="exclusion-banner-card">
          <div className="exclusion-icon-container">
            <span className="exclusion-icon">ℹ</span>
          </div>
          <div className="exclusion-content-container">
            <h4 className="exclusion-title">데모 환경 및 제외 범위 안내</h4>
            <p className="exclusion-text">
              현재 확인하고 계시는 포털 사이트는 <strong>팀 공유 및 평가를 위한 비전 프로토타입 데모 환경</strong>입니다. 
              상기 정성 인터뷰 연동 룸 구조와 리포트 분석, 텍스트 스크립트 Word/PDF 파일 다운로드 등은 백엔드와 연동되지 않은 
              <strong>100% 목업(Mock) 더미 데이터</strong>로 작동하며, 실제 데이터를 생성 또는 전송하지 않습니다.
            </p>
            <p className="exclusion-subtext">
              본 구조는 차후 실 개발 연동 결정을 고려하여, 백엔드 설계에 용이하도록 `mock/analysis.ts` 등 데이터 스펙 초안을 분리한 컴포넌트 단위로 격리 제작되었습니다.
            </p>
          </div>
        </Card>
      </div>
    </section>
  );
};

export default ScopeExclusion;
