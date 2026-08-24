import { ChartBar, FileArrowUp, Headphones, UsersThree } from "@phosphor-icons/react";

const capabilities = [
  { icon: FileArrowUp, title: "Guide to structure", text: "가이드 문서를 질문 흐름으로 정리해 조사 준비 시간을 줄입니다." },
  { icon: Headphones, title: "Interview operations", text: "진행 상황과 인터뷰 흐름을 한곳에서 보고 필요한 순간에만 개입합니다." },
  { icon: ChartBar, title: "Evidence to decision", text: "대화 속 근거를 반복 신호로 묶어 팀이 함께 읽을 수 있게 합니다." },
  { icon: UsersThree, title: "Shared workspace", text: "프로젝트·세션·산출물을 같은 맥락 안에서 공유합니다." },
];

export default function ResearchCapabilities() {
  return (
    <section className="research-capabilities container">
      <div className="research-section-heading">
        <p className="research-eyebrow">One research flow</p>
        <h2>조사의 전 과정을<br />흐트러지지 않게.</h2>
      </div>
      <div className="research-capabilities__grid">
        {capabilities.map((capability) => {
          const Icon = capability.icon;
          return (
            <article className="research-capabilities__card" key={capability.title}>
              <span><Icon size={25} weight="duotone" /></span>
              <h3>{capability.title}</h3>
              <p>{capability.text}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
