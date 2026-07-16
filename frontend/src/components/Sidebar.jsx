import React, { useState, useEffect } from 'react';
import { LANGS, STRINGS } from '../utils/translations';
import { Settings, Cpu, Key, Globe, Save, ExternalLink, CheckCircle2, AlertCircle, ChevronLeft, ChevronRight, Wifi, WifiOff } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function Sidebar({
  lang,
  setLang,
  analysisEngine,
  setAnalysisEngine,
  rankingEngine,
  setRankingEngine,
  customGeminiKey,
  setCustomGeminiKey,
  ollamaOnline
}) {
  const S = STRINGS[LANGS[lang].code];
  const [saved, setSaved] = useState(!!customGeminiKey);
  const [collapsed, setCollapsed] = useState(false);
  const [modelStatus, setModelStatus] = useState({
    groq: false,
    gemini: false,
    xai: false,
    ollama: ollamaOnline
  });
  const [loadingStatus, setLoadingStatus] = useState(true);

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

  return (
    <aside className="sidebar" style={{ width: collapsed ? '60px' : '320px', transition: 'width 0.3s ease' }}>
      <div className="sidebar-logo" style={{ justifyContent: collapsed ? 'center' : 'space-between', padding: collapsed ? '16px 0' : '16px' }}>
        {!collapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings size={24} className="text-primary" />
            <span>FindMyJobAI</span>
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

      {!collapsed && (
        <>
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
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>Groq / Llama 3.3</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {getStatusIcon(modelStatus.groq)}
                  <span style={{ color: modelStatus.groq ? 'var(--success-color)' : 'var(--error-color)', fontSize: '0.75rem' }}>
                    {getStatusText(modelStatus.groq)}
                  </span>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>Gemini 3.5 / 2.5</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {getStatusIcon(modelStatus.gemini)}
                  <span style={{ color: modelStatus.gemini ? 'var(--success-color)' : 'var(--error-color)', fontSize: '0.75rem' }}>
                    {getStatusText(modelStatus.gemini)}
                  </span>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>xAI / Grok</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {getStatusIcon(modelStatus.xai)}
                  <span style={{ color: modelStatus.xai ? 'var(--success-color)' : 'var(--error-color)', fontSize: '0.75rem' }}>
                    {getStatusText(modelStatus.xai)}
                  </span>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>Ollama (Local)</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {modelStatus.ollama ? 
                    <Wifi size={14} style={{ color: 'var(--success-color)' }} /> : 
                    <WifiOff size={14} style={{ color: 'var(--error-color)' }} />
                  }
                  <span style={{ color: modelStatus.ollama ? 'var(--success-color)' : 'var(--error-color)', fontSize: '0.75rem' }}>
                    {modelStatus.ollama ? 'En ligne' : 'Hors ligne'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="sidebar-section" style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'center' }}>
              FindMyJobAI v2.0 React
            </div>
          </div>
        </>
      )}

      {collapsed && (
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
  );
}