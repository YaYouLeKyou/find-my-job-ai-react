import React, { useState } from 'react';
import SEO from './SEO';
import HeaderButtons from './HeaderButtons';
import { LANGS, STRINGS } from '../utils/translations';
import { ArrowLeft, Search, Loader2, Briefcase, User, FileText, Star, Mail, Phone, MapPin } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "";

const WORKER_SOURCES = ['LinkedIn', 'Indeed', 'France Travail', 'Apec', 'Monster'];
const CONTRACT_TYPES = ['CDI', 'CDD', 'Stage', 'Alternance', 'Intérim', 'Temps partiel'];
const EXPERIENCE_LEVELS = ['Débutant', 'Junior (1-3 ans)', 'Confirmé (3-5 ans)', 'Senior (5-10 ans)', 'Expert (10+ ans)'];

export default function WorkerApp({ onBackToHub, lang, setLang }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [location, setLocation] = useState("France");
  const [contract, setContract] = useState("CDI");
  const [experience, setExperience] = useState("");
  const [remote, setRemote] = useState(false);
  const [selectedSources, setSelectedSources] = useState([...WORKER_SOURCES]);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchTime, setSearchTime] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleSearchCandidates = async () => {
    if (!searchQuery) return;
    const startTime = Date.now();
    setLoading(true);
    setError("");
    setCandidates([]);

    try {
      const response = await fetch(`${API_BASE}/api/search-jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: `recrute ${searchQuery} ${contract}`,
          location: remote ? '' : location,
          num_ads: 20,
          contract: contract,
          remote: remote,
          global_search: remote,
          selected_sources: selectedSources,
          sort_option: "Pertinence (IA)",
          ranking_engine: "Groq / Llama 3.3",
          lang_code: LANGS[lang].code,
          lang_label: LANGS[lang].label,
          cv_data: null
        })
      });

      if (!response.ok) throw new Error("Erreur de communication avec le serveur.");
      const data = await response.json();
      setCandidates(data.results || []);

      const endTime = Date.now();
      setSearchTime(((endTime - startTime) / 1000).toFixed(2));
      showToast(`✅ ${data.results?.length || 0} profils trouvés`, 'success');
    } catch (err) {
      console.error(err);
      setError(err.message);
      showToast(`❌ Erreur: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container" style={{ background: 'linear-gradient(135deg, rgba(255,111,0,0.03), rgba(255,143,0,0.03))' }}>
      <SEO
        title="Find My Worker AI - Recruit the Best Talent"
        description="Find the perfect candidates for your job openings with AI-powered recruitment. Post jobs and discover qualified talent."
        keywords="recruitment, hiring, employer, find workers, AI recruitment, FindMyJobAI"
      />

      {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}

      <main className="main-content">
        <button onClick={onBackToHub} className="btn btn-secondary" style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', padding: '8px 16px' }}>
          <ArrowLeft size={16} />
          Job Bridge
        </button>

        <HeaderButtons onToggleDarkMode={() => {
          const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
          if (isDark) { document.documentElement.removeAttribute('data-theme'); localStorage.setItem('darkMode', 'false'); }
          else { document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('darkMode', 'true'); }
        }} />

        <header className="header">
          <h1 style={{ color: 'var(--text-primary)', wordWrap: 'break-word', overflowWrap: 'break-word', WebkitTextStroke: '0.5px rgba(0, 0, 0, 0.15)', textShadow: '0 0 1px rgba(0, 0, 0, 0.1)' }}>
            👷 Find my worker AI
          </h1>
          <p style={{ color: 'var(--text-primary)', fontWeight: '500', opacity: 0.95 }}>
            Trouvez les meilleurs talents pour vos postes à pourvoir
          </p>
        </header>

        {/* Search Filters */}
        <div className="card" style={{ borderColor: 'rgba(255,111,0,0.2)' }}>
          <div className="card-title">
            <Briefcase size={20} style={{ color: '#ff6f00' }} />
            <span>Critères de recherche</span>
          </div>
          <div className="card-content">
            <div className="filters-row-1" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
              <div className="form-group">
                <label>📍 Localisation</label>
                <input type="text" className="input-control" value={location} onChange={e => setLocation(e.target.value)} placeholder="France, Paris..." />
              </div>
              <div className="form-group">
                <label>📋 Type de contrat</label>
                <select className="select-control" value={contract} onChange={e => setContract(e.target.value)}>
                  {CONTRACT_TYPES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>📊 Niveau d'expérience</label>
                <select className="select-control" value={experience} onChange={e => setExperience(e.target.value)}>
                  <option value="">Tous niveaux</option>
                  {EXPERIENCE_LEVELS.map(e => <option key={e} value={e}>{e}</option>)}
                </select>
              </div>
            </div>

            <div className="form-group" style={{ marginTop: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input type="checkbox" checked={remote} onChange={e => setRemote(e.target.checked)} style={{ accentColor: '#ff6f00' }} />
                🏠 Profils en télétravail uniquement
              </label>
            </div>

            <div className="form-group">
              <label>📡 Sources de recherche</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '4px' }}>
                {WORKER_SOURCES.map(src => (
                  <label key={src} style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.87rem' }}>
                    <input type="checkbox" checked={selectedSources.includes(src)}
                      onChange={(e) => setSelectedSources(prev => e.target.checked ? [...prev, src] : prev.filter(s => s !== src))}
                      style={{ accentColor: '#ff6f00' }} />
                    {src}
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Search Box */}
        <div className="card" style={{ borderColor: 'rgba(255,111,0,0.2)' }}>
          <div className="card-title">
            <Search size={20} style={{ color: '#ff6f00' }} />
            <span>Rechercher des candidats</span>
          </div>
          <div className="card-content">
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Décrivez le poste à pourvoir ou le profil recherché.
            </span>
            <div className="search-box-container">
              <div className="search-input-wrapper">
                <input type="text" className="input-control"
                  placeholder="Ex: Développeur React, Commercial, Comptable..."
                  value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleSearchCandidates(); }} />
                <Search size={18} className="search-icon-inside" />
              </div>
              <button className="btn" style={{ background: 'linear-gradient(135deg, #ff6f00, #ff8f00)', color: 'white', border: 'none' }}
                onClick={handleSearchCandidates} disabled={loading}>
                {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : 'Rechercher'}
              </button>
            </div>
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', padding: '40px 0' }}>
            <Loader2 size={48} style={{ animation: 'spin 1.5s linear infinite', color: '#ff6f00' }} />
            <span>Recherche de profils en cours...</span>
          </div>
        )}

        {error && <div className="alert alert-danger"><span>{error}</span></div>}

        {/* Results */}
        {candidates.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h2 style={{ fontSize: '1.4rem', fontWeight: '800', borderBottom: '2px solid #ff6f00', paddingBottom: '8px' }}>
              👥 Profils trouvés {searchTime && <span style={{ fontSize: '0.9rem', fontWeight: '400', color: 'var(--text-secondary)' }}>({searchTime}s)</span>}
            </h2>
            <div className="job-list">
              {candidates.map((candidate, idx) => (
                <div key={candidate.id || idx} className="card" style={{ borderColor: 'rgba(255,111,0,0.15)' }}>
                  <div className="card-content">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', flexWrap: 'wrap' }}>
                      <div style={{ flex: '1 1 auto' }}>
                        <h3 style={{ margin: '0 0 8px 0', fontSize: '1.1rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                          {candidate.title || 'Profil'}
                        </h3>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Briefcase size={14} /> {candidate.company || 'Non spécifié'}
                          </span>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <MapPin size={14} /> {candidate.location || 'Non spécifié'}
                          </span>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <FileText size={14} /> {candidate.source || 'Source inconnue'}
                          </span>
                        </div>
                      </div>
                      {candidate.link && candidate.link !== '#' && (
                        <a href={candidate.link} target="_blank" rel="noopener noreferrer"
                          className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '8px 16px', textDecoration: 'none', flexShrink: 0 }}>
                          Voir le profil →
                        </a>
                      )}
                    </div>
                    {candidate.desc && (
                      <p style={{ marginTop: '12px', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                        {candidate.desc.substring(0, 300)}{candidate.desc.length > 300 ? '...' : ''}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!loading && candidates.length === 0 && !error && (
          <div className="card" style={{ borderColor: 'rgba(255,111,0,0.1)', textAlign: 'center', padding: '40px' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
              🔍 Lancez une recherche pour découvrir des profils correspondant à votre poste
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="app-footer" style={{ background: 'rgba(255,111,0,0.05)', border: '1px solid rgba(255,111,0,0.15)' }}>
          <div className="app-footer-inner">
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              🤖 <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Gemini</span>
              <span style={{ opacity: 0.4 }}>·</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Groq</span>
              <span style={{ opacity: 0.4 }}>·</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Llama</span>
              <span style={{ opacity: 0.4 }}>·</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Ollama</span>
            </span>
            <span style={{ opacity: 0.3, fontWeight: '900' }}>|</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>by Yanès Hadiouche</span>
          </div>
        </div>
      </main>
    </div>
  );
}