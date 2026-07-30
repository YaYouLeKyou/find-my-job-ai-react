/**
 * useStreamSearch - Hook personnalisé pour la recherche progressive avec tri IA
 * 
 * Architecture:
 * 1. Accumulation brute des résultats par source
 * 2. Tri IA par paquets (chunks de 10)
 * 3. Réorganisation progressive du state
 * 4. Animations fluides sans re-render complet
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const AI_CHUNK_SIZE = 10; // Nombre d'offres par paquet pour le tri IA
const DEBOUNCE_DELAY = 300; // Délai anti-rebond pour les re-renders

export function useStreamSearch(apiBase, params, onSearchComplete) {
    const [jobs, setJobs] = useState([]);
    const [sourceCounts, setSourceCounts] = useState({});
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searchTime, setSearchTime] = useState(null);
    const [aiProcessing, setAiProcessing] = useState(false);
    const [processedCount, setProcessedCount] = useState(0);

    const eventSourceRef = useRef(null);
    const accumulatedJobsRef = useRef([]);
    const accumulatedSourceCountsRef = useRef({});
    const pendingAiChunkRef = useRef([]);
    const aiProcessingRef = useRef(false);
    const abortControllerRef = useRef(null);
    const debounceTimerRef = useRef(null);

    // Nettoyage à la destruction
    useEffect(() => {
        return () => {
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
            }
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
        };
    }, []);

    // Fonction de tri IA par paquets
    const processAiChunk = useCallback(async (chunk, rankingEngine, customGeminiKey) => {
        if (aiProcessingRef.current || chunk.length === 0) return;

        aiProcessingRef.current = true;
        setAiProcessing(true);

        try {
            // Préparer le prompt pour le scoring IA
            const jobsToScore = chunk.map(job => ({
                id: job.id,
                title: job.title,
                company: job.company,
                description: job.description?.substring(0, 500) || '',
                location: job.location,
            }));

            const prompt = `Score ces offres d'emploi de 0 à 100 selon leur pertinence et leur qualité.
Retourne un objet JSON avec ce format exact:
{
  "scores": {
    "job_id_1": 85,
    "job_id_2": 72,
    ...
  }
}

Offres à scorer:
${JSON.stringify(jobsToScore, null, 2)}`;

            const response = await fetch(`${apiBase}/api/ai/call`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt,
                    model: rankingEngine,
                    provider: 'groq', // Par défaut, peut être adapté
                    isJson: true,
                    temperature: 0.3,
                    maxTokens: 2000,
                }),
            });

            if (!response.ok) throw new Error('AI scoring failed');

            const data = await response.json();
            const scores = data.text ? JSON.parse(data.text)?.scores : {};

            // Appliquer les scores aux jobs
            setJobs(prevJobs => {
                return prevJobs.map(job => ({
                    ...job,
                    pertinence_ai: scores[job.id] || job.pertinence_ai || 50,
                    ai_scored: true,
                })).sort((a, b) => (b.pertinence_ai || 0) - (a.pertinence_ai || 0));
            });

            setProcessedCount(prev => prev + chunk.length);
        } catch (err) {
            console.error('[AI] Chunk processing error:', err);
            // En cas d'erreur, on garde les jobs sans score
            setJobs(prevJobs => {
                return prevJobs.map(job =>
                    chunk.find(c => c.id === job.id) ? { ...job, pertinence_ai: 50, ai_scored: false } : job
                );
            });
        } finally {
            aiProcessingRef.current = false;
            setAiProcessing(false);
        }
    }, [apiBase]);

    // Lancer la recherche
    const search = useCallback((searchParams) => {
        // Annuler la recherche précédente
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        // Réinitialiser les états
        setLoading(true);
        setError(null);
        setJobs([]);
        setSourceCounts({});
        setSearchTime(null);
        setAiProcessing(false);
        setProcessedCount(0);

        accumulatedJobsRef.current = [];
        accumulatedSourceCountsRef.current = {};
        pendingAiChunkRef.current = [];
        aiProcessingRef.current = false;

        const startTime = Date.now();

        // Construire l'URL
        const queryParams = new URLSearchParams(searchParams);
        const streamUrl = `${apiBase}/api/search-jobs-stream?${queryParams.toString()}`;

        // Créer un nouvel AbortController
        abortControllerRef.current = new AbortController();

        const eventSource = new EventSource(streamUrl);
        eventSourceRef.current = eventSource;

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                // STARTED
                if (data.type === 'STARTED') {
                    console.log(`[Stream] Recherche démarrée: ${data.query} (${data.total_sources} sources)`);
                }

                // PROGRESS / SOURCE_RESULT - Affichage immédiat
                if (data.type === 'PROGRESS' || data.type === 'SOURCE_RESULT') {
                    // Mettre à jour les compteurs de sources
                    if (data.source && data.jobs && data.jobs.length > 0) {
                        accumulatedSourceCountsRef.current[data.source] = data.jobs.length;

                        // Ne montrer que les sources avec des résultats
                        setSourceCounts({ ...accumulatedSourceCountsRef.current });

                        console.log(`[Stream] ${data.source}: ${data.jobs.length} offres reçues`);
                    }

                    // Ajouter les jobs à la liste accumulée
                    if (data.jobs && data.jobs.length > 0) {
                        // Ajouter un ID unique si absent
                        const jobsWithId = data.jobs.map((job, idx) => ({
                            ...job,
                            id: job.id || `${data.source}-${Date.now()}-${idx}`,
                            source: data.source,
                            receivedAt: Date.now(),
                        }));

                        accumulatedJobsRef.current = [...accumulatedJobsRef.current, ...jobsWithId];

                        // Affichage immédiat (sans tri IA pour l'instant)
                        setJobs([...accumulatedJobsRef.current]);

                        // Cacher le loader
                        if (loading) {
                            setLoading(false);
                        }

                        // Ajouter au chunk IA en attente
                        pendingAiChunkRef.current = [...pendingAiChunkRef.current, ...jobsWithId];

                        // Lancer le tri IA si on a assez de jobs
                        if (pendingAiChunkRef.current.length >= AI_CHUNK_SIZE && !aiProcessingRef.current) {
                            const chunkToProcess = pendingAiChunkRef.current.splice(0, AI_CHUNK_SIZE);
                            processAiChunk(chunkToProcess, searchParams.ranking_engine, searchParams.custom_gemini_key);
                        }
                    }
                }

                // SCORES_UPDATED - Tri IA terminé
                if (data.type === 'SCORES_UPDATED' && data.jobs) {
                    console.log(`[Stream] Tri IA terminé: ${data.jobs.length} offres scorées`);
                    setJobs(data.jobs);
                    setProcessedCount(data.jobs.length);
                }

                // COMPLETED - Fin de la recherche
                if (data.type === 'COMPLETED') {
                    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
                    setSearchTime(duration);

                    if (data.jobs && data.jobs.length > 0) {
                        setJobs(data.jobs);
                    }

                    if (data.source_status) {
                        const counts = {};
                        Object.entries(data.source_status).forEach(([source, status]) => {
                            if (status && (status.count !== undefined || status.jobs_count !== undefined)) {
                                counts[source] = status.count !== undefined ? status.count : status.jobs_count;
                            }
                        });
                        setSourceCounts(counts);
                    }

                    // Traiter le dernier chunk IA en attente
                    if (pendingAiChunkRef.current.length > 0 && !aiProcessingRef.current) {
                        processAiChunk(pendingAiChunkRef.current, searchParams.ranking_engine, searchParams.custom_gemini_key);
                        pendingAiChunkRef.current = [];
                    }

                    eventSource.close();
                    eventSourceRef.current = null;
                    setLoading(false);

                    console.log(`[Stream] Recherche terminée: ${accumulatedJobsRef.current.length} offres en ${duration}s`);

                    if (onSearchComplete) {
                        onSearchComplete({
                            jobs: accumulatedJobsRef.current,
                            sourceCounts: accumulatedSourceCountsRef.current,
                            duration,
                        });
                    }
                }

                // ERROR
                if (data.type === 'ERROR') {
                    console.error('[Stream] Erreur:', data.message);
                    setError(data.message || 'Erreur de connexion au flux');
                    eventSource.close();
                    eventSourceRef.current = null;
                    setLoading(false);
                }
            } catch (err) {
                console.error('[Stream] Erreur de parsing:', err);
            }
        };

        eventSource.onerror = (err) => {
            console.error('[Stream] Erreur de connexion:', err);
            if (eventSourceRef.current === eventSource) {
                setError('Erreur de connexion au serveur');
                eventSource.close();
                eventSourceRef.current = null;
                setLoading(false);
            }
        };
    }, [apiBase, processAiChunk, onSearchComplete]);

    // Annuler la recherche
    const cancel = useCallback(() => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        setLoading(false);
        setAiProcessing(false);
    }, []);

    return {
        jobs,
        sourceCounts,
        loading,
        error,
        searchTime,
        aiProcessing,
        processedCount,
        search,
        cancel,
    };
}