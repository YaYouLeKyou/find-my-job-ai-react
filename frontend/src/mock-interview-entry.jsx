import React from 'react';
import ReactDOM from 'react-dom/client';
import MockInterview from './components/MockInterview';
import './index.css';

// ─── Read job data from sessionStorage (with error handling) ─────────────────
let jobData = null;
let cvData = null;
let parseError = null;

try {
  const rawJob = sessionStorage.getItem('mockInterviewJob');
  const rawCv = sessionStorage.getItem('mockInterviewCvData');

  if (rawJob) {
    jobData = JSON.parse(rawJob);
  }
  if (rawCv) {
    cvData = JSON.parse(rawCv);
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
      rankingEngine="Groq / Llama 3.3"
      customGeminiKey={null}
      parseError={parseError}
    />
  </React.StrictMode>
);
