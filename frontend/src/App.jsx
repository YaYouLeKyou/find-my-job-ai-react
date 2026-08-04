/**
 * App.jsx - Application principale multi-agent
 *
 * Architecture cible :
 *   - 3 agents CLONES (Job Seeker, Freelance, Recruteur)
 *   - Même interface, même Header, même DocumentAnalyzer, même useStreamSearch
 *   - La SEULE différence : filtres Sidebar + agent_type envoyé au backend
 *
 * Flow :
 *   LandingHub → UnifiedAgentApp (avec AgentProvider + AIProvider)
 *   Le Header permet de basculer entre les 3 agents en temps réel.
 */

import React, { useState, useEffect } from 'react';
import { AIProvider, useAI } from './context/AIContext';
import { AgentProvider, useAgent } from './context/AgentContext';
import { LANGS, STRINGS } from './utils/translations';
import { useStreamSearch } from './hooks/useStreamSearch';
import { generateSearchLinks } from './utils/searchLinks';

import LandingHub from './components/LandingHub';
import AppLayout from './components/layout/AppLayout';
import AISettings from './components/features/AISettings';
import DocumentAnalyzer from './components/features/DocumentAnalyzer';
import AnalyzedCvMemory from './components/features/AnalyzedCvMemory';
import FavoritesMemory from './components/features/FavoritesMemory';
import SearchBar from './components/features/SearchBar';
import ResultCard from './components/features/ResultCard';
import ActiveSourcesHeader from './components/ActiveSourcesHeader';
import AdComponent from './components/AdComponent';
import SEO from './components/SEO';
import SearchProgressBar from './components/SearchProgressBar';
import AIChatDrawer from './components/AIChatDrawer';
import AdvancedFilters from './components/AdvancedFilters';
import AdvancedFiltersHeader from './components/AdvancedFiltersHeader';
import AdvancedFiltersDrawer from './components/AdvancedFiltersDrawer';
import useFilteredJobs from './hooks/useFilteredJobs';

import { Loader2 } from 'lucide-react';
import './styles/streaming.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ─── Client-side sorting helper ──────────────────────────────────────────────
function sortJobs(jobs, sortOption) {
    if (!jobs || jobs.length === 0) return jobs;
    const sorted = [...jobs];
    if (sortOption === 'Pertinence (IA)' || sortOption === 'Relevance (AI)' || sortOption === 'Relevancia (AI)' || sortOption === 'Relevanz (KI)' || sortOption === 'الأكثر ملاءمة (ذكاء اصطناعي)' || sortOption === '関連性 (AI)' || sortOption === '相关性 (AI)') {
        sorted.sort((a, b) => { const sa = parseFloat(a.pertinence_ai) || 0; const sb = parseFloat(b.pertinence_ai) || 0; return sb - sa; });
    } else if (sortOption === 'Plus récentes' || sortOption === 'Most recent' || sortOption === 'Más recientes' || sortOption === 'Neueste' || sortOption === 'الأحدث' || sortOption === '最新順' || sortOption === '最新发布') {
        sorted.sort((a, b) => { const da = a.posted_date || a.date || ''; const db = b.posted_date || b.date || ''; return String(db).localeCompare(String(da)); });
    } else if (sortOption === 'Plus proches' || sortOption === 'Closest' || sortOption === 'Más cercanos' || sortOption === 'Am nächsten' || sortOption === 'الأقرب' || sortOption === '近い順' || sortOption === '距离最近') {
        sorted.sort((a, b) => { const sa = parseFloat(a.distance_score) || 0; const sb = parseFloat(b.distance_score) || 0; return sb - sa; });
    }
    return sorted;
}

function hashCode(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return Math.abs(hash).toString(36);
}

// ─── Unified Agent App (CLONE for all 3 agents) ──────────────────────────────
function UnifiedAgentApp({ onBackToHub, lang, setLang, onToggleDarkMode, darkMode }) {
    const { activeAgent, agentConfig, activeFilters, noAiMode, updateFilter } = useAgent();
    const { activeModel, activeModelConfig, getActiveApiKey } = useAI();
    const customGeminiKey = getActiveApiKey() || '';

    const [cvData, setCvData] = useState(null);
    const [analyzedCvs, setAnalyzedCvs] = useState(() => {
        try {
            const raw = localStorage.getItem('analyzed_cvs');
            return raw ? JSON.parse(raw) : [];
        } catch {
            return [];
        }
    });
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedSources, setSelectedSources] = useState(agentConfig.sources);
    const [excludedSources, setExcludedSources] = useState([]);
    const [searchHistory, setSearchHistory] = useState([]);
    const [savedItems, setSavedItems] = useState([]);
    const [toast, setToast] = useState(null);
    const [visibleCount, setVisibleCount] = useState(20);
    const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(false);
    const [advancedFilters, setAdvancedFilters] = useState({
        searchQuery: '',
        minMatchScore: 0,
        companyTypes: [],
        workModes: [],
        minSalary: 0,
        techStack: [],
        sources: []
    });
    const [hiddenSources, setHiddenSources] = useState([]);

    const currentLangCode = LANGS[lang].code;
    const S = STRINGS[currentLangCode];

    // useStreamSearch - IDENTIQUE pour les 3 agents, passe agent_type au backend
    const {
        jobs,
        sourceCounts,
        loading: loadingJobs,
        error: errorJobs,
        searchTime,
        aiProcessing,
        processedCount,
        totalReceived,
        sourcesDone,
        totalSources,
        search: searchStream,
        cancel: cancelSearch,
        reset: resetSearch,
    } = useStreamSearch(API_BASE, activeAgent, noAiMode, (result) => {
        console.log('[App] Recherche terminée:', result);
    });

    // --- Load persisted state on mount ---
    useEffect(() => {
        const savedHistory = localStorage.getItem('searchHistory');
        if (savedHistory) setSearchHistory(JSON.parse(savedHistory));

        const savedItemsData = localStorage.getItem('savedItems');
        if (savedItemsData) setSavedItems(JSON.parse(savedItemsData));

        const analyzedCvsData = localStorage.getItem('analyzed_cvs');
        if (analyzedCvsData) setAnalyzedCvs(JSON.parse(analyzedCvsData));
    }, []);

    // --- Sync selectedSources when agent changes ---
    useEffect(() => {
        setSelectedSources(agentConfig.sources);
    }, [activeAgent, agentConfig.sources]);

    // --- Handlers ---
    const handleCvAnalysisSuccess = (data) => {
        setCvData(data);
        if (data.metier) setSearchQuery(data.metier);

        const entry = {
            id: Date.now().toString(36) + Math.random().toString(36).slice(2),
            ...data,
            analyzedAt: Date.now(),
        };
        setAnalyzedCvs(prev => {
            const updated = [entry, ...prev.filter(c => c.nom_complet !== data.nom_complet)].slice(0, 20);
            localStorage.setItem('analyzed_cvs', JSON.stringify(updated));
            return updated;
        });
    };

    const handleRemoveAnalyzedCv = (id) => {
        setAnalyzedCvs(prev => {
            const updated = prev.filter(c => c.id !== id);
            localStorage.setItem('analyzed_cvs', JSON.stringify(updated));
            return updated;
        });
    };

    const handleClearAnalyzedCvs = () => {
        setAnalyzedCvs([]);
        localStorage.setItem('analyzed_cvs', JSON.stringify([]));
        showToast(S.clear_history || 'Historique CV effacé', 'info');
    };

    const handleReanalyzeCv = (cv) => {
        setCvData(cv);
        if (cv.metier) setSearchQuery(cv.metier);
    };

    const handleRemoveFavorite = (id) => {
        setSavedItems(prev => {
            const updated = prev.filter(j => j.id !== id);
            localStorage.setItem('savedItems', JSON.stringify(updated));
            return updated;
        });
    };

    const handleClearFavorites = () => {
        setSavedItems([]);
        localStorage.setItem('savedItems', JSON.stringify([]));
        showToast(S.cleared_favorites || 'Favoris effacés', 'info');
    };

    const handleApplyAdvancedFilters = (filters) => {
        setAdvancedFilters(filters);
        setAdvancedFiltersOpen(false);
    };

    const handleToggleAdvancedFilters = () => {
        setAdvancedFiltersOpen(prev => !prev);
    };

    const handleSelectJobQuery = (query) => {
        setSearchQuery(query);
        handleSearchJobs(query);
    };

    const handleSelectHistory = (query) => {
        setSearchQuery(query);
        handleSearchJobs(query);
    };

    const showToast = (message, type = 'info') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    };

    const handleSearchJobs = (customQuery) => {
        const activeQuery = customQuery || searchQuery;
        if (!activeQuery) return;

        const effectiveNumAds = activeFilters.numAds || 10;
        const effectiveSortOption = activeFilters.sortOption || 'Pertinence (IA)';

        const cacheKey = `${activeAgent}_cache_${hashCode(JSON.stringify({
            q: activeQuery.toLowerCase().trim(),
            l: activeFilters.globalSearch ? '' : activeFilters.location,
            n: effectiveNumAds,
            c: activeFilters.contract,
            r: activeFilters.remote,
            s: selectedSources.sort(),
            sort: effectiveSortOption,
        }))}`;

        // Vérifier le cache
        try {
            const cachedRaw = localStorage.getItem(cacheKey);
            if (cachedRaw) {
                try {
                    const cached = JSON.parse(cachedRaw);
                    const cacheAge = Date.now() - (cached.ts || 0);
                    if (cacheAge < 30 * 60 * 1000) {
                        const results = sortJobs(cached.results || [], effectiveSortOption);
                        const sourceCounts = cached.source_counts || {};
                        showToast(`⚡ ${results.length} ${S.results_from_cache} (${(cacheAge / 1000).toFixed(0)}s)`, 'success');
                        return;
                    }
                } catch (e) {
                    localStorage.removeItem(cacheKey);
                }
            }
        } catch (e) {}

        // Lancer la recherche via le hook SSE
        const searchParams = {
            query: activeQuery,
            location: activeFilters.globalSearch ? '' : activeFilters.location,
            num_ads: String(effectiveNumAds),
            contract: activeFilters.contract || '',
            remote: String(activeFilters.remote || false),
            global_search: String(activeFilters.globalSearch || false),
            selected_sources: selectedSources.join(','),
            sort_option: effectiveSortOption,
            ranking_engine: activeModel,
            custom_gemini_key: customGeminiKey || '',
            lang_code: currentLangCode,
            lang_label: LANGS[lang].label,
            cv_data: cvData ? JSON.stringify(cvData) : '',
            // Agent-specific filters
            ...(activeAgent === 'freelance' && {
                mission_type: activeFilters.missionType || '',
                duration: activeFilters.duration || '',
                tjm_min: activeFilters.tjmMin || '',
                tjm_max: activeFilters.tjmMax || '',
            }),
            ...(activeAgent === 'recruiter' && {
                experience: activeFilters.experience || '',
                salary_min: activeFilters.salaryMin || '',
                salary_max: activeFilters.salaryMax || '',
                skills: (activeFilters.skills || []).join(','),
            }),
        };

        searchStream(searchParams);

        // Add to history
        const newHistory = [{ query: activeQuery, time: Date.now(), count: 0 }, ...searchHistory.slice(0, 9)];
        setSearchHistory(newHistory);
        localStorage.setItem('searchHistory', JSON.stringify(newHistory));
    };

    const toggleSourceExclusion = (source) => {
        if (excludedSources.includes(source)) {
            setExcludedSources(excludedSources.filter(s => s !== source));
        } else {
            setExcludedSources([...excludedSources, source]);
        }
    };

    const toggleSourceVisibility = (source) => {
        if (hiddenSources.includes(source)) {
            setHiddenSources(hiddenSources.filter(s => s !== source));
        } else {
            setHiddenSources([...hiddenSources, source]);
        }
    };

    // --- Vider le cache de recherche ---
    const clearSearchCache = () => {
        try {
            let removedCount = 0;
            const keysToRemove = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.includes('_cache_')) {
                    keysToRemove.push(key);
                    removedCount++;
                }
            }
            keysToRemove.forEach(key => localStorage.removeItem(key));

            // Reset search results to 0 (except favorites)
            setHiddenSources([]);
            setExcludedSources([]);
            setVisibleCount(20);
            
            // Reset the search stream state
            resetSearch();

            showToast(`🗑️ ${removedCount} ${removedCount > 1 ? 'caches supprimés' : 'cache supprimé'}`, 'success');
        } catch (e) {
            console.error('[Cache] Erreur lors du vidage:', e);
            showToast('❌ Erreur lors du vidage du cache', 'error');
        }
    };

    // --- Save / Unsave items ---
    const toggleSaveItem = (item) => {
        const isSaved = savedItems.some(j => j.id === item.id);
        const updated = isSaved
            ? savedItems.filter(j => j.id !== item.id)
            : [...savedItems, item];
        setSavedItems(updated);
        localStorage.setItem('savedItems', JSON.stringify(updated));
        showToast(isSaved ? `💾 ${S.removed_from_favorites}` : `✅ ${S.saved_to_favorites}`, isSaved ? 'info' : 'success');
    };

    // --- Export to CSV ---
    const exportToCSV = () => {
        if (!displayedJobs.length) return;
        const headers = currentLangCode === 'en'
            ? ['Title', 'Company', 'Location', 'Source', 'Date', 'AI Score', 'URL']
            : ['Titre', 'Entreprise', 'Localisation', 'Source', 'Date', 'Score IA', 'URL'];
        const rows = displayedJobs.map(job => [
            job.title || '',
            job.company || '',
            job.location || '',
            job.source || '',
            job.posted_date || job.date || '',
            job.pertinence_ai || '',
            job.url || job.link || '',
        ]);
        const csv = [headers.join(','), ...rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','))].join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `jobs_${new Date().toISOString().slice(0, 10)}.csv`;
        link.click();
        URL.revokeObjectURL(link.href);
        showToast(`📊 ${S.csv_export_success}`, 'success');
    };

    // --- Start Interview ---
    const handleStartInterview = (job) => {
        // Store job and CV data in sessionStorage for the standalone mock-interview page
        sessionStorage.setItem('mockInterviewJob', JSON.stringify(job));
        sessionStorage.setItem('mockInterviewCvData', JSON.stringify(cvData));
        sessionStorage.setItem('mockInterviewRankingEngine', activeModel);
        sessionStorage.setItem('mockInterviewCustomGeminiKey', customGeminiKey || '');

        const interviewUrl = `/mock-interview.html`;
        window.open(interviewUrl, '_blank');
    };

    // --- Build chips from CV data ---
    const chips = [];
    if (cvData) {
        if (cvData.metier) chips.push(cvData.metier);
        if (cvData.recommandations_metiers) {
            cvData.recommandations_metiers.slice(0, 3).forEach(r => {
                if (!chips.includes(r)) chips.push(r);
            });
        }
    }

    const directLinks = searchQuery ? generateSearchLinks(searchQuery, currentLangCode, activeAgent) : [];

    // Apply advanced filters using useMemo
    const filteredJobs = useFilteredJobs(jobs, advancedFilters);
    const displayedJobs = filteredJobs.filter(job => !excludedSources.includes(job.source) && !hiddenSources.includes(job.source));
    const visibleJobs = displayedJobs.slice(0, visibleCount);
    const hasMoreJobs = visibleCount < displayedJobs.length;
    const handleLoadMore = () => {
        setVisibleCount(prev => Math.min(prev + 10, displayedJobs.length));
    };

    // --- Result type label ---
    const resultTypeLabel = agentConfig.resultType === 'mission'
        ? S.mission_results
        : agentConfig.resultType === 'candidate'
            ? `🎯 ${S.recommended_candidates}`
            : S.top_matches;

    return (
        <AppLayout
            onBackToHub={onBackToHub}
            lang={lang}
            setLang={setLang}
            onToggleDarkMode={onToggleDarkMode}
            darkMode={darkMode}
        >

            <SEO
                title={`${agentConfig.title} - ${agentConfig.subtitle}`}
                description={agentConfig.description}
                keywords={`job search, AI, ${agentConfig.name}, ${activeAgent}, France`}
            />

            {toast && (
                <div className={`toast ${toast.type}`}>
                    {toast.message}
                </div>
            )}

            {/* AI Settings - Configuration IA au-dessus de l'analyzer */}
            <AISettings lang={lang} />

            {/* Document Analyzer (CV / Fiche de poste) - IDENTIQUE pour tous les agents */}
            <DocumentAnalyzer
                lang={lang}
                onAnalysisSuccess={handleCvAnalysisSuccess}
                cvData={cvData}
            />

            {/* Analyzed CV Memory - sous l'analyzer */}
            <AnalyzedCvMemory
                lang={lang}
                cvs={analyzedCvs}
                onRemove={handleRemoveAnalyzedCv}
                onClear={handleClearAnalyzedCvs}
                onReanalyze={handleReanalyzeCv}
            />

            {/* ─── Quick Filters (in body, under DocumentAnalyzer) ─────────── */}
            <div className="card" style={{ marginTop: '16px', background: 'var(--color-surface)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                    <span>🎛️</span>
                    <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>{S.quick_filters}</h3>
                </div>
                <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '12px',
                    alignItems: 'flex-end',
                    overflowX: 'auto',
                    paddingBottom: '8px',
                    marginLeft: '-8px',
                    marginRight: '-8px',
                    width: 'calc(100% + 16px)'
                }}>
                    <div style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: '12px',
                        alignItems: 'flex-end',
                        paddingLeft: '8px',
                        paddingRight: '8px',
                        minWidth: '100%'
                    }}>
                    {agentConfig.filters.map((filter) => {
                        const value = activeFilters[filter.id];

                        if (filter.type === 'select') {
                            return (
                                <div key={filter.id} style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        {filter.label}
                                    </label>
                                    <select
                                        value={value || ''}
                                        onChange={(e) => updateFilter(filter.id, e.target.value)}
                                        className="select-control"
                                        style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                                    >
                                        {filter.placeholder && <option value="">{filter.placeholder}</option>}
                                        {filter.options.map((opt) => (
                                            <option key={opt} value={opt}>{opt}</option>
                                        ))}
                                    </select>
                                </div>
                            );
                        }

                        if (filter.type === 'text') {
                            return (
                                <div key={filter.id} style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        {filter.label}
                                    </label>
                                    <input
                                        type="text"
                                        placeholder={filter.placeholder || ''}
                                        value={value || ''}
                                        onChange={(e) => updateFilter(filter.id, e.target.value)}
                                        className="input-control"
                                        style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                                    />
                                </div>
                            );
                        }

                        if (filter.type === 'checkbox') {
                            return (
                                <label
                                    key={filter.id}
                                    className="checkbox-container"
                                    style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        gap: '8px',
                                        padding: '8px 12px',
                                        cursor: 'pointer',
                                        fontSize: '0.875rem',
                                        fontWeight: 500,
                                        borderRadius: 'var(--radius-sm)',
                                        border: '1px solid',
                                        borderColor: value ? agentConfig.theme.primary : 'var(--border-color)',
                                        background: value ? `${agentConfig.theme.primary}15` : 'var(--color-surface)',
                                        color: value ? agentConfig.theme.primary : 'var(--text-primary)',
                                        transition: 'all 0.2s',
                                        minHeight: '38px',
                                        boxSizing: 'border-box',
                                        whiteSpace: 'normal',
                                        minWidth: '160px',
                                        flex: '1 1 160px',
                                        lineHeight: '1.3',
                                    }}
                                >
                                    <input
                                        type="checkbox"
                                        checked={!!value}
                                        onChange={(e) => updateFilter(filter.id, e.target.checked)}
                                        style={{ accentColor: 'var(--color-primary-500)' }}
                                    />
                                    {filter.label}
                                </label>
                            );
                        }

                        if (filter.type === 'range') {
                            return (
                                <div key={filter.id} style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                                        <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                            {filter.label}
                                        </label>
                                        <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--color-primary-500)', minWidth: '32px', textAlign: 'right' }}>
                                            {value || filter.default}
                                        </span>
                                    </div>
                                    <input
                                        type="range"
                                        min={filter.min}
                                        max={filter.max}
                                        step={filter.step}
                                        value={value || filter.default}
                                        onChange={(e) => updateFilter(filter.id, parseInt(e.target.value))}
                                        style={{ width: '100%', accentColor: 'var(--color-primary-500)', cursor: 'pointer', height: '38px', boxSizing: 'border-box' }}
                                    />
                                </div>
                            );
                        }

                        if (filter.type === 'number') {
                            return (
                                <div key={filter.id} style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        {filter.label}
                                    </label>
                                    <input
                                        type="number"
                                        placeholder={filter.placeholder || ''}
                                        value={value || ''}
                                        onChange={(e) => updateFilter(filter.id, e.target.value)}
                                        min={filter.min}
                                        step={filter.step}
                                        className="input-control"
                                        style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                                    />
                                </div>
                            );
                        }

                        if (filter.type === 'tags') {
                            return (
                                <div key={filter.id} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        {filter.label}
                                    </label>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                        {filter.options.slice(0, 6).map((skill) => {
                                            const isSelected = (value || []).includes(skill);
                                            return (
                                                <button
                                                    key={skill}
                                                    type="button"
                                                    onClick={() => {
                                                        const current = value || [];
                                                        const updated = isSelected
                                                            ? current.filter((s) => s !== skill)
                                                            : [...current, skill];
                                                        updateFilter(filter.id, updated);
                                                    }}
                                                    style={{
                                                        padding: '4px 10px',
                                                        fontSize: '0.75rem',
                                                        fontWeight: 500,
                                                        borderRadius: '9999px',
                                                        border: '1px solid',
                                                        borderColor: isSelected ? agentConfig.theme.primary : 'var(--border-color)',
                                                        background: isSelected ? `${agentConfig.theme.primary}20` : 'transparent',
                                                        color: isSelected ? agentConfig.theme.primary : 'var(--text-secondary)',
                                                        cursor: 'pointer',
                                                        transition: 'all 0.2s',
                                                        fontFamily: 'var(--font-sans)',
                                                    }}
                                                >
                                                    {skill}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        }

                        return null;
                    })}
                    </div>
                </div>
            </div>

            {/* Advanced Filters - directly below quick filters */}
            <div className="card" style={{ marginTop: '16px', background: 'var(--color-surface)' }}>
                <AdvancedFiltersHeader onToggle={handleToggleAdvancedFilters} />
                <AdvancedFiltersDrawer
                    activeAgent={activeAgent}
                    isOpen={advancedFiltersOpen}
                    onClose={handleToggleAdvancedFilters}
                    onApplyFilters={handleApplyAdvancedFilters}
                    currentFilters={advancedFilters}
                    cvData={cvData}
                />
            </div>

            {/* Direct Access Links - visible whenever there's a search query or CV metier */}
            {directLinks.length > 0 && (
                <div className="card" style={{
                    background: 'var(--surface-color)',
                    border: `1px solid ${agentConfig.theme.badgeBorder}`,
                }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        marginBottom: '12px',
                        fontSize: '0.85rem',
                        fontWeight: 700,
                        color: agentConfig.theme.primary,
                    }}>
                        <span>🚀</span>
                        <span>{S.direct_access}</span>
                    </div>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '12px', display: 'block' }}>
                        {S.direct_access_desc}
                    </span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        {directLinks.map(({ category, links }) => (
                            <div key={category}>
                                <div style={{
                                    fontSize: '0.8rem',
                                    fontWeight: 700,
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.05em',
                                    color: 'var(--text-muted)',
                                    marginBottom: '8px',
                                }}>
                                    {category}
                                </div>
                                <div className="direct-links-grid">
                                    {links.map(([name, url]) => (
                                        <a
                                            key={name}
                                            href={url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="btn btn-secondary"
                                            style={{
                                                textDecoration: 'none',
                                                textAlign: 'center',
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '6px',
                                                justifyContent: 'center',
                                            }}
                                        >
                                            🔍 {name}
                                        </a>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Search Bar - Recherche d'opportunités (sous l'accès direct) */}
            <SearchBar
                searchQuery={searchQuery}
                setSearchQuery={setSearchQuery}
                onSearch={() => handleSearchJobs()}
                loading={loadingJobs}
                chips={chips}
                onSelectChip={handleSelectJobQuery}
                lang={lang}
                onClearCache={clearSearchCache}
                placeholder={
                    agentConfig.resultType === 'mission'
                        ? S.mission_search_placeholder
                        : S.search_placeholder
                }
            />
             {/* Favorites Memory - sous les annonces trouvées */}
            <FavoritesMemory
                lang={lang}
                favorites={savedItems}
                onRemove={handleRemoveFavorite}
                onClear={handleClearFavorites}
                resultType={agentConfig.resultType}
                cvData={cvData}
                rankingEngine={activeModel}
                customGeminiKey={customGeminiKey}
                onStartInterview={handleStartInterview}
            />


            {/* Active Sources Header - sous la searchbar */}
            {Object.keys(sourceCounts).length > 0 && (
                <ActiveSourcesHeader
                    sourceCounts={sourceCounts}
                    aiProcessing={aiProcessing}
                    processedCount={processedCount}
                    onToggleSource={toggleSourceVisibility}
                    hiddenSources={hiddenSources}
                    lang={lang}
                />
            )}

            {/* Loading state */}
            {loadingJobs && (
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '16px',
                    padding: '40px 0',
                }}>
                    <Loader2
                        size={48}
                        style={{ animation: 'spin 1.5s linear infinite', color: 'var(--primary-color)' }}
                    />
                    <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                        {S.scanning_platforms}
                    </span>
                    <span style={{
                        fontSize: '0.8rem',
                        color: 'var(--text-muted)',
                        padding: '6px 16px',
                        background: 'rgba(99, 102, 241, 0.06)',
                        border: '1px solid rgba(99, 102, 241, 0.1)',
                        borderRadius: '9999px',
                        fontWeight: 500,
                    }}>
                        {totalSources > 0 ? `${S.source_progress} ${sourcesDone}/${totalSources}` : S.initializing}
                        {aiProcessing && ` · ${S.ai_sorting}`}
                    </span>
                    <AdComponent style={{ marginTop: '24px' }} />
                </div>
            )}

            {/* Error state */}
            {errorJobs && (
                <div className="alert alert-danger">
                    <span>{errorJobs}</span>
                </div>
            )}

            {/* Results */}
            {displayedJobs.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: '12px',
                    }}>
                        <h2 style={{
                            fontSize: '1.4rem',
                            fontWeight: '800',
                            borderBottom: '1px solid var(--border-color)',
                            paddingBottom: '8px',
                            flex: '1 1 auto',
                        }}>
                            {resultTypeLabel}
                            {searchTime && (
                                <span style={{
                                    fontSize: '0.9rem',
                                    fontWeight: '400',
                                    color: 'var(--text-secondary)',
                                }}>
                                    ({searchTime}s)
                                </span>
                            )}
                        </h2>
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                            <button
                                onClick={exportToCSV}
                                className="btn btn-secondary"
                                style={{ fontSize: '0.85rem' }}
                            >
                                📊 {S.export_csv}
                            </button>
                            <button
                                onClick={cancelSearch}
                                className="btn btn-secondary"
                                style={{ fontSize: '0.85rem' }}
                            >
                                {S.cancel}
                            </button>
                        </div>
                    </div>

                    <div className="results-grid" style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                        gap: '16px',
                    }}>
                        {visibleJobs.map((job, idx) => (
                            <ResultCard
                                key={job.id || `result-${idx}-${job.source}`}
                                item={job}
                                resultType={agentConfig.resultType}
                                onSave={toggleSaveItem}
                                isSaved={savedItems.some(j => j.id === job.id)}
                                aiScore={job.pertinence_ai}
                                aiProcessed={job.ai_scored || false}
                                cvData={cvData}
                                rankingEngine={activeModel}
                                customGeminiKey={customGeminiKey}
                                onStartInterview={handleStartInterview}
                                lang={lang}
                            />
                        ))}
                    </div>

                    {hasMoreJobs && (
                        <div style={{ display: 'flex', justifyContent: 'center', marginTop: '24px' }}>
                            <button
                                className="btn btn-primary"
                                onClick={handleLoadMore}
                                style={{ padding: '12px 32px', fontSize: '1rem' }}
                            >
                                {S.load_more} ({displayedJobs.length - visibleCount} {S.remaining})
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* No results */}
            {!loadingJobs && jobs.length > 0 && displayedJobs.length === 0 && (
                <div className="alert alert-info">
                    {S.no_results}
                </div>
            )}

           
            {/* Footer */}
            <div className="app-footer">
                <div className="app-footer-inner">
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        🤖 <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Gemini</span>
                        <span style={{ opacity: 0.4 }}>·</span>
                        <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Groq</span>
                        <span style={{ opacity: 0.4 }}>·</span>
                        <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Llama</span>
                        <span style={{ opacity: 0.4 }}>·</span>
                        <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Mistral</span>
                    </span>
                    <span style={{ opacity: 0.3, fontWeight: '900' }}>|</span>
                    <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>by Yanès Hadiouche</span>
                </div>
            </div>

            {/* AI Copilot Chat - Floating Context-Aware Assistant */}
            <AIChatDrawer
                jobs={displayedJobs}
                cvData={cvData}
                agentType={activeAgent}
                noAiMode={noAiMode}
                lang={lang}
            />
        </AppLayout>
    );
}

// ─── Root App Content with Hub Routing ───────────────────────────────────────
function AppContent() {
    const [currentApp, setCurrentApp] = useState(null);
    const [selectedLang, setSelectedLang] = useState('Français');
    const [darkMode, setDarkMode] = useState(() => {
        return localStorage.getItem('darkMode') === 'true';
    });

    // Sync dark mode with DOM and localStorage on mount and when darkMode changes
    useEffect(() => {
        if (darkMode) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('darkMode', 'true');
        } else {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('darkMode', 'false');
        }
    }, [darkMode]);

    const toggleDarkMode = () => {
        setDarkMode(prev => !prev);
    };

    const handleSelectApp = (appId, lang) => {
        setSelectedLang(lang || selectedLang);
        setCurrentApp(appId);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const handleBackToHub = () => {
        setCurrentApp(null);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    // Map hub selection to agent type
    if (currentApp === 'job' || currentApp === 'freelance' || currentApp === 'worker') {
        // The UnifiedAgentApp reads activeAgent from AgentContext.
        // We need to set it when the user selects from the hub.
        return <UnifiedAgentAppWithAgent
            agentType={currentApp === 'worker' ? 'recruiter' : currentApp}
            onBackToHub={handleBackToHub}
            lang={selectedLang}
            setLang={setSelectedLang}
            onToggleDarkMode={toggleDarkMode}
            darkMode={darkMode}
        />;
    }

    return (
        <LandingHub
            onSelectApp={handleSelectApp}
            lang={selectedLang}
            setLang={setSelectedLang}
            onToggleDarkMode={toggleDarkMode}
        />
    );
}

/**
 * Wrapper qui initialise l'agent actif depuis la sélection du hub,
 * puis rend UnifiedAgentApp.
 */
function UnifiedAgentAppWithAgent({ agentType, onBackToHub, lang, setLang, onToggleDarkMode, darkMode }) {
    const { setActiveAgent } = useAgent();

    // Set the active agent when the hub selection changes
    useEffect(() => {
        setActiveAgent(agentType);
    }, [agentType, setActiveAgent]);

    return (
        <UnifiedAgentApp
            onBackToHub={onBackToHub}
            lang={lang}
            setLang={setLang}
            onToggleDarkMode={onToggleDarkMode}
            darkMode={darkMode}
        />
    );
}

// Export UnifiedAgentApp for reuse in standalone agent apps
export { UnifiedAgentApp };

// ─── Root App wrapped with AIProvider + AgentProvider ──────────────────────────
export default function App() {
    return (
        <AIProvider>
            <AgentProvider>
                <AppContent />
            </AgentProvider>
        </AIProvider>
    );
}