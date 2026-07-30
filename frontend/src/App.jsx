import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import CvUploader from './components/CvUploader';
import CvProfile from './components/CvProfile';
import JobFilters from './components/JobFilters';
import JobCard from './components/JobCard';
import LandingHub from './components/LandingHub';
import FreelanceMissionApp from './components/FreelanceMissionApp';
import WorkerApp from './components/WorkerApp';
import MockInterview from './components/MockInterview';
import AdComponent from './components/AdComponent';
import SEO from './components/SEO';
import HeaderButtons from './components/HeaderButtons';
import SearchProgressBar from './components/SearchProgressBar';
import { AIProvider, useAI } from './context/AIContext';
import { LANGS, STRINGS } from './utils/translations';
import { Search, Loader2, RefreshCw, Key, ExternalLink, X, ArrowLeft } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "";

function hashCode(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(36);
}

// ─── Client-side sorting helper ──────────────────────────────────────────────
function sortJobs(jobs, sortOption) {
  if (!jobs || jobs.length === 0) return jobs;
  const sorted = [...jobs];
  if (sortOption === "Pertinence (IA)" || sortOption === "Relevance (AI)" || sortOption === "Relevancia (AI)" || sortOption === "Relevanz (KI)" || sortOption === "الأكثر ملاءمة (ذكاء اصطناعي)" || sortOption === "関連性 (AI)" || sortOption === "相关性 (AI)") {
    sorted.sort((a, b) => { const sa = parseFloat(a.pertinence_ai) || 0; const sb = parseFloat(b.pertinence_ai) || 0; return sb - sa; });
  } else if (sortOption === "Plus récentes" || sortOption === "Most recent" || sortOption === "Más recientes" || sortOption === "Neueste" || sortOption === "الأحدث" || sortOption === "最新順" || sortOption === "最新发布") {
    sorted.sort((a, b) => { const da = a.posted_date || a.date || ""; const db = b.posted_date || b.date || ""; return String(db).localeCompare(String(da)); });
  } else if (sortOption === "Plus proches" || sortOption === "Closest" || sortOption === "Más cercanos" || sortOption === "Am nächsten" || sortOption === "الأقرب" || sortOption === "近い順" || sortOption === "距离最近") {
    sorted.sort((a, b) => { const sa = parseFloat(a.distance_score) || 0; const sb = parseFloat(b.distance_score) || 0; return sb - sa; });
  }
  return sorted;
}

// ─── FindMyJobAI Inner App ───────────────────────────────────────────────────
function FindMyJobApp({ onBackToHub, lang, setLang }) {
  const [analysisEngine, setAnalysisEngine] = useState("Groq / Llama 3.3");
  const [rankingEngine, setRankingEngine] = useState("Groq / Llama 3.3");
  const [customGeminiKey, setCustomGeminiKey] = useState("");
  const [cvData, setCvData] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [location, setLocation] = useState("Paris, France");
  const [numAds, setNumAds] = useState(10);
  useEffect(() => { setSelectedSources(["LinkedIn", "France Travail", "Google Jobs", "Adzuna", "Enhanced", "JobSpy"]); }, []);
  const [sortOption, setSortOption] = useState("Pertinence (IA)");
  const [contract, setContract] = useState("CDI");
  const [remote, setRemote] = useState(false);
  const [globalSearch, setGlobalSearch] = useState(false);
  const [selectedSources, setSelectedSources] = useState(["LinkedIn", "France Travail", "Google Jobs", "Adzuna", "Enhanced", "JobSpy"]);
  const [excludedSources, setExcludedSources] = useState([]);
  const [dismissKeyPrompt, setDismissKeyPrompt] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [sourceCounts, setSourceCounts] = useState({});
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [errorJobs, setErrorJobs] = useState("");
  const [ollamaOnline, setOllamaOnline] = useState(false);
  const [geminiOnline, setGeminiOnline] = useState(false);
  const [searchTime, setSearchTime] = useState(null);
  const [visibleCount, setVisibleCount] = useState(20);
  const [searchHistory, setSearchHistory] = useState([]);
  const [savedJobs, setSavedJobs] = useState([]);
  const [toast, setToast] = useState(null);
  const eventSourceRef = useRef(null);
  const currentLangCode = LANGS[lang].code;
  const S = STRINGS[currentLangCode];

  useEffect(() => {
    fetch(`${API_BASE}/api/health`).then(res => res.json()).then(data => { setOllamaOnline(data.ollama_online); }).catch(err => console.error("Backend not running or unreachable:", err));
    const geoTimer = setTimeout(() => {
      const controller = new AbortController();
      const geoTimeout = setTimeout(() => controller.abort(), 3000);
      fetch("https://ipapi.co/json/", { signal: controller.signal }).then(res => res.ok ? res.json() : Promise.reject()).then(data => { if (data.city && data.country_name) setLocation(`${data.city}, ${data.country_name}`); }).catch(err => console.debug("Geolocation skipped:", err)).finally(() => clearTimeout(geoTimeout));
    }, 500);
    const savedHistory = localStorage.getItem('searchHistory');
    if (savedHistory) setSearchHistory(JSON.parse(savedHistory));
    const savedJobsData = localStorage.getItem('savedJobs');
    if (savedJobsData) setSavedJobs(JSON.parse(savedJobsData));
    const darkMode = localStorage.getItem('darkMode');
    if (darkMode === 'true') document.documentElement.setAttribute('data-theme', 'dark');
    return () => clearTimeout(geoTimer);
  }, []);

  useEffect(() => {
    if (!customGeminiKey || !customGeminiKey.trim()) return;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    fetch(`${API_BASE}/api/ai/status?custom_gemini_key=${encodeURIComponent(customGeminiKey.trim())}`, { signal: controller.signal })
      .then(res => res.ok ? res.json() : Promise.reject())
      .then(data => { const online = !!data.gemini?.online; setGeminiOnline(online); if (online) { setRankingEngine("Gemini 3.5"); setAnalysisEngine("Gemini 3.5"); } })
      .catch(err => console.debug("[Gemini] status preflight failed:", err))
      .finally(() => clearTimeout(timeout));
  }, [customGeminiKey]);

  useEffect(() => { return () => { if (eventSourceRef.current) { eventSourceRef.current.close(); eventSourceRef.current = null; } }; }, []);

  const handleCvAnalysisSuccess = (data) => { setCvData(data); if (data.metier) setSearchQuery(data.metier); };
  const handleSelectJobQuery = (query) => { setSearchQuery(query); handleSearchJobs(query); };
  const showToast = (message, type = 'info') => { setToast({ message, type }); setTimeout(() => setToast(null), 3000); };

  const handleSearchJobs = (customQuery) => {
    const activeQuery = customQuery || searchQuery;
    if (!activeQuery) return;
    const startTime = Date.now();
    setLoadingJobs(true); setErrorJobs(""); setJobs([]); setSourceCounts({}); setExcludedSources([]); setVisibleCount(20);
    if (eventSourceRef.current) { eventSourceRef.current.close(); eventSourceRef.current = null; }
    const effectiveNumAds = numAds;
    const effectiveSortOption = sortOption;
    const cacheKey = `job_cache_${hashCode(JSON.stringify({ q: activeQuery.toLowerCase().trim(), l: globalSearch ? "" : location, n: effectiveNumAds, c: contract, r: remote, s: selectedSources.sort(), sort: effectiveSortOption }))}`;
    try {
      const cachedRaw = localStorage.getItem(cacheKey);
      if (cachedRaw) {
        try {
          const cached = JSON.parse(cachedRaw);
          const cacheAge = Date.now() - (cached.ts || 0);
          if (cacheAge < 30 * 60 * 1000) {
            const results = sortJobs(cached.results || [], effectiveSortOption);
            const sourceCounts = cached.source_counts || {};
            setJobs(results); setSourceCounts(sourceCounts);
            const searchDuration = ((Date.now() - startTime) / 1000).toFixed(2);
            setSearchTime(searchDuration);
            showToast(`⚡ ${results.length} offres depuis le cache (${(cacheAge/1000).toFixed(0)}s)`, 'success');
            setLoadingJobs(false); return;
          }
        } catch (e) { localStorage.removeItem(cacheKey); }
      }
      const params = new URLSearchParams({
        query: activeQuery, location: globalSearch ? "" : location, num_ads: String(effectiveNumAds),
        contract: contract, remote: String(remote), global_search: String(globalSearch),
        selected_sources: selectedSources.join(","), sort_option: effectiveSortOption,
        ranking_engine: rankingEngine, custom_gemini_key: customGeminiKey || "",
        lang_code: currentLangCode, lang_label: LANGS[lang].label,
        cv_data: cvData ? JSON.stringify(cvData) : ""
      });
      const streamUrl = `${API_BASE}/api/search-jobs-stream?${params.toString()}`;
      const es = new EventSource(streamUrl);
      eventSourceRef.current = es;
      let accumulatedJobs = [];
      let accumulatedSourceCounts = {};
      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'STARTED') { console.log(`[SSE] Search started: ${data.query} (${data.total_sources} sources)`); }
          if (data.type === 'PROGRESS') {
            if (data.source) { accumulatedSourceCounts[data.source] = data.jobs ? data.jobs.length : 0; setSourceCounts({ ...accumulatedSourceCounts }); }
            if (data.jobs && data.jobs.length > 0) { console.log(`[SSE] ${data.source} reçu: ${data.jobs.length} offres`); }
          }
          if (data.type === 'SOURCE_RESULT' || data.type === 'PROGRESS') {
            if (data.jobs && data.jobs.length > 0) { accumulatedJobs = [...accumulatedJobs, ...data.jobs]; const sorted = sortJobs(accumulatedJobs, effectiveSortOption); setJobs(sorted); }
            if (data.source) { accumulatedSourceCounts[data.source] = data.jobs ? data.jobs.length : 0; setSourceCounts({ ...accumulatedSourceCounts }); }
          }
          if (data.type === 'SCORES_UPDATED') {
            if (data.jobs && data.jobs.length > 0) { accumulatedJobs = data.jobs; const sorted = sortJobs(accumulatedJobs, effectiveSortOption); setJobs(sorted); }
          }
          if (data.type === 'COMPLETED') {
            if (data.jobs && data.jobs.length > 0) { accumulatedJobs = data.jobs; const sorted = sortJobs(accumulatedJobs, effectiveSortOption); setJobs(sorted); }
            if (data.source_status) {
              const counts = {};
              Object.entries(data.source_status).forEach(([source, status]) => {
                if (status && (status.count !== undefined || status.jobs_count !== undefined)) { counts[source] = status.count !== undefined ? status.count : status.jobs_count; }
              });
              setSourceCounts(counts);
            }
            const searchDuration = ((Date.now() - startTime) / 1000).toFixed(2);
            setSearchTime(searchDuration);
            try { localStorage.setItem(cacheKey, JSON.stringify({ results: accumulatedJobs, source_counts: accumulatedSourceCounts, ts: Date.now() })); } catch (e) {}
            const newHistory = [{ query: activeQuery, time: new Date().toISOString(), count: accumulatedJobs.length }, ...searchHistory.filter(h => h.query !== activeQuery)].slice(0, 10);
            setSearchHistory(newHistory);
            localStorage.setItem('searchHistory', JSON.stringify(newHistory));
            showToast(`✅ ${accumulatedJobs.length} offres trouvées en ${searchDuration}s`, 'success');
            es.close(); eventSourceRef.current = null; setLoadingJobs(false);
          }
          if (data.type === 'ERROR') {
            console.error("[SSE] Stream error:", data.message);
            setErrorJobs(data.message || "Erreur de connexion au flux de recherche.");
            showToast(`❌ Erreur: ${data.message || "Erreur de connexion"}`, 'error');
            es.close(); eventSourceRef.current = null; setLoadingJobs(false);
          }
        } catch (e) { console.error("[SSE] Failed to parse event:", e); }
      };
      es.onerror = (err) => {
        console.error("[SSE] Connection error:", err);
        if (eventSourceRef.current === es) {
          setErrorJobs("Erreur de connexion au serveur de recherche. Veuillez réessayer.");
          showToast("❌ Erreur de connexion au flux SSE", 'error');
          es.close(); eventSourceRef.current = null; setLoadingJobs(false);
        }
      };
    } catch (err) { console.error(err); setErrorJobs(err.message); showToast(`❌ Erreur: ${err.message}`, 'error'); setLoadingJobs(false); }
  };

  const toggleSourceExclusion = (source) => {
    if (excludedSources.includes(source)) { setExcludedSources(excludedSources.filter(s => s !== source)); }
    else { setExcludedSources([...excludedSources, source]); }
  };
  const toggleSaveJob = (job) => {
    const isSaved = savedJobs.some(j => j.id === job.id);
    let newSavedJobs;
    if (isSaved) { newSavedJobs = savedJobs.filter(j => j.id !== job.id); showToast('Offre retirée des favoris', 'info'); }
    else { newSavedJobs = [...savedJobs, job]; showToast('⭐ Offre sauvegardée', 'success'); }
    setSavedJobs(newSavedJobs); localStorage.setItem('savedJobs', JSON.stringify(newSavedJobs));
  };
  const exportToCSV = () => {
    if (jobs.length === 0) { showToast('Aucune offre à exporter', 'error'); return; }
    const headers = ['Titre', 'Entreprise', 'Source', 'Localisation', 'Date', 'Score', 'Lien'];
    const csvContent = [headers.join(','), ...jobs.map(job => [`"${job.title || ''}"`, `"${job.company || ''}"`, `"${job.source || ''}"`, `"${job.location || ''}"`, `"${job.date || ''}"`, job.match_score || '', `"${job.link || ''}"`].join(','))].join('\n');
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `offres_${searchQuery.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.csv`;
    link.click(); showToast('📊 CSV exporté avec succès', 'success');
  };
  const toggleDarkMode = () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (isDark) { document.documentElement.removeAttribute('data-theme'); localStorage.setItem('darkMode', 'false'); }
    else { document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('darkMode', 'true'); }
  };
  const handleClearHistory = () => { setSearchHistory([]); localStorage.removeItem('searchHistory'); showToast('📋 Historique vidé', 'success'); };
  const handleClearSavedJobs = () => { setSavedJobs([]); localStorage.removeItem('savedJobs'); showToast('⭐ Annonces sauvegardées vidées', 'success'); };
  const handleClearCache = async () => {
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) { const key = localStorage.key(i); if (key && key.startsWith('job_cache_')) { keysToRemove.push(key); } }
    keysToRemove.forEach(key => localStorage.removeItem(key));
    try { const response = await fetch(`${API_BASE}/api/clear-cache`, { method: 'DELETE' }); if (response.ok) { const data = await response.json(); showToast(`🧹 Cache vidé (${keysToRemove.length} entrées locale${keysToRemove.length > 1 ? 's' : ''}, ${data.cleared || 0} clé${(data.cleared || 0) > 1 ? 's' : ''} backend)`, 'success'); } else { showToast(`🧹 Cache local vidé (${keysToRemove.length} entrées)`, 'success'); } }
    catch (err) { showToast(`🧹 Cache local vidé (${keysToRemove.length} entrées)`, 'success'); }
  };
  const handleStartInterview = (job) => { sessionStorage.setItem('mockInterviewJob', JSON.stringify(job)); sessionStorage.setItem('mockInterviewCvData', JSON.stringify(cvData)); window.open('/mock-interview.html', '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes'); };

  const generateJobSearchLinks = (jobTitle, langCode) => {
    const q = encodeURIComponent(jobTitle);
    const qSlug = q.replace(/%20/g, '-');
    const categories = { fr: { "Généralistes France": [["Indeed France", `https://fr.indeed.com/jobs?q=${q}`], ["HelloWork", `https://www.hellowork.com/fr-fr/emploi/recherche.html?k=${q}`], ["Glassdoor FR", `https://www.glassdoor.fr/emploi/emploi.htm?sc.keyword=${q}`], ["France Travail", `https://candidat.pole-emploi.fr/offres/recherche?motsCles=${q}`], ["APEC", `https://www.apec.fr/offres-d-emploi-cadre/recherche.html?motsCles=${q}`], ["Monster FR", `https://www.monster.fr/emploi/recherche?q=${q}`]], "Tech & Cadres": [["Welcome to the Jungle", `https://www.welcometothejungle.com/fr/jobs?query=${q}`], ["JobTeaser", `https://www.jobteaser.com/fr/jobs?query=${q}`], ["LinkedIn FR", `https://fr.linkedin.com/jobs/search/?keywords=${q}`]] }, en: { "Remote & Global": [["Remote OK", `https://remoteok.com/remote-${qSlug}-jobs`], ["Indeed Global", `https://www.indeed.com/jobs?q=${q}`], ["Glassdoor Global", `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${q}`], ["LinkedIn Global", `https://www.linkedin.com/jobs/search/?keywords=${q}`]], "Tech & Cadres": [["Reed.co.uk", `https://www.reed.co.uk/jobs/${qSlug}-jobs`], ["Dice (Tech US)", `https://www.dice.com/jobs?q=${q}`], ["LinkedIn US", `https://www.linkedin.com/jobs/search/?keywords=${q}`]] }, es: { "Généralistes ES": [["InfoJobs ES", `https://www.infojobs.net/jobsearch/search-results.xhtml?keywords=${q}`], ["Tecnoempleo", `https://www.tecnoempleo.com/busqueda-empleo.php?te=${q}`], ["LinkedIn ES", `https://es.linkedin.com/jobs/search/?keywords=${q}`], ["Indeed ES", `https://es.indeed.com/jobs?q=${q}`], ["Glassdoor ES", `https://www.glassdoor.es/empleo/empleo.htm?sc.keyword=${q}`], ["Monster ES", `https://www.monster.es/empleo/buscar?q=${q}`]] }, de: { "Généralistes DE": [["Xing DE", `https://www.xing.com/jobs/search?keywords=${q}`], ["StepStone DE", `https://www.stepstone.de/jobs/${qSlug}`], ["LinkedIn DE", `https://de.linkedin.com/jobs/search/?keywords=${q}`], ["Indeed DE", `https://de.indeed.com/jobs?q=${q}`], ["Glassdoor DE", `https://www.glassdoor.de/Job/jobs.htm?sc.keyword=${q}`], ["Monster DE", `https://www.monster.de/jobs/suche?q=${q}`]] }, ar: { "Middle East": [["Bayt (Middle East)", `https://www.bayt.com/en/international/jobs/?keyword=${q}`], ["GulfTalent", `https://www.gulftalent.com/jobs/search?q=${q}`], ["LinkedIn AR", `https://ar.linkedin.com/jobs/search/?keywords=${q}`], ["Indeed AE", `https://ae.indeed.com/jobs?q=${q}`]] }, ja: { "Japan": [["Indeed Japan", `https://jp.indeed.com/jobs?q=${q}`], ["LinkedIn JP", `https://jp.linkedin.com/jobs/search/?keywords=${q}`]] }, zh: { "China": [["51job", `https://search.51job.com/list/000000,000000,0000,00,9,99,${q},2,1.html`], ["LinkedIn CN", `https://cn.linkedin.com/jobs/search/?keywords=${q}`]] } };
    const globalLinks = { "Remote OK": `https://remoteok.com/remote-${qSlug}-jobs`, "Indeed Global": `https://www.indeed.com/jobs?q=${q}`, "LinkedIn Global": `https://www.linkedin.com/jobs/search/?keywords=${q}`, "Glassdoor Global": `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${q}`, "France Travail (API)": `https://candidat.pole-emploi.fr/offres/recherche?motsCles=${q}&offresPartenaires=true`, "Adzuna (API)": `https://www.adzuna.fr/emploi?q=${q}` };
    const langCategories = categories[langCode] || {};
    const allLinks = [];
    Object.entries(langCategories).forEach(([category, links]) => { allLinks.push({ category, links }); });
    allLinks.push({ category: "Global", links: Object.entries(globalLinks) });
    return allLinks;
  };

  const directLinks = searchQuery ? generateJobSearchLinks(searchQuery, currentLangCode) : [];
  const displayedJobs = jobs.filter(job => !excludedSources.includes(job.source));
  const visibleJobs = displayedJobs.slice(0, visibleCount);
  const hasMoreJobs = visibleCount < displayedJobs.length;
  const handleLoadMore = () => { setVisibleCount(prev => Math.min(prev + 10, displayedJobs.length)); };
  const chips = [];
  if (cvData) { if (cvData.metier) chips.push(cvData.metier); if (cvData.recommandations_metiers) { cvData.recommandations_metiers.slice(0, 3).forEach(r => { if (!chips.includes(r)) chips.push(r); }); } }

  return (
    <div className="app-container">
      <SEO title="Find My Job AI - Intelligent Job Search Assistant" description="Find your dream job with AI-powered CV analysis, multi-source job search, and personalized job matching. Free career assistant tool." keywords="job search, AI, CV analysis, career, employment, FindMyJobAI, job matching, France" />
      {toast && (<div className={`toast ${toast.type}`}>{toast.message}</div>)}
      <Sidebar lang={lang} setLang={setLang} ollamaOnline={ollamaOnline} searchHistory={searchHistory} savedJobs={savedJobs} onSelectHistory={handleSelectJobQuery} onToggleDarkMode={toggleDarkMode} onClearHistory={handleClearHistory} onClearSavedJobs={handleClearSavedJobs} onClearCache={handleClearCache} />
      <main className="main-content">
        <button onClick={onBackToHub} className="btn btn-secondary" style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', padding: '8px 16px' }}><ArrowLeft size={16} />Job Bridge</button>
        <HeaderButtons onToggleDarkMode={toggleDarkMode} />
        <header className="header">
          <h1 style={{ color: 'var(--text-primary)', wordWrap: 'break-word', overflowWrap: 'break-word', WebkitTextStroke: '0.5px rgba(0, 0, 0, 0.15)', textShadow: '0 0 1px rgba(0, 0, 0, 0.1)' }}>{S.title}</h1>
          <p style={{ color: 'var(--text-primary)', fontWeight: '500', opacity: 0.95 }}>{S.subtitle}</p>
        </header>
        {!customGeminiKey && !dismissKeyPrompt && (
          <div className="alert alert-info" style={{ background: 'linear-gradient(135deg, rgba(124,77,255,0.12), rgba(68,138,255,0.08))', border: '1px solid rgba(124,77,255,0.25)', padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '1 1 auto' }}>
              <Key size={22} style={{ color: 'var(--primary-color)', flexShrink: 0 }} />
              <div><span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Clé API Gemini manquante</span><span style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>Ajoutez votre clé personnelle dans le panneau latéral pour utiliser Gemini 3.5 / 2.5 (recommandé). Sans clé, seuls les modèles Groq et locaux sont disponibles.</span></div>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
              <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="btn btn-primary" style={{ textDecoration: 'none', fontSize: '0.85rem', padding: '10px 16px', whiteSpace: 'nowrap' }}><ExternalLink size={14} />Obtenir une clé gratuite</a>
              <button className="btn btn-secondary" style={{ padding: '10px 12px' }} onClick={() => setDismissKeyPrompt(true)} title="Ignorer"><X size={14} /></button>
            </div>
          </div>
        )}
        <CvUploader lang={lang} analysisEngine={analysisEngine} customGeminiKey={customGeminiKey} onAnalysisSuccess={handleCvAnalysisSuccess} />
        {cvData && <CvProfile lang={lang} cvData={cvData} onSelectJobQuery={handleSelectJobQuery} />}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <JobFilters lang={lang} numAds={numAds} setNumAds={setNumAds} sortOption={sortOption} setSortOption={setSortOption} contract={contract} setContract={setContract} remote={remote} setRemote={setRemote} globalSearch={globalSearch} setGlobalSearch={setGlobalSearch} location={location} setLocation={setLocation} selectedSources={selectedSources} setSelectedSources={setSelectedSources} onRefresh={() => handleSearchJobs()} />
          <div className="card">
            <div className="card-title"><Search size={20} style={{ color: 'var(--primary-color)' }} /><span>{S.search_section.replace('🔍 ', '')}</span></div>
            <div className="card-content">
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{S.search_info}</span>
              {chips.length > 0 && (<div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', margin: '8px 0' }}>{chips.map((chip, idx) => (<button key={idx} className="btn-chip" onClick={() => handleSelectJobQuery(chip)}>{chip}</button>))}</div>)}
              <div className="search-box-container">
                <div className="search-input-wrapper">
                  <input type="text" className="input-control" placeholder={S.search_placeholder} value={searchQuery} onChange={e => setSearchQuery(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') handleSearchJobs(); }} />
                  <Search size={18} className="search-icon-inside" />
                </div>
                <button className="btn btn-primary" onClick={() => handleSearchJobs()} disabled={loadingJobs}>{loadingJobs ? <Loader2 size={18} className="spin" style={{ animation: 'spin 1s linear infinite' }} /> : S.search}</button>
              </div>
            </div>
          </div>
        </div>
        {Object.keys(sourceCounts).length > 0 && (
          <div className="card">
            <div className="card-title"><span>{S.scan_state}</span></div>
            <div className="card-content">
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{S.scan_help}</span>
              <div className="dashboard-grid">
                {Object.entries(sourceCounts).filter(([, count]) => count > 0).map(([src, count]) => {
                  const isExcluded = excludedSources.includes(src);
                  return (<button key={src} className={`dashboard-btn ${isExcluded ? 'excluded' : 'active'}`} onClick={() => toggleSourceExclusion(src)}><span>{isExcluded ? '❌' : '✅'} {src}</span><span>({count})</span></button>);
                })}
              </div>
            </div>
          </div>
        )}
        {searchQuery && directLinks.length > 0 && (
          <div className="card">
            <div className="card-title"><span>{S.direct_access}</span></div>
            <div className="card-content">
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '12px', display: 'block' }}>{S.direct_access_desc}</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>{directLinks.map(({ category, links }) => (<div key={category}><div style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '8px' }}>{category}</div><div className="direct-links-grid">{links.map(([name, url]) => (<a key={name} href={url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary" style={{ textDecoration: 'none', textAlign: 'center', display: 'inline-flex', alignItems: 'center', gap: '6px', justifyContent: 'center' }}>🔍 {name}</a>))}</div></div>))}</div>
            </div>
          </div>
        )}
        <SearchProgressBar isSearching={loadingJobs} totalSources={selectedSources.length} sourcesCompleted={Object.keys(sourceCounts).length} />
        {loadingJobs && (<div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px', padding: '40px 0' }}><span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Scan global des plateformes en cours...</span><AdComponent style={{ marginTop: '24px' }} /></div>)}
        {errorJobs && <div className="alert alert-danger"><span>{errorJobs}</span></div>}
        {displayedJobs.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
              <h2 style={{ fontSize: '1.4rem', fontWeight: '800', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', flex: '1 1 auto' }}>{S.top_matches} {searchTime && <span style={{ fontSize: '0.9rem', fontWeight: '400', color: 'var(--text-secondary)' }}>({searchTime}s)</span>}</h2>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}><button onClick={exportToCSV} className="btn btn-secondary" style={{ fontSize: '0.85rem' }}>📊 Exporter CSV</button></div>
            </div>
            <div className="job-list">{visibleJobs.map(job => (<JobCard key={job.id} lang={lang} job={job} cvData={cvData} rankingEngine={rankingEngine} customGeminiKey={customGeminiKey} onSaveJob={toggleSaveJob} isSaved={savedJobs.some(j => j.id === job.id)} onStartInterview={handleStartInterview} />))}</div>
            {hasMoreJobs && (<div style={{ display: 'flex', justifyContent: 'center', marginTop: '24px' }}><button className="btn btn-primary" onClick={handleLoadMore} style={{ padding: '12px 32px', fontSize: '1rem' }}>Charger plus d'offres ({displayedJobs.length - visibleCount} restantes)</button></div>)}
          </div>
        )}
        {!loadingJobs && jobs.length > 0 && displayedJobs.length === 0 && (<div className="alert alert-info">{S.no_results}</div>)}
        <div className="app-footer"><div className="app-footer-inner"><span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>🤖 <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Gemini</span><span style={{ opacity: 0.4 }}>·</span><span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Groq</span><span style={{ opacity: 0.4 }}>·</span><span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Llama</span><span style={{ opacity: 0.4 }}>·</span><span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Ollama</span></span><span style={{ opacity: 0.3, fontWeight: '900' }}>|</span><span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>by Yanès Hadiouche</span></div></div>
      </main>
    </div>
  );
}

// ─── Root App Content with Hub Routing ───────────────────────────────────────
function AppContent() {
  const [currentApp, setCurrentApp] = useState(null);
  const [selectedLang, setSelectedLang] = useState("Français");
  const toggleDarkMode = () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (isDark) { document.documentElement.removeAttribute('data-theme'); localStorage.setItem('darkMode', 'false'); }
    else { document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('darkMode', 'true'); }
  };
  const handleSelectApp = (appId, lang) => { setSelectedLang(lang || selectedLang); setCurrentApp(appId); window.scrollTo({ top: 0, behavior: 'smooth' }); };
  const handleBackToHub = () => { setCurrentApp(null); window.scrollTo({ top: 0, behavior: 'smooth' }); };
  if (currentApp === 'job') { return <FindMyJobApp onBackToHub={handleBackToHub} lang={selectedLang} setLang={setSelectedLang} />; }
  if (currentApp === 'freelance') { return <FreelanceMissionApp onBackToHub={handleBackToHub} lang={selectedLang} setLang={setSelectedLang} />; }
  if (currentApp === 'worker') { return <WorkerApp onBackToHub={handleBackToHub} lang={selectedLang} setLang={setSelectedLang} />; }
  return <LandingHub onSelectApp={handleSelectApp} lang={selectedLang} setLang={setSelectedLang} onToggleDarkMode={toggleDarkMode} />;
}

// ─── Root App wrapped with AIProvider ────────────────────────────────────────
export default function App() {
  return (
    <AIProvider>
      <AppContent />
    </AIProvider>
  );
}