import React, { useState, useEffect } from 'react';
import SEO from './SEO';
import HeaderButtons from './HeaderButtons';
import AdComponent from './AdComponent';
import { LANGS, STRINGS } from '../utils/translations';
import { ArrowLeft, Search, Loader2, Briefcase, User, FileText, Star, Mail, Phone, MapPin, Trash2, Download, Filter, X, ChevronDown, ChevronUp, Eye, Heart, AlertCircle, CheckCircle2 } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "";

const WORKER_SOURCES = ['LinkedIn', 'Indeed', 'France Travail', 'Apec', 'Monster'];
const CONTRACT_TYPES = ['CDI', 'CDD', 'Stage', 'Alternance', 'Intérim', 'Temps partiel'];
const EXPERIENCE_LEVELS = ['Débutant', 'Junior (1-3 ans)', 'Confirmé (3-5 ans)', 'Senior (5-10 ans)', 'Expert (10+ ans)'];
const SKILLS_SUGGESTIONS = ['JavaScript', 'Python', 'React', 'Node.js', 'Java', 'SQL', 'AWS', 'Docker', 'Kubernetes', 'Git', 'Agile', 'Marketing', 'Vente', 'Communication'];

export default function WorkerApp({ onBackToHub, lang }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [location, setLocation] = useState("France");
  const [contract, setContract] = useState("CDI");
  const [experience, setExperience] = useState("");
  const [remote, setRemote] = useState(false);
  const [selectedSources, setSelectedSources] = useState([...WORKER_SOURCES]);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchTime, setSearchTime] = useState(null);
  const [toast, setToast] = useState(null);
  
  // New features
  const [savedCandidates, setSavedCandidates] = useState([]);
  const [searchHistory, setSearchHistory] = useState([]);
  const [salaryMin, setSalaryMin] = useState("");
  const [salaryMax, setSalaryMax] = useState("");
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  // Load saved data from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('savedCandidates');
    if (saved) setSavedCandidates(JSON.parse(saved));
    
    const history = localStorage.getItem('workerSearchHistory');
    if (history) setSearchHistory(JSON.parse(history));
  }, []);

  // Save to localStorage when data changes
  useEffect(() => {
    if (savedCandidates.length > 0) {
      localStorage.setItem('savedCandidates', JSON.stringify(savedCandidates));
    }
  }, [savedCandidates]);

  useEffect(() => {
    if (searchHistory.length > 0) {
      localStorage.setItem('workerSearchHistory', JSON.stringify(searchHistory));
    }
  }, [searchHistory]);

  const handleSearchCandidates = async () => {
    if (!searchQuery) return;
    const startTime = Date.now();
    setLoading(true);
    setError("");
    setCandidates([]);
    setCurrentPage(1);

    try {
      const response = await fetch(`${API_BASE}/api/search-jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: `recrute ${searchQuery} ${contract}`,
          location: remote ? '' : location,
          num_ads: 50,
          contract: contract,
          remote: remote,
          global_search: remote,
          selected_sources: selectedSources,
          sort_option: "Pertinence (IA)",
          ranking_engine: "Groq / Llama 3.3",
          lang_code: LANGS[lang].code,
          lang_label: LANGS[lang].label,
          cv_data: null
        })
      });

      if (!response.ok) throw new Error("Erreur de communication avec le serveur.");
      const data = await response.json();
      let results = data.results || [];
      
      // Apply filters
      if (salaryMin || salaryMax) {
        results = results.filter(candidate => {
          const salary = candidate.salary || candidate.tjm || 0;
          if (salaryMin && salary < parseInt(salaryMin)) return false;
          if (salaryMax && salary > parseInt(salaryMax)) return false;
          return true;
        });
      }
      
      if (selectedSkills.length > 0) {
        results = results.filter(candidate => {
          const desc = (candidate.desc || candidate.title || '').toLowerCase();
          return selectedSkills.some(skill => desc.includes(skill.toLowerCase()));
        });
      }
      
      setCandidates(results);

      const endTime = Date.now();
      setSearchTime(((endTime - startTime) / 1000).toFixed(2));
      showToast(`✅ ${results.length} profils trouvés`, 'success');
      
      // Add to history
      const newHistory = [{ query: searchQuery, time: new Date().toISOString(), count: results.length }, ...searchHistory.filter(h => h.query !== searchQuery)].slice(0, 10);
      setSearchHistory(newHistory);
    } catch (err) {
      console.error(err);
      setError(err.message);
      showToast(`❌ Erreur: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const toggleSaveCandidate = (candidate) => {
    const isSaved = savedCandidates.some(c => c.id === candidate.id);
    let newSaved;
    if (isSaved) {
      newSaved = savedCandidates.filter(c => c.id !== candidate.id);
      showToast('Candidat retiré des favoris', 'info');
    } else {
      newSaved = [...savedCandidates, candidate];
      showToast('⭐ Candidat sauvegardé', 'success');
    }
    setSavedCandidates(newSaved);
  };

  const handleClearCache = () => {
    if (window.confirm('Effacer toutes les données en cache ?\n\nCela supprimera :\n- Candidats sauvegardés\n- Historique des recherches\n- Préférences utilisateur')) {
      localStorage.removeItem('savedCandidates');
      localStorage.removeItem('workerSearchHistory');
      localStorage.removeItem('darkMode');
      setSavedCandidates([]);
      setSearchHistory([]);
      showToast('🗑️ Cache vidé avec succès', 'success');
    }
  };

  const exportToCSV = () => {
    if (candidates.length === 0) { showToast('Aucun candidat à exporter', 'error'); return; }
    const headers = ['Titre', 'Entreprise', 'Localisation', 'Source', 'Salaire', 'Lien'];
    const csvContent = [
      headers.join(','),
      ...candidates.map(c => [
        `"${c.title || ''}"`, `"${c.company || ''}"`, `"${c.location || ''}"`,
        `"${c.source || ''}"`, `"${c.salary || c.tjm || 'Non spécifié'}"`, `"${c.link || ''}"`
      ].join(','))
    ].join('\n');

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `candidats_${searchQuery.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    showToast('📊 CSV exporté avec succès', 'success');
  };

  const toggleSkill = (skill) => {
    setSelectedSkills(prev => 
      prev.includes(skill) ? prev.filter(s => s !== skill) : [...prev, skill]
    );
  };

  const openCandidateDetail = (candidate) => {
    setSelectedCandidate(candidate);
    setShowDetailModal(true);
  };

  return (
    <div className="app-container" style={{ background: 'linear-gradient(135deg, rgba(255,111,0,0.03), rgba(255,143,0,0.03))' }}>
      <SEO
        title="Find My Worker AI - Recruit the Best Talent"
        description="Find the perfect candidates for your job openings with AI-powered recruitment. Post jobs and discover qualified talent."
        keywords="recruitment, hiring, employer, find workers, AI recruitment, FindMyJobAI"
      />

      {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}

      <main className="main-content">
        <button onClick={onBackToHub} className="btn btn-secondary" style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', padding: '8px 16px' }}>
          <ArrowLeft size={16} />
          Job Bridge
        </button>

        <HeaderButtons onToggleDarkMode={() => {
          const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
          if (isDark) { document.documentElement.removeAttribute('data-theme'); localStorage.setItem('darkMode', 'false'); }
          else { document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('darkMode', 'true'); }
        }} />

        <header className="header">
          <h1 style={{ color: 'var(--text-primary)', wordWrap: 'break-word', overflowWrap: 'break-word', WebkitTextStroke: '0.5px rgba(0, 0, 0, 0.15)', textShadow: '0 0 1px rgba(0, 0, 0, 0.1)' }}>
            👷 Find my worker AI
          </h1>
          <p style={{ color: 'var(--text-primary)', fontWeight: '500', opacity: 0.95 }}>
            Trouvez les meilleurs talents pour vos postes à pourvoir
          </p>
        </header>

        {/* Search Filters */}
        <div className="card" style={{ borderColor: 'rgba(255,111,0,0.2)' }}>
          <div className="card-title">
            <Briefcase size={20} style={{ color: '#ff6f00' }} />
            <span>Critères de recherche</span>
            <button 
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              style={{ marginLeft: 'auto', background: 'none', border: 'none', color: '#ff6f00', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.85rem' }}
            >
              <Filter size={16} /> {showAdvancedFilters ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>
          <div className="card-content">
            <div className="filters-row-1" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
              <div className="form-group">
                <label>📍 Localisation</label>
                <input type="text" className="input-control" value={location} onChange={e => setLocation(e.target.value)} placeholder="France, Paris..." />
              </div>
              <div className="form-group">
                <label>📋 Type de contrat</label>
                <select className="select-control" value={contract} onChange={e => setContract(e.target.value)}>
                  {CONTRACT_TYPES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>📊 Niveau d'expérience</label>
                <select className="select-control" value={experience} onChange={e => setExperience(e.target.value)}>
                  <option value="">Tous niveaux</option>
                  {EXPERIENCE_LEVELS.map(e => <option key={e} value={e}>{e}</option>)}
                </select>
              </div>
            </div>

            <div className="form-group" style={{ marginTop: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input type="checkbox" checked={remote} onChange={e => setRemote(e.target.checked)} style={{ accentColor: '#ff6f00' }} />
                🏠 Profils en télétravail uniquement
              </label>
            </div>

            <div className="form-group">
              <label>📡 Sources de recherche</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '4px' }}>
                {WORKER_SOURCES.map(src => (
                  <label key={src} style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.87rem' }}>
                    <input type="checkbox" checked={selectedSources.includes(src)}
                      onChange={(e) => setSelectedSources(prev => e.target.checked ? [...prev, src] : prev.filter(s => s !== src))}
                      style={{ accentColor: '#ff6f00' }} />
                    {src}
                  </label>
                ))}
              </div>
            </div>

            {/* Advanced Filters */}
            {showAdvancedFilters && (
              <div style={{ marginTop: '16px', padding: '16px', background: 'rgba(255,111,0,0.05)', borderRadius: '8px', border: '1px solid rgba(255,111,0,0.1)' }}>
                <div className="filters-row-1" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: '12px' }}>
                  <div className="form-group">
                    <label>💰 Salaire min (€/mois)</label>
                    <input type="number" className="input-control" placeholder="2000" value={salaryMin} onChange={e => setSalaryMin(e.target.value)} min="0" step="100" />
                  </div>
                  <div className="form-group">
                    <label>💰 Salaire max (€/mois)</label>
                    <input type="number" className="input-control" placeholder="8000" value={salaryMax} onChange={e => setSalaryMax(e.target.value)} min="0" step="100" />
                  </div>
                </div>
                
                <div className="form-group">
                  <label>🎯 Compétences requises</label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '4px' }}>
                    {SKILLS_SUGGESTIONS.map(skill => (
                      <button
                        key={skill}
                        onClick={() => toggleSkill(skill)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: '20px',
                          border: '1px solid ' + (selectedSkills.includes(skill) ? '#ff6f00' : 'var(--border-color)'),
                          background: selectedSkills.includes(skill) ? 'rgba(255,111,0,0.1)' : 'transparent',
                          color: selectedSkills.includes(skill) ? '#ff6f00' : 'var(--text-secondary)',
                          cursor: 'pointer',
                          fontSize: '0.85rem',
                          transition: 'all 0.2s'
                        }}
                      >
                        {skill}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Search Box */}
        <div className="card" style={{ borderColor: 'rgba(255,111,0,0.2)' }}>
          <div className="card-title">
            <Search size={20} style={{ color: '#ff6f00' }} />
            <span>Rechercher des candidats</span>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
              {savedCandidates.length > 0 && (
                <button onClick={handleClearCache} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} title="Effacer le cache">
                  <Trash2 size={14} /> Cache
                </button>
              )}
              {candidates.length > 0 && (
                <button onClick={exportToCSV} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
                  <Download size={14} /> CSV
                </button>
              )}
            </div>
          </div>
          <div className="card-content">
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Décrivez le poste à pourvoir ou le profil recherché.
            </span>
            <div className="search-box-container">
              <div className="search-input-wrapper">
                <input type="text" className="input-control"
                  placeholder="Ex: Développeur React, Commercial, Comptable..."
                  value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleSearchCandidates(); }} />
                <Search size={18} className="search-icon-inside" />
              </div>
              <button className="btn" style={{ background: 'linear-gradient(135deg, #ff6f00, #ff8f00)', color: 'white', border: 'none' }}
                onClick={handleSearchCandidates} disabled={loading}>
                {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : 'Rechercher'}
              </button>
            </div>
          </div>
        </div>

        {/* Ad - During Search */}
        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', padding: '40px 0' }}>
            <Loader2 size={48} style={{ animation: 'spin 1.5s linear infinite', color: '#ff6f00' }} />
            <span>Recherche de profils en cours...</span>
            <AdComponent style={{ marginTop: '24px' }} />
          </div>
        )}

        {error && <div className="alert alert-danger"><span>{error}</span></div>}

        {/* Ad - Results Section */}
        {candidates.length > 0 && <AdComponent style={{ marginTop: '24px' }} />}

        {/* Results with pagination */}
        {candidates.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h2 style={{ fontSize: '1.4rem', fontWeight: '800', borderBottom: '2px solid #ff6f00', paddingBottom: '8px' }}>
              👥 Profils trouvés {searchTime && <span style={{ fontSize: '0.9rem', fontWeight: '400', color: 'var(--text-secondary)' }}>({searchTime}s)</span>}
            </h2>
            <div className="job-list">
              {candidates.slice(0, currentPage * itemsPerPage).map((candidate, idx) => (
                <div key={candidate.id || idx} className="card" style={{ borderColor: 'rgba(255,111,0,0.15)', cursor: 'pointer', minHeight: '160px' }} onClick={() => openCandidateDetail(candidate)}>
                  <div className="card-content">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', flexWrap: 'wrap' }}>
                      <div style={{ flex: '1 1 auto' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', minHeight: '28px' }}>
                          <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                            {candidate.title || 'Profil'}
                          </h3>
                          {savedCandidates.some(c => c.id === candidate.id) && (
                            <Heart size={16} style={{ color: '#ff6f00', fill: '#ff6f00' }} />
                          )}
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', fontSize: '0.85rem', color: 'var(--text-secondary)', minHeight: '20px' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Briefcase size={14} /> {candidate.company || 'Non spécifié'}
                          </span>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <MapPin size={14} /> {candidate.location || 'Non spécifié'}
                          </span>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <FileText size={14} /> {candidate.source || 'Source inconnue'}
                          </span>
                          {candidate.match_score && (
                            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#2e7d32', fontWeight: '600' }}>
                              <CheckCircle2 size={14} /> {Math.round(candidate.match_score * 100)}% match
                            </span>
                          )}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                        <button
                          onClick={(e) => { e.stopPropagation(); toggleSaveCandidate(candidate); }}
                          className="btn btn-secondary"
                          style={{ padding: '8px', fontSize: '0.8rem' }}
                          title={savedCandidates.some(c => c.id === candidate.id) ? 'Retirer des favoris' : 'Sauvegarder'}
                        >
                          <Heart size={16} color={savedCandidates.some(c => c.id === candidate.id) ? '#ff6f00' : 'currentColor'} />
                        </button>
                        {candidate.link && candidate.link !== '#' && (
                          <a href={candidate.link} target="_blank" rel="noopener noreferrer"
                            className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '8px 16px', textDecoration: 'none' }}
                            onClick={(e) => e.stopPropagation()}>
                            Voir →
                          </a>
                        )}
                      </div>
                    </div>
                    {candidate.desc && (
                      <p style={{ marginTop: '12px', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5', minHeight: '60px' }}>
                        {candidate.desc.substring(0, 300)}{candidate.desc.length > 300 ? '...' : ''}
                      </p>
                    )}
                    <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', minHeight: '20px' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Eye size={12} /> Cliquez pour voir les détails
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Pagination */}
            {candidates.length > itemsPerPage && (
              <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginTop: '24px' }}>
                <button 
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="btn btn-secondary"
                  style={{ padding: '10px 20px' }}
                >
                  Précédent
                </button>
                <span style={{ display: 'flex', alignItems: 'center', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  Page {currentPage} / {Math.ceil(candidates.length / itemsPerPage)}
                </span>
                <button 
                  onClick={() => setCurrentPage(prev => Math.min(Math.ceil(candidates.length / itemsPerPage), prev + 1))}
                  disabled={currentPage >= Math.ceil(candidates.length / itemsPerPage)}
                  className="btn btn-secondary"
                  style={{ padding: '10px 20px' }}
                >
                  Suivant
                </button>
              </div>
            )}
          </div>
        )}

        {!loading && candidates.length === 0 && !error && (
          <div className="card" style={{ borderColor: 'rgba(255,111,0,0.1)', textAlign: 'center', padding: '40px' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
              🔍 Lancez une recherche pour découvrir des profils correspondant à votre poste
            </p>
            {searchHistory.length > 0 && (
              <div style={{ marginTop: '24px', textAlign: 'left' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>📋 Recherches récentes</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {searchHistory.slice(0, 5).map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => { setSearchQuery(item.query); handleSearchCandidates(item.query); }}
                      style={{
                        padding: '10px 14px',
                        background: 'var(--glass-bg)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer',
                        textAlign: 'left',
                        fontSize: '0.85rem',
                        color: 'var(--text-primary)',
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => { e.target.style.background = 'var(--primary-color)'; e.target.style.color = 'white'; }}
                      onMouseLeave={(e) => { e.target.style.background = 'var(--glass-bg)'; e.target.style.color = 'var(--text-primary)'; }}
                    >
                      <div style={{ fontWeight: '600' }}>{item.query}</div>
                      <div style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '2px' }}>
                        {new Date(item.time).toLocaleDateString('fr-FR')} - {item.count} résultats
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Candidate Detail Modal */}
        {showDetailModal && selectedCandidate && (
          <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, padding: '20px'
          }} onClick={() => setShowDetailModal(false)}>
            <div style={{
              background: 'var(--bg-primary)', borderRadius: '12px', maxWidth: '700px', width: '100%',
              maxHeight: '90vh', overflowY: 'auto', padding: '32px', position: 'relative'
            }} onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => setShowDetailModal(false)}
                style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: 'var(--text-secondary)' }}
              >
                <X size={24} />
              </button>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
                <div>
                  <h2 style={{ margin: '0 0 8px 0', fontSize: '1.5rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                    {selectedCandidate.title || 'Profil'}
                  </h2>
                  <p style={{ margin: 0, fontSize: '1rem', color: 'var(--text-secondary)' }}>
                    {selectedCandidate.company || 'Entreprise non spécifiée'}
                  </p>
                </div>
                <button
                  onClick={() => toggleSaveCandidate(selectedCandidate)}
                  className="btn btn-secondary"
                  style={{ padding: '10px' }}
                >
                  <Heart size={20} color={savedCandidates.some(c => c.id === selectedCandidate.id) ? '#ff6f00' : 'currentColor'} />
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <MapPin size={16} /> {selectedCandidate.location || 'Non spécifié'}
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <FileText size={16} /> {selectedCandidate.source || 'Source inconnue'}
                  </span>
                  {selectedCandidate.match_score && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#2e7d32', fontWeight: '600' }}>
                      <CheckCircle2 size={16} /> {Math.round(selectedCandidate.match_score * 100)}% de correspondance
                    </span>
                  )}
                </div>
              </div>

              {selectedCandidate.desc && (
                <div style={{ marginBottom: '24px' }}>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '12px', color: 'var(--text-primary)' }}>Description</h3>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
                    {selectedCandidate.desc}
                  </p>
                </div>
              )}

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                {selectedCandidate.link && selectedCandidate.link !== '#' && (
                  <a href={selectedCandidate.link} target="_blank" rel="noopener noreferrer" className="btn btn-primary" style={{ textDecoration: 'none', flex: '1 1 auto' }}>
                    Voir le profil complet →
                  </a>
                )}
                <button onClick={() => setShowDetailModal(false)} className="btn btn-secondary" style={{ flex: '1 1 auto' }}>
                  Fermer
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="app-footer" style={{ background: 'rgba(255,111,0,0.05)', border: '1px solid rgba(255,111,0,0.15)' }}>
          <div className="app-footer-inner">
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              🤖 <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Gemini</span>
              <span style={{ opacity: 0.4 }}>·</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Groq</span>
              <span style={{ opacity: 0.4 }}>·</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Llama</span>
              <span style={{ opacity: 0.4 }}>·</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Ollama</span>
            </span>
            <span style={{ opacity: 0.3, fontWeight: '900' }}>|</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>by Yanès Hadiouche</span>
          </div>
        </div>
      </main>
    </div>
  );
}