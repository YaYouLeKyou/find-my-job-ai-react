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
    "Simplyhired", "Careerbuilder", "Monster"
  ];

  const handleSourceChange = (source) => {
    if (selectedSources.includes(source)) {
      setSelectedSources(selectedSources.filter(s => s !== source));
    } else {
      setSelectedSources([...selectedSources, source]);
    }
  };

  return (
    <div className="card" style={{ padding: '24px', background: 'var(--glass-bg)', backdropFilter: 'var(--blur)' }}>
      <div className="card-title">
        <Sliders size={20} style={{ color: 'var(--primary-color)' }} />
        <span>Filtres de Recherche</span>
      </div>

      <div className="card-content" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Row 1: Limit & Sort */}
        <div className="filters-row-1">
          
          <div className="form-group">
            <label>{S.num_ads} ({numAds})</label>
            <input
              type="range"
              min="1"
              max="50"
              value={numAds}
              onChange={(e) => setNumAds(parseInt(e.target.value))}
              style={{
                accentColor: 'var(--primary-color)',
                cursor: 'pointer',
                height: '6px',
                borderRadius: 'var(--radius-full)',
                background: 'rgba(255, 255, 255, 0.1)'
              }}
            />
          </div>

          <div className="form-group">
            <label>{S.sort_by}</label>
            <select
              className="select-control"
              value={sortOption}
              onChange={(e) => setSortOption(e.target.value)}
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
        <div className="filters-row-2">
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <label className="checkbox-container">
              <input
                type="checkbox"
                checked={remote}
                onChange={(e) => {
                  setRemote(e.target.checked);
                  if (!e.target.checked) setGlobalSearch(false);
                }}
              />
              <div className="checkbox-custom"></div>
              <span>{S.remote}</span>
            </label>

            {remote && (
              <label className="checkbox-container" style={{ marginLeft: '12px' }}>
                <input
                  type="checkbox"
                  checked={globalSearch}
                  onChange={(e) => setGlobalSearch(e.target.checked)}
                />
                <div className="checkbox-custom"></div>
                <span>{S.global_search}</span>
              </label>
            )}
          </div>

          <div className="form-group">
            <label>{S.location}</label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                className="input-control"
                style={{ width: '100%', paddingLeft: '40px', opacity: globalSearch ? 0.5 : 1 }}
                placeholder="Ex: Paris, France..."
                value={globalSearch ? "" : location}
                onChange={(e) => setLocation(e.target.value)}
                disabled={globalSearch}
              />
              <MapPin size={16} style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)'
              }} />
            </div>
          </div>

        </div>

        {/* Checkboxes: Sources */}
        <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
          <label style={{ display: 'block', marginBottom: '10px', fontWeight: '700' }}>
            {S.select_sources}
          </label>
          <div className="source-grid">
            {allAvailableSources.map((source) => (
              <label key={source} className="checkbox-container">
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
