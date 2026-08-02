import React from 'react';
import { Settings } from 'lucide-react';

export default function AdvancedFiltersHeader({ onToggle }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '16px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '1rem' }}>🎛️</span>
        <h3 style={{
          fontSize: '0.875rem',
          fontWeight: 600,
          color: 'var(--color-text-primary)'
        }}>
          Filtres avancés
        </h3>
      </div>
      <button
        onClick={onToggle}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 12px',
          background: 'var(--color-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-sm)',
          cursor: 'pointer',
          fontSize: '0.875rem',
          fontWeight: 500,
          color: 'var(--color-text-primary)',
          transition: 'all 0.2s'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'var(--color-surface-hover)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'var(--color-surface)';
        }}
      >
        <Settings size={16} />
        <span>Configurer</span>
      </button>
    </div>
  );
}