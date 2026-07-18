import React, { useState, useEffect } from 'react';
import FreelanceSidebar from './FreelanceSidebar';
import CvUploader from './CvUploader';
import CvProfile from './CvProfile';
import FreelanceMissionCard from './FreelanceMissionCard';
import { Search, Loader2, RefreshCw, Key, ExternalLink, X, ArrowLeft, Briefcase } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "";

const FREELANCE_SOURCES = ['Malt', 'Upwork', 'Freelancer', 'Toptal', 'Codeur.com'];
const MISSION_TYPES = ['Développement', 'Design', 'Conseil', 'Rédaction', 'Marketing', 'Data', 'DevOps', 'Mobile'];
const DURATIONS = ['Court terme (< 1 mois)', 'Moyen terme (1-3 mois)', 'Long terme (> 3 mois)', 'Récurrent'];
const REMOTE_OPTIONS = ['Remote', 'Hybride', 'Présentiel'];

const generateFreelanceLinks = (query) => {
  const q = encodeURIComponent(query);
  return {
    'Malt': `https://www.malt.fr/s?q=${q}`,
    'Upwork': `https://www.upwork.com/search/jobs/?q=${q}`,
    'Freelancer': `https://www.freelancer.com/jobs/?keyword=${q}`,
    'Toptal': `https://www.toptal.com/freelance-jobs`,
    'Codeur.com': `https://www.codeur.com/projects?search=${q}`,
    'Comet (FR)': `https://app.comet.co/freelancer/search?query=${q}`,
    'Crème de la Crème': `https://cremedelacreme.io/fr/missions?query=${q}`,
    'Freelance Informatique': `https://www.freelance-informatique.fr/offres?q=${q}`,
    'Remote OK': `https://remoteok.com/remote-${encodeURIComponent(query.replace(/\s+/g,'-'))}-jobs`,
    'Guru': `https://www.guru.com/d/jobs/q/${q}/`,
  };
};

export default function FreelanceMissionApp({ onBackToHub }) {
  const [lang, setLang] = useState("Français");
  const [analysisEngine, setAnalysisEngine] = useState("Groq / Llama 3.3");
  const [rankingEngine, setRankingEngine] = useState("Groq / Llama 3.3");
  const [customGeminiKey, setCustomGeminiKey] = useState("");
  const [cvData, setCvData] = useState(null);

  // Search params
  const [searchQuery, setSearchQuery] = useState("");
  const [location, setLocation] = useState("France");
  const [numAds, setNumAds] = useState(10);
  const [remote, setRemote] = useState("Remote");
  const [missionType, setMissionType] = useState("");
  const [duration, setDuration] = useState("");
  const [selectedSources, setSelectedSources] = useState([...FREELANCE_SOURCES]);
  const [excludedSources, setExcludedSources] = useState([]);
  const [tjmMin, setTjmMin] = useState("");
  const [tjmMax, setTjmMax] = useState("");
  const [recommendedTjm, setRecommendedTjm] = useState(null);

  // Results & UI
  const [missions, setMissions] = useState([]);
  const [sourceCounts, setSourceCounts] = useState({});
  const [loadingMissions, setLoadingMissions] = useState(false);
  const [errorMissions, setErrorMissions] = useState("");
  const [searchTime, setSearchTime] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [searchHistory, setSearchHistory] = useState([]);
  const [savedMissions, setSavedMissions] = useState([]);
  const [toast, setToast] = useState(null);
  const [dismissKeyPrompt, setDismissKeyPrompt] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then(res => res.json())
      .catch(err => console.error("Backend not running:", err));

    fetch("https://ipapi.co/json/")
      .then(res => res.json())
      .then(data => { if (data.country_name) setLocation(data.country_name); })
      .catch(() => {});

    const savedHistory = localStorage.getItem('freelanceSearchHistory');
    if (savedHistory) setSearchHistory(JSON.parse(savedHistory));

    const savedMissionsData = localStorage.getItem('savedFreelanceMissions');
    if (savedMissionsData) setSavedMissions(JSON.parse(savedMissionsData));

    const darkMode = localStorage.getItem('darkMode');
    if (darkMode === 'true') document.documentElement.setAttribute('data-theme', 'dark');
  }, []);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleCvAnalysisSuccess = (data) => {
    setCvData(data);
    if (data.metier) setSearchQuery(data.metier);
    // Extract recommended TJM from AI analysis if available
    if (data.tjm_recommande) setRecommendedTjm(data.tjm_recommande);
    else if (data.experience) {
      // Estimate TJM from experience level
      const exp = (data.experience || '').toLowerCase();
      if (exp.includes('senior') || exp.includes('10') || exp.includes('expert')) setRecommendedTjm(650);
      else if (exp.includes('confirmé') || exp.includes('5') || exp.includes('6') || exp.includes('7')) setRecommendedTjm(500);
      else if (exp.includes('junior') || exp.includes('1') || exp.includes('2')) setRecommendedTjm(300);
      else setRecommendedTjm(420);
    }
  };

  const handleSelectMissionQuery = (query) => {
    setSearchQuery(query);
    handleSearchMissions(query);
  };

  const handleSearchMissions = async (customQuery) => {
    const activeQuery = customQuery || searchQuery;
    if (!activeQuery) return;

    const startTime = Date.now();
    setLoadingMissions(true);
    setErrorMissions("");
    setMissions([]);
    setSourceCounts({});
    setExcludedSources([]);
    setCurrentPage(1);

    // Build query with freelance context
    const freelanceQuery = `freelance mission ${activeQuery} ${missionType ? missionType : ''}`.trim();

    // Map freelance source names to real backend-supported sources
    const sourceMap = {
      'Malt': 'Indeed',
      'Upwork': 'LinkedIn',
      'Freelancer': 'Glassdoor',
      'Toptal': 'Google Jobs',
      'Codeur.com': 'Monster',
    };
    const mappedSources = selectedSources.map(s => sourceMap[s] || s);

    try {
      const response = await fetch(`${API_BASE}/api/search-jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: freelanceQuery,
          location: remote === 'Remote' ? '' : location,
          num_ads: numAds,
          contract: "Freelance",
          remote: remote === 'Remote',
          global_search: remote === 'Remote',
          selected_sources: mappedSources,
          sort_option: "Pertinence (IA)",
          ranking_engine: rankingEngine,
          custom_gemini_key: customGeminiKey || null,
          lang_code: "fr",
          lang_label: "français",
          cv_data: cvData,
          is_freelance: true,
          tjm_min: tjmMin ? parseInt(tjmMin) : null,
          tjm_max: tjmMax ? parseInt(tjmMax) : null,
        })
      });

      if (!response.ok) throw new Error("Erreur de communication avec le serveur.");

      const data = await response.json();
      setMissions(data.results || []);
      setSourceCounts(data.source_counts || {});

      const endTime = Date.now();
      const dur = ((endTime - startTime) / 1000).toFixed(2);
      setSearchTime(dur);

      const newHistory = [
        { query: activeQuery, time: new Date().toISOString(), count: data.results?.length || 0 },
        ...searchHistory.filter(h => h.query !== activeQuery)
      ].slice(0, 10);
      setSearchHistory(newHistory);
      localStorage.setItem('freelanceSearchHistory', JSON.stringify(newHistory));

      showToast(`✅ ${data.results?.length || 0} missions trouvées en ${dur}s`, 'success');
    } catch (err) {
      console.error(err);
      setErrorMissions(err.message);
      showToast(`❌ Erreur: ${err.message}`, 'error');
    } finally {
      setLoadingMissions(false);
    }
  };

  const toggleSaveMission = (mission) => {
    const isSaved = savedMissions.some(m => m.id === mission.id);
    let next;
    if (isSaved) {
      next = savedMissions.filter(m => m.id !== mission.id);
      showToast('Mission retirée des favoris', 'info');
    } else {
      next = [...savedMissions, mission];
      showToast('⭐ Mission sauvegardée', 'success');
    }
    setSavedMissions(next);
    localStorage.setItem('savedFreelanceMissions', JSON.stringify(next));
  };

  const toggleSourceExclusion = (src) => {
    setExcludedSources(prev =>
      prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]
    );
  };

  const toggleDarkMode = () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (isDark) {
      document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('darkMode', 'false');
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('darkMode', 'true');
    }
  };

  const exportToCSV = () => {
    if (!missions.length) { showToast('Aucune mission à exporter', 'error'); return; }
    const headers = ['Titre', 'Client', 'Source', 'TJM', 'Durée', 'Remote', 'Score', 'Lien'];
    const csvContent = [
      headers.join(','),
      ...missions.map(m => [
        `"${m.title || ''}"`, `"${m.company || ''}"`, `"${m.source || ''}"`,
        `"${m.tjm || ''}"`, `"${m.duration || ''}"`,
        m.remote ? 'Oui' : 'Non', m.match_score || '', `"${m.link || ''}"`
      ].join(','))
    ].join('\n');

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `missions_${searchQuery.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    showToast('📊 CSV exporté', 'success');
  };

  const directLinks = searchQuery ? generateFreelanceLinks(searchQuery) : {};

  const displayedMissions = missions.filter(m => !excludedSources.includes(m.source));
  const indexOfLast = currentPage * itemsPerPage;
  const indexOfFirst = indexOfLast - itemsPerPage;
  const currentMissions = displayedMissions.slice(indexOfFirst, indexOfLast);
  const totalPages = Math.ceil(displayedMissions.length / itemsPerPage);

  const chips = [];
  if (cvData) {
    if (cvData.metier) chips.push(cvData.metier);
    if (cvData.recommandations_metiers) cvData.recommandations_metiers.slice(0, 3).forEach(r => { if (!chips.includes(r)) chips.push(r); });
  }

  return (
    <div className="app-container freelance-app">
      {/* Toast */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.message}
        </div>
      )}

      {/* Sidebar */}
      <FreelanceSidebar
        lang={lang} setLang={setLang}
        analysisEngine={analysisEngine} setAnalysisEngine={setAnalysisEngine}
        rankingEngine={rankingEngine} setRankingEngine={setRankingEngine}
        customGeminiKey={customGeminiKey} setCustomGeminiKey={setCustomGeminiKey}
        searchHistory={searchHistory}
        savedMissions={savedMissions}
        onSelectHistory={handleSelectMissionQuery}
        onToggleDarkMode={toggleDarkMode}
        tjmMin={tjmMin} setTjmMin={setTjmMin}
        tjmMax={tjmMax} setTjmMax={setTjmMax}
        recommendedTjm={recommendedTjm}
      />

      {/* Main Content */}
      <main className="main-content">
        {/* Back to Hub Button */}
        <button
          onClick={onBackToHub}
          className="btn btn-secondary"
          style={{
            alignSelf: 'flex-start',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.85rem',
            padding: '8px 16px',
          }}
        >
          <ArrowLeft size={16} />
          Find my work AI
        </button>

        {/* Header */}
        <header className="header">
          <h1 style={{
            color: 'var(--text-primary)',
            wordWrap: 'break-word',
            overflowWrap: 'break-word',
            WebkitTextStroke: '0.5px rgba(0, 0, 0, 0.15)',
            textShadow: '0 0 1px rgba(0, 0, 0, 0.1)',
          }}>
            🚀 Find my freelance mission AI
          </h1>
          <p style={{
            color: 'var(--text-primary)',
            fontWeight: '500',
            opacity: 0.95
          }}>Trouvez des missions freelance adaptées à votre profil grâce à l'IA</p>
        </header>

        {/* API Key prompt */}
        {!customGeminiKey && !dismissKeyPrompt && (
          <div className="alert alert-info" style={{
            background: 'linear-gradient(135deg, rgba(0,188,212,0.1), rgba(0,137,123,0.06))',
            border: '1px solid rgba(0,188,212,0.25)',
            padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', borderRadius: 'var(--radius-md)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '1 1 auto' }}>
              <Key size={22} style={{ color: 'var(--freelance-primary)', flexShrink: 0 }} />
              <div>
                <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Clé API Gemini manquante</span>
                <span style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  Ajoutez votre clé personnelle dans le panneau latéral pour utiliser Gemini (recommandé).
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
              <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="btn btn-freelance"
                style={{ textDecoration: 'none', fontSize: '0.85rem', padding: '10px 16px', whiteSpace: 'nowrap' }}>
                <ExternalLink size={14} /> Obtenir une clé gratuite
              </a>
              <button className="btn btn-secondary" style={{ padding: '10px 12px' }} onClick={() => setDismissKeyPrompt(true)}>
                <X size={14} />
              </button>
            </div>
          </div>
        )}

        {/* CV Uploader */}
        <CvUploader
          lang={lang}
          analysisEngine={analysisEngine}
          customGeminiKey={customGeminiKey}
          onAnalysisSuccess={handleCvAnalysisSuccess}
        />

        {/* CV Profile */}
        {cvData && (
          <CvProfile
            lang={lang}
            cvData={cvData}
            onSelectJobQuery={handleSelectMissionQuery}
          />
        )}

        {/* Freelance Filters */}
        <div className="card freelance-card-wrapper">
          <div className="card-title">
            <Briefcase size={20} style={{ color: 'var(--freelance-primary)' }} />
            <span>Filtres de mission</span>
          </div>
          <div className="card-content">
            <div className="filters-row-1" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
              <div className="form-group">
                <label>📍 Localisation</label>
                <input type="text" className="input-control freelance-input" value={location} onChange={e => setLocation(e.target.value)} placeholder="France, Paris..." />
              </div>
              <div className="form-group">
                <label>🏠 Mode de travail</label>
                <select className="select-control freelance-select" value={remote} onChange={e => setRemote(e.target.value)}>
                  {REMOTE_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>⏱️ Durée de mission</label>
                <select className="select-control freelance-select" value={duration} onChange={e => setDuration(e.target.value)}>
                  <option value="">Toutes durées</option>
                  {DURATIONS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
            </div>

            <div className="filters-row-1" style={{ gridTemplateColumns: '1fr 1fr 1fr 1fr' }}>
              <div className="form-group">
                <label>🎯 Type de mission</label>
                <select className="select-control freelance-select" value={missionType} onChange={e => setMissionType(e.target.value)}>
                  <option value="">Tous types</option>
                  {MISSION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>💰 TJM min (€/j)</label>
                <input type="number" className="input-control freelance-input" placeholder="350" value={tjmMin} onChange={e => setTjmMin(e.target.value)} min="0" step="50" />
              </div>
              <div className="form-group">
                <label>💰 TJM max (€/j)</label>
                <input type="number" className="input-control freelance-input" placeholder="800" value={tjmMax} onChange={e => setTjmMax(e.target.value)} min="0" step="50" />
              </div>
              <div className="form-group">
                <label>📊 Nombre de résultats</label>
                <select className="select-control freelance-select" value={numAds} onChange={e => setNumAds(parseInt(e.target.value))}>
                  {[5, 10, 20, 30, 50].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
            </div>

            {/* Source selector */}
            <div className="form-group">
              <label>📡 Plateformes freelance</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '4px' }}>
                {FREELANCE_SOURCES.map(src => (
                  <label key={src} style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.87rem' }}>
                    <input
                      type="checkbox"
                      checked={selectedSources.includes(src)}
                      onChange={(e) => setSelectedSources(prev => e.target.checked ? [...prev, src] : prev.filter(s => s !== src))}
                      style={{ accentColor: 'var(--freelance-primary)' }}
                    />
                    {src}
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Search box */}
        <div className="card">
          <div className="card-title">
            <Search size={20} style={{ color: 'var(--freelance-primary)' }} />
            <span>Recherche de missions</span>
          </div>
          <div className="card-content">
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Décrivez votre expertise ou le type de mission recherché.
            </span>

            {chips.length > 0 && (
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', margin: '8px 0' }}>
                {chips.map((chip, idx) => (
                  <button key={idx} className="btn-chip btn-chip-freelance" onClick={() => handleSelectMissionQuery(chip)}>
                    {chip}
                  </button>
                ))}
              </div>
            )}

            <div className="search-box-container">
              <div className="search-input-wrapper">
                <input
                  type="text"
                  className="input-control freelance-input"
                  placeholder="Ex: Développeur React, Consultant Data, UX Designer..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleSearchMissions(); }}
                />
                <Search size={18} className="search-icon-inside" />
              </div>
              <button
                className="btn btn-freelance"
                onClick={() => handleSearchMissions()}
                disabled={loadingMissions}
              >
                {loadingMissions ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : 'Rechercher'}
              </button>
            </div>
          </div>
        </div>

        {/* Source Scan Status */}
        {Object.keys(sourceCounts).length > 0 && (
          <div className="card">
            <div className="card-title"><span>📊 Résultats par plateforme</span></div>
            <div className="card-content">
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Cliquez pour inclure/exclure une source.</span>
              <div className="dashboard-grid">
                {Object.entries(sourceCounts).map(([src, count]) => {
                  const isExcluded = excludedSources.includes(src);
                  return (
                    <button key={src} className={`dashboard-btn ${isExcluded ? 'excluded' : 'active'}`} onClick={() => toggleSourceExclusion(src)}>
                      <span>{isExcluded ? '❌' : '✅'} {src}</span>
                      <span>({count})</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Direct Links */}
        {searchQuery && (
          <div className="card">
            <div className="card-title"><span>🚀 Accès direct aux plateformes</span></div>
            <div className="card-content">
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
                Accès optimisé aux plateformes freelance pour votre recherche :
              </span>
              <div className="direct-links-grid">
                {Object.entries(directLinks).map(([name, url]) => (
                  <a key={name} href={url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary"
                    style={{ textDecoration: 'none', textAlign: 'center', borderColor: 'rgba(0,188,212,0.2)' }}>
                    🔍 {name}
                  </a>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Loading */}
        {loadingMissions && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', padding: '40px 0' }}>
            <Loader2 size={48} style={{ animation: 'spin 1.5s linear infinite', color: 'var(--freelance-primary)' }} />
            <span>Scan des plateformes freelance en cours...</span>
          </div>
        )}

        {errorMissions && <div className="alert alert-danger"><span>{errorMissions}</span></div>}

        {/* Results */}
        {displayedMissions.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
              <h2 style={{ fontSize: '1.4rem', fontWeight: '800', borderBottom: '2px solid var(--freelance-primary)', paddingBottom: '8px', flex: '1 1 auto' }}>
                🎯 Missions recommandées par l'IA {searchTime && <span style={{ fontSize: '0.9rem', fontWeight: '400', color: 'var(--text-secondary)' }}>({searchTime}s)</span>}
              </h2>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button onClick={exportToCSV} className="btn btn-secondary" style={{ fontSize: '0.85rem' }}>📊 Exporter CSV</button>
                <button onClick={toggleDarkMode} className="btn btn-secondary" style={{ fontSize: '0.85rem' }}>🌓 Mode</button>
              </div>
            </div>

            <div className="job-list">
              {currentMissions.map(mission => (
                <FreelanceMissionCard
                  key={mission.id}
                  mission={mission}
                  cvData={cvData}
                  rankingEngine={rankingEngine}
                  customGeminiKey={customGeminiKey}
                  onSaveMission={toggleSaveMission}
                  isSaved={savedMissions.some(m => m.id === mission.id)}
                />
              ))}
            </div>

            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '24px', flexWrap: 'wrap' }}>
                <button className="btn btn-secondary" onClick={() => { setCurrentPage(p => p - 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }} disabled={currentPage === 1} style={{ padding: '8px 16px' }}>
                  ← Précédent
                </button>
                <span style={{ display: 'flex', alignItems: 'center', padding: '0 12px', fontWeight: '600' }}>
                  Page {currentPage} / {totalPages}
                </span>
                <button className="btn btn-secondary" onClick={() => { setCurrentPage(p => p + 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }} disabled={currentPage === totalPages} style={{ padding: '8px 16px' }}>
                  Suivant →
                </button>
              </div>
            )}
          </div>
        )}

        {!loadingMissions && missions.length > 0 && displayedMissions.length === 0 && (
          <div className="alert alert-info">⚠️ Aucune mission visible avec ces filtres de sources.</div>
        )}

        {/* Footer */}
        <div className="app-footer" style={{ background: 'rgba(0, 188, 212, 0.05)', border: '1px solid rgba(0, 188, 212, 0.15)' }}>
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
