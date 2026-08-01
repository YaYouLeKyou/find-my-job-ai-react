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

                        // Process complete SSE events delimited by double newline
                        let sepIndex;
                        while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
                            const rawEvent = buffer.slice(0, sepIndex);
                            buffer = buffer.slice(sepIndex + 2);

                            // Aggregate data: lines (can be multiple) into a single string
                            const dataLines = rawEvent.split('\n').filter(l => l.startsWith('data:'));
                            if (dataLines.length === 0) continue;
                            const dataStr = dataLines.map(l => l.slice(6)).join('\n');
                            try {
                                const data = JSON.parse(dataStr);

                                // STARTED
                                if (data.type === 'STARTED') {
                                    console.log(`[Stream] Recherche démarrée: ${data.query} (${data.total_sources} sources)`);
                                    if (data.total_sources !== undefined) {
                                        setTotalSources(data.total_sources);
                                    }
                                }

                                // PROGRESS / SOURCE_RESULT - Affichage IMMÉDIAT
                                if (data.type === 'PROGRESS' || data.type === 'SOURCE_RESULT') {
                                    // Mettre à jour les compteurs de sources (même si 0 résultat)
                                    if (data.source) {
                                        const count = data.jobs ? data.jobs.length : 0;
                                        const execTime = data.execution_time ? (data.execution_time * 1000).toFixed(1) : '?';
                                        accumulatedSourceCountsRef.current[data.source] = count;
                                        setSourceCounts({ ...accumulatedSourceCountsRef.current });
                                        console.log(`[Stream] ${data.source}: ${count} offres reçues en ${execTime}ms (status=${data.status || 'unknown'})`);
                                    }

                                    // Mettre à jour le suivi des sources
                                    if (data['sources_done'] !== undefined && data['total_sources'] !== undefined) {
                                        setSourcesDone(data['sources_done']);
                                        setTotalSources(data['total_sources']);
                                    }

                                    // Ajouter les jobs à la liste accumulée
                                    if (data.jobs && data.jobs.length > 0) {
                                        // Ajouter un ID stable basé sur title+company+link
                                        const jobsWithId = data.jobs.map((job, idx) => ({
                                            ...job,
                                            id: job.id || generateJobId(job),
                                            source: data.source,
                                            receivedAt: Date.now(),
                                            // Préserver ai_scored si le backend l'a déjà envoyé
                                            ai_scored: job.ai_scored || false,
                                        }));

                                        // Dédupliquer en temps réel
                                        const deduplicatedJobs = deduplicateJobs(jobsWithId, accumulatedJobsRef.current);

                                        // Accumuler
                                        accumulatedJobsRef.current = [...accumulatedJobsRef.current, ...deduplicatedJobs];
                                        setTotalReceived(prev => prev + deduplicatedJobs.length);

                                        // FORCE MISE À JOUR IMMÉDIATE DE L'UI
                                        setJobs([...accumulatedJobsRef.current]);

                                        // Cacher le loader dès la première réception réelle
                                        if (accumulatedJobsRef.current.length > 0 && loading) {
                                            setLoading(false);
                                        }

                                        // Ajouter au chunk IA en attente (seulement si on a des jobs)
                                        if (deduplicatedJobs.length > 0) {
                                            pendingAiChunkRef.current = [...pendingAiChunkRef.current, ...deduplicatedJobs];
                                        }

                                        // Lancer le tri IA si on a assez de jobs (en arrière-plan, sans await)
                                        if (pendingAiChunkRef.current.length >= AI_CHUNK_SIZE && !aiProcessingRef.current) {
                                            const chunkToProcess = pendingAiChunkRef.current.splice(0, AI_CHUNK_SIZE);
                                            processAiChunk(chunkToProcess, searchParams.ranking_engine, searchParams.custom_gemini_key).catch(err =>
                                                console.error('[AI] Background scoring error:', err)
                                            );
                                        }
                                    }
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

                                    // Re-sort by AI score descending
                                    merged.sort((a, b) => (b.pertinence_ai || 0) - (a.pertinence_ai || 0));

                                    accumulatedJobsRef.current = merged;
                                    setJobs([...merged]);
                                    setProcessedCount(data.jobs.length);
                                }

                                // COMPLETED - Fin de la recherche
                                if (data.type === 'COMPLETED') {
                                    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
                                    setSearchTime(duration);

                                    if (data.jobs && data.jobs.length > 0) {
                                        setJobs(data.jobs);
                                        accumulatedJobsRef.current = data.jobs;
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
                                    console.log(`[Stream] Recherche terminée: ${data.jobs ? data.jobs.length : accumulatedJobsRef.current.length} offres en ${duration}s`);

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
                                console.error('[Stream] Erreur de parsing JSON:', err, dataStr);
                            }
                        }

                        // Continue reading
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
        sourcesDone,
        totalSources,
        search,
        cancel,
    };
}