import React from 'react';
import { LANGS, STRINGS } from '../utils/translations';
import { Sliders, MapPin, Globe } from 'lucide-react';

export default function JobFilters({
  lang,
  numAds,
  setNumAds,
  sortOption,
  setSortOption,
  contract,
  setContract,
  remote,
  setRemote,
  globalSearch,
  setGlobalSearch,
  location,
  setLocation,
  selectedSources,
  setSelectedSources,
  onRefresh
}) {
  const S = STRINGS[LANGS[lang].code];

  const allAvailableSources = [
    "LinkedIn", "Indeed", "France Travail", "Google Jobs", 
    "Adzuna", "Jooble", "Glassdoor", "ZipRecruiter", 
    "Simplyhired", "Careerbuilder", "Monster",
    "Welcome to the Jungle", "HelloWork", "APEC", "JobTeaser",
    "Reed", "StepStone", "Xing", "InfoJobs", "Dice",
    "Naukri", "Bayt", "Seek",
    "RégionsJob", "ChooseYourBoss", "LesJeudis", "Talent.io",
    "Remotive", "RemoteOK", "Jobijoba", "Emploi Public",
    "Freelance.com", "Malt"
  ];

  const handleSourceChange = (source) => {
    if (selectedSources.includes(source)) {
      setSelectedSources(selectedSources.filter(s => s !== source));
    } else {
      setSelectedSources([...selectedSources, source]);
    }
  };

  return (
    <div className="card" style={{ padding: '24px', background: 'var(--surface-color)', border: '1px solid var(--border-color)' }}>
      <div className="card-title" style={{ borderBottom: '1px solid var(--border-light)', marginBottom: '12px' }}>
        <Sliders size={20} style={{ color: 'var(--primary-color)' }} />
        <span>Filtres de Recherche</span>
      </div>

      <div className="card-content" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        {/* Row 1: Limit & Sort */}
        <div className="filters-row-1" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
          
          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label>{S.num_ads}</label>
              <span style={{ fontWeight: 800, color: 'var(--primary-color)', fontSize: '1rem' }}>{numAds}</span>
            </div>
            <input
              type="range"
              min="5"
              max="100"
              step="5"
              value={numAds}
              onChange={(e) => setNumAds(parseInt(e.target.value))}
              style={{
                accentColor: 'var(--primary-color)',
                cursor: 'pointer',
                height: '8px',
                borderRadius: 'var(--radius-full)',
                marginTop: '10px'
              }}
            />
          </div>

          <div className="form-group">
            <label>{S.sort_by}</label>
            <select
              className="select-control"
              value={sortOption}
              onChange={(e) => setSortOption(e.target.value)}
              style={{ height: '48px' }}
            >
              <option value={S.sort_relevant}>{S.sort_relevant}</option>
              <option value={S.sort_recent}>{S.sort_recent}</option>
              <option value={S.sort_closest}>{S.sort_closest}</option>
            </select>
          </div>

          <div className="form-group">
            <label>{S.contract}</label>
            <select
              className="select-control"
              value={contract}
              onChange={(e) => setContract(e.target.value)}
              style={{ height: '48px' }}
            >
              <option value="CDI">CDI</option>
              <option value="CDD">CDD</option>
              <option value="Alternance">Alternance</option>
              <option value="Stage">Stage</option>
              <option value="Interim">Interim</option>
            </select>
          </div>

        </div>

        {/* Row 2: Location & Remote */}
        <div className="filters-row-2" style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <label className="checkbox-container" style={{ padding: '8px 12px', background: 'var(--surface-secondary)', borderRadius: 'var(--radius-sm)' }}>
              <input
                type="checkbox"
                checked={remote}
                onChange={(e) => {
                  setRemote(e.target.checked);
                  if (!e.target.checked) setGlobalSearch(false);
                }}
              />
              <div className="checkbox-custom"></div>
              <span style={{ fontWeight: 600 }}>{S.remote}</span>
            </label>

            {remote && (
              <label className="checkbox-container" style={{ padding: '8px 12px', background: 'var(--surface-secondary)', borderRadius: 'var(--radius-sm)', animation: 'slideUp 0.3s ease' }}>
                <input
                  type="checkbox"
                  checked={globalSearch}
                  onChange={(e) => setGlobalSearch(e.target.checked)}
                />
                <div className="checkbox-custom"></div>
                <span style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Globe size={14} /> {S.global_search}
                </span>
              </label>
            )}
          </div>

          <div className="form-group">
            <label>{S.location}</label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                className="input-control"
                style={{ width: '100%', paddingLeft: '44px', height: '48px', opacity: globalSearch ? 0.5 : 1 }}
                placeholder="Ex: Paris, France..."
                value={globalSearch ? "" : location}
                onChange={(e) => setLocation(e.target.value)}
                disabled={globalSearch}
              />
              <MapPin size={20} style={{
                position: 'absolute',
                left: '14px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--primary-color)'
              }} />
            </div>
          </div>

        </div>

        {/* Checkboxes: Sources */}
        <div style={{ background: 'var(--surface-secondary)', padding: '20px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-light)' }}>
          <label style={{ display: 'block', marginBottom: '16px', fontWeight: '800', color: 'var(--text-primary)', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {S.select_sources}
          </label>
          <div className="source-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '12px' }}>
            {allAvailableSources.map((source) => (
              <label key={source} className="checkbox-container" style={{ fontSize: '0.85rem' }}>
                <input
                  type="checkbox"
                  checked={selectedSources.includes(source)}
                  onChange={() => handleSourceChange(source)}
                />
                <div className="checkbox-custom"></div>
                <span>{source}</span>
              </label>
            ))}
          </div>
        </div>


        {/* Refresh / Apply changes button */}
        <button
          className="btn btn-secondary"
          style={{ width: '100%' }}
          onClick={onRefresh}
        >
          {S.relaunch}
        </button>

      </div>
    </div>
  );
}
