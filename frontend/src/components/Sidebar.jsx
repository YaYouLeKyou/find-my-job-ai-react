import React, { useState, useEffect } from 'react';
import { LANGS, STRINGS } from '../utils/translations';
import { Settings, Cpu, Key, Globe, Save, ExternalLink, CheckCircle2, AlertCircle, ChevronLeft, ChevronRight, Wifi, WifiOff, Menu, X } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function Sidebar({
  lang,
  setLang,
  analysisEngine,
  setAnalysisEngine,
  rankingEngine,
  setRankingEngine,
  customGeminiKey,
  setCustomGeminiKey,
  ollamaOnline,
  searchHistory,
  savedJobs,
  onSelectHistory,
  onToggleDarkMode
}) {
  const S = STRINGS[LANGS[lang].code];
  const [saved, setSaved] = useState(!!customGeminiKey);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [modelStatus, setModelStatus] = useState({
    groq: false,
    gemini: false,
    xai: false,
    ollama: ollamaOnline
  });
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [activeTab, setActiveTab] = useState('settings');

  const handleSaveKey = () => {
    if (customGeminiKey && customGeminiKey.trim()) {
      localStorage.setItem('gemini_api_key', customGeminiKey.trim());
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    }
  };

  // Load saved key on mount
  React.useEffect(() => {
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey && !customGeminiKey) {
      setCustomGeminiKey(savedKey);
    }
  }, []);

  // Fetch model status from diagnostic endpoint
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/diagnostic`);
        if (response.ok) {
          const data = await response.json();
          setModelStatus({
            groq: data.groq_key_configured || false,
            gemini: data.gemini_key_configured || false,
            xai: data.xai_key_configured || false,
            ollama: data.ollama_configured || false
          });
        }
      } catch (error) {
        console.error("Failed to fetch diagnostic:", error);
      } finally {
        setLoadingStatus(false);
      }
    };

    fetchStatus();
  }, []);

  // Close mobile sidebar on window resize above breakpoint
  React.useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 599 && mobileOpen) {
        setMobileOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [mobileOpen]);

  const getStatusIcon = (isAvailable) => {
    if (loadingStatus) return <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>...</span>;
    return isAvailable ? 
      <CheckCircle2 size={14} style={{ color: 'var(--success-color)' }} /> : 
      <AlertCircle size={14} style={{ color: 'var(--error-color)' }} />;
  };

  const getStatusText = (isAvailable) => {
    if (loadingStatus) return 'Vérification...';
    return isAvailable ? 'Disponible' : 'Non configuré';
  };

  const closeMobile = () => setMobileOpen(false);

  return (
    <>
      {/* Mobile hamburger toggle button */}
      <button
        className="sidebar-toggle-mobile"
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle sidebar"
        title={mobileOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
      >
        {mobileOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Mobile overlay backdrop */}
      {mobileOpen && (
        <div className="sidebar-overlay" onClick={closeMobile} />
      )}

      <aside
        className={`sidebar ${mobileOpen ? 'open' : ''}`}
        style={{ width: collapsed ? '60px' : '320px', transition: 'width 0.3s ease' }}
      >
      <div className="sidebar-logo" style={{ justifyContent: collapsed ? 'center' : 'space-between', padding: collapsed ? '16px 0' : '16px' }}>
        {!collapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings size={24} className="text-primary" />
            <span>Find my job AI</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title={collapsed ? 'Développer' : 'Réduire'}
        >
          {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>

      {!collapsed ? (
        <React.Fragment>
          {/* Tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', marginBottom: '8px' }}>
            <button
              onClick={() => setActiveTab('settings')}
              style={{
                flex: 1,
                padding: '8px',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'settings' ? '2px solid var(--primary-color)' : 'none',
                color: activeTab === 'settings' ? 'var(--primary-color)' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem'
              }}
            >
              ⚙️
            </button>
            <button
              onClick={() => setActiveTab('history')}
              style={{
                flex: 1,
                padding: '8px',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'history' ? '2px solid var(--primary-color)' : 'none',
                color: activeTab === 'history' ? 'var(--primary-color)' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem',
                position: 'relative'
              }}
            >
              📋
              {searchHistory.length > 0 && (
                <span style={{
                  position: 'absolute',
                  top: '4px',
                  right: '8px',
                  background: 'var(--primary-color)',
                  color: 'white',
                  borderRadius: '50%',
                  width: '16px',
                  height: '16px',
                  fontSize: '0.7rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  {searchHistory.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('saved')}
              style={{
                flex: 1,
                padding: '8px',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'saved' ? '2px solid var(--primary-color)' : 'none',
                color: activeTab === 'saved' ? 'var(--primary-color)' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem',
                position: 'relative'
              }}
            >
              ⭐
              {savedJobs.length > 0 && (
                <span style={{
                  position: 'absolute',
                  top: '4px',
                  right: '8px',
                  background: 'var(--primary-color)',
                  color: 'white',
                  borderRadius: '50%',
                  width: '16px',
                  height: '16px',
                  fontSize: '0.7rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  {savedJobs.length}
                </span>
              )}
            </button>
          </div>

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <React.Fragment>
              <div className="sidebar-section">
                <h3 className="sidebar-section-title">
                  <Globe size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                  Language
                </h3>
                <div className="form-group">
                  <select
                    className="select-control"
                    value={lang}
                    onChange={(e) => setLang(e.target.value)}
                  >
                    {Object.keys(LANGS).map((key) => (
                      <option key={key} value={key}>
                        {key}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="sidebar-section">
                <h3 className="sidebar-section-title">
                  <Cpu size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                  {S.ai_config}
                </h3>
                
                <div className="form-group" style={{ marginBottom: '12px' }}>
                  <label>{S.cv_analysis}</label>
                  <select
                    className="select-control"
                    value={analysisEngine}
                    onChange={(e) => setAnalysisEngine(e.target.value)}
                  >
                    <option value="Gemini 3.5">Gemini 3.5</option>
                    <option value="Gemini 2.5">Gemini 2.5</option>
                    <option value="Groq / Llama 3.3">Groq / Llama 3.3</option>
                    <option value="Llama 3.2 (Local/dev)">Llama 3.2 (Local/dev)</option>
                    <option value="Llama 3.2 Vision (Local/dev)">Llama 3.2 Vision (Local/dev)</option>
                  </select>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Llama 3.3 via Groq est ultra-rapide.
                  </span>
                </div>

                <div className="form-group">
                  <label>{S.tri_redac}</label>
                  <select
                    className="select-control"
                    value={rankingEngine}
                    onChange={(e) => setRankingEngine(e.target.value)}
                  >
                    <option value="Gemini 3.5">Gemini 3.5</option>
                    <option value="Gemini 2.5">Gemini 2.5</option>
                    <option value="Groq / Llama 3.3">Groq / Llama 3.3</option>
                    <option value="Llama 3.2 (Local/dev)">Llama 3.2 (Local/dev)</option>
                    <option value="Qwen 3 4B (Local/dev)">Qwen 3 4B (Local/dev)</option>
                  </select>
                </div>
              </div>

              <div className="sidebar-section">
                <h3 className="sidebar-section-title">
                  <Key size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                  {S.personal_key}
                </h3>
                <div className="form-group">
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      type="password"
                      className="input-control"
                      style={{ flexGrow: 1 }}
                      placeholder="Clé Gemini API..."
                      value={customGeminiKey}
                      onChange={(e) => {
                        setCustomGeminiKey(e.target.value);
                        setSaved(false);
                      }}
                    />
                    <button
                      className="btn btn-primary"
                      style={{ padding: '8px 12px', flexShrink: 0 }}
                      onClick={handleSaveKey}
                      disabled={!customGeminiKey || !customGeminiKey.trim()}
                      title="Enregistrer la clé pour la session"
                    >
                      <Save size={16} />
                    </button>
                  </div>
                  {saved && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--success-color)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}>
                      <CheckCircle2 size={12} />
                      Clé enregistrée pour cette session
                    </span>
                  )}
                  <a
                    href="https://aistudio.google.com/app/apikey"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      fontSize: '0.75rem',
                      color: 'var(--primary-color)',
                      textDecoration: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      marginTop: '4px'
                    }}
                  >
                    <ExternalLink size={12} />
                    Obtenir une clé Gemini API gratuite
                  </a>
                </div>
              </div>

              <div className="sidebar-section">
                <h3 className="sidebar-section-title">
                  <Cpu size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                  Statut des modèles AI
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 10px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>Groq / Llama 3.3</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {getStatusIcon(modelStatus.groq)}
                      <span style={{ color: modelStatus.groq ? '#2e7d32' : '#c62828', fontSize: '0.8rem', fontWeight: '700' }}>
                        {getStatusText(modelStatus.groq)}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 10px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>Gemini 3.5 / 2.5</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {getStatusIcon(modelStatus.gemini)}
                      <span style={{ color: modelStatus.gemini ? '#2e7d32' : '#c62828', fontSize: '0.8rem', fontWeight: '700' }}>
                        {getStatusText(modelStatus.gemini)}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 10px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>Ollama (Local)</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {modelStatus.ollama ? 
                        <Wifi size={16} style={{ color: '#2e7d32' }} /> : 
                        <WifiOff size={16} style={{ color: '#c62828' }} />
                      }
                      <span style={{ color: modelStatus.ollama ? '#2e7d32' : '#c62828', fontSize: '0.8rem', fontWeight: '700' }}>
                        {modelStatus.ollama ? 'En ligne' : 'Hors ligne'}
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
              <h3 className="sidebar-section-title">
                📋 Historique des recherches
              </h3>
              {searchHistory.length === 0 ? (
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
                        padding: '8px 12px',
                        background: 'var(--glass-bg)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer',
                        textAlign: 'left',
                        fontSize: '0.85rem',
                        color: 'var(--text-primary)',
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        e.target.style.background = 'var(--primary-color)';
                        e.target.style.color = 'white';
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.background = 'var(--glass-bg)';
                        e.target.style.color = 'var(--text-primary)';
                      }}
                    >
                      <div style={{ fontWeight: '600' }}>{item.query}</div>
                      <div style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '2px' }}>
                        {new Date(item.time).toLocaleDateString('fr-FR')} - {item.count} résultats
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Saved Jobs Tab */}
          {activeTab === 'saved' && (
            <div className="sidebar-section">
              <h3 className="sidebar-section-title">
                ⭐ Offres sauvegardées
              </h3>
              {savedJobs.length === 0 ? (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                  Aucune offre sauvegardée
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflowY: 'auto' }}>
                  {savedJobs.map((job, idx) => (
                    <a
                      key={idx}
                      href={job.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        padding: '8px 12px',
                        background: 'var(--glass-bg)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-sm)',
                        textDecoration: 'none',
                        fontSize: '0.85rem',
                        color: 'var(--text-primary)',
                        display: 'block',
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        e.target.style.background = 'var(--primary-color)';
                        e.target.style.color = 'white';
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.background = 'var(--glass-bg)';
                        e.target.style.color = 'var(--text-primary)';
                      }}
                    >
                      <div style={{ fontWeight: '600', fontSize: '0.8rem' }}>{job.title}</div>
                      <div style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '2px' }}>
                        {job.company}
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="sidebar-section" style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Find my work AI v2.0</span>
              {onToggleDarkMode && (
                <button
                  onClick={onToggleDarkMode}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '4px',
                    fontSize: '1.2rem',
                    title: 'Basculer mode sombre/clair'
                  }}
                >
                  🌓
                </button>
              )}
            </div>
          </div>
        </React.Fragment>
      ) : (
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          gap: '16px',
          marginTop: '16px'
        }}>
          <Globe size={20} style={{ color: 'var(--text-secondary)' }} title="Language" />
          <Cpu size={20} style={{ color: 'var(--text-secondary)' }} title="AI Config" />
          <Key size={20} style={{ color: 'var(--text-secondary)' }} title="Clé API" />
        </div>
      )}
    </aside>
    </>
  );
}
