/**
 * useStreamSearch - Hook de recherche progressive avec rendu immédiat
 * 
 * Architecture:
 * 1. Rendu immédiat des jobs dès réception (PROGRESS/SOURCE_RESULT)
 * 2. Tri IA en arrière-plan par chunks de 10
 * 3. Déduplication temps réel
 * 4. Réorganisation fluide du state
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const AI_CHUNK_SIZE = 10; // Nombre d'offres par paquet pour le tri IA

export function useStreamSearch(apiBase, params, onSearchComplete) {
    const [jobs, setJobs] = useState([]);
    const [sourceCounts, setSourceCounts] = useState({});
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searchTime, setSearchTime] = useState(null);
    const [aiProcessing, setAiProcessing] = useState(false);
    const [processedCount, setProcessedCount] = useState(0);
    const [totalReceived, setTotalReceived] = useState(0);

    const eventSourceRef = useRef(null);
    const accumulatedJobsRef = useRef([]);
    const accumulatedSourceCountsRef = useRef({});
    const pendingAiChunkRef = useRef([]);
    const aiProcessingRef = useRef(false);
    const seenKeysRef = useRef(new Set());
    const abortControllerRef = useRef(null);

    // Nettoyage à la destruction
    useEffect(() => {
        return () => {
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
            }
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    // Fonction de déduplication temps réel
    const deduplicateJobs = useCallback((newJobs, existingJobs) => {
        const existingKeys = new Set(
            existingJobs.map(job => {
                const title = (job.title || '').toLowerCase().trim();
                const company = (job.company || '').toLowerCase().trim();
                return `${title}|${company}`;
            })
        );

        return newJobs.filter(job => {
            const title = (job.title || '').toLowerCase().trim();
            const company = (job.company || '').toLowerCase().trim();
            const key = `${title}|${company}`;

            if (existingKeys.has(key)) {
                return false;
            }
            existingKeys.add(key);
            return true;
        });
    }, []);

    // Fonction de tri IA par paquets (NON BLOQUANTE)
    const processAiChunk = useCallback(async (chunk, rankingEngine, customGeminiKey) => {
        if (aiProcessingRef.current || chunk.length === 0) return;

        aiProcessingRef.current = true;
        setAiProcessing(true);

        try {
            const jobsToScore = chunk.map(job => ({
                id: job.id,
                title: job.title,
                company: job.company,
                description: (job.description || '').substring(0, 500),
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
                    provider: 'groq',
                    isJson: true,
                    temperature: 0.3,
                    maxTokens: 2000,
                }),
            });

            if (!response.ok) throw new Error('AI scoring failed');

            const data = await response.json();
            const scores = data.text ? JSON.parse(data.text)?.scores : {};

            // Appliquer les scores aux jobs (mise à jour non-bloquante)
            setJobs(prevJobs => {
                return prevJobs.map(job => {
                    if (scores[job.id]) {
                        return {
                            ...job,
                            pertinence_ai: scores[job.id],
                            ai_scored: true,
                        };
                    }
                    return job;
                }).sort((a, b) => (b.pertinence_ai || 0) - (a.pertinence_ai || 0));
            });

            setProcessedCount(prev => prev + chunk.length);
        } catch (err) {
            console.error('[AI] Chunk processing error:', err);
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
        setTotalReceived(0);

        accumulatedJobsRef.current = [];
        accumulatedSourceCountsRef.current = {};
        pendingAiChunkRef.current = [];
        aiProcessingRef.current = false;
        seenKeysRef.current = new Set();

        const startTime = Date.now();

        // Construire l'URL
        const queryParams = new URLSearchParams(searchParams);
        const streamUrl = `${apiBase}/api/search-jobs-stream?${queryParams.toString()}`;

        // Créer un AbortController pour annuler la requête
        abortControllerRef.current = new AbortController();

        // Utiliser fetch avec streaming au lieu de EventSource
        fetch(streamUrl, {
            signal: abortControllerRef.current.signal,
            headers: {
                'Accept': 'text/event-stream',
            },
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                const readStream = () => {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            return;
                        }

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop() || '';

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.slice(6));

                                    // STARTED
                                    if (data.type === 'STARTED') {
                                        console.log(`[Stream] Recherche démarrée: ${data.query} (${data.total_sources} sources)`);
                                    }

                                    // PROGRESS / SOURCE_RESULT - Affichage IMMÉDIAT
                                    if (data.type === 'PROGRESS' || data.type === 'SOURCE_RESULT') {
                                        // Mettre à jour les compteurs de sources (même si 0 résultat)
                                        if (data.source) {
                                            const count = data.jobs ? data.jobs.length : 0;
                                            accumulatedSourceCountsRef.current[data.source] = count;
                                            setSourceCounts({ ...accumulatedSourceCountsRef.current });
                                            console.log(`[Stream] ${data.source}: ${count} offres reçues (status=${data.status || 'unknown'})`);
                                        }

                                        // Ajouter les jobs à la liste accumulée
                                        if (data.jobs && data.jobs.length > 0) {
                                            // Ajouter un ID unique si absent
                                            const jobsWithId = data.jobs.map((job, idx) => ({
                                                ...job,
                                                id: job.id || `${data.source}-${Date.now()}-${idx}`,
                                                source: data.source,
                                                receivedAt: Date.now(),
                                                isAiScored: false,
                                            }));

                                            // Dédupliquer en temps réel
                                            const deduplicatedJobs = deduplicateJobs(jobsWithId, accumulatedJobsRef.current);

                                            // Accumuler
                                            accumulatedJobsRef.current = [...accumulatedJobsRef.current, ...deduplicatedJobs];
                                            setTotalReceived(prev => prev + deduplicatedJobs.length);

                                            // AFFICHAGE IMMÉDIAT
                                            setJobs([...accumulatedJobsRef.current]);

                                            // Cacher le loader dès la première réception
                                            setLoading(false);

                                            // Ajouter au chunk IA en attente
                                            pendingAiChunkRef.current = [...pendingAiChunkRef.current, ...deduplicatedJobs];

                                            // Lancer le tri IA si on a assez de jobs (en arrière-plan, sans await)
                                            if (pendingAiChunkRef.current.length >= AI_CHUNK_SIZE && !aiProcessingRef.current) {
                                                const chunkToProcess = pendingAiChunkRef.current.splice(0, AI_CHUNK_SIZE);
                                                processAiChunk(chunkToProcess, searchParams.ranking_engine, searchParams.custom_gemini_key).catch(err =>
                                                    console.error('[AI] Background scoring error:', err)
                                                );
                                            }
                                        }
                                    }

                                    // SCORES_UPDATED - Tri IA terminé pour un chunk
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
                                        setLoading(false);
                                    }
                                } catch (err) {
                                    console.error('[Stream] Erreur de parsing:', err);
                                }
                            }
                        }

                        readStream();
                    }).catch(err => {
                        if (err.name !== 'AbortError') {
                            console.error('[Stream] Erreur de lecture:', err);
                            setError('Erreur de connexion au serveur');
                            setLoading(false);
                        }
                    });
                };

                readStream();
            })
            .catch(err => {
                if (err.name !== 'AbortError') {
                    console.error('[Stream] Erreur de connexion:', err);
                    setError('Erreur de connexion au serveur');
                    setLoading(false);
                }
            });
    }, [apiBase, processAiChunk, onSearchComplete, deduplicateJobs]);

    // Annuler la recherche
    const cancel = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
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
        totalReceived,
        search,
        cancel,
    };
}