import React from 'react';
import ReactDOM from 'react-dom/client';
import MockInterview from './components/MockInterview';

// Read job data from sessionStorage
const jobData = sessionStorage.getItem('mockInterviewJob');
const cvData = sessionStorage.getItem('mockInterviewCvData');

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <React.StrictMode>
        <MockInterview
            onBack={() => {
                window.close();
            }}
            job={jobData ? JSON.parse(jobData) : null}
            cvData={cvData ? JSON.parse(cvData) : null}
            rankingEngine="Groq / Llama 3.3"
            customGeminiKey={null}
        />
    </React.StrictMode>
);