import React, { useState, useEffect } from 'react';
import { Settings, Cpu, Key, Save, ExternalLink, CheckCircle2, AlertCircle, ChevronLeft, ChevronRight, Wifi, WifiOff, Globe, DollarSign, Briefcase } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function FreelanceSidebar({
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
  savedMissions,
  onSelectHistory,
  onToggleDarkMode,
  tjmMin,
  setTjmMin,
  tjmMax,
  setTjmMax,
  recommendedTjm,
}) {
  const [saved, setSaved] = useState(!!customGeminiKey);
  const [collapsed, setCollapsed] = useState(false);
  const [modelStatus, setModelStatus] = useState({ groq: false, gemini: false, ollama: ollamaOnline });
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [activeTab, setActiveTab] = useState('settings');

  const LANGS_MAP = {
    "Français": { code: "fr" },
    "English": { code: "en" },
    "Español": { code: "es" },
    "Deutsch": { code: "de" },
  };

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
        const response = await fetch(`${API_BASE}/api/diagnostic`);
        if (response.ok) {
          const data = await response.json();
          setModelStatus({
            groq: data.groq_key_configured || false,
            gemini: data.gemini_key_configured || false,
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

  const tabs = [
    { id: 'settings', icon: '⚙️', label: 'Paramètres' },
    { id: 'history', icon: '📋', label: 'Historique', count: searchHistory?.length },
    { id: 'saved', icon: '⭐', label: 'Missions', count: savedMissions?.length },
    { id: 'tjm', icon: '💰', label: 'TJM' },
  ];

  return (
    <aside
      className="sidebar freelance-sidebar"
      style={{ width: collapsed ? '60px' : '320px', transition: 'width 0.3s ease' }}
    >
      {/* Logo */}
      <div
        className="sidebar-logo"
        style={{
          justifyContent: collapsed ? 'center' : 'space-between',
          padding: collapsed ? '16px 0' : '16px',
          background: 'linear-gradient(135deg, rgba(0,188,212,0.08) 0%, rgba(0,137,123,0.08) 100%)',
          borderRadius: '12px',
          marginBottom: '4px',
        }}
      >
        {!collapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.3rem' }}>🚀</span>
            <span
              style={{
                background: 'linear-gradient(135deg, #00bcd4, #00897b)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                fontWeight: '800',
                fontSize: '1rem',
              }}
            >
              FreelanceMissionAI
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
                  borderBottom: activeTab === tab.id ? '2px solid var(--freelance-primary)' : 'none',
                  color: activeTab === tab.id ? 'var(--freelance-primary)' : 'var(--text-secondary)',
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
                    background: 'var(--freelance-primary)', color: 'white',
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
                  <select className="select-control freelance-select" value={lang} onChange={(e) => setLang(e.target.value)}>
                    {Object.keys(LANGS_MAP).map(k => <option key={k} value={k}>{k}</option>)}
                  </select>
                </div>
              </div>

              <div className="sidebar-section">
                <h3 className="sidebar-section-title">
                  <Cpu size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                  Configuration IA
                </h3>
                <div className="form-group" style={{ marginBottom: '12px' }}>
                  <label>🔬 Analyse du profil</label>
                  <select className="select-control freelance-select" value={analysisEngine} onChange={(e) => setAnalysisEngine(e.target.value)}>
                    <option value="Gemini 3.5">Gemini 3.5</option>
                    <option value="Gemini 2.5">Gemini 2.5</option>
                    <option value="Groq / Llama 3.3">Groq / Llama 3.3</option>
                    <option value="Llama 3.2 (Local/dev)">Llama 3.2 (Local)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>⚖️ Tri & Proposition</label>
                  <select className="select-control freelance-select" value={rankingEngine} onChange={(e) => setRankingEngine(e.target.value)}>
                    <option value="Gemini 3.5">Gemini 3.5</option>
                    <option value="Gemini 2.5">Gemini 2.5</option>
                    <option value="Groq / Llama 3.3">Groq / Llama 3.3</option>
                    <option value="Llama 3.2 (Local/dev)">Llama 3.2 (Local)</option>
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
                      className="input-control freelance-input"
                      style={{ flexGrow: 1 }}
                      placeholder="Clé Gemini API..."
                      value={customGeminiKey}
                      onChange={(e) => { setCustomGeminiKey(e.target.value); setSaved(false); }}
                    />
                    <button
                      className="btn btn-freelance"
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
                    style={{ fontSize: '0.75rem', color: 'var(--freelance-primary)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}>
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
                    <div key={m.key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '7px 10px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
                      <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>{m.label}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {getStatusIcon(modelStatus[m.key])}
                        <span style={{ color: modelStatus[m.key] ? '#2e7d32' : '#c62828', fontSize: '0.75rem', fontWeight: '700' }}>
                          {getStatusText(modelStatus[m.key])}
                        </span>
                      </div>
                    </div>
                  ))}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '7px 10px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>Ollama (Local)</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {modelStatus.ollama ? <Wifi size={14} style={{ color: '#2e7d32' }} /> : <WifiOff size={14} style={{ color: '#c62828' }} />}
                      <span style={{ color: modelStatus.ollama ? '#2e7d32' : '#c62828', fontSize: '0.75rem', fontWeight: '700' }}>
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
              <h3 className="sidebar-section-title">📋 Historique des recherches</h3>
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
                      onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--freelance-primary)'; e.currentTarget.style.color = 'white'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--glass-bg)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
                    >
                      <div style={{ fontWeight: '600' }}>{item.query}</div>
                      <div style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '2px' }}>
                        {new Date(item.time).toLocaleDateString('fr-FR')} — {item.count} missions
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Saved Missions Tab */}
          {activeTab === 'saved' && (
            <div className="sidebar-section">
              <h3 className="sidebar-section-title">⭐ Missions sauvegardées</h3>
              {!savedMissions?.length ? (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                  Aucune mission sauvegardée
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '350px', overflowY: 'auto' }}>
                  {savedMissions.map((m, idx) => (
                    <a
                      key={idx} href={m.link} target="_blank" rel="noopener noreferrer"
                      style={{
                        padding: '8px 12px', background: 'var(--glass-bg)', border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-sm)', textDecoration: 'none', fontSize: '0.85rem',
                        color: 'var(--text-primary)', display: 'block', transition: 'all 0.2s',
                      }}
                    >
                      <div style={{ fontWeight: '600', fontSize: '0.82rem' }}>{m.title}</div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                        <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>{m.company || m.client}</span>
                        {m.tjm && <span style={{ fontSize: '0.75rem', color: 'var(--freelance-primary)', fontWeight: '700' }}>💰 {m.tjm}</span>}
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TJM Calculator Tab */}
          {activeTab === 'tjm' && (
            <div className="sidebar-section">
              <h3 className="sidebar-section-title">💰 Calculateur TJM</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div className="form-group">
                  <label>TJM minimum (€/jour)</label>
                  <input
                    type="number"
                    className="input-control freelance-input"
                    placeholder="ex: 350"
                    value={tjmMin || ''}
                    onChange={(e) => setTjmMin(e.target.value)}
                    min="0"
                    step="50"
                  />
                </div>
                <div className="form-group">
                  <label>TJM maximum (€/jour)</label>
                  <input
                    type="number"
                    className="input-control freelance-input"
                    placeholder="ex: 800"
                    value={tjmMax || ''}
                    onChange={(e) => setTjmMax(e.target.value)}
                    min="0"
                    step="50"
                  />
                </div>

                {recommendedTjm && (
                  <div style={{
                    padding: '14px',
                    background: 'linear-gradient(135deg, rgba(0,188,212,0.1), rgba(0,137,123,0.1))',
                    border: '1px solid rgba(0,188,212,0.25)',
                    borderRadius: '12px',
                    marginTop: '4px',
                  }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--freelance-primary)', fontWeight: '700', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      🤖 TJM recommandé par l'IA
                    </div>
                    <div style={{ fontSize: '1.6rem', fontWeight: '900', color: 'var(--freelance-dark)', letterSpacing: '-0.02em' }}>
                      {recommendedTjm} €/jour
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
                  💡 Analysez votre CV pour obtenir un TJM recommandé selon votre profil et les tendances du marché freelance.
                </div>
              </div>
            </div>
          )}

          <div className="sidebar-section" style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>FreelanceMissionAI v1.0</span>
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
          <DollarSign size={20} style={{ color: 'var(--freelance-primary)' }} />
        </div>
      )}
    </aside>
  );
}
