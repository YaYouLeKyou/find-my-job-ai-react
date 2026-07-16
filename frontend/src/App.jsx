import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import CvUploader from './components/CvUploader';
import CvProfile from './components/CvProfile';
import JobFilters from './components/JobFilters';
import JobCard from './components/JobCard';
import { LANGS, STRINGS } from './utils/translations';
import { Search, Loader2, RefreshCw, Key, ExternalLink, X } from 'lucide-react';
import './styles/global.css';

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function App() {
  // Global States
  const [lang, setLang] = useState("Français");
  const [analysisEngine, setAnalysisEngine] = useState("Groq / Llama 3.3");
  const [rankingEngine, setRankingEngine] = useState("Groq / Llama 3.3");
  const [customGeminiKey, setCustomGeminiKey] = useState("");
  const [cvData, setCvData] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [location, setLocation] = useState("Paris, France");
  const [numAds, setNumAds] = useState(10);
  const [sortOption, setSortOption] = useState("Pertinence (IA)");
  const [contract, setContract] = useState("CDI");
  const [remote, setRemote] = useState(false);
  const [globalSearch, setGlobalSearch] = useState(false);
  const [selectedSources, setSelectedSources] = useState([
    "LinkedIn", "Indeed", "France Travail", "Google Jobs", "Adzuna",
    "Jooble", "Glassdoor", "ZipRecruiter", "Simplyhired", "Careerbuilder", "Monster"
  ]);
  const [excludedSources, setExcludedSources] = useState([]);
  
  const [dismissKeyPrompt, setDismissKeyPrompt] = useState(false);

  // Results & UI states
  const [jobs, setJobs] = useState([]);
  const [sourceCounts, setSourceCounts] = useState({});
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [errorJobs, setErrorJobs] = useState("");
  const [ollamaOnline, setOllamaOnline] = useState(false);
  const [searchTime, setSearchTime] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [searchHistory, setSearchHistory] = useState([]);
  const [savedJobs, setSavedJobs] = useState([]);
  const [toast, setToast] = useState(null);

  const currentLangCode = LANGS[lang].code;
  const S = STRINGS[currentLangCode];

  // Startup configurations
  useEffect(() => {
    // Check local backend health (Ollama online status)
    fetch(`${API_BASE}/api/health`)
      .then(res => res.json())
      .then(data => {
        setOllamaOnline(data.ollama_online);
      })
      .catch(err => console.error("Backend not running or unreachable:", err));

    // Geolocate user via IP
    fetch("https://ipapi.co/json/")
      .then(res => res.json())
      .then(data => {
        if (data.city && data.country_name) {
          setLocation(`${data.city}, ${data.country_name}`);
        }
      })
      .catch(err => console.error("Geolocation failed:", err));

    // Load search history from localStorage
    const savedHistory = localStorage.getItem('searchHistory');
    if (savedHistory) {
      setSearchHistory(JSON.parse(savedHistory));
    }

    // Load saved jobs from localStorage
    const savedJobsData = localStorage.getItem('savedJobs');
    if (savedJobsData) {
      setSavedJobs(JSON.parse(savedJobsData));
    }

    // Load dark mode preference
    const darkMode = localStorage.getItem('darkMode');
    if (darkMode === 'true') {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }, []);

  // Set default query and details on CV analysis success
  const handleCvAnalysisSuccess = (data) => {
    setCvData(data);
    if (data.metier) {
      setSearchQuery(data.metier);
    }
  };

  const handleSelectJobQuery = (query) => {
    setSearchQuery(query);
    // Trigger immediate search
    handleSearchJobs(query);
  };

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleSearchJobs = async (customQuery) => {
    const activeQuery = customQuery || searchQuery;
    if (!activeQuery) return;

    const startTime = Date.now();
    setLoadingJobs(true);
    setErrorJobs("");
    setJobs([]);
    setSourceCounts({});
    setExcludedSources([]);
    setCurrentPage(1);

    try {
      const response = await fetch(`${API_BASE}/api/search-jobs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query: activeQuery,
          location: globalSearch ? "" : location,
          num_ads: numAds,
          contract: contract,
          remote: remote,
          global_search: globalSearch,
          selected_sources: selectedSources,
          sort_option: S.sort_relevant,
          ranking_engine: rankingEngine,
          custom_gemini_key: customGeminiKey || null,
          lang_code: currentLangCode,
          lang_label: LANGS[lang].label,
          cv_data: cvData
        })
      });

      if (!response.ok) {
        throw new Error("Erreur de communication avec le serveur d'offres.");
      }

      const data = await response.json();
      setJobs(data.results || []);
      setSourceCounts(data.source_counts || {});
      
      // Calculate search time
      const endTime = Date.now();
      const duration = ((endTime - startTime) / 1000).toFixed(2);
      setSearchTime(duration);

      // Add to search history
      const newHistory = [{ query: activeQuery, time: new Date().toISOString(), count: data.results?.length || 0 }, ...searchHistory.filter(h => h.query !== activeQuery)].slice(0, 10);
      setSearchHistory(newHistory);
      localStorage.setItem('searchHistory', JSON.stringify(newHistory));

      showToast(`✅ ${data.results?.length || 0} offres trouvées en ${duration}s`, 'success');
    } catch (err) {
      console.error(err);
      setErrorJobs(err.message);
      showToast(`❌ Erreur: ${err.message}`, 'error');
    } finally {
      setLoadingJobs(false);
    }
  };

  const toggleSourceExclusion = (source) => {
    if (excludedSources.includes(source)) {
      setExcludedSources(excludedSources.filter(s => s !== source));
    } else {
      setExcludedSources([...excludedSources, source]);
    }
  };

  const toggleSaveJob = (job) => {
    const isSaved = savedJobs.some(j => j.id === job.id);
    let newSavedJobs;
    if (isSaved) {
      newSavedJobs = savedJobs.filter(j => j.id !== job.id);
      showToast('Offre retirée des favoris', 'info');
    } else {
      newSavedJobs = [...savedJobs, job];
      showToast('⭐ Offre sauvegardée', 'success');
    }
    setSavedJobs(newSavedJobs);
    localStorage.setItem('savedJobs', JSON.stringify(newSavedJobs));
  };

  const exportToCSV = () => {
    if (jobs.length === 0) {
      showToast('Aucune offre à exporter', 'error');
      return;
    }

    const headers = ['Titre', 'Entreprise', 'Source', 'Localisation', 'Date', 'Score', 'Lien'];
    const csvContent = [
      headers.join(','),
      ...jobs.map(job => [
        `"${job.title || ''}"`,
        `"${job.company || ''}"`,
        `"${job.source || ''}"`,
        `"${job.location || ''}"`,
        `"${job.date || ''}"`,
        job.match_score || '',
        `"${job.link || ''}"`
      ].join(','))
    ].join('\n');

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `offres_${searchQuery.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    showToast('📊 CSV exporté avec succès', 'success');
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

  // Direct access link utility
  const generateJobSearchLinks = (jobTitle, langCode) => {
    const q = encodeURIComponent(jobTitle);
    const qSlug = q.replace(/%20/g, '-');
    const links = {
      fr: {
        "Welcome to the Jungle": `https://www.welcometothejungle.com/fr/jobs?query=${q}`,
        "HelloWork": `https://www.hellowork.com/fr-fr/emploi/recherche.html?k=${q}`,
        "Service Public": `https://www.choisirleservicepublic.gouv.fr/nos-offres/filtres/mots-cles/${q}/`,
        "Indeed France": `https://fr.indeed.com/jobs?q=${q}`,
        "Glassdoor FR": `https://www.glassdoor.fr/emploi/emploi.htm?sc.keyword=${q}`,
        "APEC": `https://www.apec.fr/offres-d-emploi-cadre/recherche.html?motsCles=${q}`,
        "Monster FR": `https://www.monster.fr/emploi/recherche?q=${q}`,
        "LinkedIn FR": `https://fr.linkedin.com/jobs/search/?keywords=${q}`,
        "Pôle Emploi": `https://candidat.pole-emploi.fr/offres/recherche?motsCles=${q}`,
        "JobTeaser": `https://www.jobteaser.com/fr/jobs?query=${q}`
      },
      en: {
        "LinkedIn US": `https://www.linkedin.com/jobs/search/?keywords=${q}`,
        "Reed.co.uk": `https://www.reed.co.uk/jobs/${qSlug}-jobs`,
        "Dice (Tech US)": `https://www.dice.com/jobs?q=${q}`,
        "Indeed US": `https://www.indeed.com/jobs?q=${q}`,
        "Glassdoor US": `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${q}`,
        "Monster US": `https://www.monster.com/jobs/search?q=${q}`,
        "CareerBuilder": `https://www.careerbuilder.com/jobs?q=${q}`,
        "SimplyHired": `https://www.simplyhired.com/jobs?q=${q}`,
        "ZipRecruiter": `https://www.ziprecruiter.com/jobs/search?search=${q}`,
        "Google Jobs": `https://www.google.com/search?q=${q}+jobs&ibp=htl;jobs`
      },
      es: {
        "InfoJobs ES": `https://www.infojobs.net/jobsearch/search-results.xhtml?keywords=${q}`,
        "Tecnoempleo": `https://www.tecnoempleo.com/busqueda-empleo.php?te=${q}`,
        "Turijobs": `https://www.turijobs.com/ofertas-trabajo/${qSlug}`,
        "LinkedIn ES": `https://es.linkedin.com/jobs/search/?keywords=${q}`,
        "Indeed ES": `https://es.indeed.com/jobs?q=${q}`,
        "Glassdoor ES": `https://www.glassdoor.es/empleo/empleo.htm?sc.keyword=${q}`,
        "Monster ES": `https://www.monster.es/empleo/buscar?q=${q}`,
        "JobisJob": `https://www.jobisjob.es/buscar/empleo?q=${q}`
      },
      de: {
        "Xing DE": `https://www.xing.com/jobs/search?keywords=${q}`,
        "StepStone DE": `https://www.stepstone.de/jobs/${qSlug}`,
        "Honeypot.io": `https://app.honeypot.io/vacancies?q=${q}`,
        "LinkedIn DE": `https://de.linkedin.com/jobs/search/?keywords=${q}`,
        "Indeed DE": `https://de.indeed.com/jobs?q=${q}`,
        "Glassdoor DE": `https://www.glassdoor.de/Job/jobs.htm?sc.keyword=${q}`,
        "Monster DE": `https://www.monster.de/jobs/suche?q=${q}`,
        "Jobvector": `https://www.jobvector.de/jobs?keywords=${q}`
      },
      ar: {
        "Bayt (Middle East)": `https://www.bayt.com/en/international/jobs/?keyword=${q}`,
        "GulfTalent": `https://www.gulftalent.com/jobs/search?q=${q}`,
        "Naukrigulf": `https://www.naukrigulf.com/${q}-jobs`,
        "LinkedIn AR": `https://ar.linkedin.com/jobs/search/?keywords=${q}`,
        "Indeed AE": `https://ae.indeed.com/jobs?q=${q}`,
        "Glassdoor AE": `https://www.glassdoor.ae/Job/jobs.htm?sc.keyword=${q}`
      },
      ja: {
        "Indeed Japan": `https://jp.indeed.com/jobs?q=${q}`,
        "Mynavi Tenshoku": `https://tenshoku.mynavi.jp/list/kw${q}/`,
        "Rikunabi Next": `https://next.rikunabi.com/rnc/docs/cp_s0070.jsp?sayonama_word=${q}`,
        "LinkedIn JP": `https://jp.linkedin.com/jobs/search/?keywords=${q}`,
        "Green": `https://www.green-japan.com/search?keyword=${q}`,
        "Daijob": `https://www.daijob.com/en/jobs/search?keywords=${q}`
      },
      zh: {
        "51job": `https://search.51job.com/list/000000,000000,0000,00,9,99,${q},2,1.html`,
        "Liepin": `https://www.liepin.com/zhaopin/?key=${q}`,
        "Zhaopin": `https://sou.zhaopin.com/?jl=489&kw=${q}&kt=3`,
        "LinkedIn CN": `https://cn.linkedin.com/jobs/search/?keywords=${q}`,
        "Indeed CN": `https://cn.indeed.com/jobs?q=${q}`,
        "Boss Zhipin": `https://www.zhipin.com/web/geek/job?query=${q}`
      }
    };
    const globalLinks = {
      "Remote OK": `https://remoteok.com/remote-${qSlug}-jobs`,
      "Indeed Global": `https://www.indeed.com/jobs?q=${q}`,
      "LinkedIn Global": `https://www.linkedin.com/jobs/search/?keywords=${q}`,
      "Glassdoor Global": `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${q}`,
      "Monster Global": `https://www.monster.com/jobs/search?q=${q}`,
      "CareerBuilder": `https://www.careerbuilder.com/jobs?q=${q}`,
      "SimplyHired": `https://www.simplyhired.com/jobs?q=${q}`,
      "ZipRecruiter": `https://www.ziprecruiter.com/jobs/search?search=${q}`,
      "Google Jobs": `https://www.google.com/search?q=${q}+jobs&ibp=htl;jobs`,
      "France Travail (API)": `https://candidat.pole-emploi.fr/offres/recherche?motsCles=${q}&offresPartenaires=true`,
      "Adzuna (API)": `https://www.adzuna.fr/emploi?q=${q}`,
      "Jooble (API)": `https://fr.jooble.org/emploi-${qSlug}`,
      "SerpApi Google Jobs": `https://www.google.com/search?q=${q}+jobs&ibp=htl;jobs`,
      "Apify LinkedIn": `https://www.linkedin.com/jobs/search/?keywords=${q}`
    };
    return { ...(links[langCode] || {}), ...globalLinks };
  };

  const directLinks = searchQuery ? generateJobSearchLinks(searchQuery, currentLangCode) : {};

  // Filter jobs by excluded sources
  const displayedJobs = jobs.filter(job => !excludedSources.includes(job.source));

  // Pagination
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentJobs = displayedJobs.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(displayedJobs.length / itemsPerPage);

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Get dynamic chips (primary job and recommendations)
  const chips = [];
  if (cvData) {
    if (cvData.metier) chips.push(cvData.metier);
    if (cvData.recommandations_metiers) {
      cvData.recommandations_metiers.slice(0, 3).forEach(r => {
        if (!chips.includes(r)) chips.push(r);
      });
    }
  }

  return (
    <div className="app-container">
      {/* Toast Notification */}
      {toast && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          padding: '16px 24px',
          borderRadius: 'var(--radius-md)',
          background: toast.type === 'success' ? 'var(--success-color)' : toast.type === 'error' ? 'var(--error-color)' : 'var(--primary-color)',
          color: 'white',
          fontWeight: '600',
          zIndex: 1000,
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          animation: 'slideIn 0.3s ease'
        }}>
          {toast.message}
        </div>
      )}

      {/* Sidebar Setting Controls */}
      <Sidebar
        lang={lang}
        setLang={setLang}
        analysisEngine={analysisEngine}
        setAnalysisEngine={setAnalysisEngine}
        rankingEngine={rankingEngine}
        setRankingEngine={setRankingEngine}
        customGeminiKey={customGeminiKey}
        setCustomGeminiKey={setCustomGeminiKey}
        ollamaOnline={ollamaOnline}
        searchHistory={searchHistory}
        savedJobs={savedJobs}
        onSelectHistory={handleSelectJobQuery}
        onToggleDarkMode={toggleDarkMode}
      />

      {/* Main Container */}
      <main className="main-content">
        <header className="header">
          <h1>{S.title}</h1>
          <p>{S.subtitle}</p>
        </header>

        {/* Gemini Key Prompt - visible when no key is set */}
        {!customGeminiKey && !dismissKeyPrompt && (
          <div className="alert alert-info" style={{
            background: 'linear-gradient(135deg, rgba(124,77,255,0.12), rgba(68,138,255,0.08))',
            border: '1px solid rgba(124,77,255,0.25)',
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            flexWrap: 'wrap',
            borderRadius: 'var(--radius-md)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '1 1 auto' }}>
              <Key size={22} style={{ color: 'var(--primary-color)', flexShrink: 0 }} />
              <div>
                <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                  Clé API Gemini manquante
                </span>
                <span style={{
                  display: 'block',
                  fontSize: '0.8rem',
                  color: 'var(--text-secondary)',
                  marginTop: '2px'
                }}>
                  Ajoutez votre clé personnelle dans le panneau latéral pour utiliser Gemini 3.5 / 2.5 (recommandé).
                  Sans clé, seuls les modèles Groq et locaux sont disponibles.
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
                style={{ textDecoration: 'none', fontSize: '0.85rem', padding: '10px 16px', whiteSpace: 'nowrap' }}
              >
                <ExternalLink size={14} />
                Obtenir une clé gratuite
              </a>
              <button
                className="btn btn-secondary"
                style={{ padding: '10px 12px' }}
                onClick={() => setDismissKeyPrompt(true)}
                title="Ignorer"
              >
                <X size={14} />
              </button>
            </div>
          </div>
        )}

        {/* Drag and Drop PDF Uploader */}
        <CvUploader
          lang={lang}
          analysisEngine={analysisEngine}
          customGeminiKey={customGeminiKey}
          onAnalysisSuccess={handleCvAnalysisSuccess}
        />

        {/* Profile Details section */}
        {cvData && (
          <CvProfile
            lang={lang}
            cvData={cvData}
            onSelectJobQuery={handleSelectJobQuery}
          />
        )}

        {/* Search Job filters & input */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <JobFilters
            lang={lang}
            numAds={numAds}
            setNumAds={setNumAds}
            sortOption={sortOption}
            setSortOption={setSortOption}
            contract={contract}
            setContract={setContract}
            remote={remote}
            setRemote={setRemote}
            globalSearch={globalSearch}
            setGlobalSearch={setGlobalSearch}
            location={location}
            setLocation={setLocation}
            selectedSources={selectedSources}
            setSelectedSources={setSelectedSources}
            onRefresh={() => handleSearchJobs()}
          />

          <div className="card">
            <div className="card-title">
              <Search size={20} style={{ color: 'var(--primary-color)' }} />
              <span>{S.search_section}</span>
            </div>

            <div className="card-content">
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {S.search_info}
              </span>

              {/* Chips Suggestions */}
              {chips.length > 0 && (
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', margin: '8px 0' }}>
                  {chips.map((chip, idx) => (
                    <button
                      key={idx}
                      className="btn-chip"
                      onClick={() => handleSelectJobQuery(chip)}
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              )}

              <div className="search-box-container">
                <div className="search-input-wrapper">
                  <input
                    type="text"
                    className="input-control"
                    placeholder={S.search_placeholder}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSearchJobs();
                    }}
                  />
                  <Search size={18} className="search-icon-inside" />
                </div>
                <button
                  className="btn btn-primary"
                  onClick={() => handleSearchJobs()}
                  disabled={loadingJobs}
                >
                  {loadingJobs ? (
                    <Loader2 size={18} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
                  ) : (
                    S.search
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Dashboard Status of sources */}
        {Object.keys(sourceCounts).length > 0 && (
          <div className="card">
            <div className="card-title">
              <span>{S.scan_state}</span>
            </div>
            <div className="card-content">
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {S.scan_help}
              </span>
              <div className="dashboard-grid">
                {Object.entries(sourceCounts).map(([src, count]) => {
                  const isExcluded = excludedSources.includes(src);
                  return (
                    <button
                      key={src}
                      className={`dashboard-btn ${isExcluded ? 'excluded' : 'active'}`}
                      onClick={() => toggleSourceExclusion(src)}
                    >
                      <span>{isExcluded ? '❌' : '✅'} {src}</span>
                      <span>({count})</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Direct Access platform links */}
        {searchQuery && (
          <div className="card">
            <div className="card-title">
              <span>{S.direct_access}</span>
            </div>
            <div className="card-content">
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px', display: 'block' }}>
                {S.direct_access_desc}
              </span>
              <div className="direct-links-grid">
                {Object.entries(directLinks).map(([name, url]) => (
                  <a
                    key={name}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-secondary"
                    style={{ textDecoration: 'none', textAlign: 'center' }}
                  >
                    🔍 {name}
                  </a>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Search Results */}
        {loadingJobs && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px', padding: '40px 0' }}>
            <Loader2 size={48} className="spin" style={{ animation: 'spin 1.5s linear infinite', color: 'var(--primary-color)' }} />
            <span>Scan global des plateformes en cours...</span>
          </div>
        )}

        {errorJobs && (
          <div className="alert alert-danger">
            <span>{errorJobs}</span>
          </div>
        )}

        {displayedJobs.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
              <h2 style={{ fontSize: '1.4rem', fontWeight: '800', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', flex: '1 1 auto' }}>
                {S.top_matches} {searchTime && <span style={{ fontSize: '0.9rem', fontWeight: '400', color: 'var(--text-secondary)' }}>({searchTime}s)</span>}
              </h2>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button onClick={exportToCSV} className="btn btn-secondary" style={{ fontSize: '0.85rem' }}>
                  📊 Exporter CSV
                </button>
                <button onClick={toggleDarkMode} className="btn btn-secondary" style={{ fontSize: '0.85rem' }}>
                  🌓 Mode
                </button>
              </div>
            </div>
            
            <div className="job-list">
              {currentJobs.map((job) => (
                <JobCard
                  key={job.id}
                  lang={lang}
                  job={job}
                  cvData={cvData}
                  rankingEngine={rankingEngine}
                  customGeminiKey={customGeminiKey}
                  onSaveJob={toggleSaveJob}
                  isSaved={savedJobs.some(j => j.id === job.id)}
                />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '24px', flexWrap: 'wrap' }}>
                <button 
                  className="btn btn-secondary"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  style={{ padding: '8px 16px' }}
                >
                  ← Précédent
                </button>
                <span style={{ display: 'flex', alignItems: 'center', padding: '0 12px', fontWeight: '600' }}>
                  Page {currentPage} / {totalPages}
                </span>
                <button 
                  className="btn btn-secondary"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  style={{ padding: '8px 16px' }}
                >
                  Suivant →
                </button>
              </div>
            )}
          </div>
        )}

        {/* No results notice */}
        {!loadingJobs && jobs.length > 0 && displayedJobs.length === 0 && (
          <div className="alert alert-info">
            {S.no_results}
          </div>
        )}
      </main>
    </div>
  );
}
