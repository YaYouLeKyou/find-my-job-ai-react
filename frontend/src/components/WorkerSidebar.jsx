import React, { useState, useEffect } from 'react';
import { Settings, Cpu, Key, Save, ExternalLink, CheckCircle2, AlertCircle, ChevronLeft, ChevronRight, Globe, DollarSign, Briefcase, Trash2 } from 'lucide-react';
import { LANGS } from '../utils/translations';

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function WorkerSidebar({
  lang,
  setLang,
  customGeminiKey,
  setCustomGeminiKey,
  ollamaOnline,
  searchHistory,
  savedCandidates,
  onSelectHistory,
  onToggleDarkMode,
  onClearHistory,
  onClearSavedCandidates,
  salaryMin,
  setSalaryMin,
  salaryMax,
  setSalaryMax,
  recommendedSalary,
}) {
  const [saved, setSaved] = useState(!!customGeminiKey);
  const [collapsed, setCollapsed] = useState(false);
  const [modelStatus, setModelStatus] = useState({ groq: false, gemini: false, ollama: ollamaOnline });
  const [modelDetails, setModelDetails] = useState({ groq: {}, gemini: {}, ollama: {} });
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [activeTab, setActiveTab] = useState('settings');

  // AI Mode Toggle State
  const [aiMode, setAiMode] = useState(false);

  const handleSaveKey = () => {
    if (customGeminiKey && customGeminiKey.trim()) {
      localStorage.setItem('gemini_api_key', customGeminiKey.trim());
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    }
  };

  useEffect(() => {
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey && !customGeminiKey) {
      setCustomGeminiKey(savedKey);
    }
  }, []);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/ai/status`);
        const text = await response.text();
        console.log('[DEBUG] AI status response:', response.status, text.substring(0, 300));
        if (response.ok && text.trim().startsWith('{')) {
          const data = JSON.parse(text);
          setModelStatus({
            groq: !!data.groq?.online,
            gemini: !!data.gemini?.online,
            ollama: !!data.ollama?.online
          });
          setModelDetails({
            groq: data.groq || {},
            gemini: data.gemini || {},
            ollama: data.ollama || {}
          });
        } else {
          console.error('[DEBUG] AI status returned non-JSON:', text);
        }
      } catch (error) {
        console.error("Failed to fetch AI status:", error);
      } finally {
        setLoadingStatus(false);
      }
    };
    fetchStatus();
  }, []);

  const getStatusIcon = (isAvailable) => {
    if (loadingStatus) return <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>...</span>;
    return isAvailable ?
      <CheckCircle2 size={14} style={{ color: 'var(--success-color)' }} /> :
      <AlertCircle size={14} style={{ color: 'var(--error-color)' }} />;
  };

  const getStatusText = (isAvailable, modelKey) => {
    if (loadingStatus) return 'Vérification...';
    if (!isAvailable) return 'Non configuré';
    const details = modelDetails[modelKey] || {};
    if (details.online) return 'En ligne';
    if (details.configured && details.error) return 'Hors ligne';
    return 'Disponible';
  };

  const tabs = [
    { id: 'settings', icon: '⚙️', label: 'Paramètres' },
    { id: 'history', icon: '📋', label: 'Historique', count: searchHistory?.length },
    { id: 'saved', icon: '⭐', label: 'Favoris', count: savedCandidates?.length },
    { id: 'salary', icon: '💰', label: 'Salaire' },
  ];

  return (
    <aside
      className="sidebar worker-sidebar"
      style={{ width: collapsed ? '60px' : '320px', transition: 'width 0.3s ease' }}
    >
      {/* Logo */}
      <div
        className="sidebar-logo"
        style={{
          justifyContent: collapsed ? 'center' : 'space-between',
          padding: collapsed ? '16px 0' : '16px',
          background: 'linear-gradient(135deg, rgba(255,111,0,0.08) 0%, rgba(255,143,0,0.08) 100%)',
          borderRadius: '12px',
          marginBottom: '4px',
        }}
      >
        {!collapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.3rem' }}>👷</span>
            <span
              style={{
                background: 'linear-gradient(135deg, #ff6f00, #ff8f00)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                fontWeight: '800',
                fontSize: '1rem',
              }}
            >
              Find My Worker AI
            </span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          title={collapsed ? 'Développer' : 'Réduire'}
        >
          {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>

      {!collapsed ? (
        <React.Fragment>
          {/* AI Mode Toggle */}
          <div className="sidebar-section" style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--surface-secondary)', borderRadius: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Cpu size={18} style={{ color: '#ff6f00' }} />
                <span style={{ fontWeight: '600', fontSize: '0.9rem' }}>Mode IA</span>
              </div>
              <button
                onClick={() => setAiMode(!aiMode)}
                style={{
                  width: '50px',
                  height: '26px',
                  background: aiMode ? '#ff6f00' : 'var(--border-color)',
                  borderRadius: '13px',
                  border: 'none',
                  cursor: 'pointer',
                  position: 'relative',
                  transition: 'background 0.3s'
                }}
              >
                <div style={{
                  position: 'absolute',
                  top: '3px',
                  left: aiMode ? '27px' : '3px',
                  width: '20px',
                  height: '20px',
                  background: 'white',
                  borderRadius: '50%',
                  transition: 'left 0.3s',
                  boxShadow: 'var(--shadow-sm)'
                }} />
              </button>
              <span style={{ fontSize: '0.8rem', color: aiMode ? '#ff6f00' : 'var(--text-muted)', fontWeight: '600' }}>
                {aiMode ? 'Avec IA' : 'Sans IA'}
              </span>
            </div>
          </div>

          {/* Tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', marginBottom: '8px' }}>
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  flex: 1,
                  padding: '8px 4px',
                  background: 'none',
                  border: 'none',
                  borderBottom: activeTab === tab.id ? '2px solid var(--worker-primary)' : 'none',
                  color: activeTab === tab.id ? 'var(--worker-primary)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontWeight: '600',
                  fontSize: '0.75rem',
                  position: 'relative',
                  transition: 'color 0.2s',
                }}
                title={tab.label}
              >
                {tab.icon}
                {tab.count > 0 && (
                  <span style={{
                    position: 'absolute', top: '4px', right: '4px',
                    background: 'var(--worker-primary)', color: 'white',
                    borderRadius: '50%', width: '14px', height: '14px',
                    fontSize: '0.65rem', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <React.Fragment>
              <div className="sidebar-section">
                <h3 className="sidebar-section-title">
                  <Globe size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                  Langue
                </h3>
                <div className="form-group">
                  <select className="select-control worker-select" value={lang} onChange={(e) => setLang(e.target.value)}>
                    {Object.keys(LANGS).map(k => <option key={k} value={k}>{k}</option>)}
                  </select>
                </div>
              </div>

              <div className="sidebar-section">
                <h3 className="sidebar-section-title">
                  <Cpu size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                  Configuration IA
                </h3>
                <div className="form-group" style={{ marginBottom: '12px' }}>
                  <label>🔬 Traitement du CV</label>
                  <select className="select-control worker-select" value={lang} onChange={(e) => setLang(e.target.value)}>
                    <option value="français">Gemini 3.5</option>
                    <option value="français">Gemini 2.5</option>
                    <option value="français">Groq / Llama 3.3</option>
                    <option value="français">Llama 3.2 (Local)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>⚖️ Tri & Proposition</label>
                  <select className="select-control worker-select" value={lang} onChange={(e) => setLang(e.target.value)}>
                    <option value="français">Gemini 3.5</option>
                    <option value="français">Gemini 2.5</option>
                    <option value="français">Groq / Llama 3.3</option>
                    <option value="français">Llama 3.2 (Local)</option>
                  </select>
                </div>
              </div>

              <div className="sidebar-section">
                <h3 className="sidebar-section-title">
                  <Key size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                  Clé API Gemini
                </h3>
                <div className="form-group">
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      type="password"
                      className="input-control worker-input"
                      style={{ flexGrow: 1 }}
                      placeholder="Clé Gemini API..."
                      value={customGeminiKey}
                      onChange={(e) => { setCustomGeminiKey(e.target.value); setSaved(false); }}
                    />
                    <button
                      className="btn btn-worker"
                      style={{ padding: '8px 12px', flexShrink: 0 }}
                      onClick={handleSaveKey}
                      disabled={!customGeminiKey || !customGeminiKey.trim()}
                    >
                      <Save size={16} />
                    </button>
                  </div>
                  {saved && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--success-color)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}>
                      <CheckCircle2 size={12} /> Clé enregistrée
                    </span>
                  )}
                  <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer"
                    style={{ fontSize: '0.75rem', color: 'var(--worker-primary)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}>
                    <ExternalLink size={12} /> Obtenir une clé gratuite
                  </a>
                </div>
              </div>

              <div className="sidebar-section">
                <h3 className="sidebar-section-title">
                  <Cpu size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                  Statut des modèles
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.82rem' }}>
                  {[
                    { label: 'Groq / Llama 3.3', key: 'groq' },
                    { label: 'Gemini 3.5 / 2.5', key: 'gemini' },
                  ].map(m => (
                    <div key={m.key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '7px 10px', background: 'var(--surface-secondary)', borderRadius: 'var(--radius-sm)' }}>
                      <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>{m.label}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {getStatusIcon(modelStatus[m.key])}
                        <span style={{ color: modelStatus[m.key] ? '#2e7d32' : '#c62828', fontSize: '0.75rem', fontWeight: '700' }}>
                          {getStatusText(modelStatus[m.key], m.key)}
                        </span>
                      </div>
                    </div>
                  ))}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '7px 10px', background: 'var(--surface-secondary)', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {modelStatus.ollama ? <Wifi size={14} style={{ color: '#2e7d32' }} /> : <WifiOff size={14} style={{ color: '#c62828' }} />}
                      <span style={{ color: modelStatus.ollama ? '#2e7d32' : '#c62828', fontSize: '0.75rem', fontWeight: '700' }}>
                        {getStatusText(modelStatus.ollama, 'ollama')}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </React.Fragment>
          )}

          {/* History Tab */}
          {activeTab === 'history' && (
            <div className="sidebar-section">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h3 className="sidebar-section-title" style={{ margin: 0 }}>📋 Historique des recherches</h3>
                {searchHistory?.length > 0 && onClearHistory && (
                  <button
                    onClick={onClearHistory}
                    className="btn btn-secondary"
                    style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}
                    title="Vider l'historique"
                  >
                    <Trash2 size={12} /> Vider
                  </button>
                )}
              </div>
              {!searchHistory?.length ? (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                  Aucune recherche récente
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflowY: 'auto' }}>
                  {searchHistory.map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => onSelectHistory(item.query)}
                      style={{
                        padding: '8px 12px', background: 'var(--glass-bg)', border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-sm)', cursor: 'pointer', textAlign: 'left', fontSize: '0.85rem',
                        color: 'var(--text-primary)', transition: 'all 0.2s',
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--worker-primary)'; e.currentTarget.style.color = 'white'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--glass-bg)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
                    >
                      <div style={{ fontWeight: '600' }}>{item.query}</div>
                      <div style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '2px' }}>
                        {new Date(item.time).toLocaleDateString('fr-FR')} — {item.count} résultats
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Saved Candidates Tab */}
          {activeTab === 'saved' && (
            <div className="sidebar-section">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h3 className="sidebar-section-title" style={{ margin: 0 }}>⭐ Favoris</h3>
                {savedCandidates?.length > 0 && onClearSavedCandidates && (
                  <button
                    onClick={onClearSavedCandidates}
                    className="btn btn-secondary"
                    style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}
                    title="Vider les favoris"
                  >
                    <Trash2 size={12} /> Vider
                  </button>
                )}
              </div>
              {!savedCandidates?.length ? (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                  Aucun favori
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '350px', overflowY: 'auto' }}>
                  {savedCandidates.map((candidate, idx) => (
                    <a
                      key={idx} href={candidate.link} target="_blank" rel="noopener noreferrer"
                      style={{
                        padding: '8px 12px', background: 'var(--glass-bg)', border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-sm)', textDecoration: 'none', fontSize: '0.85rem',
                        color: 'var(--text-primary)', display: 'block', transition: 'all 0.2s',
                      }}
                    >
                      <div style={{ fontWeight: '600', fontSize: '0.82rem' }}>{candidate.title}</div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                        <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>{candidate.company || 'Non spécifié'}</span>
                        {candidate.salary && <span style={{ fontSize: '0.75rem', color: '#ff6f00', fontWeight: '700' }}>💰 {candidate.salary}</span>}
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Salary Calculator Tab */}
          {activeTab === 'salary' && (
            <div className="sidebar-section">
              <h3 className="sidebar-section-title">💰 Calculateur de salaire</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div className="form-group">
                  <label>Salaire minimum (€/mois)</label>
                  <input
                    type="number"
                    className="input-control worker-input"
                    placeholder="ex: 2000"
                    value={salaryMin || ''}
                    onChange={(e) => setSalaryMin(e.target.value)}
                    min="0"
                    step="100"
                  />
                </div>
                <div className="form-group">
                  <label>Salaire maximum (€/mois)</label>
                  <input
                    type="number"
                    className="input-control worker-input"
                    placeholder="ex: 8000"
                    value={salaryMax || ''}
                    onChange={(e) => setSalaryMax(e.target.value)}
                    min="0"
                    step="100"
                  />
                </div>

                {recommendedSalary && (
                  <div style={{
                    padding: '14px',
                    background: 'linear-gradient(135deg, rgba(255,111,0,0.1), rgba(255,143,0,0.1))',
                    border: '1px solid rgba(255,111,0,0.25)',
                    borderRadius: '12px',
                    marginTop: '4px',
                  }}>
                    <div style={{ fontSize: '0.75rem', color: '#ff6f00', fontWeight: '700', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      🤖 Salaire recommandé par l'IA
                    </div>
                    <div style={{ fontSize: '1.6rem', fontWeight: '900', color: 'var(--worker-dark)', letterSpacing: '-0.02em' }}>
                      {recommendedSalary} €/mois
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Basé sur votre profil + données marché
                    </div>
                  </div>
                )}

                <div style={{
                  padding: '12px',
                  background: 'rgba(0,0,0,0.03)',
                  borderRadius: '10px',
                  fontSize: '0.78rem',
                  color: 'var(--text-muted)',
                  lineHeight: '1.6',
                }}>
                  💡 Analysez votre profil pour obtenir un salaire recommandé selon votre niveau d'expérience et les tendances du marché de l'emploi.
                </div>
              </div>
            </div>
          )}

          <div className="sidebar-section" style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>WorkerAI v1.0</span>
              {onToggleDarkMode && (
                <button
                  onClick={onToggleDarkMode}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', fontSize: '1.1rem' }}
                >
                  🌓
                </button>
              )}
            </div>
          </div>
        </React.Fragment>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '16px' }}>
          <Globe size={20} style={{ color: 'var(--text-secondary)' }} />
          <Cpu size={20} style={{ color: 'var(--text-secondary)' }} />
          <Key size={20} style={{ color: 'var(--text-secondary)' }} />
          <DollarSign size={20} style={{ color: '#ff6f00' }} />
        </div>
      )}

    </aside>
  );
}
