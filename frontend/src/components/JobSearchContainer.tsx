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

interface ProgressEvent {
  type: 'progress';
  stage: number;
  progress: number;
  message: string;
}

interface JobsDataEvent {
  type: 'jobs_data';
  source: string;
  jobs: Job[];
  timestamp: string;
}

interface JobsSortedEvent {
  type: 'jobs_sorted';
  order: string[];
  timestamp: string;
}

interface CompleteEvent {
  type: 'complete';
  total_jobs: number;
  timestamp: string;
}

interface ErrorEvent {
  type: 'error';
  message: string;
}

type SSEEvent = ProgressEvent | JobsDataEvent | JobsSortedEvent | CompleteEvent | ErrorEvent;

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

  // Start search when query changes
  useEffect(() => {
    if (!query || query.length < 3) return;

    // Reset state
    setJobs([]);
    setProgress(0);
    setMessage('Initialisation de la recherche...');
    setIsStreaming(true);
    setIsComplete(false);
    setError(null);

    // Cleanup previous connection
    cleanup();

    // Create new SSE connection
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
              const newJobs = data.jobs.filter(job =>
                !existingIds.has(job.id)
              ).map(job => ({
                ...job,
                id: job.id || `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
              }));
              return [...prevJobs, ...newJobs];
            });
            break;

          case 'jobs_sorted':
            setJobs(prevJobs => {
              const idToIndex = new Map(data.order.map((id, index) => [id, index]));
              return [...prevJobs].sort((a, b) => {
                const aIndex = idToIndex.get(a.id) ?? 999;
                const bIndex = idToIndex.get(b.id) ?? 999;
                return aIndex - bIndex;
              });
            });
            break;

          case 'complete':
            setIsComplete(true);
            setIsStreaming(false);
            setMessage(`Recherche terminée ! ${data.total_jobs} offres trouvées.`);
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