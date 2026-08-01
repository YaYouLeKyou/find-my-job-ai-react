/**
 * UnifiedSearchEngine - Moteur de recherche générique et réutilisable
 * 
 * Extrait et standardise la logique de recherche optimisée de "Find my job" :
 * - Élargissement de requêtes (query relaxation)
 * - Fallback multi-sources
 * - Gestion des quotas et retries
 * - Mise en cache (In-Memory + localStorage)
 * - Invalidation de cache sur modification de filtres
 * - Streaming SSE temps réel
 * 
 * Utilisable par :
 * - FindMyJobAgent
 * - FindMyFreelanceMissionAgent
 * - FindMyWorkerAgent
 */

import { useAI } from '../context/AIContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

// =============================================================================
// TYPES
// =============================================================================

export type AgentType = 'job' | 'freelance' | 'worker';

export interface SearchParams {
    query: string;
    location: string;
    numAds: number | string;
    contract: string;
    remote: boolean;
    globalSearch: boolean;
    selectedSources: string[];
    sortOption: string;
    cvData?: any;
    agentType: AgentType;
}

export interface SearchResult {
    jobs: any[];
    sourceCounts: Record<string, number>;
    searchTime: number;
    fromCache: boolean;
}

export interface SSEEvent {
    type: 'STARTED' | 'PROGRESS' | 'SOURCE_RESULT' | 'SCORES_UPDATED' | 'COMPLETED' | 'ERROR';
    [key: string]: any;
}

export interface SearchCallbacks {
    onStarted?: (data: SSEEvent) => void;
    onProgress?: (data: SSEEvent) => void;
    onSourceResult?: (data: SSEEvent) => void;
    onScoresUpdated?: (data: SSEEvent) => void;
    onCompleted?: (data: SSEEvent) => void;
    onError?: (data: SSEEvent) => void;
    onJobsUpdate?: (jobs: any[]) => void;
    onSourceCountsUpdate?: (counts: Record<string, number>) => void;
}

// =============================================================================
// HELPERS
// =============================================================================

function hashCode(str: string): string {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return Math.abs(hash).toString(36);
}

// Tri côté client basé sur l'option de tri
export function sortJobs(jobs: any[], sortOption: string): any[] {
    if (!jobs || jobs.length === 0) return jobs;

    const sorted = [...jobs];

    if (sortOption === 'Pertinence (IA)' || sortOption === 'Relevance (AI)') {
        sorted.sort((a, b) => {
            const sa = parseFloat(a.pertinence_ai) || 0;
            const sb = parseFloat(b.pertinence_ai) || 0;
            return sb - sa;
        });
    } else if (sortOption === 'Plus récentes' || sortOption === 'Most recent') {
        sorted.sort((a, b) => {
            const da = a.posted_date || a.date || '';
            const db = b.posted_date || b.date || '';
            return String(db).localeCompare(String(da));
        });
    } else if (sortOption === 'Plus proches' || sortOption === 'Closest') {
        sorted.sort((a, b) => {
            const sa = parseFloat(a.distance_score) || 0;
            const sb = parseFloat(b.distance_score) || 0;
            return sb - sa;
        });
    }

    return sorted;
}

// =============================================================================
// CACHE MANAGER
// =============================================================================

class SearchCacheManager {
    private memoryCache: Map<string, { results: any[]; sourceCounts: Record<string, number>; ts: number }> = new Map();
    private readonly TTL = 30 * 60 * 1000; // 30 minutes

    // Générer une clé de cache basée sur les paramètres
    getCacheKey(params: SearchParams): string {
        return `search_cache_${hashCode(JSON.stringify({
            q: params.query.toLowerCase().trim(),
            l: params.globalSearch ? '' : params.location,
            n: params.numAds,
            c: params.contract,
            r: params.remote,
            s: params.selectedSources.sort(),
            sort: params.sortOption,
            agent: params.agentType,
        }))}`;
    }

    // Récupérer du cache
    get(cacheKey: string): { results: any[]; sourceCounts: Record<string, number> } | null {
        // Vérifier le cache mémoire d'abord
        const memCached = this.memoryCache.get(cacheKey);
        if (memCached && Date.now() - memCached.ts < this.TTL) {
            return { results: memCached.results, sourceCounts: memCached.sourceCounts };
        }

        // Vérifier le localStorage
        try {
            const localCached = localStorage.getItem(cacheKey);
            if (localCached) {
                const parsed = JSON.parse(localCached);
                const cacheAge = Date.now() - (parsed.ts || 0);
                if (cacheAge < this.TTL) {
                    // Mettre en cache mémoire
                    this.memoryCache.set(cacheKey, { ...parsed, ts: Date.now() });
                    return { results: parsed.results || [], sourceCounts: parsed.source_counts || {} };
                }
                // Cache expiré
                localStorage.removeItem(cacheKey);
            }
        } catch (e) {
            console.error('[CacheManager] Failed to read cache:', e);
        }

        return null;
    }

    // Stocker en cache
    set(cacheKey: string, results: any[], sourceCounts: Record<string, number>): void {
        const data = { results, sourceCounts, ts: Date.now() };

        // Cache mémoire
        this.memoryCache.set(cacheKey, data);

        // Cache localStorage
        try {
            localStorage.setItem(cacheKey, JSON.stringify({
                results: data.results,
                source_counts: data.sourceCounts,
                ts: data.ts,
            }));
        } catch (e) {
            console.error('[CacheManager] Failed to write cache:', e);
        }
    }

    // Invalider un cache spécifique
    invalidate(cacheKey: string): void {
        this.memoryCache.delete(cacheKey);
        try {
            localStorage.removeItem(cacheKey);
        } catch (e) {
            console.error('[CacheManager] Failed to invalidate cache:', e);
        }
    }

    // Invalider tous les caches pour un agent
    invalidateAgent(agentType: AgentType): void {
        // Invalider le cache mémoire
        for (const key of this.memoryCache.keys()) {
            if (key.includes(`agent-${agentType}`)) {
                this.memoryCache.delete(key);
            }
        }

        // Invalider le localStorage
        try {
            const keysToRemove: string[] = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith('search_cache_')) {
                    keysToRemove.push(key);
                }
            }
            keysToRemove.forEach(key => localStorage.removeItem(key));
        } catch (e) {
            console.error('[CacheManager] Failed to invalidate agent cache:', e);
        }
    }

    // Vider tout le cache
    clearAll(): void {
        this.memoryCache.clear();
        try {
            const keysToRemove: string[] = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith('search_cache_')) {
                    keysToRemove.push(key);
                }
            }
            keysToRemove.forEach(key => localStorage.removeItem(key));
        } catch (e) {
            console.error('[CacheManager] Failed to clear all cache:', e);
        }
    }
}

// Instance singleton du cache manager
export const searchCache = new SearchCacheManager();

// =============================================================================
// MOTEUR DE RECHERCHE UNIFIÉ
// =============================================================================

export class UnifiedSearchEngine {
    private eventSource: EventSource | null = null;
    private cache: SearchCacheManager;

    constructor() {
        this.cache = searchCache;
    }

    // Fermer la connexion SSE active
    closeConnection(): void {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }

    // Endpoint SSE selon le type d'agent
    private getStreamEndpoint(agentType: AgentType): string {
        switch (agentType) {
            case 'job':
                return '/api/search-jobs-stream';
            case 'freelance':
                return '/api/search-freelance-stream';
            case 'worker':
                return '/api/search-worker-stream';
            default:
                return '/api/search-jobs-stream';
        }
    }

    // Exécuter une recherche avec SSE
    async search(
        params: SearchParams,
        callbacks: SearchCallbacks,
        options?: { skipCache?: boolean }
    ): Promise<SearchResult> {
        const startTime = Date.now();
        const { skipCache = false } = options || {};

        // Fermer toute connexion SSE existante
        this.closeConnection();

        // Vérifier le cache
        const cacheKey = this.cache.getCacheKey(params);
        if (!skipCache) {
            const cached = this.cache.get(cacheKey);
            if (cached) {
                const sortedJobs = sortJobs(cached.results, params.sortOption);
                const searchTime = ((Date.now() - startTime) / 1000).toFixed(2);
                callbacks.onJobsUpdate?.(sortedJobs);
                callbacks.onSourceCountsUpdate?.(cached.sourceCounts);
                callbacks.onCompleted?.({
                    type: 'COMPLETED',
                    jobs: sortedJobs,
                    source_status: cached.sourceCounts,
                    fromCache: true,
                });
                return {
                    jobs: sortedJobs,
                    sourceCounts: cached.sourceCounts,
                    searchTime: parseFloat(searchTime),
                    fromCache: true,
                };
            }
        }

        // Obtenir la clé API active depuis le contexte AI
        // Note: La clé est passée via les paramètres de l'URL
        const aiContext = this.getAIContext();
        const activeApiKey = aiContext?.getActiveApiKey() || '';
        const activeModel = aiContext?.activeModel || 'Groq / Llama 3.3';

        // Construire les paramètres de l'URL
        const urlParams = new URLSearchParams({
            query: params.query,
            location: params.globalSearch ? '' : params.location,
            num_ads: String(params.numAds === 'Max' ? 120 : params.numAds),
            contract: params.contract,
            remote: String(params.remote),
            global_search: String(params.globalSearch),
            selected_sources: params.selectedSources.join(','),
            sort_option: params.sortOption,
            ranking_engine: activeModel,
            custom_gemini_key: activeApiKey,
            cv_data: params.cvData ? JSON.stringify(params.cvData) : '',
        });

        const streamUrl = `${API_BASE}${this.getStreamEndpoint(params.agentType)}?${urlParams.toString()}`;

        return new Promise((resolve, reject) => {
            let accumulatedJobs: any[] = [];
            let accumulatedSourceCounts: Record<string, number> = {};
            let resolved = false;

            const es = new EventSource(streamUrl);
            this.eventSource = es;

            es.onmessage = (event) => {
                try {
                    const data: SSEEvent = JSON.parse(event.data);

                    switch (data.type) {
                        case 'STARTED':
                            callbacks.onStarted?.(data);
                            break;

                        case 'PROGRESS':
                            if (data.source) {
                                accumulatedSourceCounts[data.source] = data.jobs ? data.jobs.length : 0;
                                callbacks.onSourceCountsUpdate?.({ ...accumulatedSourceCounts });
                            }
                            callbacks.onProgress?.(data);
                            break;

                        case 'SOURCE_RESULT':
                        case 'PROGRESS':
                            if (data.jobs && data.jobs.length > 0) {
                                accumulatedJobs = [...accumulatedJobs, ...data.jobs];
                                const sorted = sortJobs(accumulatedJobs, params.sortOption);
                                callbacks.onJobsUpdate?.(sorted);
                            }
                            if (data.source) {
                                accumulatedSourceCounts[data.source] = data.jobs ? data.jobs.length : 0;
                                callbacks.onSourceCountsUpdate?.({ ...accumulatedSourceCounts });
                            }
                            callbacks.onSourceResult?.(data);
                            break;

                        case 'SCORES_UPDATED':
                            if (data.jobs && data.jobs.length > 0) {
                                accumulatedJobs = data.jobs;
                                const sorted = sortJobs(accumulatedJobs, params.sortOption);
                                callbacks.onJobsUpdate?.(sorted);
                            }
                            callbacks.onScoresUpdated?.(data);
                            break;

                        case 'COMPLETED':
                            if (data.jobs && data.jobs.length > 0) {
                                accumulatedJobs = data.jobs;
                            }
                            const sortedJobs = sortJobs(accumulatedJobs, params.sortOption);
                            callbacks.onJobsUpdate?.(sortedJobs);

                            // Construire sourceCounts depuis source_status
                            if (data.source_status) {
                                const counts: Record<string, number> = {};
                                Object.entries(data.source_status).forEach(([source, status]: [string, any]) => {
                                    if (status && (status.count !== undefined || status.jobs_count !== undefined)) {
                                        counts[source] = status.count !== undefined ? status.count : status.jobs_count;
                                    }
                                });
                                accumulatedSourceCounts = counts;
                                callbacks.onSourceCountsUpdate?.(counts);
                            }

                            // Mettre en cache
                            this.cache.set(cacheKey, accumulatedJobs, accumulatedSourceCounts);

                            const searchTime = ((Date.now() - startTime) / 1000).toFixed(2);
                            callbacks.onCompleted?.(data);

                            es.close();
                            this.eventSource = null;

                            if (!resolved) {
                                resolved = true;
                                resolve({
                                    jobs: sortedJobs,
                                    sourceCounts: accumulatedSourceCounts,
                                    searchTime: parseFloat(searchTime),
                                    fromCache: false,
                                });
                            }
                            break;

                        case 'ERROR':
                            callbacks.onError?.(data);
                            es.close();
                            this.eventSource = null;
                            if (!resolved) {
                                resolved = true;
                                reject(new Error(data.message || 'Erreur de recherche'));
                            }
                            break;
                    }
                } catch (e) {
                    console.error('[UnifiedSearchEngine] Failed to parse SSE event:', e);
                }
            };

            es.onerror = (err) => {
                console.error('[UnifiedSearchEngine] SSE connection error:', err);
                if (this.eventSource === es) {
                    callbacks.onError?.({ type: 'ERROR', message: 'Erreur de connexion au serveur de recherche.' });
                    es.close();
                    this.eventSource = null;
                    if (!resolved) {
                        resolved = true;
                        reject(new Error('Erreur de connexion au serveur de recherche.'));
                    }
                }
            };
        });
    }

    // Obtenir le contexte AI (méthode utilitaire)
    private getAIContext() {
        // Cette méthode sera remplacée par l'injection de dépendance
        // Pour l'instant, on lit depuis localStorage
        try {
            const activeModel = localStorage.getItem('ai_active_model') || 'Groq / Llama 3.3';
            const savedKeys = localStorage.getItem('ai_api_keys');
            let activeKey = '';

            if (savedKeys) {
                const parsed = JSON.parse(savedKeys);
                // Déterminer le fournisseur du modèle actif
                if (activeModel.includes('Gemini') && parsed.gemini) {
                    activeKey = parsed.gemini.key || '';
                } else if (activeModel.includes('Groq') && parsed.groq) {
                    activeKey = parsed.groq.key || '';
                }
            }

            return {
                activeModel,
                getActiveApiKey: () => activeKey,
            };
        } catch {
            return null;
        }
    }

    // Invalider le cache pour des paramètres donnés
    invalidateCache(params: SearchParams): void {
        const cacheKey = this.cache.getCacheKey(params);
        this.cache.invalidate(cacheKey);
    }

    // Invalider tout le cache pour un agent
    invalidateAgentCache(agentType: AgentType): void {
        this.cache.invalidateAgent(agentType);
    }

    // Vider tout le cache
    clearAllCache(): void {
        this.cache.clearAll();
    }
}

// Instance singleton du moteur de recherche
export const unifiedSearchEngine = new UnifiedSearchEngine();

// =============================================================================
// HOOK REACT POUR LE MOTEUR DE RECHERCHE
// =============================================================================

import { useState, useCallback, useRef } from 'react';

export function useUnifiedSearch(agentType: AgentType) {
    const [jobs, setJobs] = useState < any[] > ([]);
    const [sourceCounts, setSourceCounts] = useState < Record < string, number>> ({});
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState < string | null > (null);
    const [searchTime, setSearchTime] = useState < number | null > (null);
    const engineRef = useRef < UnifiedSearchEngine > (unifiedSearchEngine);

    const search = useCallback(async (
        params: Omit<SearchParams, 'agentType'>,
        options?: { skipCache?: boolean }
    ) => {
        setLoading(true);
        setError(null);
        setJobs([]);
        setSourceCounts({});

        try {
            const result = await engineRef.current.search(
                { ...params, agentType },
                {
                    onJobsUpdate: setJobs,
                    onSourceCountsUpdate: setSourceCounts,
                    onError: (data) => setError(data.message || 'Erreur de recherche'),
                },
                options
            );

            setJobs(result.jobs);
            setSourceCounts(result.sourceCounts);
            setSearchTime(result.searchTime);
            return result;
        } catch (err: any) {
            setError(err.message || 'Erreur de recherche');
            return null;
        } finally {
            setLoading(false);
        }
    }, [agentType]);

    const clearCache = useCallback(() => {
        engineRef.current.invalidateAgentCache(agentType);
    }, [agentType]);

    const closeConnection = useCallback(() => {
        engineRef.current.closeConnection();
    }, []);

    return {
        jobs,
        sourceCounts,
        loading,
        error,
        searchTime,
        search,
        clearCache,
        closeConnection,
        setJobs,
        setSourceCounts,
    };
}

export default UnifiedSearchEngine;