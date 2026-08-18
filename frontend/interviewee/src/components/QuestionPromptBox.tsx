interface QuestionPromptBoxProps {
  question: string;
}

export default function QuestionPromptBox({ question }: QuestionPromptBoxProps) {
  return (
    <section className="question-prompt-box">
      <div className="question-box">
        <p className="question-bubble">
          {question || "평소 업무나 일상에서 AI 도구를 얼마나 자주 사용하시나요? 어떤 상황에서 가장 유용하다고 느끼셨는지 말씀해 주세요."}
        </p>
      </div>
    </section>
  );
}
