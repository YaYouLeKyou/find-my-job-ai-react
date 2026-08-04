import React from 'react';
import { AgentProvider } from '../context/AgentContext';
import { AIProvider } from '../context/AIContext';
import { UnifiedAgentApp } from '../App';
import RecruiterCvAnalyzer from './RecruiterCvAnalyzer';

export default function WorkerApp({ onBackToHub, lang, setLang }) {
  return (
    <AgentProvider>
      <AIProvider>
        <UnifiedAgentApp
          onBackToHub={onBackToHub}
          lang={lang}
          setLang={setLang}
          CvAnalyzer={RecruiterCvAnalyzer}
        />
      </AIProvider>
    </AgentProvider>
  );
}