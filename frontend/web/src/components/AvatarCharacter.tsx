import React from "react";

interface AvatarCharacterProps {
  variant: 1 | 2 | 3 | 4;
  className?: string;
  size?: number | string;
}

export const AvatarCharacter: React.FC<AvatarCharacterProps> = ({
  variant,
  className = "",
  size = 64,
}) => {
  const getAvatarContent = () => {
    switch (variant) {
      case 1:
        // 김은향: Round face + Circular glasses + Cute cap/hair
        return (
          <>
            {/* Background circle */}
            <circle cx="50" cy="50" r="46" fill="var(--color-surface)" stroke="var(--color-accent)" strokeWidth="2" />
            {/* Hair/Cap background */}
            <path d="M 25,50 A 25,25 0 0 1 75,50 Z" fill="var(--color-text)" opacity="0.15" />
            {/* Face/Head */}
            <circle cx="50" cy="53" r="18" fill="var(--color-bg)" stroke="var(--color-text)" strokeWidth="1.5" />
            {/* Glasses */}
            <circle cx="43" cy="51" r="5" fill="none" stroke="var(--color-accent)" strokeWidth="1.5" />
            <circle cx="57" cy="51" r="5" fill="none" stroke="var(--color-accent)" strokeWidth="1.5" />
            <line x1="48" y1="51" x2="52" y2="51" stroke="var(--color-accent)" strokeWidth="1.5" />
            {/* Smile */}
            <path d="M 46,60 Q 50,64 54,60" fill="none" stroke="var(--color-text)" strokeWidth="1.5" strokeLinecap="round" />
            {/* Designer Hat/Cap */}
            <path d="M 32,38 Q 50,30 68,38 L 50,32 Z" fill="var(--color-accent)" />
          </>
        );
      case 2:
        // 장다희: Square/Neat face + Square glasses + Professional hair
        return (
          <>
            <circle cx="50" cy="50" r="46" fill="var(--color-surface)" stroke="var(--color-accent)" strokeWidth="2" />
            {/* Neat Hair */}
            <path d="M 30,35 L 70,35 L 70,45 L 30,45 Z" fill="var(--color-text)" opacity="0.15" />
            {/* Face/Head */}
            <rect x="33" y="38" width="34" height="30" rx="6" fill="var(--color-bg)" stroke="var(--color-text)" strokeWidth="1.5" />
            {/* Square Glasses */}
            <rect x="38" y="44" width="8" height="8" rx="1" fill="none" stroke="var(--color-accent)" strokeWidth="1.5" />
            <rect x="54" y="44" width="8" height="8" rx="1" fill="none" stroke="var(--color-accent)" strokeWidth="1.5" />
            <line x1="46" y1="48" x2="54" y2="48" stroke="var(--color-accent)" strokeWidth="1.5" />
            {/* Smile */}
            <line x1="46" y1="58" x2="54" y2="58" stroke="var(--color-text)" strokeWidth="1.5" strokeLinecap="round" />
            {/* Top Tie decoration */}
            <circle cx="50" cy="34" r="3" fill="var(--color-accent)" />
          </>
        );
      case 3:
        // 박성은: Creative Hexagonal face + Tech headset
        return (
          <>
            <circle cx="50" cy="50" r="46" fill="var(--color-surface)" stroke="var(--color-accent)" strokeWidth="2" />
            {/* Face/Head */}
            <path d="M 50,32 L 67,42 L 67,60 L 50,70 L 33,60 L 33,42 Z" fill="var(--color-bg)" stroke="var(--color-text)" strokeWidth="1.5" />
            {/* Headset arc */}
            <path d="M 30,50 A 20,20 0 0 1 70,50" fill="none" stroke="var(--color-accent)" strokeWidth="3" strokeLinecap="round" />
            {/* Earcups */}
            <rect x="27" y="45" width="6" height="12" rx="2" fill="var(--color-accent)" />
            <rect x="67" y="45" width="6" height="12" rx="2" fill="var(--color-accent)" />
            {/* Eyes */}
            <circle cx="43" cy="48" r="2" fill="var(--color-text)" />
            <circle cx="57" cy="48" r="2" fill="var(--color-text)" />
            {/* Smile */}
            <path d="M 45,56 Q 50,60 55,56" fill="none" stroke="var(--color-text)" strokeWidth="1.5" strokeLinecap="round" />
          </>
        );
      case 4:
        // 강민기: Rounded face + Coding Glasses + Hoodie/Tech gear
        return (
          <>
            <circle cx="50" cy="50" r="46" fill="var(--color-surface)" stroke="var(--color-accent)" strokeWidth="2" />
            {/* Hoodie triangle shape */}
            <path d="M 22,72 L 50,30 L 78,72 Z" fill="var(--color-text)" opacity="0.1" />
            {/* Face/Head */}
            <circle cx="50" cy="54" r="16" fill="var(--color-bg)" stroke="var(--color-text)" strokeWidth="1.5" />
            {/* Coding Glasses (Sleek rects) */}
            <rect x="39" y="49" width="9" height="6" rx="1" fill="none" stroke="var(--color-accent)" strokeWidth="1.5" />
            <rect x="52" y="49" width="9" height="6" rx="1" fill="none" stroke="var(--color-accent)" strokeWidth="1.5" />
            <line x1="48" y1="52" x2="52" y2="52" stroke="var(--color-accent)" strokeWidth="1.5" />
            {/* Smile */}
            <path d="M 47,61 Q 50,64 53,61" fill="none" stroke="var(--color-text)" strokeWidth="1.5" strokeLinecap="round" />
            {/* Top Node */}
            <circle cx="50" cy="30" r="4" fill="var(--color-accent)" />
          </>
        );
      default:
        return null;
    }
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      className={`avatar-character ${className}`}
      style={{ display: "inline-block", verticalAlign: "middle" }}
    >
      {getAvatarContent()}
    </svg>
  );
};

export default AvatarCharacter;
