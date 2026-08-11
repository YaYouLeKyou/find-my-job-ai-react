import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Mic, MicOff, Send, MessageSquare, VolumeX, ArrowLeft,
  CheckCircle2, AlertCircle, Loader2, BookOpen, Target,
  Copy, Download, RefreshCw, Sun, Moon, Sparkles, ChevronRight
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function MockInterview({ onBack, job, cvData, rankingEngine, customGeminiKey, parseError }) {
  const [mode, setMode] = useState('written');
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [currentEvaluation, setCurrentEvaluation] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState(null);
  const [darkMode, setDarkMode] = useState(false);
  const [questionCount, setQuestionCount] = useState(0);
  const [answeredCount, setAnsweredCount] = useState(0);
  const [scores, setScores] = useState([]);
  const [interviewStage, setInterviewStage] = useState('intermédiaire');
  const [questionType, setQuestionType] = useState('mixte');

  const recognitionRef = useRef(null);
  const synthesisRef = useRef(null);

  const avgScore = scores.length > 0
    ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
    : 0;

  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  useEffect(() => {
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
      recognitionRef.current.onerror = () => {
        setIsListening(false);
        showToast('Erreur de reconnaissance vocale', 'error');
      };
      recognitionRef.current.onend = () => setIsListening(false);
    }
    if ('speechSynthesis' in window) {
      synthesisRef.current = window.speechSynthesis;
    }
    const savedDark = localStorage.getItem('mockInterviewDarkMode');
    if (savedDark === 'true') {
      setDarkMode(true);
      document.documentElement.setAttribute('data-theme', 'dark');
    }
    return () => {
      if (recognitionRef.current) recognitionRef.current.abort();
      if (synthesisRef.current) synthesisRef.current.cancel();
    };
  }, []);

  const toggleDarkMode = () => {
    const newDark = !darkMode;
    setDarkMode(newDark);
    localStorage.setItem('mockInterviewDarkMode', String(newDark));
    if (newDark) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      showToast('✅ Copié !', 'success');
    } catch {
      showToast('Erreur de copie', 'error');
    }
  };

  const exportConversation = () => {
    if (!currentQuestion && !currentEvaluation) {
      showToast('Aucune conversation à exporter', 'warning');
      return;
    }
    const lines = [];
    lines.push(`=== Simulation d'Entretien - Job Bridge ===`);
    lines.push(`Poste : ${job?.title || job?.titre || 'N/A'}`);
    lines.push(`Entreprise : ${job?.company || job?.entreprise || 'N/A'}`);
    lines.push(`Date : ${new Date().toLocaleString('fr-FR')}`);
    lines.push(`Questions répondues : ${answeredCount}/${questionCount}`);
    lines.push(`Score moyen : ${avgScore > 0 ? `${avgScore}/10` : 'N/A'}`);
    lines.push('');
    if (currentQuestion) lines.push(`❓ QUESTION : ${currentQuestion}`);
    if (userAnswer) lines.push(`\n🗣️ RÉPONSE : ${userAnswer}`);
    if (currentEvaluation) lines.push(`\n📋 ÉVALUATION : ${currentEvaluation}`);
    const content = lines.join('\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `entretien_${(job?.company || 'entreprise').replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('✅ Conversation exportée', 'success');
  };

  const restartInterview = () => {
    if (window.confirm('Voulez-vous vraiment recommencer l\'entretien ? Toute la progression sera perdue.')) {
      setCurrentQuestion(null);
      setCurrentEvaluation(null);
      setUserAnswer('');
      setQuestionCount(0);
      setAnsweredCount(0);
      setScores([]);
      setError('');
      showToast('Entretien recommencé', 'info');
    }
  };

  const generateQuestion = async () => {
    if (!job) return;
    setLoading(true);
    setError('');
    setCurrentEvaluation(null);
    setUserAnswer('');
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

      if (data.error) {
        throw new Error(data.error);
      }

      const question = data.question;
      setCurrentQuestion(question);
      setQuestionCount(prev => prev + 1);
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
    const answerText = userAnswer;
    try {
      const response = await fetch(`${API_BASE}/api/mock-interview/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: currentQuestion,
          answer: answerText,
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

      if (data.error) {
        throw new Error(data.error);
      }

      const evaluation = data.evaluation;
      setCurrentEvaluation(evaluation);
      setAnsweredCount(prev => prev + 1);

      let evaluationText = evaluation;
      let scoreValue = null;

      if (typeof evaluation === 'object' && evaluation !== null) {
        const score = evaluation.score ?? evaluation.note ?? evaluation.points;
        if (typeof score === 'number') {
          scoreValue = Math.min(10, Math.max(0, score));
        } else if (typeof score === 'string') {
          const m = score.match(/(\d+)/);
          if (m) scoreValue = Math.min(10, Math.max(0, parseInt(m[1])));
        }

        const parts = [];
        if (typeof evaluation.feedback === 'string') parts.push(evaluation.feedback);
        if (typeof evaluation.commentaire === 'string') parts.push(evaluation.commentaire);
        if (typeof evaluation.retour === 'string') parts.push(evaluation.retour);
        if (typeof evaluation.evaluation === 'string') parts.push(evaluation.evaluation);
        if (typeof evaluation.texte === 'string') parts.push(evaluation.texte);
        if (parts.length > 0) {
          evaluationText = parts.join('\n\n');
        } else {
          evaluationText = JSON.stringify(evaluation, null, 2);
        }
      } else if (typeof evaluation === 'string') {
        evaluationText = evaluation;
        const m = evaluation.match(/(\d+)\s*\/\s*10/);
        if (m) scoreValue = parseInt(m[1]);
      }

      setCurrentEvaluation(evaluationText);
      if (scoreValue !== null) {
        setScores(prev => [...prev, scoreValue]);
      }
      if (mode === 'voice' && synthesisRef.current) {
        speakText(evaluation);
      }
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
    setUserAnswer('');
    generateQuestion();
  };

  const extractScore = (text) => {
    if (typeof text === 'string') {
      const match = text.match(/(\d+)\s*\/\s*10/);
      return match ? parseInt(match[1]) : null;
    }
    if (typeof text === 'object' && text !== null) {
      const score = text.score ?? text.note ?? text.points;
      if (typeof score === 'number') return Math.min(10, Math.max(0, score));
      if (typeof score === 'string') {
        const m = score.match(/(\d+)/);
        if (m) return Math.min(10, Math.max(0, parseInt(m[1])));
      }
    }
    return null;
  };

  const getScoreColor = (score) => {
    if (!score) return null;
    if (score >= 7) return 'high';
    if (score >= 5) return 'medium';
    return 'low';
  };

  if (parseError || !job) {
    return (
      <div className="app-container">
        <div className="main-content">
          <div className="standalone-title-bar">
            <div className="title-left">
              <BookOpen size={24} style={{ color: 'var(--primary-color)' }} />
              <h2>Simulation d'Entretien</h2>
            </div>
            <div className="title-right">
              <button className="btn-close" onClick={onBack}>✕ Fermer</button>
            </div>
          </div>
          <div className="card">
            <div className="card-content">
              <div className="alert alert-danger">
                <AlertCircle size={20} />
                <div>
                  {parseError
                    ? `Erreur de données : ${parseError}. Veuillez relancer l'entretien depuis la page principale.`
                    : 'Aucun poste sélectionné pour l\'entretien.'}
                </div>
              </div>
              <button onClick={onBack} className="btn btn-secondary" style={{ marginTop: '16px' }}>
                <ArrowLeft size={16} /> Retour
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}

      <div className="main-content" style={{ maxWidth: '800px', margin: '0 auto', width: '100%' }}>
        {/* Title Bar */}
        <div className="standalone-title-bar">
          <div className="title-left">
            <BookOpen size={24} style={{ color: 'var(--primary-color)' }} />
            <div>
              <h2>Simulation d'Entretien</h2>
              <div className="job-info">
                {job.title || job.titre || 'Poste'} • {job.company || job.entreprise || 'Entreprise'}
              </div>
            </div>
          </div>
          <div className="title-right">
            <button
              onClick={toggleDarkMode}
              className="btn btn-secondary"
              style={{ padding: '8px 12px' }}
              title={darkMode ? 'Mode clair' : 'Mode sombre'}
            >
              {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <button className="btn-close" onClick={onBack}>✕ Fermer</button>
          </div>
        </div>

        {/* Controls Bar */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <button onClick={onBack} className="btn btn-secondary">
            <ArrowLeft size={16} /> Retour
          </button>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              onClick={() => setMode(mode === 'written' ? 'voice' : 'written')}
              className="btn btn-secondary"
              style={{ padding: '8px 16px' }}
            >
              {mode === 'written' ? <><Mic size={16} /> Vocal</> : <><MessageSquare size={16} /> Écrit</>}
            </button>
            {mode === 'voice' && isSpeaking && (
              <button onClick={stopSpeaking} className="btn btn-secondary" style={{ padding: '8px 16px' }}>
                <VolumeX size={16} /> Stop
              </button>
            )}
            <button
              onClick={exportConversation}
              className="btn btn-secondary"
              style={{ padding: '8px 16px' }}
              title="Exporter"
              disabled={!currentQuestion && !currentEvaluation}
            >
              <Download size={16} />
            </button>
            <button
              onClick={restartInterview}
              className="btn btn-secondary"
              style={{ padding: '8px 16px' }}
              title="Recommencer"
              disabled={questionCount === 0}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>

        {/* Stats Bar */}
        {questionCount > 0 && (
          <div className="interview-stats-bar" style={{ marginBottom: '20px' }}>
            <div className="stat-item">
              <Target size={14} />
              <span>Question :</span>
              <span className="stat-value">{questionCount}</span>
            </div>
            <div className="stat-item">
              <MessageSquare size={14} />
              <span>Répondues :</span>
              <span className="stat-value">{answeredCount}</span>
            </div>
            <div className="stat-item">
              <CheckCircle2 size={14} />
              <span>Score moyen :</span>
              <span className="stat-value">{avgScore > 0 ? `${avgScore}/10` : '—'}</span>
            </div>
          </div>
        )}

        {/* Error */}
        {error && <div className="alert alert-danger" style={{ marginBottom: '16px' }}><span>{error}</span></div>}

        {/* Interview Settings */}
        {!loading && questionCount === 0 && (
          <div className="card" style={{ marginBottom: '20px', padding: '24px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-text-secondary)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Niveau de l'entretien
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {['débutant', 'intermédiaire', 'avancé'].map(stage => (
                    <button
                      key={stage}
                      onClick={() => setInterviewStage(stage)}
                      style={{
                        padding: '10px 20px',
                        borderRadius: 'var(--radius-sm)',
                        border: `2px solid ${interviewStage === stage ? 'var(--color-primary-500)' : 'var(--color-border)'}`,
                        background: interviewStage === stage ? 'rgba(99,102,241,0.1)' : 'var(--color-surface)',
                        color: interviewStage === stage ? 'var(--color-primary-500)' : 'var(--color-text-secondary)',
                        fontWeight: 600,
                        fontSize: '0.9rem',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        fontFamily: 'var(--font-sans)',
                        textTransform: 'capitalize',
                      }}
                    >
                      {stage}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-text-secondary)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Type de questions
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {[
                    { value: 'technique', label: 'Technique' },
                    { value: 'comportemental', label: 'Comportemental' },
                    { value: 'situationnel', label: 'Situationnel' },
                    { value: 'mixte', label: 'Mixte' },
                  ].map(type => (
                    <button
                      key={type.value}
                      onClick={() => setQuestionType(type.value)}
                      style={{
                        padding: '10px 20px',
                        borderRadius: 'var(--radius-sm)',
                        border: `2px solid ${questionType === type.value ? 'var(--color-primary-500)' : 'var(--color-border)'}`,
                        background: questionType === type.value ? 'rgba(99,102,241,0.1)' : 'var(--color-surface)',
                        color: questionType === type.value ? 'var(--color-primary-500)' : 'var(--color-text-secondary)',
                        fontWeight: 600,
                        fontSize: '0.9rem',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        fontFamily: 'var(--font-sans)',
                      }}
                    >
                      {type.label}
                    </button>
                  ))}
                </div>
              </div>
              <button
                onClick={generateQuestion}
                className="btn btn-primary"
                disabled={loading}
                style={{ padding: '14px 40px', fontSize: '1rem', marginTop: '8px' }}
              >
                <BookOpen size={16} /> Commencer l'entretien
              </button>
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="card" style={{ padding: '32px' }}>
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <Loader2 size={40} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary-color)' }} />
              <p style={{ marginTop: '16px', color: 'var(--text-secondary)' }}>Génération de la question...</p>
            </div>
          </div>
        )}

        {/* Question Card */}
        {!loading && currentQuestion && !currentEvaluation && (
          <div className="card" style={{
            marginBottom: '20px',
            borderColor: 'rgba(124,77,255,0.3)',
            background: 'linear-gradient(135deg, rgba(124,77,255,0.08) 0%, rgba(68,138,255,0.05) 100%)',
            padding: '32px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
              <span style={{
                background: 'linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%)',
                color: 'white',
                padding: '4px 12px',
                borderRadius: '9999px',
                fontSize: '0.75rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}>
                Question {questionCount}
              </span>
              {mode === 'voice' && (
                <button
                  onClick={isSpeaking ? stopSpeaking : () => speakText(currentQuestion)}
                  className="btn btn-secondary"
                  style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                >
                  {isSpeaking ? <VolumeX size={14} /> : <MessageSquare size={14} />}
                  {isSpeaking ? 'Stop' : 'Écouter'}
                </button>
              )}
            </div>
            <h3 style={{
              fontSize: '1.3rem',
              fontWeight: 700,
              lineHeight: '1.5',
              color: 'var(--color-text-primary)',
              margin: 0,
            }}>
              {currentQuestion}
            </h3>
          </div>
        )}

        {/* Answer Input */}
        {!loading && currentQuestion && !currentEvaluation && (
          <div className="card" style={{ marginBottom: '20px', padding: '24px' }}>
            <div className="card-title" style={{ marginBottom: '16px' }}>
              <MessageSquare size={20} />
              <span>Votre réponse</span>
            </div>
            <div className="card-content">
              {mode === 'written' ? (
                <>
                  <textarea
                    className="textarea-control"
                    style={{ height: '150px', width: '100%', resize: 'vertical', marginBottom: '12px', fontSize: '1rem' }}
                    placeholder="Tapez votre réponse ici..."
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                        submitAnswer();
                      }
                    }}
                  />
                  <button
                    onClick={submitAnswer}
                    className="btn btn-primary"
                    disabled={!userAnswer.trim() || evaluating}
                    style={{ width: '100%', padding: '14px', fontSize: '1rem' }}
                  >
                    {evaluating ? <><Loader2 size={16} className="spin" /> Évaluation en cours...</> : <><Send size={16} /> Envoyer la réponse</>}
                  </button>
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
                  <p style={{ margin: '0 0 16px 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {userAnswer || 'Votre réponse apparaîtra ici...'}
                  </p>
                  {userAnswer && (
                    <button
                      onClick={submitAnswer}
                      className="btn btn-primary"
                      disabled={evaluating}
                      style={{ padding: '12px 32px' }}
                    >
                      {evaluating ? <><Loader2 size={16} className="spin" /> Évaluation...</> : <><Send size={16} /> Envoyer la réponse</>}
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* AI Synthesis Card */}
        {!loading && currentEvaluation && (
          <div className="card" style={{
            marginBottom: '20px',
            borderColor: 'rgba(46,125,50,0.3)',
            background: 'linear-gradient(135deg, rgba(46,125,50,0.08) 0%, rgba(16,185,129,0.05) 100%)',
            padding: '32px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
              <span style={{
                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                color: 'white',
                padding: '4px 12px',
                borderRadius: '9999px',
                fontSize: '0.75rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}>
                <Sparkles size={12} /> Synthèse IA
              </span>
              {(() => {
                const score = extractScore(currentEvaluation);
                const scoreColor = getScoreColor(score);
                if (score !== null) {
                  return (
                    <span className={`score-badge-inline ${scoreColor}`} style={{ fontSize: '1rem', padding: '6px 16px' }}>
                      {score}/10
                    </span>
                  );
                }
                return null;
              })()}
              <button
                onClick={() => copyToClipboard(currentEvaluation)}
                className="btn btn-secondary"
                style={{ padding: '4px 10px', fontSize: '0.75rem', marginLeft: 'auto' }}
                title="Copier"
              >
                <Copy size={14} />
              </button>
            </div>
            <div style={{
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm)',
              padding: '20px',
              whiteSpace: 'pre-wrap',
              lineHeight: '1.7',
              fontSize: '0.95rem',
              color: 'var(--color-text-primary)',
              wordWrap: 'break-word',
            }}>
              {currentEvaluation}
            </div>
          </div>
        )}

        {/* Next Question Button */}
        {!loading && currentEvaluation && (
          <div style={{ textAlign: 'center', marginTop: '24px', marginBottom: '40px' }}>
            <button
              onClick={nextQuestion}
              className="btn btn-primary"
              style={{ padding: '14px 40px', fontSize: '1rem' }}
            >
              <ChevronRight size={18} /> Question suivante
            </button>
          </div>
        )}
      </div>
    </div>
  );
}