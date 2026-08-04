import React from 'react';
import { AgentProvider, useAgent } from '../context/AgentContext';
import { AIProvider } from '../context/AIContext';
import { UnifiedAgentApp } from '../App';
import FreelanceCvAnalyzer from './FreelanceCvAnalyzer';

function FreelanceAgentWrapper({ onBackToHub, lang, setLang }) {
  const { setActiveAgent } = useAgent();

  React.useEffect(() => {
    setActiveAgent('freelance');
  }, [setActiveAgent]);

  return (
    <UnifiedAgentApp
      onBackToHub={onBackToHub}
      lang={lang}
      setLang={setLang}
      CvAnalyzer={FreelanceCvAnalyzer}
    />
  );
}

export default function FreelanceMissionApp({ onBackToHub, lang, setLang }) {
  return (
    <AgentProvider>
      <AIProvider>
        <FreelanceAgentWrapper
          onBackToHub={onBackToHub}
          lang={lang}
          setLang={setLang}
        />
      </AIProvider>
    </AgentProvider>
  );
}
