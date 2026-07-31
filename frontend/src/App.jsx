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

import React, { useState, useEffect, useRef } from 'react';
import { AIProvider, useAI } from './context/AIContext';
import { AgentProvider, useAgent } from './context/AgentContext';
import { LANGS, STRINGS } from './utils/translations';
import { useStreamSearch } from './hooks/useStreamSearch';

import LandingHub from './components/LandingHub';
import AppLayout from './components/layout/AppLayout';
import AISettings from './components/features/AISettings';
import DocumentAnalyzer from './components/features/DocumentAnalyzer';
import SearchBar from './components/features/SearchBar';
import ResultCard from './components/features/ResultCard';
import ActiveSourcesHeader from './components/ActiveSourcesHeader';
import AdComponent from './components/AdComponent';
import SEO from './components/SEO';
import SearchProgressBar from './components/SearchProgressBar';

import { Loader2 } from 'lucide-react';
import './styles/streaming.css';

const API_BASE = import.meta.env.VITE_API_URL || '';

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
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedSources, setSelectedSources] = useState(agentConfig.sources);
    const [excludedSources, setExcludedSources] = useState([]);
    const [searchHistory, setSearchHistory] = useState([]);
    const [savedItems, setSavedItems] = useState([]);
    const [toast, setToast] = useState(null);
    const [visibleCount, setVisibleCount] = useState(20);

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
    } = useStreamSearch(API_BASE, activeAgent, noAiMode, (result) => {
        console.log('[App] Recherche terminée:', result);
    });

    // --- Load persisted state on mount ---
    useEffect(() => {
        const savedHistory = localStorage.getItem('searchHistory');
        if (savedHistory) setSearchHistory(JSON.parse(savedHistory));

        const savedItemsData = localStorage.getItem('savedItems');
        if (savedItemsData) setSavedItems(JSON.parse(savedItemsData));
    }, []);

    // --- Sync selectedSources when agent changes ---
    useEffect(() => {
        setSelectedSources(agentConfig.sources);
    }, [activeAgent, agentConfig.sources]);

    // --- Handlers ---
    const handleCvAnalysisSuccess = (data) => {
        setCvData(data);
        if (data.metier) setSearchQuery(data.metier);
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
                        showToast(`⚡ ${results.length} résultats depuis le cache (${(cacheAge / 1000).toFixed(0)}s)`, 'success');
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

    // --- Save / Unsave items ---
    const toggleSaveItem = (item) => {
        const isSaved = savedItems.some(j => j.id === item.id);
        const updated = isSaved
            ? savedItems.filter(j => j.id !== item.id)
            : [...savedItems, item];
        setSavedItems(updated);
        localStorage.setItem('savedItems', JSON.stringify(updated));
        showToast(isSaved ? '💾 Retiré des favoris' : '✅ Sauvegardé dans les favoris', isSaved ? 'info' : 'success');
    };

    // --- Export to CSV ---
    const exportToCSV = () => {
        if (!displayedJobs.length) return;
        const headers = ['Titre', 'Entreprise', 'Localisation', 'Source', 'Date', 'Score IA', 'URL'];
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
        showToast('📊 Export CSV réussi !', 'success');
    };

    // --- Start Interview ---
    const handleStartInterview = (job) => {
        const interviewUrl = `/mock-interview.html?job=${encodeURIComponent(job.title || '')}&company=${encodeURIComponent(job.company || '')}`;
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

    // --- Build direct access links ---
    const generateSearchLinks = (jobTitle, langCode, agentType) => {
        const q = encodeURIComponent(jobTitle);
        const qSlug = q.replace(/%20/g, '-');
        const categories = {
            fr: {
                'Généralistes France': [
                    ['Indeed France', `https://fr.indeed.com/jobs?q=${q}`],
                    ['HelloWork', `https://www.hellowork.com/fr-fr/emploi/recherche.html?k=${q}`],
                    ['Glassdoor FR', `https://www.glassdoor.fr/emploi/emploi.htm?sc.keyword=${q}`],
                    ['France Travail', `https://candidat.pole-emploi.fr/offres/recherche?motsCles=${q}`],
                    ['APEC', `https://www.apec.fr/offres-d-emploi-cadre/recherche.html?motsCles=${q}`],
                    ['Monster FR', `https://www.monster.fr/emploi/recherche?q=${q}`],
                ],
                'Tech & Cadres': [
                    ['Welcome to the Jungle', `https://www.welcometothejungle.com/fr/jobs?query=${q}`],
                    ['JobTeaser', `https://www.jobteaser.com/fr/jobs?query=${q}`],
                    ['LinkedIn FR', `https://fr.linkedin.com/jobs/search/?keywords=${q}`],
                ],
            },
            en: {
                'Remote & Global': [
                    ['Remote OK', `https://remoteok.com/remote-${qSlug}-jobs`],
                    ['Indeed Global', `https://www.indeed.com/jobs?q=${q}`],
                    ['Glassdoor Global', `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${q}`],
                    ['LinkedIn Global', `https://www.linkedin.com/jobs/search/?keywords=${q}`],
                ],
                'Tech & Cadres': [
                    ['Reed.co.uk', `https://www.reed.co.uk/jobs/${qSlug}-jobs`],
                    ['Dice (Tech US)', `https://www.dice.com/jobs?q=${q}`],
                    ['LinkedIn US', `https://www.linkedin.com/jobs/search/?keywords=${q}`],
                ],
            },
        };
        const globalLinks = {
            'Remote OK': `https://remoteok.com/remote-${qSlug}-jobs`,
            'Indeed Global': `https://www.indeed.com/jobs?q=${q}`,
            'LinkedIn Global': `https://www.linkedin.com/jobs/search/?keywords=${q}`,
            'Glassdoor Global': `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${q}`,
            'France Travail (API)': `https://candidat.pole-emploi.fr/offres/recherche?motsCles=${q}&offresPartenaires=true`,
            'Adzuna (API)': `https://www.adzuna.fr/emploi?q=${q}`,
        };

        // Freelance-specific platforms
        const freelanceLinks = {
            'Malt': `https://www.malt.fr/search?query=${q}`,
            'Upwork': `https://www.upwork.com/nx/search/jobs/?q=${q}`,
            'Freelancer': `https://www.freelancer.com/jobs/?keyword=${q}`,
            'Toptal': `https://www.toptal.com/talent/apply`,
            'Codeur.com': `https://www.codeur.com/missions?keyword=${q}`,
            'Fiverr': `https://www.fiverr.com/search/gigs?query=${q}`,
        };

        // Recruiter-specific platforms (candidate search)
        const recruiterLinks = {
            'LinkedIn Recruiter': `https://www.linkedin.com/talent/search?keywords=${q}`,
            'Indeed CV': `https://www.indeed.com/hire/resumes?q=${q}`,
            'APEC Candidats': `https://www.apec.fr/candidat/recherche-candidats.html?motsCles=${q}`,
            'Monster CV': `https://www.monster.fr/employeurs/recherche-cv?keyword=${q}`,
        };

        const langCategories = categories[langCode] || {};
        const allLinks = [];
        Object.entries(langCategories).forEach(([category, links]) => {
            allLinks.push({ category, links });
        });
        allLinks.push({ category: 'Global', links: Object.entries(globalLinks) });

        // Add agent-specific links
        if (agentType === 'freelance') {
            allLinks.push({ category: '🚀 Freelance', links: Object.entries(freelanceLinks) });
        } else if (agentType === 'recruiter') {
            allLinks.push({ category: '👷 Recrutement', links: Object.entries(recruiterLinks) });
        }

        return allLinks;
    };

    const directLinks = searchQuery ? generateSearchLinks(searchQuery, currentLangCode, activeAgent) : [];
    const displayedJobs = jobs.filter(job => !excludedSources.includes(job.source));
    const visibleJobs = displayedJobs.slice(0, visibleCount);
    const hasMoreJobs = visibleCount < displayedJobs.length;
    const handleLoadMore = () => {
        setVisibleCount(prev => Math.min(prev + 10, displayedJobs.length));
    };

    // --- Result type label ---
    const resultTypeLabel = agentConfig.resultType === 'mission'
        ? S.mission_results || '🎯 Missions recommandées'
        : agentConfig.resultType === 'candidate'
            ? '🎯 Candidats recommandés'
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
            <AISettings />

            {/* Document Analyzer (CV / Fiche de poste) - IDENTIQUE pour tous les agents */}
            <DocumentAnalyzer
                lang={lang}
                onAnalysisSuccess={handleCvAnalysisSuccess}
            />

            {/* ─── Quick Filters (in body, under DocumentAnalyzer) ─────────── */}
            <div className="card" style={{ marginTop: '16px', background: 'var(--color-surface)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                    <span style={{ fontSize: '1rem' }}>🎛️</span>
                    <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>Filtres rapides</h3>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {agentConfig.filters.map((filter) => {
                        const value = activeFilters[filter.id];

                        if (filter.type === 'select') {
                            return (
                                <div key={filter.id} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        {filter.label}
                                    </label>
                                    <select
                                        value={value || ''}
                                        onChange={(e) => updateFilter(filter.id, e.target.value)}
                                        className="select-control"
                                        style={{ padding: '8px 12px', fontSize: '0.875rem' }}
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
                                <div key={filter.id} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        {filter.label}
                                    </label>
                                    <input
                                        type="text"
                                        placeholder={filter.placeholder || ''}
                                        value={value || ''}
                                        onChange={(e) => updateFilter(filter.id, e.target.value)}
                                        className="input-control"
                                        style={{ padding: '8px 12px', fontSize: '0.875rem', minWidth: '150px' }}
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
                                <div key={filter.id} style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '120px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                            {filter.label}
                                        </label>
                                        <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--color-primary-500)' }}>
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
                                        style={{ width: '100%', accentColor: 'var(--color-primary-500)', cursor: 'pointer' }}
                                    />
                                </div>
                            );
                        }

                        if (filter.type === 'number') {
                            return (
                                <div key={filter.id} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
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
                                        style={{ padding: '8px 12px', fontSize: '0.875rem', minWidth: '100px' }}
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

            {/* Active Sources Header */}
            {Object.keys(sourceCounts).length > 0 && (
                <ActiveSourcesHeader
                    sourceCounts={sourceCounts}
                    totalJobs={jobs.length}
                    aiProcessing={aiProcessing}
                    processedCount={processedCount}
                />
            )}

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
                placeholder={
                    agentConfig.resultType === 'mission'
                        ? S.mission_search_placeholder
                        : S.search_placeholder
                }
            />

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
                        Scan global des plateformes en cours...
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
                        {totalSources > 0 ? `Source ${sourcesDone}/${totalSources}` : 'Initialisation...'}
                        {aiProcessing && ' · Tri IA...'}
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
                                📊 Exporter CSV
                            </button>
                            <button
                                onClick={cancelSearch}
                                className="btn btn-secondary"
                                style={{ fontSize: '0.85rem' }}
                            >
                                Annuler
                            </button>
                        </div>
                    </div>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
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
                                Charger plus de résultats ({displayedJobs.length - visibleCount} restants)
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
                    </span>
                    <span style={{ opacity: 0.3, fontWeight: '900' }}>|</span>
                    <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>by Yanès Hadiouche</span>
                </div>
            </div>
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
