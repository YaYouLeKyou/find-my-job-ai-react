import React, { useState } from 'react';
import { LANGS, STRINGS } from '../utils/translations';
import { Settings, Cpu, Key, Globe, LogIn, Save, ExternalLink, CheckCircle2, AlertCircle } from 'lucide-react';

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

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <Settings size={24} className="text-primary" />
        <span>FindMyJobAI</span>
      </div>

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
            <span style={{ fontSize: '0.75rem', color: 'var(--success-color)', display: 'flex', alignItems: 'center', gap: '4px' }}>
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

      <div className="sidebar-section" style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <span>Statut Ollama :</span>
          <span style={{ 
            display: 'inline-block', 
            width: '8px', 
            height: '8px', 
            borderRadius: '50%', 
            background: ollamaOnline ? 'var(--success-color)' : 'var(--error-color)' 
          }} />
        </div>
        <div style={{ marginTop: '8px', fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'center' }}>
          FindMyJobAI v2.0 React
        </div>
      </div>
    </aside>
  );
}
