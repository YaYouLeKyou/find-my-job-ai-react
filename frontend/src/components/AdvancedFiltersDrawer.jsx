import React, { useState, useCallback, useMemo } from 'react';
import { X, Plus, Minus, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { LANGS, STRINGS } from '../utils/translations';

export default function AdvancedFiltersDrawer({
  activeAgent,
  isOpen,
  onClose,
  onApplyFilters,
  currentFilters = {},
  cvData = null,
  jobData = null,
  lang = 'Français'
}) {
  const S = STRINGS[LANGS[lang]?.code || 'fr'];
  // State for all possible filter types
  const [minMatchScore, setMinMatchScore] = useState(currentFilters.minMatchScore || 0);
  const [companyTypes, setCompanyTypes] = useState(currentFilters.companyTypes || []);
  const [workModes, setWorkModes] = useState(currentFilters.workModes || []);
  const [minSalary, setMinSalary] = useState(currentFilters.minSalary || 0);
  const [includeAISalary, setIncludeAISalary] = useState(currentFilters.includeAISalary || true);
  const [offerFreshness, setOfferFreshness] = useState(currentFilters.offerFreshness || 'all');
  const [contractTypes, setContractTypes] = useState(currentFilters.contractTypes || []);
  const [employerTypes, setEmployerTypes] = useState(currentFilters.employerTypes || []);
  const [remoteRhythm, setRemoteRhythm] = useState(currentFilters.remoteRhythm || '');
  const [benefits, setBenefits] = useState(currentFilters.benefits || []);
  const [companySize, setCompanySize] = useState(currentFilters.companySize || '');
  const [intermediary, setIntermediary] = useState(currentFilters.intermediary || '');
  const [missionDuration, setMissionDuration] = useState(currentFilters.missionDuration || '');
  const [minTJM, setMinTJM] = useState(currentFilters.minTJM || 0);
  const [startNotice, setStartNotice] = useState(currentFilters.startNotice || '');
  const [candidateAvailability, setCandidateAvailability] = useState(currentFilters.candidateAvailability || '');
  const [candidateType, setCandidateType] = useState(currentFilters.candidateType || '');
  const [maxSalaryExpectation, setMaxSalaryExpectation] = useState(currentFilters.maxSalaryExpectation || 0);
  const [seniorityLevel, setSeniorityLevel] = useState(currentFilters.seniorityLevel || '');
  const [softSkills, setSoftSkills] = useState(currentFilters.softSkills || []);
  const [techStackMustHave, setTechStackMustHave] = useState(currentFilters.techStackMustHave || []);
  const [techStackExclude, setTechStackExclude] = useState(currentFilters.techStackExclude || []);
  const [newTechStackItem, setNewTechStackItem] = useState('');
  const [newExcludeTechItem, setNewExcludeTechItem] = useState('');
  const [excludedSources, setExcludedSources] = useState(currentFilters.excludedSources || []);

  // Sources config for each agent
  const agentSources = {
    job: ['LinkedIn', 'France Travail', 'Google Jobs', 'Adzuna', 'Enhanced', 'JobSpy'],
    freelance: ['Malt', 'Upwork', 'Freelancer', 'Toptal', 'Codeur.com'],
    recruiter: ['LinkedIn', 'Indeed', 'France Travail', 'Apec', 'Monster']
  };

  const currentSources = useMemo(() => agentSources[activeAgent] || agentSources.job, [activeAgent]);

  // Expanded sections state
  const [expandedSections, setExpandedSections] = useState({
    basic: true,
    agentSpecific: true,
    techStack: false,
    sources: true
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Calculate active filter count
  const activeFilterCount = useMemo(() => [
    minMatchScore > 0 ? 1 : 0,
    companyTypes.length > 0 ? 1 : 0,
    workModes.length > 0 ? 1 : 0,
    minSalary > 0 ? 1 : 0,
    offerFreshness !== 'all' ? 1 : 0,
    contractTypes.length > 0 ? 1 : 0,
    employerTypes.length > 0 ? 1 : 0,
    remoteRhythm ? 1 : 0,
    benefits.length > 0 ? 1 : 0,
    companySize ? 1 : 0,
    intermediary ? 1 : 0,
    missionDuration ? 1 : 0,
    minTJM > 0 ? 1 : 0,
    startNotice ? 1 : 0,
    candidateAvailability ? 1 : 0,
    candidateType ? 1 : 0,
    maxSalaryExpectation > 0 ? 1 : 0,
    seniorityLevel ? 1 : 0,
    softSkills.length > 0 ? 1 : 0,
    techStackMustHave.length > 0 ? 1 : 0,
    techStackExclude.length > 0 ? 1 : 0,
    excludedSources.length > 0 ? 1 : 0
  ].reduce((sum, val) => sum + val, 0), [
    minMatchScore, companyTypes, workModes, minSalary, offerFreshness,
    contractTypes, employerTypes, remoteRhythm, benefits, companySize,
    intermediary, missionDuration, minTJM, startNotice, candidateAvailability,
    candidateType, maxSalaryExpectation, seniorityLevel, softSkills,
    techStackMustHave, techStackExclude, excludedSources
  ]);

  // Extract tech stack from CV data if available
  const suggestedTechStack = useMemo(() => {
    if (!cvData) return [];

    const techStack = [];
    if (cvData.competences_techniques) {
      techStack.push(...cvData.competences_techniques.split(',').map(s => s.trim()));
    }
    if (cvData.langages) {
      techStack.push(...cvData.langages.split(',').map(s => s.trim()));
    }
    if (cvData.outils) {
      techStack.push(...cvData.outils.split(',').map(s => s.trim()));
    }

    return [...new Set(techStack.filter(s => s))].slice(0, 10);
  }, [cvData]);

  const handleApplyFilters = useCallback(() => {
    onApplyFilters({
      minMatchScore,
      companyTypes,
      workModes,
      minSalary,
      includeAISalary,
      offerFreshness,
      // Agent-specific filters
      ...(activeAgent === 'job' && {
        contractTypes,
        employerTypes,
        remoteRhythm,
        benefits,
        companySize
      }),
      ...(activeAgent === 'freelance' && {
        intermediary,
        missionDuration,
        minTJM,
        startNotice
      }),
      ...(activeAgent === 'recruiter' && {
        candidateAvailability,
        candidateType,
        maxSalaryExpectation,
        seniorityLevel,
        softSkills
      }),
      // Source exclusion filters
      excludedSources,
      // Dynamic tech stack filters
      techStackMustHave,
      techStackExclude
    });
  }, [
    activeAgent, minMatchScore, companyTypes, workModes, minSalary, includeAISalary, offerFreshness,
    activeAgent === 'job' && { contractTypes, employerTypes, remoteRhythm, benefits, companySize },
    activeAgent === 'freelance' && { intermediary, missionDuration, minTJM, startNotice },
    activeAgent === 'recruiter' && { candidateAvailability, candidateType, maxSalaryExpectation, seniorityLevel, softSkills },
    techStackMustHave, techStackExclude, excludedSources, onApplyFilters
  ]);

  const handleReset = useCallback(() => {
    onApplyFilters({
      minMatchScore: 0,
      companyTypes: [],
      workModes: [],
      minSalary: 0,
      includeAISalary: true,
      offerFreshness: 'all',
      contractTypes: [],
      employerTypes: [],
      remoteRhythm: '',
      benefits: [],
      companySize: '',
      intermediary: '',
      missionDuration: '',
      minTJM: 0,
      startNotice: '',
      candidateAvailability: '',
      candidateType: '',
      maxSalaryExpectation: 0,
      seniorityLevel: '',
      softSkills: [],
      techStackMustHave: [],
      techStackExclude: [],
      excludedSources: []
    });
    setMinMatchScore(0);
    setCompanyTypes([]);
    setWorkModes([]);
    setMinSalary(0);
    setIncludeAISalary(true);
    setOfferFreshness('all');
    setContractTypes([]);
    setEmployerTypes([]);
    setRemoteRhythm('');
    setBenefits([]);
    setCompanySize('');
    setIntermediary('');
    setMissionDuration('');
    setMinTJM(0);
    setStartNotice('');
    setCandidateAvailability('');
    setCandidateType('');
    setMaxSalaryExpectation(0);
    setSeniorityLevel('');
    setSoftSkills([]);
    setTechStackMustHave([]);
    setTechStackExclude([]);
    setExcludedSources([]);
  }, [onApplyFilters]);

  // Toggle handlers
  const toggleCompanyType = (type) => {
    setCompanyTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const toggleWorkMode = (mode) => {
    setWorkModes(prev =>
      prev.includes(mode)
        ? prev.filter(m => m !== mode)
        : [...prev, mode]
    );
  };

  const toggleContractType = (type) => {
    setContractTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const toggleEmployerType = (type) => {
    setEmployerTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const toggleBenefit = (benefit) => {
    setBenefits(prev =>
      prev.includes(benefit)
        ? prev.filter(b => b !== benefit)
        : [...prev, benefit]
    );
  };

  const toggleSoftSkill = (skill) => {
    setSoftSkills(prev =>
      prev.includes(skill)
        ? prev.filter(s => s !== skill)
        : [...prev, skill]
    );
  };

  const toggleSource = (source) => {
    setExcludedSources(prev =>
      prev.includes(source)
        ? prev.filter(s => s !== source)
        : [...prev, source]
    );
  };

  const addTechStackItem = () => {
    if (newTechStackItem.trim() && !techStackMustHave.includes(newTechStackItem.trim())) {
      setTechStackMustHave([...techStackMustHave, newTechStackItem.trim()]);
      setNewTechStackItem('');
    }
  };

  const addExcludeTechItem = () => {
    if (newExcludeTechItem.trim() && !techStackExclude.includes(newExcludeTechItem.trim())) {
      setTechStackExclude([...techStackExclude, newExcludeTechItem.trim()]);
      setNewExcludeTechItem('');
    }
  };

  const removeTechStackItem = (item) => {
    setTechStackMustHave(techStackMustHave.filter(i => i !== item));
  };

  const removeExcludeTechItem = (item) => {
    setTechStackExclude(techStackExclude.filter(i => i !== item));
  };

  if (!isOpen) return null;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '12px',
      alignItems: 'flex-end',
      position: 'relative'
    }}>
      {/* Basic Filters Section */}
      <div style={{ width: '100%' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer',
            marginBottom: '8px'
          }}
          onClick={() => toggleSection('basic')}
        >
          <h4 style={{
            fontSize: '0.85rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--color-text-secondary)'
          }}>
            {S.advanced_filters}
          </h4>
          {expandedSections.basic ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>

        {expandedSections.basic && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
            {/* Match Score */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Score de match minimum
                </label>
                <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--color-primary-500)', minWidth: '32px', textAlign: 'right' }}>
                  {minMatchScore}%
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={1}
                value={minMatchScore}
                onChange={(e) => setMinMatchScore(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--color-primary-500)', cursor: 'pointer', height: '38px', boxSizing: 'border-box' }}
              />
            </div>

            {/* Company Type */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Type d'entreprise
              </label>
              <select
                value={companyTypes[0] || ''}
                onChange={(e) => toggleCompanyType(e.target.value)}
                className="select-control"
                style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
              >
                <option value="">Tous les types</option>
                <option value="Client Final">Client Final</option>
                <option value="ESN / Cabinet">ESN / Cabinet</option>
              </select>
            </div>

            {/* Work Mode */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Mode de travail
              </label>
              <select
                value={workModes[0] || ''}
                onChange={(e) => toggleWorkMode(e.target.value)}
                className="select-control"
                style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
              >
                <option value="">Tous les modes</option>
                <option value="Full Remote (100%)">Full Remote (100%)</option>
                <option value="Hybride (3-4j)">Hybride (3-4j)</option>
                <option value="Hybride (1-2j)">Hybride (1-2j)</option>
                <option value="Présentiel (0j)">Présentiel (0j)</option>
              </select>
            </div>

            {/* Salary */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Salaire minimum annuel
              </label>
              <input
                type="number"
                placeholder="Salaire minimum"
                value={minSalary || ''}
                onChange={(e) => setMinSalary(parseInt(e.target.value) || 0)}
                min={0}
                step={1000}
                className="input-control"
                style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
              />
            </div>

            {/* AI Salary Checkbox */}
            <label
              className="checkbox-container"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 12px',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: 500,
                borderRadius: 'var(--radius-sm)',
                border: '1px solid',
                borderColor: includeAISalary ? 'var(--color-primary-500)' : 'var(--border-color)',
                background: includeAISalary ? 'var(--color-primary-500)15' : 'var(--color-surface)',
                color: includeAISalary ? 'var(--color-primary-500)' : 'var(--text-primary)',
                transition: 'all 0.2s',
                minHeight: '38px',
                boxSizing: 'border-box',
                whiteSpace: 'normal',
                minWidth: '160px',
                flex: '1 1 160px',
                lineHeight: '1.3',
              }}
            >
              <input
                type="checkbox"
                checked={includeAISalary}
                onChange={(e) => setIncludeAISalary(e.target.checked)}
                style={{ accentColor: 'var(--color-primary-500)' }}
              />
              Inclure estimations IA
            </label>

            {/* Offer Freshness */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Fraîcheur de l'offre
              </label>
              <select
                value={offerFreshness}
                onChange={(e) => setOfferFreshness(e.target.value)}
                className="select-control"
                style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
              >
                <option value="all">Toutes</option>
                <option value="24h">Moins de 24h</option>
                <option value="3d">Moins de 3 jours</option>
                <option value="7d">Moins de 7 jours</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Sources Section */}
      <div style={{ width: '100%' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer',
            marginBottom: '8px'
          }}
          onClick={() => toggleSection('sources')}
        >
          <h4 style={{
            fontSize: '0.85rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--color-text-secondary)'
          }}>
            {S.filters}
          </h4>
          {expandedSections.sources ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>

        {expandedSections.sources && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center' }}>
            {currentSources.map((source) => {
              const isExcluded = excludedSources.includes(source);
              return (
                <button
                  key={source}
                  type="button"
                  onClick={() => toggleSource(source)}
                  style={{
                    padding: '8px 16px',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    borderRadius: '8px',
                    border: '2px solid',
                    borderColor: isExcluded ? '#ef4444' : '#10b981',
                    background: isExcluded ? '#ef4444' : '#10b981',
                    color: 'white',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    boxSizing: 'border-box'
                  }}
                >
                  {source}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Agent-Specific Filters Section */}
      <div style={{ width: '100%' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer',
            marginBottom: '8px'
          }}
          onClick={() => toggleSection('agentSpecific')}
        >
          <h4 style={{
            fontSize: '0.85rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--color-text-secondary)'
          }}>
            {activeAgent === 'job' ? 'FILTRES CANDIDAT' :
             activeAgent === 'freelance' ? 'FILTRES FREELANCE' : 'FILTRES RECRUTEUR'}
          </h4>
          {expandedSections.agentSpecific ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>

        {expandedSections.agentSpecific && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
            {/* Job Agent Specific Filters */}
            {activeAgent === 'job' && (
              <>
                {/* Contract Types */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Type de contrat
                  </label>
                  <select
                    value={contractTypes[0] || ''}
                    onChange={(e) => toggleContractType(e.target.value)}
                    className="select-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  >
                    <option value="">Tous les contrats</option>
                    <option value="CDI">CDI</option>
                    <option value="CDD">CDD</option>
                    <option value="Télétravail">Télétravail</option>
                    <option value="Alternance">Alternance</option>
                    <option value="Stage">Stage</option>
                    <option value="Intérim">Intérim</option>
                  </select>
                </div>

                {/* Employer Types */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Type d'employeur
                  </label>
                  <select
                    value={employerTypes[0] || ''}
                    onChange={(e) => toggleEmployerType(e.target.value)}
                    className="select-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  >
                    <option value="">Tous les employeurs</option>
                    <option value="Client Final uniquement">Client Final uniquement</option>
                    <option value="Masquer les ESN / Cabinets">Masquer les ESN / Cabinets</option>
                  </select>
                </div>

                {/* Remote Rhythm */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Rythme télétravail
                  </label>
                  <select
                    value={remoteRhythm}
                    onChange={(e) => setRemoteRhythm(e.target.value)}
                    className="select-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  >
                    <option value="">Tous les rythmes</option>
                    <option value="Full Remote (100%)">Full Remote (100%)</option>
                    <option value="Hybride (3-4j)">Hybride (3-4j/sem)</option>
                    <option value="Hybride (1-2j)">Hybride (1-2j/sem)</option>
                    <option value="Présentiel (0j)">Présentiel (0j)</option>
                  </select>
                </div>

                {/* Benefits */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Avantages entreprise
                  </label>
                  <select
                    value={benefits[0] || ''}
                    onChange={(e) => toggleBenefit(e.target.value)}
                    className="select-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  >
                    <option value="">Tous les avantages</option>
                    <option value="Télétravail pris en charge">Télétravail pris en charge</option>
                    <option value="RTT">RTT</option>
                    <option value="Mutuelle">Mutuelle</option>
                    <option value="PEE/Intéressement">PEE/Intéressement</option>
                  </select>
                </div>

                {/* Company Size */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Taille de l'entreprise
                  </label>
                  <select
                    value={companySize}
                    onChange={(e) => setCompanySize(e.target.value)}
                    className="select-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  >
                    <option value="">Toutes les tailles</option>
                    <option value="Startup / PME">Startup / PME</option>
                    <option value="ETI">ETI</option>
                    <option value="Grand Groupe">Grand Groupe</option>
                  </select>
                </div>
              </>
            )}

            {/* Freelance Agent Specific Filters */}
            {activeAgent === 'freelance' && (
              <>
                {/* Intermediary */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Intermédiaire
                  </label>
                  <select
                    value={intermediary}
                    onChange={(e) => setIntermediary(e.target.value)}
                    className="select-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  >
                    <option value="">Tous les intermédiaires</option>
                    <option value="Direct Client uniquement">Direct Client uniquement</option>
                    <option value="Via ESN / Agence">Via ESN / Agence</option>
                  </select>
                </div>

                {/* Mission Duration */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Durée exacte souhaitée
                  </label>
                  <select
                    value={missionDuration}
                    onChange={(e) => setMissionDuration(e.target.value)}
                    className="select-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  >
                    <option value="">Toutes les durées</option>
                    <option value="< 1 mois">{'< 1 mois'}</option>
                    <option value="1 à 3 mois">1 à 3 mois</option>
                    <option value="3 à 6 mois">3 à 6 mois</option>
                    <option value="> 6 mois">{'> 6 mois'}</option>
                    <option value="Longue durée">Longue durée</option>
                  </select>
                </div>

                {/* TJM */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    TJM Minimum (€/j)
                  </label>
                  <input
                    type="number"
                    placeholder="TJM minimum"
                    value={minTJM || ''}
                    onChange={(e) => setMinTJM(parseInt(e.target.value) || 0)}
                    min={0}
                    step={10}
                    className="input-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  />
                </div>

                {/* Start Notice */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Préavis / Démarrage
                  </label>
                  <select
                    value={startNotice}
                    onChange={(e) => setStartNotice(e.target.value)}
                    className="select-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  >
                    <option value="">Tous les préavis</option>
                    <option value="Immédiat">Immédiat</option>
                    <option value="Sous 15 jours">Sous 15 jours</option>
                    <option value="Sous 1 mois">Sous 1 mois</option>
                  </select>
                </div>
              </>
            )}

            {/* Recruiter Agent Specific Filters */}
            {activeAgent === 'recruiter' && (
              <>
                {/* Candidate Availability */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Disponibilité du candidat
                  </label>
                  <select
                    value={candidateAvailability}
                    onChange={(e) => setCandidateAvailability(e.target.value)}
                    className="select-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  >
                    <option value="">Toutes les disponibilités</option>
                    <option value="Immédiate">Immédiate</option>
                    <option value="En préavis (1 à 3 mois)">En préavis (1 à 3 mois)</option>
                    <option value="En poste">En poste</option>
                  </select>
                </div>

                {/* Candidate Type */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Type de profil
                  </label>
                  <select
                    value={candidateType}
                    onChange={(e) => setCandidateType(e.target.value)}
                    className="select-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  >
                    <option value="">Tous les types</option>
                    <option value="Cherche un Salarié (CDI/CDD)">Cherche un Salarié (CDI/CDD)</option>
                    <option value="Cherche un Freelance">Cherche un Freelance</option>
                  </select>
                </div>

                {/* Max Salary Expectation */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Prétentions salariales max (€/an)
                  </label>
                  <input
                    type="number"
                    placeholder="Prétentions max"
                    value={maxSalaryExpectation || ''}
                    onChange={(e) => setMaxSalaryExpectation(parseInt(e.target.value) || 0)}
                    min={0}
                    step={1000}
                    className="input-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  />
                </div>

                {/* Seniority Level */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Niveau de séniorité
                  </label>
                  <select
                    value={seniorityLevel}
                    onChange={(e) => setSeniorityLevel(e.target.value)}
                    className="select-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  >
                    <option value="">Tous les niveaux</option>
                    <option value="Junior (0-2 ans)">Junior (0-2 ans)</option>
                    <option value="Confirmé (3-5 ans)">Confirmé (3-5 ans)</option>
                    <option value="Senior (5-8 ans)">Senior (5-8 ans)</option>
                    <option value="Lead/Expert (8+ ans)">Lead/Expert (8+ ans)</option>
                  </select>
                </div>

                {/* Soft Skills */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Soft Skills
                  </label>
                  <select
                    value={softSkills[0] || ''}
                    onChange={(e) => toggleSoftSkill(e.target.value)}
                    className="select-control"
                    style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
                  >
                    <option value="">Tous les soft skills</option>
                    <option value="Autonomie">Autonomie</option>
                    <option value="Management">Management</option>
                    <option value="Communication">Communication</option>
                    <option value="Bilingue Anglais">Bilingue Anglais</option>
                  </select>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Tech Stack Filters Section (Dynamic based on CV analysis) */}
      {suggestedTechStack.length > 0 && (
        <div style={{ width: '100%' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              cursor: 'pointer',
              marginBottom: '8px'
            }}
            onClick={() => toggleSection('techStack')}
          >
            <h4 style={{
              fontSize: '0.85rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--color-text-secondary)'
            }}>
              STACK TECHNIQUE (DÉTECTÉE PAR IA)
            </h4>
            {expandedSections.techStack ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>

          {expandedSections.techStack && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                {/* Must Have Tech Stack */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '240px', flex: '1 1 240px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      🟢 ET (MUST HAVE)
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', minHeight: '60px', border: '1px dashed var(--border-color)', padding: '8px', borderRadius: 'var(--radius-sm)' }}>
                    {techStackMustHave.map((tech, index) => (
                      <div key={index} style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        background: 'var(--color-primary-500)',
                        color: 'white',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 500
                      }}>
                        {tech}
                        <button
                          onClick={() => removeTechStackItem(tech)}
                          style={{
                            background: 'rgba(255,255,255,0.2)',
                            border: 'none',
                            color: 'white',
                            cursor: 'pointer',
                            padding: '0 4px',
                            borderRadius: '2px'
                          }}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                    <input
                      type="text"
                      placeholder="Ajouter une technologie"
                      value={newTechStackItem}
                      onChange={(e) => setNewTechStackItem(e.target.value)}
                      style={{ flex: 1, padding: '6px 10px', fontSize: '0.875rem' }}
                    />
                    <button
                      onClick={addTechStackItem}
                      style={{
                        padding: '6px 10px',
                        background: 'var(--color-primary-500)',
                        color: 'white',
                        border: 'none',
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer'
                      }}
                    >
                      <Plus size={16} />
                    </button>
                  </div>
                </div>

                {/* Exclude Tech Stack */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '240px', flex: '1 1 240px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      🔴 NON (EXCLUSION)
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', minHeight: '60px', border: '1px dashed var(--border-color)', padding: '8px', borderRadius: 'var(--radius-sm)' }}>
                    {techStackExclude.map((tech, index) => (
                      <div key={index} style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        background: 'var(--color-danger-500)',
                        color: 'white',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 500
                      }}>
                        {tech}
                        <button
                          onClick={() => removeExcludeTechItem(tech)}
                          style={{
                            background: 'rgba(255,255,255,0.2)',
                            border: 'none',
                            color: 'white',
                            cursor: 'pointer',
                            padding: '0 4px',
                            borderRadius: '2px'
                          }}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                    <input
                      type="text"
                      placeholder="Ajouter une exclusion"
                      value={newExcludeTechItem}
                      onChange={(e) => setNewExcludeTechItem(e.target.value)}
                      style={{ flex: 1, padding: '6px 10px', fontSize: '0.875rem' }}
                    />
                    <button
                      onClick={addExcludeTechItem}
                      style={{
                        padding: '6px 10px',
                        background: 'var(--color-danger-500)',
                        color: 'white',
                        border: 'none',
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer'
                      }}
                    >
                      <Plus size={16} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Suggested tech stack from CV */}
              {suggestedTechStack.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    SUGGESTIONS IA (CLIQUEZ POUR AJOUTER)
                  </label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {suggestedTechStack.map((tech, index) => (
                      <button
                        key={index}
                        onClick={() => {
                          if (!techStackMustHave.includes(tech)) {
                            setTechStackMustHave([...techStackMustHave, tech]);
                          }
                        }}
                        style={{
                          padding: '4px 10px',
                          fontSize: '0.75rem',
                          fontWeight: 500,
                          borderRadius: '9999px',
                          border: '1px solid var(--border-color)',
                          background: techStackMustHave.includes(tech) ? 'var(--color-primary-500)20' : 'transparent',
                          color: techStackMustHave.includes(tech) ? 'var(--color-primary-500)' : 'var(--text-secondary)',
                          cursor: 'pointer',
                          transition: 'all 0.2s'
                        }}
                      >
                        {techStackMustHave.includes(tech) ? <Check size={12} /> : <Plus size={12} />}
                        {tech}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '16px' }}>
        <button
            onClick={handleReset}
            className="btn btn-secondary"
            style={{ fontSize: '0.85rem' }}
        >
            {S.reset_filters}
        </button>
        <button
            onClick={handleApplyFilters}
            className="btn btn-primary"
            style={{ fontSize: '0.85rem' }}
        >
            {S.apply_filters} ({activeFilterCount})
        </button>
      </div>
    </div>
  );
}
