import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Mic, MicOff, Send, MessageSquare, VolumeX, ArrowLeft,
  CheckCircle2, AlertCircle, Loader2, BookOpen, Target,
  Copy, Check, Download, RefreshCw, Sun, Moon, Wifi, WifiOff,
  Clock, BarChart3, FileText
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function MockInterview({ onBack, job, cvData, rankingEngine, customGeminiKey, parseError }) {
  // ─── Core State ──────────────────────────────────────────────────────────
  const [mode, setMode] = useState('written');
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

  // ─── New State for Improvements ──────────────────────────────────────────
  const [questionCount, setQuestionCount] = useState(0);
  const [responseTimer, setResponseTimer] = useState(0);
  const [timerActive, setTimerActive] = useState(false);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [darkMode, setDarkMode] = useState(false);
  const [copiedMessageId, setCopiedMessageId] = useState(null);
  const [showStats, setShowStats] = useState(false);

  const recognitionRef = useRef(null);
  const synthesisRef = useRef(null);
  const timerRef = useRef(null);

  // ─── Computed Statistics ─────────────────────────────────────────────────
  const answeredQuestions = conversation.filter(m => m.type === 'answer').length;
  const evaluations = conversation.filter(m => m.type === 'evaluation');
  const avgScore = evaluations.length > 0
    ? Math.round(evaluations.reduce((sum, m) => {
        const match = m.content.match(/(\d+)\/10/);
        return sum + (match ? parseInt(match[1]) : 5);
      }, 0) / evaluations.length)
    : 0;
  const totalWords = conversation.filter(m => m.type === 'answer')
    .reduce((sum, m) => sum + m.content.trim().split(/\s+/).filter(w => w.length > 0).length, 0);

  // ─── Toast ───────────────────────────────────────────────────────────────
  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // ─── Backend Health Check ────────────────────────────────────────────────
  const checkBackend = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(5000) });
      if (response.ok) {
        setBackendStatus('online');
      } else {
        setBackendStatus('offline');
      }
    } catch {
      setBackendStatus('offline');
    }
  }, []);

  // ─── Speech Recognition Init ─────────────────────────────────────────────
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

    // Generate first question on mount
    if (job) {
      generateQuestion();
    }

    // Check backend health
    checkBackend();

    // Load dark mode preference
    const savedDark = localStorage.getItem('mockInterviewDarkMode');
    if (savedDark === 'true') {
      setDarkMode(true);
      document.documentElement.setAttribute('data-theme', 'dark');
    }

    return () => {
      if (recognitionRef.current) recognitionRef.current.abort();
      if (synthesisRef.current) synthesisRef.current.cancel();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // ─── Regenerate question if job changes ──────────────────────────────────
  useEffect(() => {
    if (job && conversation.length === 0) {
      generateQuestion();
    }
  }, [job]);

  // ─── Response Timer ──────────────────────────────────────────────────────
  useEffect(() => {
    if (timerActive) {
      timerRef.current = setInterval(() => {
        setResponseTimer(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [timerActive]);

  // ─── Dark Mode Toggle ────────────────────────────────────────────────────
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

  // ─── Format Timer ────────────────────────────────────────────────────────
  const formatTimer = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // ─── Copy to Clipboard ───────────────────────────────────────────────────
  const copyToClipboard = async (text, messageId) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch {
      showToast('Erreur de copie', 'error');
    }
  };

  // ─── Export Conversation ─────────────────────────────────────────────────
  const exportConversation = () => {
    if (conversation.length === 0) {
      showToast('Aucune conversation à exporter', 'warning');
      return;
    }
    const lines = [];
    lines.push(`=== Simulation d'Entretien - Job Bridge ===`);
    lines.push(`Poste : ${job?.title || job?.titre || 'N/A'}`);
    lines.push(`Entreprise : ${job?.company || job?.entreprise || 'N/A'}`);
    lines.push(`Date : ${new Date().toLocaleString('fr-FR')}`);
    lines.push(`Questions répondues : ${answeredQuestions}`);
    lines.push(`Score moyen : ${avgScore}/10`);
    lines.push('');
    conversation.forEach((msg, idx) => {
      const typeLabel = msg.type === 'question' ? '❓ QUESTION' :
                        msg.type === 'answer' ? '🗣️ RÉPONSE' : '📋 ÉVALUATION';
      lines.push(`\n${typeLabel} (${idx + 1})`);
      lines.push(msg.content);
      lines.push('');
    });
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

  // ─── Restart Interview ───────────────────────────────────────────────────
  const restartInterview = () => {
    if (window.confirm('Voulez-vous vraiment recommencer l\'entretien ? Toute la conversation sera perdue.')) {
      setConversation([]);
      setCurrentQuestion(null);
      setCurrentEvaluation(null);
      setUserAnswer('');
      setQuestionCount(0);
      setResponseTimer(0);
      setTimerActive(false);
      setError('');
      showToast('Entretien recommencé', 'info');
      setTimeout(() => {
        if (job) generateQuestion();
      }, 100);
    }
  };

  // ─── Generate Question ───────────────────────────────────────────────────
  const generateQuestion = async () => {
    if (!job) return;

    setLoading(true);
    setError('');
    setCurrentEvaluation(null);
    setTimerActive(false);
    setResponseTimer(0);

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
      setConversation(prev => [...prev, { type: 'question', content: question, id: Date.now() }]);
      setQuestionCount(prev => prev + 1);
      setBackendStatus('online');

      if (mode === 'voice' && synthesisRef.current) {
        speakText(question);
      }
    } catch (err) {
      console.error(err);
      setError(err.message);
      showToast(`❌ Erreur: ${err.message}`, 'error');
      setBackendStatus('offline');
    } finally {
      setLoading(false);
    }
  };

  // ─── Submit Answer ───────────────────────────────────────────────────────
  const submitAnswer = async () => {
    if (!userAnswer.trim() || !currentQuestion) return;

    setEvaluating(true);
    setError('');
    setTimerActive(false);

    const answerText = userAnswer;
    const answerId = Date.now();

    setConversation(prev => [...prev, { type: 'answer', content: answerText, id: answerId }]);
    setUserAnswer('');

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
      const evaluation = data.evaluation;

      setCurrentEvaluation(evaluation);
      setConversation(prev => [...prev, { type: 'evaluation', content: evaluation, id: Date.now() }]);
      setBackendStatus('online');

      if (mode === 'voice' && synthesisRef.current) {
        speakText(evaluation);
      }

      showToast('✅ Réponse évaluée', 'success');
    } catch (err) {
      console.error(err);
      setError(err.message);
      showToast(`❌ Erreur: ${err.message}`, 'error');
      setBackendStatus('offline');
    } finally {
      setEvaluating(false);
    }
  };

  // ─── Speech Synthesis ────────────────────────────────────────────────────
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

  // ─── Speech Recognition ──────────────────────────────────────────────────
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

  // ─── Next Question ───────────────────────────────────────────────────────
  const nextQuestion = () => {
    setCurrentEvaluation(null);
    generateQuestion();
  };

  // ─── Extract Score from Evaluation ───────────────────────────────────────
  const extractScore = (text) => {
    const match = text.match(/(\d+)\s*\/\s*10/);
    return match ? parseInt(match[1]) : null;
  };

  const getScoreColor = (score) => {
    if (!score) return null;
    if (score >= 7) return 'high';
    if (score >= 5) return 'medium';
    return 'low';
  };

  // ─── Fallback UI for parseError or no job ────────────────────────────────
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

  // ─── Main Render ─────────────────────────────────────────────────────────
  return (
    <div className="app-container">
      {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}

      <div className="main-content">
        {/* ─── Standalone Title Bar ─────────────────────────────────────── */}
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
            {/* Dark Mode Toggle */}
            <button
              onClick={toggleDarkMode}
              className="btn btn-secondary"
              style={{ padding: '8px 12px' }}
              title={darkMode ? 'Mode clair' : 'Mode sombre'}
            >
              {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            {/* Backend Status */}
            <div className={`connection-status ${backendStatus === 'offline' ? 'offline' : ''}`}>
              {backendStatus === 'online' ? <Wifi size={14} /> : <WifiOff size={14} />}
              <span>{backendStatus === 'online' ? 'Connecté' : 'Hors ligne'}</span>
            </div>
            {/* Close Button */}
            <button className="btn-close" onClick={onBack}>✕ Fermer</button>
          </div>
        </div>

        {/* ─── Header Actions ───────────────────────────────────────────── */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
          <button onClick={onBack} className="btn btn-secondary">
            <ArrowLeft size={16} /> Retour aux résultats
          </button>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            {/* Mode Toggle */}
            <button
              onClick={() => setMode(mode === 'written' ? 'voice' : 'written')}
              className="btn btn-secondary"
              style={{ padding: '8px 16px' }}
            >
              {mode === 'written' ? <><Mic size={16} /> Mode Vocal</> : <><MessageSquare size={16} /> Mode Écrit</>}
            </button>

            {/* Stop Speaking */}
            {mode === 'voice' && isSpeaking && (
              <button onClick={stopSpeaking} className="btn btn-secondary" style={{ padding: '8px 16px' }}>
                <VolumeX size={16} /> Stop
              </button>
            )}

            {/* Stats Toggle */}
            <button
              onClick={() => setShowStats(!showStats)}
              className="btn btn-secondary"
              style={{ padding: '8px 16px' }}
              title="Statistiques"
            >
              <BarChart3 size={16} />
            </button>

            {/* Export */}
            <button
              onClick={exportConversation}
              className="btn btn-secondary"
              style={{ padding: '8px 16px' }}
              title="Exporter la conversation"
              disabled={conversation.length === 0}
            >
              <Download size={16} />
            </button>

            {/* Restart */}
            <button
              onClick={restartInterview}
              className="btn btn-secondary"
              style={{ padding: '8px 16px' }}
              title="Recommencer l'entretien"
              disabled={conversation.length === 0}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>

        {/* ─── Stats Bar (collapsible) ─────────────────────────────────── */}
        {showStats && (
          <div className="interview-stats-bar">
            <div className="stat-item">
              <Target size={14} />
              <span>Questions :</span>
              <span className="stat-value">{questionCount}</span>
            </div>
            <div className="stat-item">
              <MessageSquare size={14} />
              <span>Répondues :</span>
              <span className="stat-value">{answeredQuestions}</span>
            </div>
            <div className="stat-item">
              <Clock size={14} />
              <span>Temps total :</span>
              <span className="stat-value">{formatTimer(responseTimer)}</span>
            </div>
            <div className="stat-item">
              <BarChart3 size={14} />
              <span>Score moyen :</span>
              <span className="stat-value">{avgScore > 0 ? `${avgScore}/10` : '—'}</span>
            </div>
            <div className="stat-item">
              <FileText size={14} />
              <span>Mots écrits :</span>
              <span className="stat-value">{totalWords}</span>
            </div>
          </div>
        )}

        {/* ─── Job Info Card ─────────────────────────────────────────── */}
        <div className="card" style={{ marginBottom: '20px', borderColor: 'rgba(124,77,255,0.2)' }}>
          <div className="card-content">
            <h3 style={{ margin: '0 0 8px 0' }}>{job.title || job.titre || 'Poste'}</h3>
            <p style={{ margin: 0, color: 'var(--text-secondary)' }}>{job.company || job.entreprise || 'Entreprise'}</p>
          </div>
        </div>

        {/* ─── Interview Settings ─────────────────────────────────────── */}
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

        {/* ─── Error ─────────────────────────────────────────────────── */}
        {error && <div className="alert alert-danger"><span>{error}</span></div>}

        {/* ─── Conversation (Scrollable Container) ───────────────────── */}
        {conversation.length > 0 && (
          <div className="interview-conversation-container">
            {conversation.map((msg, idx) => {
              const isAnswer = msg.type === 'answer';
              const isEvaluation = msg.type === 'evaluation';
              const score = isEvaluation ? extractScore(msg.content) : null;
              const scoreColor = score ? getScoreColor(score) : null;

              return (
                <div
                  key={msg.id || idx}
                  className="msg-wrapper"
                  style={{
                    position: 'relative',
                    padding: '16px',
                    borderRadius: '8px',
                    background: msg.type === 'question' ? 'rgba(124,77,255,0.1)' :
                               msg.type === 'answer' ? 'rgba(68,138,255,0.1)' :
                               'rgba(46,125,50,0.1)',
                    border: `1px solid ${
                      msg.type === 'question' ? 'rgba(124,77,255,0.2)' :
                      msg.type === 'answer' ? 'rgba(68,138,255,0.2)' :
                      'rgba(46,125,50,0.2)'
                    }`,
                    marginBottom: '12px',
                  }}
                >
                  {/* Copy Button (for answers and evaluations) */}
                  {(isAnswer || isEvaluation) && (
                    <button
                      className="msg-copy-btn"
                      onClick={() => copyToClipboard(msg.content, msg.id)}
                      title="Copier"
                    >
                      {copiedMessageId === msg.id ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                  )}

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
                    {/* Score Badge for Evaluations */}
                    {isEvaluation && score !== null && (
                      <span className={`score-badge-inline ${scoreColor}`}>
                        {score}/10
                      </span>
                    )}
                  </div>
                  <p style={{ margin: 0, whiteSpace: 'pre-wrap', lineHeight: '1.6', wordWrap: 'break-word' }}>
                    {msg.content}
                  </p>
                </div>
              );
            })}
          </div>
        )}

        {/* ─── Loading Skeleton (instead of plain spinner) ─────────────── */}
        {loading && (
          <div style={{ padding: '20px' }}>
            <div className="skeleton" style={{ height: '24px', width: '60%', marginBottom: '12px' }}></div>
            <div className="skeleton" style={{ height: '16px', width: '100%', marginBottom: '8px' }}></div>
            <div className="skeleton" style={{ height: '16px', width: '90%', marginBottom: '8px' }}></div>
            <div className="skeleton" style={{ height: '16px', width: '70%', marginTop: '8px' }}></div>
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <p style={{ marginTop: '16px', color: 'var(--text-secondary)' }}>Génération de la question...</p>
            </div>
          </div>
        )}

        {/* ─── Current Question Indicator ─────────────────────────────── */}
        {currentQuestion && !currentEvaluation && (
          <div className="card" style={{ marginBottom: '20px', borderColor: 'rgba(124,77,255,0.2)', background: 'rgba(124,77,255,0.05)' }}>
            <div className="card-content">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <AlertCircle size={16} style={{ color: '#7c4dff' }} />
                <strong>Question actuelle :</strong>
              </div>
              <p style={{ margin: 0, fontStyle: 'italic', lineHeight: '1.6' }}>{currentQuestion}</p>
            </div>
          </div>
        )}

        {/* ─── Answer Input ─────────────────────────────────────────── */}
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
                    onChange={(e) => {
                      setUserAnswer(e.target.value);
                      if (!timerActive && e.target.value.trim()) {
                        setTimerActive(true);
                      }
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                        submitAnswer();
                      }
                    }}
                  />
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button
                      onClick={submitAnswer}
                      className="btn btn-primary"
                      disabled={!userAnswer.trim() || evaluating}
                      style={{ flex: 1 }}
                    >
                      {evaluating ? <><Loader2 size={16} className="spin" /> Évaluation...</> : <><Send size={16} /> Envoyer (Ctrl+Enter)</>}
                    </button>
                    {timerActive && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        <Clock size={14} />
                        <span>{formatTimer(responseTimer)}</span>
                      </div>
                    )}
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

        {/* ─── Next Question Button (after evaluation) ───────────────── */}
        {currentEvaluation && (
          <div style={{ textAlign: 'center', marginTop: '24px' }}>
            <button onClick={nextQuestion} className="btn btn-primary" style={{ padding: '12px 32px' }}>
              <BookOpen size={16} /> Question suivante
            </button>
          </div>
        )}

        {/* ─── Empty State ─────────────────────────────────────────── */}
        {!loading && conversation.length === 0 && !currentQuestion && (
          <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
            <BookOpen size={48} style={{ color: 'var(--text-muted)', marginBottom: '16px' }} />
            <h3 style={{ marginBottom: '8px' }}>Prêt pour votre entretien ?</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Cliquez sur "Nouvelle question" pour commencer la simulation.
            </p>
            <button onClick={generateQuestion} className="btn btn-primary">
              <BookOpen size={16} /> Commencer l'entretien
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
