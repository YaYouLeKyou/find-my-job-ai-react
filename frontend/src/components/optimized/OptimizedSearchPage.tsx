/**
 * OptimizedSearchPage - Enhanced job search page with UX improvements
 * Implements all recommendations from UX/UI audit
 */
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Badge } from './Badge';
import { StatCard } from './StatCard';
import { OneClickApplyButton } from './OneClickApplyButton';

// Types
interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  date: string;
  contract: string;
  description: string;
  salary?: number;
  logo?: string;
  skills?: string[];
}

interface SearchFilters {
  remote: boolean;
  salaryRange: [number, number];
  contractType: string;
  experience: string;
}

export const OptimizedSearchPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filters, setFilters] = useState<SearchFilters>({
    remote: false,
    salaryRange: [30000, 120000],
    contractType: 'all',
    experience: 'all'
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Mock data for demonstration
  useEffect(() => {
    setIsLoading(true);
    const timer = setTimeout(() => {
      const mockJobs: Job[] = [
        {
          id: '1',
          title: 'Développeur Full-Stack Senior',
          company: 'TechInnov',
          location: 'Paris (Remote possible)',
          date: 'Il y a 2 jours',
          contract: 'CDI',
          description: 'Recherche développeur Full-Stack pour projet innovant dans le domaine de la santé. Expérience requise en React, Node.js et AWS.',
          salary: 65000,
          logo: 'https://via.placeholder.com/50',
          skills: ['React', 'Node.js', 'AWS', 'TypeScript']
        },
        {
          id: '2',
          title: 'Ingénieur DevOps',
          company: 'CloudSolutions',
          location: 'Lyon',
          date: 'Il y a 1 jour',
          contract: 'CDI',
          description: 'Expert DevOps pour optimiser notre infrastructure cloud. Kubernetes, Docker et CI/CD requis.',
          salary: 70000,
          logo: 'https://via.placeholder.com/50',
          skills: ['Kubernetes', 'Docker', 'CI/CD', 'AWS']
        },
        {
          id: '3',
          title: 'Data Scientist',
          company: 'DataInsight',
          location: 'Remote',
          date: 'Il y a 3 jours',
          contract: 'CDI',
          description: 'Analyse de données et machine learning pour projets santé. Python et TensorFlow requis.',
          salary: 55000,
          logo: 'https://via.placeholder.com/50',
          skills: ['Python', 'Machine Learning', 'SQL', 'TensorFlow']
        }
      ];
      setJobs(mockJobs);
      setIsLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // Implement search logic here
    console.log('Searching for:', searchQuery, 'with filters:', filters);
  };

  const handleFilterChange = (newFilters: Partial<SearchFilters>) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
  };

  return (
    <div className="max-w-7xl mx-auto p-4">
      {/* Hero Section with CTA */}
      <section className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-8 mb-8 text-white">
        <div className="max-w-4xl">
          <h1 className="text-4xl font-bold mb-4">Trouvez l'emploi de vos rêves</h1>
          <p className="text-xl mb-6">+10,000 offres vérifiées mises à jour quotidiennement</p>

          {/* Enhanced Search Bar */}
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Métier, compétence ou entreprise..."
                className="w-full px-5 py-3 rounded-lg text-gray-900 text-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            </div>
            <button
              type="submit"
              className="bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors flex items-center justify-center"
            >
              🔍 Rechercher
            </button>
          </form>
        </div>
      </section>

      {/* Advanced Filters */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Affiner votre recherche</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Contract Type */}
          <div>
            <h3 className="font-semibold text-gray-700 mb-3">Type de contrat</h3>
            <div className="flex flex-wrap gap-2">
              {['Tous', 'CDI', 'CDD', 'Freelance', 'Stage'].map((type) => (
                <button
                  key={type}
                  onClick={() => handleFilterChange({ contractType: type.toLowerCase() })}
                  className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                    filters.contractType === type.toLowerCase()
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          {/* Salary Range */}
          <div>
            <h3 className="font-semibold text-gray-700 mb-3">Salaire annuel</h3>
            <input
              type="range"
              min="0"
              max="150000"
              value={filters.salaryRange[1]}
              onChange={(e) => handleFilterChange({ salaryRange: [0, Number(e.target.value)] })}
              className="w-full"
            />
            <div className="flex justify-between text-sm text-gray-600 mt-2">
              <span>0€</span>
              <span>{filters.salaryRange[1].toLocaleString()}€+</span>
            </div>
          </div>

          {/* Remote Filter */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="remote"
              checked={filters.remote}
              onChange={(e) => handleFilterChange({ remote: e.target.checked })}
              className="w-5 h-5 rounded text-blue-600 focus:ring-blue-500 mr-3"
            />
            <label htmlFor="remote" className="font-semibold text-gray-700">
              Télétravail uniquement 🏠
            </label>
          </div>

          {/* Experience Level */}
          <div>
            <h3 className="font-semibold text-gray-700 mb-3">Expérience</h3>
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

      {/* Stats Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard
          title="Offres actives"
          value={jobs.length}
          trend="+12%"
          icon="📄"
          color="blue"
        />
        <StatCard
          title="Nouvelles aujourd'hui"
          value="42"
          trend="+8"
          icon="✨"
          color="green"
        />
        <StatCard
          title="Moyenne salaire"
          value="58K€"
          trend="+5%"
          icon="💰"
          color="purple"
        />
      </div>

      {/* Search Results */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 mb-6" role="alert">
          <p className="font-medium">Erreur de recherche</p>
          <p>{error}</p>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 animate-pulse">
              <div className="h-6 bg-gray-200 rounded mb-4"></div>
              <div className="h-4 bg-gray-200 rounded mb-2"></div>
              <div className="h-4 bg-gray-200 rounded mb-4"></div>
              <div className="h-8 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-xl">
          <div className="mx-auto w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-4 text-2xl">
            🔍
          </div>
          <h3 className="text-xl font-semibold mb-2">Aucun résultat trouvé</h3>
          <p className="text-gray-600">Essayez d'élargir vos critères de recherche</p>
        </div>
      ) : (
        <div className="space-y-6">
          {jobs.map((job) => (
            <motion.div
              key={job.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center space-x-4">
                  <div className="w-14 h-14 bg-gray-100 rounded-lg flex items-center justify-center font-bold text-xl">
                    {job.company.charAt(0)}
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-gray-900">{job.title}</h3>
                    <p className="text-gray-600">{job.company}</p>
                  </div>
                </div>
                <OneClickApplyButton
                  jobId={job.id}
                  cvId="user-cv-123"
                  className="px-6 py-2"
                />
              </div>

              <div className="flex flex-wrap gap-2 mb-4">
                <Badge type="location">{job.location}</Badge>
                <Badge type="contract">{job.contract}</Badge>
                {job.salary && <Badge type="salary">{job.salary.toLocaleString()}€/an</Badge>}
                <Badge type="experience">
                  {job.skills?.length ? `${job.skills.length}+ compétences` : 'Expérience requise'}
                </Badge>
              </div>

              <p className="text-gray-700 mb-4 line-clamp-3">
                {job.description}
              </p>

              <div className="flex justify-between items-center">
                <div className="flex flex-wrap gap-2">
                  {job.skills?.slice(0, 3).map((skill, i) => (
                    <Badge key={i} type="skill">{skill}</Badge>
                  ))}
                </div>
                <span className="text-sm text-gray-500">{job.date}</span>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {jobs.length > 0 && (
        <div className="flex justify-center items-center space-x-4 mt-8">
          <button
            disabled
            className="px-4 py-2 bg-gray-100 text-gray-400 rounded-lg cursor-not-allowed"
          >
            ← Précédent
          </button>
          <span className="font-medium">Page 1 sur 5</span>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Suivant →
          </button>
        </div>
      )}
    </div>
  );
};

export default OptimizedSearchPage;