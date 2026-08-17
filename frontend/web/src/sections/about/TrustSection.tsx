import React from "react";
import SectionHeading from "../../components/SectionHeading";
import Card from "../../components/Card";

export const TrustSection: React.FC = () => {
  return (
    <section className="trust-section section-padding">
      <div className="container">
        <SectionHeading
          title="신뢰성 향상을 위한 3대 과제"
          subtitle="Gromit은 대화형 AI 정성조사의 한계를 극복하고 데이터 신뢰도를 높이기 위해 다음의 기술적 솔루션을 구현합니다."
        />

        <div className="trust-grid">
          <div className="trust-challenges-list">
            <Card variant="flat" padding="md" className="trust-challenge-card">
              <div className="challenge-num">01</div>
              <div className="challenge-content">
                <h4 className="challenge-title">대화 통제 및 턴 조율</h4>
                <p className="challenge-desc">
                  VAD(Voice Activity Detection) 2~3초 대기 시간을 적용하여 응답자의 발언 흐름을 끊지 않으면서 정밀한 턴 조율을 실현합니다. 또한, 질문이 한쪽으로 편향되거나 답을 유도하지 않도록 유도질문 방지 알고리즘이 가동됩니다.
                </p>
              </div>
            </Card>

            <Card variant="flat" padding="md" className="trust-challenge-card">
              <div className="challenge-num">02</div>
              <div className="challenge-content">
                <h4 className="challenge-title">개입 시 쿠션어 자동 주입</h4>
                <p className="challenge-desc">
                  백룸에서 관찰자인 PM이 인터뷰 흐름에 강제로 개입하여 지시어를 내릴 때, AI 아바타가 대화 맥락에 어울리는 정중한 쿠션어를 문맥상 자동으로 덧붙여 주입함으로써 대화 흐름이 매끄럽게 이어집니다.
                </p>
              </div>
            </Card>

            <Card variant="flat" padding="md" className="trust-challenge-card">
              <div className="challenge-num">03</div>
              <div className="challenge-content">
                <h4 className="challenge-title">초저지연 오디오 & 고유명사 사전</h4>
                <p className="challenge-desc">
                  네트워크 지연 현상을 차단하는 초저지연 오디오 전송 기술을 적용합니다. 브랜드명, 제품명, 신조어 등 음성인식(STT) 과정에서 혼동하기 쉬운 특수 어휘들을 명확히 정제하기 위해 고유명사 사전 모듈을 운영합니다.
                </p>
              </div>
            </Card>
          </div>

          <div className="trust-ethics-pane">
            <div className="ethics-banner">
              <div className="ethics-icon">💡</div>
              <h3 className="ethics-title">Gromit 연구 윤리 원칙</h3>
              <p className="ethics-body">
                Gromit 솔루션은 EU AI Act 50조 및 글로벌 마케팅 조사 연합체인 Insights Association의 투명성 권고 지침을 엄격히 준수합니다.
              </p>
              <div className="ethics-highlight">
                "인터뷰 진행 시, 응답자에게 AI 모더레이터 에이전트가 인터뷰를 진행하고 있다는 사실을 반드시 사전에 고지합니다."
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default TrustSection;
