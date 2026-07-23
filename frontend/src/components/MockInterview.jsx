import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Send, MessageSquare, Volume2, VolumeX, ArrowLeft, CheckCircle2, AlertCircle, Loader2, BookOpen, Target } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function MockInterview({ onBack, job, cvData, rankingEngine, customGeminiKey }) {
  const [mode, setMode] = useState('written'); // 'written' or 'voice'
  const [interviewStage, setInterviewStage] = useState('débutant');
  const [questionType, setQuestionType] = useState('technique');
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [conversation, setConversation] = useState([]);
  const [userAnswer, setUserAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [currentEvaluation, setCurrentEvaluation] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState(null);
  
  const recognitionRef = useRef(null);
  const synthesisRef = useRef(null);

  useEffect(() => {
    // Initialize speech recognition
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'fr-FR';

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setUserAnswer(transcript);
        setIsListening(false);
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        showToast('Erreur de reconnaissance vocale', 'error');
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }

    // Initialize speech synthesis
    if ('speechSynthesis' in window) {
      synthesisRef.current = window.speechSynthesis;
    }

    // Generate first question on mount
    if (job) {
      generateQuestion();
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
      if (synthesisRef.current) {
        synthesisRef.current.cancel();
      }
    };
  }, []);

  useEffect(() => {
    if (job && conversation.length === 0) {
      generateQuestion();
    }
  }, [job]);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const generateQuestion = async () => {
    if (!job) return;
    
    setLoading(true);
    setError('');
    setCurrentEvaluation(null);

    try {
      const response = await fetch(`${API_BASE}/api/mock-interview/question`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_title: job.title || job.titre || "Poste",
          job_description: job.desc || job.description || "",
          company: job.company || job.entreprise || "Entreprise",
          cv_data: cvData,
          interview_stage: interviewStage,
          question_type: questionType,
          ranking_engine: rankingEngine || "Groq / Llama 3.3",
          custom_gemini_key: customGeminiKey || null,
          lang_label: "français"
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Erreur lors de la génération de la question");
      }

      const data = await response.json();
      const question = data.question;
      
      setCurrentQuestion(question);
      setConversation(prev => [...prev, { type: 'question', content: question }]);
      
      // Speak the question in voice mode
      if (mode === 'voice' && synthesisRef.current) {
        speakText(question);
      }
    } catch (err) {
      console.error(err);
      setError(err.message);
      showToast(`❌ Erreur: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!userAnswer.trim() || !currentQuestion) return;

    setEvaluating(true);
    setError('');

    try {
      // Add user answer to conversation
      setConversation(prev => [...prev, { type: 'answer', content: userAnswer }]);

      // Evaluate the answer
      const response = await fetch(`${API_BASE}/api/mock-interview/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: currentQuestion,
          answer: userAnswer,
          job_title: job.title || job.titre || "Poste",
          job_description: job.desc || job.description || "",
          cv_data: cvData,
          ranking_engine: rankingEngine || "Groq / Llama 3.3",
          custom_gemini_key: customGeminiKey || null,
          lang_label: "français"
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Erreur lors de l'évaluation");
      }

      const data = await response.json();
      const evaluation = data.evaluation;
      
      setCurrentEvaluation(evaluation);
      setConversation(prev => [...prev, { type: 'evaluation', content: evaluation }]);
      
      // Speak evaluation in voice mode
      if (mode === 'voice' && synthesisRef.current) {
        speakText(evaluation);
      }

      setUserAnswer('');
      showToast('✅ Réponse évaluée', 'success');
    } catch (err) {
      console.error(err);
      setError(err.message);
      showToast(`❌ Erreur: ${err.message}`, 'error');
    } finally {
      setEvaluating(false);
    }
  };

  const speakText = (text) => {
    if (!synthesisRef.current) return;
    
    synthesisRef.current.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'fr-FR';
    utterance.rate = 0.9;
    utterance.pitch = 1;
    
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    
    synthesisRef.current.speak(utterance);
  };

  const stopSpeaking = () => {
    if (synthesisRef.current) {
      synthesisRef.current.cancel();
      setIsSpeaking(false);
    }
  };

  const startListening = () => {
    if (recognitionRef.current && !isListening) {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const stopListening = () => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  };

  const nextQuestion = () => {
    setCurrentEvaluation(null);
    generateQuestion();
  };

  if (!job) {
    return (
      <div className="app-container">
        <div className="main-content">
          <button onClick={onBack} className="btn btn-secondary" style={{ marginBottom: '20px' }}>
            <ArrowLeft size={16} /> Retour
          </button>
          <div className="alert alert-danger">
            Aucun poste sélectionné pour l'entretien.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}

      <div className="main-content">
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
          <button onClick={onBack} className="btn btn-secondary">
            <ArrowLeft size={16} /> Retour aux résultats
          </button>
          
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              onClick={() => setMode(mode === 'written' ? 'voice' : 'written')}
              className="btn btn-secondary"
              style={{ padding: '8px 16px' }}
            >
              {mode === 'written' ? <><Mic size={16} /> Mode Vocal</> : <><MessageSquare size={16} /> Mode Écrit</>}
            </button>
            {mode === 'voice' && isSpeaking && (
              <button onClick={stopSpeaking} className="btn btn-secondary" style={{ padding: '8px 16px' }}>
                <VolumeX size={16} /> Stop
              </button>
            )}
          </div>
        </div>

        {/* Job Info */}
        <div className="card" style={{ marginBottom: '20px', borderColor: 'rgba(124,77,255,0.2)' }}>
          <div className="card-content">
            <h3 style={{ margin: '0 0 8px 0' }}>{job.title || job.titre || 'Poste'}</h3>
            <p style={{ margin: 0, color: 'var(--text-secondary)' }}>{job.company || job.entreprise || 'Entreprise'}</p>
          </div>
        </div>

        {/* Interview Settings */}
        <div className="card" style={{ marginBottom: '20px' }}>
          <div className="card-title">
            <Target size={20} />
            <span>Paramètres de l'entretien</span>
          </div>
          <div className="card-content">
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <div className="form-group">
                <label>Niveau</label>
                <select 
                  className="select-control" 
                  value={interviewStage} 
                  onChange={(e) => setInterviewStage(e.target.value)}
                  disabled={loading}
                >
                  <option value="débutant">Débutant</option>
                  <option value="intermédiaire">Intermédiaire</option>
                  <option value="avancé">Avancé</option>
                </select>
              </div>
              <div className="form-group">
                <label>Type de question</label>
                <select 
                  className="select-control" 
                  value={questionType} 
                  onChange={(e) => setQuestionType(e.target.value)}
                  disabled={loading}
                >
                  <option value="technique">Technique</option>
                  <option value="comportemental">Comportemental</option>
                  <option value="situationnel">Situations professionnelles</option>
                </select>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                <button 
                  onClick={nextQuestion} 
                  className="btn btn-primary"
                  disabled={loading}
                  style={{ marginBottom: '8px' }}
                >
                  <BookOpen size={16} /> Nouvelle question
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && <div className="alert alert-danger"><span>{error}</span></div>}

        {/* Conversation */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '20px' }}>
          {conversation.map((msg, idx) => (
            <div key={idx} style={{
              padding: '16px',
              borderRadius: '8px',
              background: msg.type === 'question' ? 'rgba(124,77,255,0.1)' :
                         msg.type === 'answer' ? 'rgba(68,138,255,0.1)' :
                         'rgba(46,125,50,0.1)',
              border: `1px solid ${
                msg.type === 'question' ? 'rgba(124,77,255,0.2)' :
                msg.type === 'answer' ? 'rgba(68,138,255,0.2)' :
                'rgba(46,125,50,0.2)'
              }`
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                {msg.type === 'question' && <BookOpen size={16} style={{ color: '#7c4dff' }} />}
                {msg.type === 'answer' && <MessageSquare size={16} style={{ color: '#448aff' }} />}
                {msg.type === 'evaluation' && <CheckCircle2 size={16} style={{ color: '#2e7d32' }} />}
                <strong style={{ 
                  color: msg.type === 'question' ? '#7c4dff' :
                         msg.type === 'answer' ? '#448aff' :
                         '#2e7d32'
                }}>
                  {msg.type === 'question' ? 'Question' :
                   msg.type === 'answer' ? 'Votre réponse' :
                   'Évaluation'}
                </strong>
              </div>
              <p style={{ margin: 0, whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{msg.content}</p>
            </div>
          ))}
        </div>

        {/* Current Question Indicator */}
        {currentQuestion && !currentEvaluation && (
          <div className="card" style={{ marginBottom: '20px', borderColor: 'rgba(124,77,255,0.2)', background: 'rgba(124,77,255,0.05)' }}>
            <div className="card-content">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <AlertCircle size={16} style={{ color: '#7c4dff' }} />
                <strong>Question actuelle :</strong>
              </div>
              <p style={{ margin: 0, fontStyle: 'italic' }}>{currentQuestion}</p>
            </div>
          </div>
        )}

        {/* Answer Input */}
        {currentQuestion && !currentEvaluation && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <div className="card-title">
              <MessageSquare size={20} />
              <span>Votre réponse</span>
            </div>
            <div className="card-content">
              {mode === 'written' ? (
                <>
                  <textarea
                    className="textarea-control"
                    style={{ height: '150px', width: '100%', resize: 'vertical', marginBottom: '12px' }}
                    placeholder="Tapez votre réponse ici..."
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                        submitAnswer();
                      }
                    }}
                  />
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button 
                      onClick={submitAnswer}
                      className="btn btn-primary"
                      disabled={!userAnswer.trim() || evaluating}
                      style={{ flex: 1 }}
                    >
                      {evaluating ? <><Loader2 size={16} className="spin" /> Évaluation...</> : <><Send size={16} /> Envoyer (Ctrl+Enter)</>}
                    </button>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '20px' }}>
                  <button
                    onClick={isListening ? stopListening : startListening}
                    className="btn"
                    style={{
                      width: '80px',
                      height: '80px',
                      borderRadius: '50%',
                      background: isListening ? 'linear-gradient(135deg, #f44336, #d32f2f)' : 'linear-gradient(135deg, #7c4dff, #448aff)',
                      color: 'white',
                      border: 'none',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 16px',
                      animation: isListening ? 'pulse 1.5s infinite' : 'none'
                    }}
                  >
                    {isListening ? <MicOff size={32} /> : <Mic size={32} />}
                  </button>
                  <p style={{ margin: '0 0 8px 0', fontSize: '1rem', fontWeight: '600' }}>
                    {isListening ? 'Écoute en cours...' : 'Cliquez pour parler'}
                  </p>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {userAnswer || 'Votre réponse apparaîtra ici...'}
                  </p>
                  {userAnswer && (
                    <button 
                      onClick={submitAnswer}
                      className="btn btn-primary"
                      disabled={evaluating}
                      style={{ marginTop: '16px' }}
                    >
                      {evaluating ? <><Loader2 size={16} className="spin" /> Évaluation...</> : <><Send size={16} /> Envoyer la réponse</>}
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Next Question Button */}
        {currentEvaluation && (
          <div style={{ textAlign: 'center', marginTop: '24px' }}>
            <button onClick={nextQuestion} className="btn btn-primary" style={{ padding: '12px 32px' }}>
              <BookOpen size={16} /> Question suivante
            </button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Loader2 size={48} style={{ animation: 'spin 1.5s linear infinite', color: '#7c4dff' }} />
            <p style={{ marginTop: '16px', color: 'var(--text-secondary)' }}>Génération de la question...</p>
          </div>
        )}
      </div>
    </div>
  );
}