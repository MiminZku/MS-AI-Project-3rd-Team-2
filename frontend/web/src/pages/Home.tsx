import React from "react";
import WaveMeetHero from "../sections/home/WaveMeetHero";
import Hero from "../sections/home/Hero";
import ProblemSection from "../sections/home/ProblemSection";
import SolutionSection from "../sections/home/SolutionSection";
import DifferentiatorSection from "../sections/home/DifferentiatorSection";
import HowItWorksSection from "../sections/home/HowItWorksSection";
import CtaSection from "../sections/home/CtaSection";

export const Home: React.FC = () => {
  return (
    <div className="home-page">
      <WaveMeetHero />
      <Hero />
      <ProblemSection />
      <SolutionSection />
      <DifferentiatorSection />
      <HowItWorksSection />
      <CtaSection />
    </div>
  );
};

export default Home;
