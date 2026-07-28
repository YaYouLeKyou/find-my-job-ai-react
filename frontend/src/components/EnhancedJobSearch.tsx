/**
 * Enhanced Job Search Component with UX/UI Improvements
 * Features:
 * - Enhanced search bar with autocomplete
 * - Advanced filters with visual badges
 * - Improved job cards with better hierarchy
 * - Mobile-responsive design
 * - Accessibility improvements
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
  salaire?: number;
  logo?: string;
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

// Enhanced Search Bar with Autocomplete
const EnhancedSearchBar: React.FC<{
  query: string;
  onSearch: (query: string) => void;
}> = ({ query, onSearch }) => {
  const [inputValue, setInputValue] = useState(query);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // Simulate suggestions based on input
  useEffect(() => {
    if (inputValue.length > 2) {
      const mockSuggestions = [
        `${inputValue} Paris`,
        `${inputValue} Remote`,
        `${inputValue} CDI`,
        `${inputValue} Freelance`,
        `${inputValue} Senior`,
        `${inputValue} Junior`
      ];
      setSuggestions(mockSuggestions);
    } else {
      setSuggestions([]);
    }
  }, [inputValue]);

  const handleSearch = () => {
    if (inputValue.trim()) {
      onSearch(inputValue.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="relative mb-6">
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Métier, compétence ou entreprise..."
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            aria-label="Rechercher des offres d'emploi"
          />
          {suggestions.length > 0 && (
            <ul className="absolute z-10 w-full bg-white border border-gray-200 rounded-b-lg shadow-lg mt-1 max-h-60 overflow-auto">
              {suggestions.map((suggestion, index) => (
                <li
                  key={index}
                  className="px-4 py-2 hover:bg-gray-50 cursor-pointer"
                  onClick={() => {
                    setInputValue(suggestion);
                    setSuggestions([]);
                    onSearch(suggestion);
                  }}
                >
                  {suggestion}
                </li>
              ))}
            </ul>
          )}
        </div>
        <button
          onClick={handleSearch}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200"
        >
          🔍 Rechercher
        </button>
      </div>
    </div>
  );
};

// Advanced Filters Component
const AdvancedFilters: React.FC<{
  onFilterChange: (filters: any) => void;
}> = ({ onFilterChange }) => {
  const [filters, setFilters] = useState({
    remote: false,
    salaryRange: [0, 100000],
    contractType: 'all',
    experience: 'all'
  });

  const handleFilterChange = (newFilters: any) => {
    const updatedFilters = { ...filters, ...newFilters };
    setFilters(updatedFilters);
    onFilterChange(updatedFilters);
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 mb-6">
      <h3 className="font-semibold text-lg mb-4">Filtres de recherche</h3>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Type de contrat</label>
          <div className="flex flex-wrap gap-2">
            {['Tous', 'CDI', 'CDD', 'Freelance', 'Stage', 'Alternance'].map((type) => (
              <button
                key={type}
                onClick={() => handleFilterChange({
                  contractType: type.toLowerCase()
                })}
                className={`px-3 py-1 rounded-full text-sm transition-colors ${
                  filters.contractType === type.toLowerCase()
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Salaire annuel (€)</label>
          <input
            type="range"
            min="0"
            max="100000"
            value={filters.salaryRange[1]}
            onChange={(e) => handleFilterChange({
              salaryRange: [0, Number(e.target.value)]
            })}
            className="w-full"
          />
          <div className="flex justify-between text-sm text-gray-600 mt-1">
            <span>0</span>
            <span>{filters.salaryRange[1].toLocaleString()}€+</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="remote"
            checked={filters.remote}
            onChange={(e) => handleFilterChange({ remote: e.target.checked })}
            className="rounded text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="remote" className="text-sm text-gray-700">
            Télétravail uniquement
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Expérience</label>
          <select
            value={filters.experience}
            onChange={(e) => handleFilterChange({ experience: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">Toutes</option>
            <option value="junior">Junior (0-2 ans)</option>
            <option value="mid">Intermédiaire (2-5 ans)</option>
            <option value="senior">Senior (5+ ans)</option>
          </select>
        </div>
      </div>
    </div>
  );
};

// Enhanced Job Card with Better UX
const EnhancedJobCard: React.FC<{ job: Job; index: number }> = ({ job, index }) => {
  const [isSaved, setIsSaved] = useState(false);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      whileHover={{ y: -2 }}
      className="bg-white p-5 rounded-xl shadow-sm border border-gray-100"
    >
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center font-semibold text-lg">
            {job.entreprise.charAt(0)}
          </div>
          <div>
            <h3 className="font-semibold text-lg text-gray-800">{job.titre}</h3>
            <p className="text-gray-600">{job.entreprise}</p>
          </div>
        </div>
        <button
          onClick={() => setIsSaved(!isSaved)}
          className="text-gray-400 hover:text-red-500 transition-colors"
          aria-label={isSaved ? "Retirer des favoris" : "Ajouter aux favoris"}
        >
          {isSaved ? '❤️' : '♡'}
        </button>
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
          {job.location}
        </span>
        <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
          {job.contrat || 'CDI'}
        </span>
        {job.salaire && (
          <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-xs">
            {job.salaire.toLocaleString()}€/an
          </span>
        )}
      </div>

      <p className="text-gray-700 mb-4 line-clamp-3">
        {job.description}
      </p>

      <div className="flex justify-between items-center">
        <div className="flex flex-wrap gap-2">
          {job.competences?.slice(0, 3).map((skill, i) => (
            <span key={i} className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs">
              {skill}
            </span>
          ))}
        </div>
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
          Postuler
        </button>
      </div>
    </motion.div>
  );
};

// Enhanced Progress Bar
const EnhancedProgressBar: React.FC<{
  progress: number;
  message: string;
  isStreaming: boolean;
}> = ({ progress, message, isStreaming }) => {
  return (
    <div className="w-full bg-gray-100 rounded-full h-4 mb-6 relative">
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

// Main Enhanced Job Search Component
export const EnhancedJobSearch: React.FC<{
  query: string;
  location?: string;
}> = ({ query, location = 'France' }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [progress, setProgress] = useState<number>(0);
  const [message, setMessage] = useState<string>('Initialisation...');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isComplete, setIsComplete] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<any>({});
  const [searchQuery, setSearchQuery] = useState(query);

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
    return cleanup;
  }, []);

  // Start search when query changes
  useEffect(() => {
    if (!searchQuery || searchQuery.length < 3) return;

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
      `http://localhost:8000/api/v1/jobs/stream?query=${encodeURIComponent(searchQuery)}&location=${encodeURIComponent(location)}`
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

    return cleanup;
  }, [searchQuery, location]);

  // Skeleton loader for empty state
  const SkeletonLoader = () => (
    <div className="space-y-4">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
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
    <div className="max-w-6xl mx-auto p-4">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">
        Recherche d'offres d'emploi
      </h1>

      {/* Enhanced Search Bar */}
      <EnhancedSearchBar
        query={searchQuery}
        onSearch={setSearchQuery}
      />

      {/* Advanced Filters */}
      <AdvancedFilters onFilterChange={setFilters} />

      {/* Progress Bar */}
      <EnhancedProgressBar
        progress={progress}
        message={message}
        isStreaming={isStreaming}
      />

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-lg mb-6">
          ⚠️ {error}
        </div>
      )}

      {/* Job Results */}
      <div className="space-y-4">
        {jobs.length === 0 && !isComplete ? (
          <SkeletonLoader />
        ) : jobs.length === 0 && isComplete ? (
          <div className="text-center py-12">
            <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              🔍
            </div>
            <h3 className="text-xl font-semibold mb-2">Aucun résultat trouvé</h3>
            <p className="text-gray-600">Essayez d'élargir vos critères de recherche</p>
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
                  <EnhancedJobCard job={job} index={index} />
                </Reorder.Item>
              ))}
            </AnimatePresence>
          </Reorder.Group>
        )}
      </div>

      {/* Completion Message */}
      {isComplete && jobs.length > 0 && (
        <div className="mt-8 text-center text-sm text-gray-500">
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

export default EnhancedJobSearch;