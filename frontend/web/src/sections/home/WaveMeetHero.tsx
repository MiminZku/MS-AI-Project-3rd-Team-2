import React from "react";

export const WaveMeetHero: React.FC = () => {
  return (
    <section className="wave-meet-hero-section">
      <div className="container wave-meet-container">
        
        {/* Copy block with 11-2 copy exactly */}
        <div className="wave-hero-copy">
          <div className="copy-line-large">인사이트를 만나다.</div>
          <div className="copy-line-large">니즈를 만나다.</div>
          <div className="copy-line-small">
            그 사이, <span className="copy-brand-text">Gromit</span>.
          </div>
        </div>

        {/* Waveform line-art illustration */}
        <div className="wave-hero-illustration">
          <svg className="wave-svg" viewBox="0 0 1000 600" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Left Voice Wave: Market Insight / Respondent (var(--color-accent)) */}
            <g className="wave-left-group">
              {/* Secondary wave for depth */}
              <path 
                d="M 0 300 Q 75 300 150 300 T 300 260 T 400 370 T 470 240 T 520 340 T 570 300" 
                stroke="var(--color-accent)" 
                strokeWidth="1.5" 
                strokeLinecap="round"
                opacity="0.3" 
              />
              {/* Main wave */}
              <path 
                d="M 0 300 Q 75 300 150 300 T 270 230 T 370 390 T 450 180 T 510 380 T 560 300" 
                stroke="var(--color-accent)" 
                strokeWidth="3" 
                strokeLinecap="round"
              />
            </g>

            {/* Right Voice Wave: Client Needs (rgba(255, 255, 255, 0.4)) */}
            <g className="wave-right-group">
              {/* Secondary wave for depth */}
              <path 
                d="M 1000 300 Q 925 300 850 300 T 700 340 T 600 230 T 530 360 T 480 260 T 430 300" 
                stroke="rgba(255, 255, 255, 0.4)" 
                strokeWidth="1.5" 
                strokeLinecap="round"
                opacity="0.2" 
              />
              {/* Main wave */}
              <path 
                d="M 1000 300 Q 925 300 850 300 T 730 370 T 630 210 T 550 420 T 490 220 T 440 300" 
                stroke="rgba(255, 255, 255, 0.4)" 
                strokeWidth="3" 
                strokeLinecap="round"
              />
            </g>
          </svg>

          {/* Gromit wordmark positioned in the dead center overlap area */}
          <div className="wave-wordmark-container">
            <span className="wave-glow-wordmark">Gromit</span>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="scroll-indicator">
          <span className="scroll-indicator-text">스크롤하여 시작하기</span>
          <div className="scroll-indicator-arrow">↓</div>
        </div>

      </div>
    </section>
  );
};

export default WaveMeetHero;
