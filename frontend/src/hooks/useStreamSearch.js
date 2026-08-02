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

// Réduire la taille du chunk pour des mises à jour plus fréquentes
const AI_CHUNK_SIZE = 5; // Réduit de 10 à 5 pour des updates plus fréquents

function generateJobId(job) {
    const title = (job.title || job.titre || job.intitule || '').toLowerCase().trim();
    const company = (job.company || job.entreprise || job.companyName || 'N/C').toLowerCase().trim();
    const link = (job.link || job.lien || job.job_url || job.url || '#').toLowerCase().trim();
    const raw = `${title}|${company}|${link}`;
    let hash = 0;
    for (let i = 0; i < raw.length; i++) {
        const char = raw.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash |= 0;
    }
    return Math.abs(hash).toString(16).padStart(12, '0').slice(0, 12);
}

function normalizeIncomingJob(job, source = '') {
    return {
        ...job,
        title: job.title || job.titre || job.intitule || job.poste || job.mission || job.name || '',
        company: job.company || job.entreprise || job.organisme || job.client || job.employer || '',
        link: job.link || job.lien || job.url || job.job_url || job.source_url || '#',
        location: job.location || job.lieu || job.city || job.region || '',
        description: job.description || job.desc || job.resume || job.summary || '',
        source: job.source || source || job.source_name || job.origin || '',
        ai_scored: job.ai_scored || false,
    };
}

export function useStreamSearch(apiBase, params, onSearchComplete) {
    const [jobs, setJobs] = useState([]);
    const [sourceCounts, setSourceCounts] = useState({});
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searchTime, setSearchTime] = useState(null);
    const [aiProcessing, setAiProcessing] = useState(false);
    const [processedCount, setProcessedCount] = useState(0);
    const [totalReceived, setTotalReceived] = useState(0);
    const [sourcesDone, setSourcesDone] = useState(0);
    const [totalSources, setTotalSources] = useState(0);
    const [sourceDiagnostics, setSourceDiagnostics] = useState({});
    const [sourceErrors, setSourceErrors] = useState({});

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
                const title = (job.title || job.titre || '').toLowerCase().trim();
                const company = (job.company || job.entreprise || '').toLowerCase().trim();
                const link = (job.link || job.lien || '').toLowerCase().trim();
                return `${title}|${company}|${link}`;
            })
        );

        return newJobs.filter(job => {
            const title = (job.title || job.titre || '').toLowerCase().trim();
            const company = (job.company || job.entreprise || '').toLowerCase().trim();
            const link = (job.link || job.lien || '').toLowerCase().trim();
            const key = `${title}|${company}|${link}`;

            if (!title && !company && !link) {
                return true;
            }

            if (existingKeys.has(key)) {
                return false;
            }
            existingKeys.add(key);
            return true;
        });
    }, []);

    const mergeJobsById = useCallback((base, incoming) => {
        const map = new Map();
        for (const job of base) {
            map.set(job.id, job);
        }
        for (const job of incoming) {
            map.set(job.id, job);
        }
        return Array.from(map.values());
    }, []);

    // Fonction de tri IA par paquets (NON BLOQUANTE)
    const processAiChunk = useCallback(async (chunk, rankingEngine, customGeminiKey) => {
        if (aiProcessingRef.current || chunk.length === 0) return;

        aiProcessingRef.current = true;
        setAiProcessing(true);

        try {
            const jobsToScore = chunk.map(job => ({
                id: job.id,
                title: job.title || job.titre || '',
                company: job.company || job.entreprise || '',
                description: (job.description || job.desc || '').substring(0, 500),
                location: job.location || job.lieu || '',
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
        setSourcesDone(0);
        setTotalSources(0);

        accumulatedJobsRef.current = [];
        accumulatedSourceCountsRef.current = {};
        pendingAiChunkRef.current = [];
        aiProcessingRef.current = false;
        seenKeysRef.current = new Set();
        setSourceDiagnostics({});
        setSourceErrors({});

        const startTime = Date.now();

        // Construire l'URL
        const queryParams = new URLSearchParams(searchParams);
        const streamUrl = `${apiBase}/api/search-jobs-stream?${queryParams.toString()}`;

        // Créer un EventSource natif pour le streaming SSE
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }

        const es = new EventSource(streamUrl);
        eventSourceRef.current = es;

        const streamCompletedRef = { current: false };

        es.onopen = () => {
            console.log('[Stream] Connexion SSE établie');
        };

        es.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'STARTED') {
                    console.log(`[Stream] Recherche démarrée: ${data.query} (${data.total_sources} sources)`);
                    if (data.total_sources !== undefined) {
                        setTotalSources(data.total_sources);
                    }
                    return;
                }

                if (data.type === 'PROGRESS' || data.type === 'SOURCE_RESULT') {
                    if (data.source) {
                        const count = data.total_found_by_source !== undefined ? data.total_found_by_source : (data.jobs ? data.jobs.length : 0);
                        const execTime = data.execution_time ? (data.execution_time * 1000).toFixed(1) : '?';
                        accumulatedSourceCountsRef.current[data.source] = count;
                        setSourceCounts({ ...accumulatedSourceCountsRef.current });

                        // 📊 Diagnostic: afficher la cause du 0 résultat
                        if (count === 0) {
                            const diag = data.diagnostic || {};
                            const errorMsg = diag.error || data.error || 'Aucun résultat';
                            const hint = diag.hint || '';

                            // Stocker le diagnostic pour affichage
                            setSourceDiagnostics(prev => ({
                                ...prev,
                                [data.source]: {
                                    error: errorMsg,
                                    hint: hint,
                                    status: data.status || 'error',
                                    execution_time: data.execution_time,
                                }
                            }));
                            setSourceErrors(prev => ({
                                ...prev,
                                [data.source]: errorMsg
                            }));

                            console.warn(`[Stream] ⚠️ ${data.source}: 0 offres (status=${data.status || 'unknown'})`);
                            if (errorMsg) console.warn(`[Stream]   Cause: ${errorMsg}`);
                            if (hint) console.warn(`[Stream]   💡 Suggestion: ${hint}`);
                        } else {
                            // Source OK - effacer le diagnostic si existant
                            setSourceDiagnostics(prev => {
                                if (prev[data.source]) {
                                    const { [data.source]: _, ...rest } = prev;
                                    return rest;
                                }
                                return prev;
                            });
                            setSourceErrors(prev => {
                                if (prev[data.source]) {
                                    const { [data.source]: _, ...rest } = prev;
                                    return rest;
                                }
                                return prev;
                            });
                        }

                        console.log(`[Stream] ${data.source}: ${count} offres reçues en ${execTime}ms (status=${data.status || 'unknown'})`);
                    }

                    if (data.sources_done !== undefined && data.total_sources !== undefined) {
                        setSourcesDone(data.sources_done);
                        setTotalSources(data.total_sources);
                    }

                    if (data.jobs && data.jobs.length > 0) {
                        const normalizedJobs = data.jobs.map((job) => {
                            const normalized = normalizeIncomingJob(job, data.source);
                            return {
                                ...normalized,
                                id: job.id || normalized.id || generateJobId(normalized),
                                source: normalized.source || data.source,
                                receivedAt: Date.now(),
                            };
                        });

                        const deduplicatedJobs = deduplicateJobs(normalizedJobs, accumulatedJobsRef.current);
                        accumulatedJobsRef.current = [...accumulatedJobsRef.current, ...deduplicatedJobs];
                        setTotalReceived(prev => prev + deduplicatedJobs.length);
                        setJobs([...accumulatedJobsRef.current]);

                        if (accumulatedJobsRef.current.length > 0 && loading) {
                            setLoading(false);
                        }

                        if (deduplicatedJobs.length > 0) {
                            pendingAiChunkRef.current = [...pendingAiChunkRef.current, ...deduplicatedJobs];
                        }

                        if (pendingAiChunkRef.current.length >= AI_CHUNK_SIZE && !aiProcessingRef.current) {
                            const chunkToProcess = pendingAiChunkRef.current.splice(0, AI_CHUNK_SIZE);
                            processAiChunk(chunkToProcess, searchParams.ranking_engine, searchParams.custom_gemini_key).catch(err =>
                                console.error('[AI] Background scoring error:', err)
                            );
                        }
                    }
                    return;
                }

                if (data.type === 'SCORES_UPDATED' && data.jobs) {
                    console.log(`[Stream] Tri IA terminé: ${data.jobs.length} offres scorées`);

                    const jobSignature = (job) =>
                        `${(job.title || job.titre || '').toLowerCase().trim()}|${(job.company || job.entreprise || '').toLowerCase().trim()}|${(job.link || job.lien || '').toLowerCase().trim()}`;

                    const scoredBySignature = new Map(
                        data.jobs.map(job => [jobSignature(job), job])
                    );

                    const merged = accumulatedJobsRef.current.map(job => {
                        const scored = scoredBySignature.get(jobSignature(job));
                        return scored ? { ...job, pertinence_ai: scored.pertinence_ai, ai_scored: true } : job;
                    });

                    merged.sort((a, b) => (b.pertinence_ai || 0) - (a.pertinence_ai || 0));
                    accumulatedJobsRef.current = merged;
                    setJobs([...merged]);
                    setProcessedCount(data.jobs.length);
                    return;
                }

                if (data.type === 'COMPLETED') {
                    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
                    setSearchTime(duration);

                    if (data.jobs && data.jobs.length > 0) {
                        const normalizedJobs = data.jobs.map((job) => {
                            const normalized = normalizeIncomingJob(job, job.source || job.source_name || '');
                            return {
                                ...normalized,
                                id: job.id || normalized.id || generateJobId(normalized),
                                source: normalized.source || job.source || job.source_name || '',
                            };
                        });
                        setJobs(normalizedJobs);
                        accumulatedJobsRef.current = normalizedJobs;
                    }

                    if (data.source_status) {
                        const counts = {};
                        const diags = {};
                        const errs = {};
                        Object.entries(data.source_status).forEach(([source, status]) => {
                            if (status && (status.count !== undefined || status.jobs_count !== undefined)) {
                                counts[source] = status.count !== undefined ? status.count : status.jobs_count;
                            }
                            // Collecter les diagnostics du COMPLETED event
                            if (status && status.diagnostic) {
                                diags[source] = {
                                    error: status.error || 'Aucun résultat',
                                    hint: status.diagnostic,
                                    status: status.status || 'error',
                                    execution_time: status.execution_time,
                                };
                                errs[source] = status.error || 'Aucun résultat';
                            } else if (status && status.count === 0) {
                                diags[source] = {
                                    error: status.error || 'Aucun résultat trouvé',
                                    hint: status.diagnostic || 'Essayez d\'élargir la recherche ou de modifier la localisation.',
                                    status: status.status || 'error',
                                    execution_time: status.execution_time,
                                };
                                errs[source] = status.error || 'Aucun résultat trouvé';
                            }
                        });
                        setSourceCounts(counts);
                        if (Object.keys(diags).length > 0) {
                            setSourceDiagnostics(diags);
                            setSourceErrors(errs);
                        }
                    }

                    if (pendingAiChunkRef.current.length > 0 && !aiProcessingRef.current) {
                        processAiChunk(pendingAiChunkRef.current, searchParams.ranking_engine, searchParams.custom_gemini_key);
                        pendingAiChunkRef.current = [];
                    }

                    setLoading(false);
                    console.log(`[Stream] Recherche terminée: ${data.jobs ? data.jobs.length : accumulatedJobsRef.current.length} offres en ${duration}s`);
                    streamCompletedRef.current = true;

                    if (onSearchComplete) {
                        onSearchComplete({
                            jobs: accumulatedJobsRef.current,
                            sourceCounts: accumulatedSourceCountsRef.current,
                            duration,
                            sourceDiagnostics: sourceDiagnostics,
                            sourceErrors: sourceErrors,
                        });
                    }
                    return;
                }

                if (data.type === 'ERROR') {
                    console.error('[Stream] Erreur:', data.message);
                    setError(data.message || 'Erreur de connexion au flux');
                    setLoading(false);
                    return;
                }
            } catch (err) {
                console.error('[Stream] Erreur de parsing JSON:', err, event.data);
            }
        };

        es.onerror = (err) => {
            if (streamCompletedRef.current) {
                console.log('[Stream] Fermeture normale après COMPLETED');
                es.close();
                return;
            }
            console.error('[Stream] Erreur SSE:', err);
            setError('Erreur de connexion au serveur');
            setLoading(false);
            es.close();
        };

        return () => {
            es.close();
        };
    }, [apiBase, processAiChunk, onSearchComplete, deduplicateJobs]);

    // Annuler la recherche
    const cancel = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
        setLoading(false);
        setAiProcessing(false);
    }, []);

    // Réinitialiser tous les résultats
    const reset = () => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }

        setJobs([]);
        setSourceCounts({});
        setLoading(false);
        setError(null);
        setSearchTime(null);
        setAiProcessing(false);
        setProcessedCount(0);
        setTotalReceived(0);
        setSourcesDone(0);
        setTotalSources(0);
        setSourceDiagnostics({});
        setSourceErrors({});

        accumulatedJobsRef.current = [];
        accumulatedSourceCountsRef.current = {};
        pendingAiChunkRef.current = [];
        aiProcessingRef.current = false;
        seenKeysRef.current = new Set();
    };

    return {
        jobs,
        sourceCounts,
        loading,
        error,
        searchTime,
        aiProcessing,
        processedCount,
        totalReceived,
        sourcesDone,
        totalSources,
        sourceDiagnostics,
        sourceErrors,
        search,
        cancel,
        reset,
    };
}
