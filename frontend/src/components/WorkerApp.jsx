import React from 'react';
import { AgentProvider } from '../context/AgentContext';
import { AIProvider } from '../context/AIContext';
import { UnifiedAgentApp } from '../App';

export default function WorkerApp({ onBackToHub, lang, setLang }) {
  return (
    <AgentProvider>
      <AIProvider>
        <UnifiedAgentApp 
          onBackToHub={onBackToHub} 
          lang={lang} 
          setLang={setLang} 
        />
      </AIProvider>
    </AgentProvider>
  );
}