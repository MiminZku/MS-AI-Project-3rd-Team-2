import React from "react";
import SectionHeading from "../../components/SectionHeading";
import Card from "../../components/Card";

export const DifferentiatorSection: React.FC = () => {
  return (
    <section className="differentiator-section section-padding">
      <div className="container">
        <SectionHeading
          title="Gromit만의 독보적인 차별점"
          subtitle="실시간 관찰, 동시통역, 즉각 개입의 세 가지 핵심 기능 결합은 오직 Gromit에서만 가능합니다."
          align="center"
        />

        <div className="differentiator-content-grid">
          <div className="diff-desc-pane">
            <h3 className="diff-headline">
              "실시간 백룸 참관 + 라이브 동시통역 + 즉각 개입"의 시너지
            </h3>
            <p className="diff-body-text">
              글로벌 탑티어 정성조사 에이전시 및 AI 플랫폼들(Conveo, Outset 등)도 일부 개별 기능은 지원하지만, 
              <strong>실시간 참관 및 라이브 동시통역과 즉각적 질문 개입 기능의 통합</strong>은 아직 구현되지 않은 독자적 조합입니다.
            </p>
            <p className="diff-body-text">
              Gromit은 비개발 참관자들도 쉽게 다국어 인터뷰를 참관하고, 그 자리에서 바로 인터뷰 방향을 유도함으로써 정성조사의 질을 극대화합니다.
            </p>
          </div>

          <div className="diff-matrix-pane">
            <Card variant="default" padding="md">
              <table className="comparison-table">
                <thead>
                  <tr>
                    <th>핵심 기능 조합</th>
                    <th className="highlight-column">Gromit</th>
                    <th>기타 글로벌 AI 플랫폼</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>AI 자동 인터뷰 진행</td>
                    <td className="highlight-column text-center">✔</td>
                    <td className="text-center">✔</td>
                  </tr>
                  <tr>
                    <td>실시간 백룸(참관) 화면 제공</td>
                    <td className="highlight-column text-center">✔</td>
                    <td className="text-center">일부 제공</td>
                  </tr>
                  <tr>
                    <td>라이브 다국어 동시통역</td>
                    <td className="highlight-column text-center">✔</td>
                    <td className="text-center">❌</td>
                  </tr>
                  <tr>
                    <td>실시간 즉각 개입 및 유도</td>
                    <td className="highlight-column text-center">✔</td>
                    <td className="text-center">❌</td>
                  </tr>
                </tbody>
              </table>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
};

export default DifferentiatorSection;
