import React from 'react';
import { LANGS, STRINGS } from '../utils/translations';
import { Settings, Cpu, Key, Globe, LogIn } from 'lucide-react';

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
          <input
            type="password"
            className="input-control"
            placeholder="Clé Gemini API..."
            value={customGeminiKey}
            onChange={(e) => setCustomGeminiKey(e.target.value)}
          />
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {S.personal_key_help}
          </span>
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
