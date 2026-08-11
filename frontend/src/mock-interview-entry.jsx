import React from 'react';
import ReactDOM from 'react-dom/client';
import MockInterview from './components/MockInterview';
import './index.css';

// ─── Read data from sessionStorage (with error handling) ─────────────────
let jobData = null;
let cvData = null;
let parseError = null;
let rankingEngine = "Groq / Llama 3.3";
let customGeminiKey = null;

try {
  const rawJob = sessionStorage.getItem('mockInterviewJob');
  const rawCv = sessionStorage.getItem('mockInterviewCvData');
  const rawRankingEngine = sessionStorage.getItem('mockInterviewRankingEngine');
  const rawCustomGeminiKey = sessionStorage.getItem('mockInterviewCustomGeminiKey');

  if (rawJob) {
    jobData = JSON.parse(rawJob);
  }
  if (rawCv) {
    cvData = JSON.parse(rawCv);
  }
  if (rawRankingEngine) {
    rankingEngine = rawRankingEngine;
  }
  if (rawCustomGeminiKey) {
    customGeminiKey = rawCustomGeminiKey;
  }
} catch (err) {
  console.error('Erreur parsing sessionStorage:', err);
  parseError = err.message;
}

// ─── Render MockInterview ────────────────────────────────────────────────────
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <MockInterview
      onBack={() => window.close()}
      job={jobData}
      cvData={cvData}
      rankingEngine={rankingEngine}
      customGeminiKey={customGeminiKey}
      parseError={parseError}
    />
  </React.StrictMode>
);
