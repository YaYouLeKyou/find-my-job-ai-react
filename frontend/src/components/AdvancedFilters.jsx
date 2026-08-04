import React, { useState, useCallback } from 'react';
import { LANGS, STRINGS } from '../utils/translations';

export default function AdvancedFilters({
  isOpen = true,
  onClose = () => {},
  onApplyFilters,
  currentFilters = {},
  totalJobs = 0,
  filteredCount = 0,
  lang = 'Français'
}) {
  const S = STRINGS[LANGS[lang]?.code || 'fr'];
  // Initialize state from props or defaults
  const [minMatchScore, setMinMatchScore] = useState(currentFilters.minMatchScore || 0);
  const [companyTypes, setCompanyTypes] = useState(currentFilters.companyTypes || []);
  const [workModes, setWorkModes] = useState(currentFilters.workModes || []);
  const [minSalary, setMinSalary] = useState(currentFilters.minSalary || 0);
  const [includeAISalary, setIncludeAISalary] = useState(currentFilters.includeAISalary || true);
  const [offerFreshness, setOfferFreshness] = useState(currentFilters.offerFreshness || 'all');

  // Calculate active filter count
  const activeFilterCount = [
    minMatchScore > 0 ? 1 : 0,
    companyTypes.length > 0 ? 1 : 0,
    workModes.length > 0 ? 1 : 0,
    minSalary > 0 ? 1 : 0,
    offerFreshness !== 'all' ? 1 : 0,
  ].reduce((sum, val) => sum + val, 0);

  const handleApplyFilters = useCallback(() => {
    onApplyFilters({
      minMatchScore,
      companyTypes,
      workModes,
      minSalary,
      includeAISalary,
      offerFreshness
    });
  }, [
    minMatchScore,
    companyTypes,
    workModes,
    minSalary,
    includeAISalary,
    offerFreshness,
    onApplyFilters
  ]);

  const handleReset = useCallback(() => {
    setMinMatchScore(0);
    setCompanyTypes([]);
    setWorkModes([]);
    setMinSalary(0);
    setIncludeAISalary(true);
    setOfferFreshness('all');
    onApplyFilters({
      minMatchScore: 0,
      companyTypes: [],
      workModes: [],
      minSalary: 0,
      includeAISalary: true,
      offerFreshness: 'all'
    });
  }, [onApplyFilters]);

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  // Checkbox toggle handlers
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'flex-end' }}>
      {/* Header - Matching quick filters style */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
        <span style={{ fontSize: '1rem' }}>🎛️</span>
        <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
          {S.advanced_filters}
        </h3>
      </div>

      {/* Filters Grid - Matching quick filters layout */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>

        {/* Match Score - Range style */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {S.min_match_score}
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

        {/* Company Type - Select style */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {S.company_type}
          </label>
          <select
            value={companyTypes[0] || ''}
            onChange={(e) => toggleCompanyType(e.target.value)}
            className="select-control"
            style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
          >
            <option value="">{S.all_companies}</option>
            <option value="Client Final">{S.client_final}</option>
            <option value="ESN / Cabinet">{S.esn_cabinet}</option>
          </select>
        </div>

        {/* Work Mode - Select style */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {S.work_mode}
          </label>
          <select
            value={workModes[0] || ''}
            onChange={(e) => toggleWorkMode(e.target.value)}
            className="select-control"
            style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
          >
            <option value="">{S.all_types}</option>
            <option value="Full Remote (100%)">{S.full_remote}</option>
            <option value="Hybride (3-4j)">Hybride (3-4j)</option>
            <option value="Hybride (1-2j)">Hybride (1-2j)</option>
            <option value="Présentiel (0j)">Présentiel (0j)</option>
          </select>
        </div>

        {/* Salary - Number style */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {S.min_salary}
          </label>
          <input
            type="number"
            placeholder={S.salary_placeholder}
            value={minSalary || ''}
            onChange={(e) => setMinSalary(parseInt(e.target.value) || 0)}
            min={0}
            step={1000}
            className="input-control"
            style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
          />
        </div>

        {/* AI Salary Checkbox - Checkbox style */}
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
          {S.include_ai_salary}
        </label>

        {/* Offer Freshness - Select style */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px', flex: '1 1 160px' }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {S.offer_freshness}
          </label>
          <select
            value={offerFreshness}
            onChange={(e) => setOfferFreshness(e.target.value)}
            className="select-control"
            style={{ padding: '8px 12px', fontSize: '0.875rem', width: '100%', height: '38px', boxSizing: 'border-box' }}
          >
            <option value="all">{S.all_freshness}</option>
            <option value="24h">{S.less_24h}</option>
            <option value="3d">{S.less_3d}</option>
            <option value="7d">{S.less_7d}</option>
          </select>
        </div>
      </div>

      {/* Action buttons - Matching quick filters style */}
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
            {S.apply_filters}
        </button>
      </div>
    </div>
  );
}
