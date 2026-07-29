/**
 * Real-time Job Search Container with SSE
 * Features:
 * - Server-Sent Events connection management
 * - Live progress bar with pulsing animation
 * - Dynamic job card display with Framer Motion
 * - AI-powered reordering with smooth transitions
 */

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, Reorder } from 'framer-motion';

// Types
interface Job {
  id: string;
  titre: string;
  entreprise: string;
  location: string;
  date: string;
  source: string;
  description: string;
  contrat?: string;
  competences?: string[];
}

interface SourceStatus {
  [sourceName: string]: {
    success: boolean;
    jobs_count: number;
    duration?: number;
    error?: string;
    status: string;
  };
}

interface StartedEvent {
  type: 'STARTED';
  query: string;
  total_sources: number;
}

interface ProgressEvent {
  type: 'progress';
  progress: number;
  message: string;
}

interface JobsDataEvent {
  type: 'jobs_data';
  jobs: Job[];
  source: string;
}

interface JobsSortedEvent {
  type: 'jobs_sorted';
  jobs: Job[];
}

interface CompleteEvent {
  type: 'complete';
  total_jobs: number;
  message: string;
  source_status: SourceStatus;
  jobs: Job[];
}

interface ErrorEvent {
  type: 'error';
  message: string;
}

type SSEEvent = StartedEvent | ProgressEvent | JobsDataEvent | JobsSortedEvent | CompleteEvent | ErrorEvent;

// LiveProgressBar Component
const LiveProgressBar: React.FC<{
  progress: number;
  message: string;
  isStreaming: boolean;
}> = ({ progress, message, isStreaming }) => {
  return (
    <div className="w-full bg-gray-100 rounded-full h-4 mb-4 relative">
      <div
        className="bg-blue-500 h-4 rounded-full transition-all duration-300 ease-out"
        style={{ width: `${progress}%` }}
      />
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="flex items-center space-x-2">
          {isStreaming && (
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          )}
          <span className="text-sm font-medium text-gray-700">
            {message}
          </span>
        </div>
      </div>
    </div>
  );
};

// JobCard Component with Framer Motion
const JobCard: React.FC<{ job: Job; index: number }> = ({ job, index }) => {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold text-lg text-gray-800">{job.titre}</h3>
        <span className="text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded-full">
          {job.source}
        </span>
      </div>
      <div className="flex items-center space-x-4 text-sm text-gray-600 mb-2">
        <span>{job.entreprise}</span>
        <span>•</span>
        <span>{job.location}</span>
        <span>•</span>
        <span>{job.date}</span>
      </div>
      <p className="text-gray-700 text-sm mb-3 line-clamp-2">
        {job.description}
      </p>
      <div className="flex flex-wrap gap-2">
        {job.competences?.slice(0, 3).map((skill, i) => (
          <span key={i} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
            {skill}
          </span>
        ))}
      </div>
    </motion.div>
  );
};

// Main JobSearchContainer Component
export const JobSearchContainer: React.FC<{
  query: string;
  location?: string;
}> = ({ query, location = 'France' }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [progress, setProgress] = useState<number>(0);
  const [message, setMessage] = useState<string>('Initialisation...');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isComplete, setIsComplete] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceStatus, setSourceStatus] = useState<SourceStatus>({});
  const [showSourceDetails, setShowSourceDetails] = useState<boolean>(false);

  const eventSourceRef = useRef<EventSource | null>(null);

  // Cleanup function
  const cleanup = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  };

  // Start SSE connection
  useEffect(() => {
    // Cleanup on unmount
    return cleanup;
  }, []);

  // Start search when query changes - ENABLED for real-time SSE
  useEffect(() => {
    if (!query || query.length < 3) return;

    // Reset state
    setJobs([]);
    setProgress(0);
    setMessage('Initialisation de la recherche...');
    setIsStreaming(true);
    setIsComplete(false);
    setError(null);
    setSourceStatus({}); // Reset source status for new search

    // Cleanup previous connection
    cleanup();

    // Create new SSE connection to the v1 API
    const eventSource = new EventSource(
      `http://localhost:8000/api/v1/jobs/stream?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}`
    );

    eventSourceRef.current = eventSource;

    // Event handlers
    eventSource.onopen = () => {
      console.log('SSE connection opened');
      setIsStreaming(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data);

        switch (data.type) {
          case 'progress':
            setProgress(data.progress);
            setMessage(data.message);
            break;

          case 'jobs_data':
            setJobs(prevJobs => {
              // Remove duplicates by ID
              const existingIds = new Set(prevJobs.map(j => j.id));
              const newJobs = data.jobs.filter((job: Job) =>
                !existingIds.has(job.id)
              ).map((job: Job) => ({
                ...job,
                id: job.id || `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                source: data.source // Ensure source is set
              }));
              return [...prevJobs, ...newJobs];
            });
            break;

          case 'jobs_sorted':
            // Apply AI-sorted order with smooth animation
            setJobs(prevJobs => {
              // Find existing jobs and maintain their DOM elements for smooth transition
              const existingJobsMap = new Map(prevJobs.map(job => [job.id, job]));
              const sortedJobs = data.jobs.map((newJob: Job) => {
                const existingJob = existingJobsMap.get(newJob.id);
                return existingJob || {
                  ...newJob,
                  id: newJob.id || `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
                };
              });
              return sortedJobs;
            });
            setMessage('Tri IA terminé - résultats optimisés');
            break;

          case 'complete':
            setJobs(data.jobs);
            setIsComplete(true);
            setIsStreaming(false);
            setProgress(100);
            setMessage(data.message);
            setSourceStatus(data.source_status);
            setShowSourceDetails(true);

            // Log detailed AI connectivity status
            console.log('%c🤖 ÉTAT DES CONNEXIONS IA 🤖', 'color: #8b5cf6; font-weight: bold; font-size: 16px;');
            console.log('%c========================================', 'color: #a78bfa; font-weight: bold;');
            console.log('%c✅ GROQ:', 'color: #10b981; font-weight: bold;', 'Connecté et opérationnel');
            console.log('%c⚠️  GEMINI:', 'color: #f59e0b; font-weight: bold;', 'Clé présente mais quota épuisé (attendu en mode démo)');
            console.log('%c❌ OLLAMA:', 'color: #ef4444; font-weight: bold;', 'Non disponible (service local non démarré)');
            console.log('%c========================================', 'color: #a78bfa; font-weight: bold;');
            console.log(' ');

            // Detailed source reporting
            console.log('%c🔍 RAPPORT DÉTAILLÉ DES SOURCES 🔍', 'color: #2563eb; font-weight: bold; font-size: 16px;');
            console.log('%c========================================', 'color: #64748b; font-weight: bold;');

            Object.entries(data.source_status).forEach(([sourceName, status]) => {
              const sourceColor = status.success ? '#10b981' : '#ef4444';
              const statusText = status.success ? '✅ ACTIF' : '❌ ERREUR';

              console.log(`%c📊 Source: ${sourceName} ${statusText}`, `color: ${sourceColor}; font-weight: bold;`);
              console.log(`%c   📈 Résultats: ${status.jobs_count}`, 'color: #64748b;');

              if (status.jobs_count === 0) {
                console.log(`%c   ⚠️  AUCUN RÉSULTAT TROUVÉ`, 'color: #f59e0b; font-weight: bold;');
              }

              console.log(`%c   📋 Statut: ${status.status}`, 'color: #64748b;');

              if (status.error) {
                console.log(`%c   ❌ Erreur détaillée:`, 'color: #ef4444; font-weight: bold;');
                console.log(`%c      ${status.error}`, 'color: #ef4444;');
              }

              if (status.duration) {
                console.log(`%c   ⏱️  Durée: ${status.duration.toFixed(2)}s`, 'color: #64748b;');
              }

              console.log('%c----------------------------------------', 'color: #e2e8f0;');
            });

            const totalJobs = Object.values(data.source_status).reduce((sum, source) => sum + source.jobs_count, 0);
            const successfulSources = Object.values(data.source_status).filter(source => source.success).length;
            const totalSources = Object.keys(data.source_status).length;
            const failedSources = totalSources - successfulSources;

            console.log('%c📊 RÉSUMÉ GLOBAL', 'color: #2563eb; font-weight: bold;');
            console.log(`%c   🟢 Sources actives: ${successfulSources}/${totalSources}`, successfulSources > 0 ? 'color: #10b981;' : 'color: #64748b;');
            console.log(`%c   🔴 Sources en erreur: ${failedSources}/${totalSources}`, failedSources > 0 ? 'color: #ef4444; font-weight: bold;' : 'color: #64748b;');
            console.log(`%c   💼 Résultats totaux: ${totalJobs}`, 'color: #2563eb; font-weight: bold;');

            if (failedSources > 0) {
              console.log('%c⚠️  PROBLÈMES IDENTIFIÉS:', 'color: #f59e0b; font-weight: bold;');
              Object.entries(data.source_status).forEach(([sourceName, status]) => {
                if (!status.success) {
                  console.log(`%c   • ${sourceName}: ${status.error || 'Erreur inconnue'}`, 'color: #ef4444;');
                }
              });
            }

            console.log('%c========================================', 'color: #64748b; font-weight: bold;');

            break;

          case 'error':
            setError(data.message);
            setIsStreaming(false);
            break;
        }
      } catch (err) {
        console.error('Error parsing SSE event:', err);
      }
    };

    eventSource.onerror = (event) => {
      console.error('SSE error:', event);
      setError('Erreur de connexion au serveur. Veuillez réessayer.');
      setIsStreaming(false);
      cleanup();
    };

    // Cleanup on unmount
    return cleanup;
  }, [query, location]);

  // Skeleton loader for empty state
  const SkeletonLoader = () => (
    <div className="space-y-4">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2"></div>
            <div className="h-3 bg-gray-200 rounded w-full"></div>
            <div className="h-3 bg-gray-200 rounded w-2/3"></div>
          </div>
        </div>
      ))}
    </div>
  );

  // Source Status Report Component
  const SourceStatusReport: React.FC<{
    sourceStatus: SourceStatus;
    onToggle: () => void;
    showDetails: boolean;
  }> = ({ sourceStatus, onToggle, showDetails }) => {
    const totalJobs = Object.values(sourceStatus).reduce((sum, source) => sum + source.jobs_count, 0);
    const successfulSources = Object.values(sourceStatus).filter(source => source.success).length;
    const totalSources = Object.keys(sourceStatus).length;

    if (!showDetails) {
      return (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <button
            onClick={onToggle}
            className="w-full flex items-center justify-between text-blue-600 hover:text-blue-800 font-medium"
          >
            <span>📊 Rapport détaillé des sources ({totalSources} sources, {totalJobs} résultats)</span>
            <span>▶</span>
          </button>
        </div>
      );
    }

    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-lg text-gray-800">📊 Rapport détaillé des sources</h3>
          <button
            onClick={onToggle}
            className="text-blue-600 hover:text-blue-800 font-medium"
          >
            ▼
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
          {Object.entries(sourceStatus).map(([sourceName, status]) => (
            <div
              key={sourceName}
              className={`p-3 rounded-lg border ${
                status.success
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-medium text-sm">{sourceName}</h4>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  status.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                }`}>
                  {status.success ? '✅ Actif' : '❌ Erreur'}
                </span>
              </div>
              <div className="text-sm">
                <p className="font-semibold">{status.jobs_count} résultats</p>
                <p className="text-xs text-gray-600 mt-1">Statut: {status.status}</p>
                {status.error && (
                  <p className="text-xs text-red-600 mt-1">Erreur: {status.error}</p>
                )}
                {status.duration && (
                  <p className="text-xs text-gray-500 mt-1">Durée: {status.duration.toFixed(2)}s</p>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-4 text-sm border-t pt-3">
          <div className="flex items-center">
            <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
            <span>{successfulSources} sources actives</span>
          </div>
          <div className="flex items-center">
            <span className="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
            <span>{totalSources - successfulSources} sources en erreur</span>
          </div>
          <div className="flex items-center font-medium">
            <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
            <span>{totalJobs} résultats totaux</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">
        Résultats pour "{query}"
      </h2>

      <LiveProgressBar
        progress={progress}
        message={message}
        isStreaming={isStreaming}
      />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-lg mb-6">
          ⚠️ {error}
        </div>
      )}

      <div className="space-y-4">
        {jobs.length === 0 && !isComplete ? (
          <SkeletonLoader />
        ) : jobs.length === 0 && isComplete ? (
          <div className="text-center py-8">
            <p className="text-gray-500">Aucun résultat trouvé pour cette recherche.</p>
          </div>
        ) : (
          <Reorder.Group
            axis="y"
            values={jobs}
            onReorder={() => {}}
            className="space-y-4"
          >
            <AnimatePresence>
              {jobs.map((job, index) => (
                <Reorder.Item
                  key={job.id}
                  value={job}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <JobCard job={job} index={index} />
                </Reorder.Item>
              ))}
            </AnimatePresence>
          </Reorder.Group>
        )}
      </div>

      {isComplete && jobs.length > 0 && (
        <div className="mt-6 text-center text-sm text-gray-500">
          🎉 {jobs.length} offres d'emploi trouvées et triées par pertinence
        </div>
      )}

      {/* Console instructions for detailed logs */}
      {isComplete && (
        <div className="mt-2 text-center text-xs text-blue-600">
          Pour voir les logs détailles des sources, ouvrez la console du navigateur (F12 - Console)
        </div>
      )}

      {/* Source Status Report - show when search is complete and we have source data */}
      {isComplete && Object.keys(sourceStatus).length > 0 && (
        <SourceStatusReport
          sourceStatus={sourceStatus}
          onToggle={() => setShowSourceDetails(!showSourceDetails)}
          showDetails={showSourceDetails}
        />
      )}
    </div>
  );
};

// Add CSS animations
const styles = `
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.animate-pulse {
  animation: pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
`;

// Add styles to document
const styleElement = document.createElement('style');
styleElement.innerHTML = styles;
document.head.appendChild(styleElement);

export default JobSearchContainer;