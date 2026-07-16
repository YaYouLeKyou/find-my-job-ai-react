import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import CvUploader from './components/CvUploader';
import CvProfile from './components/CvProfile';
import JobFilters from './components/JobFilters';
import JobCard from './components/JobCard';
import { LANGS, STRINGS } from './utils/translations';
import { Search, Loader2, RefreshCw, Key, ExternalLink, X } from 'lucide-react';

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

  const handleSearchJobs = async (customQuery) => {
    const activeQuery = customQuery || searchQuery;
    if (!activeQuery) return;

    setLoadingJobs(true);
    setErrorJobs("");
    setJobs([]);
    setSourceCounts({});
    setExcludedSources([]);

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
    } catch (err) {
      console.error(err);
      setErrorJobs(err.message);
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

  // Direct access link utility
  const generateJobSearchLinks = (jobTitle, langCode) => {
    const q = encodeURIComponent(jobTitle);
    const links = {
      fr: {
        "Welcome to the Jungle": `https://www.welcometothejungle.com/fr/jobs?query=${q}`,
        "HelloWork": `https://www.hellowork.com/fr-fr/emploi/recherche.html?k=${q}`,
        "Service Public": `https://www.choisirleservicepublic.gouv.fr/nos-offres/filtres/mots-cles/${q}/`
      },
      en: {
        "LinkedIn US": `https://www.linkedin.com/jobs/search/?keywords=${q}`,
        "Reed.co.uk": `https://www.reed.co.uk/jobs/${q.replace(/%20/g, '-')}-jobs`,
        "Dice (Tech US)": `https://www.dice.com/jobs?q=${q}`
      },
      es: {
        "InfoJobs ES": `https://www.infojobs.net/jobsearch/search-results.xhtml?keywords=${q}`,
        "Tecnoempleo": `https://www.tecnoempleo.com/busqueda-empleo.php?te=${q}`,
        "Turijobs": `https://www.turijobs.com/ofertas-trabajo/${q.replace(/%20/g, '-')}`
      },
      de: {
        "Xing DE": `https://www.xing.com/jobs/search?keywords=${q}`,
        "StepStone DE": `https://www.stepstone.de/jobs/${q.replace(/%20/g, '-')}`,
        "Honeypot.io": `https://app.honeypot.io/vacancies?q=${q}`
      },
      ar: {
        "Bayt (Middle East)": `https://www.bayt.com/en/international/jobs/?keyword=${q}`,
        "GulfTalent": `https://www.gulftalent.com/jobs/search?q=${q}`,
        "Naukrigulf": `https://www.naukrigulf.com/${q}-jobs`
      },
      ja: {
        "Indeed Japan": `https://jp.indeed.com/jobs?q=${q}`,
        "Mynavi Tenshoku": `https://tenshoku.mynavi.jp/list/kw${q}/`,
        "Rikunabi Next": `https://next.rikunabi.com/rnc/docs/cp_s0070.jsp?sayonara_word=${q}`
      },
      zh: {
        "51job": `https://search.51job.com/list/000000,000000,0000,00,9,99,${q},2,1.html`,
        "Liepin": `https://www.liepin.com/zhaopin/?key=${q}`,
        "Zhaopin": `https://sou.zhaopin.com/?jl=489&kw=${q}&kt=3`
      }
    };
    const globalLinks = {
      "Remote OK": `https://remoteok.com/remote-${q.replace(/%20/g, '-')}-jobs`,
      "Indeed Global": `https://www.indeed.com/jobs?q=${q}`
    };
    return { ...(links[langCode] || {}), ...globalLinks };
  };

  const directLinks = searchQuery ? generateJobSearchLinks(searchQuery, currentLangCode) : {};

  // Filter jobs by excluded sources
  const displayedJobs = jobs.filter(job => !excludedSources.includes(job.source));

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
            <h2 style={{ fontSize: '1.4rem', fontWeight: '800', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
              {S.top_matches}
            </h2>
            <div className="job-list">
              {displayedJobs.map((job) => (
                <JobCard
                  key={job.id}
                  lang={lang}
                  job={job}
                  cvData={cvData}
                  rankingEngine={rankingEngine}
                  customGeminiKey={customGeminiKey}
                />
              ))}
            </div>
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
