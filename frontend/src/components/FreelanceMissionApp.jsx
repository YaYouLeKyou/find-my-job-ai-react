import React from 'react';
import { AgentProvider } from '../context/AgentContext';
import { AIProvider } from '../context/AIContext';
import { UnifiedAgentApp } from '../App';

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
    />
  );
}

import { useAgent } from '../context/AgentContext';

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