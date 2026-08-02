/**
 * ActiveSourcesHeader - Affiche les sources actives et le compteur global
 * 
 * Affiche uniquement les sources qui ont trouvé des résultats (pas de badge grisé pour les sources vides)
 */

import React from 'react';
import { LANGS, STRINGS } from '../utils/translations';

export default function ActiveSourcesHeader({ sourceCounts, aiProcessing, processedCount, lang = 'Français', onToggleSource }) {
  const S = STRINGS[LANGS[lang]?.code || 'fr'];
  const totalRealJobs = Object.values(sourceCounts).reduce((a, b) => a + b, 0);
  // Ne garder que les sources avec au moins 1 résultat
  const activeSources = Object.entries(sourceCounts)
    .filter(([source, count]) => count > 0)
    .sort((a, b) => b[1] - a[1]); // Trier par nombre de résultats décroissant

  return (
    <div style={{
      padding: '16px 20px',
      background: 'linear-gradient(135deg, rgba(124, 77, 255, 0.08), rgba(68, 138, 255, 0.05))',
      border: '1px solid rgba(124, 77, 255, 0.2)',
      borderRadius: 'var(--radius-md)',
      marginBottom: '20px',
    }}>
      {/* Compteur global */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: activeSources.length > 0 ? '12px' : '0',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{
            fontSize: '1.5rem',
            fontWeight: '800',
            color: 'var(--text-primary)',
            letterSpacing: '-0.02em',
          }}>
            {totalRealJobs}
          </span>
          <span style={{
            fontSize: '0.9rem',
            color: 'var(--text-secondary)',
            fontWeight: '500',
          }}>
             {S.jobs_found}
          </span>
        </div>

        {/* Indicateur de traitement IA */}
        {aiProcessing && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 12px',
            background: 'rgba(124, 77, 255, 0.1)',
            border: '1px solid rgba(124, 77, 255, 0.2)',
            borderRadius: '9999px',
            fontSize: '0.8rem',
            color: 'var(--primary-color)',
            fontWeight: '600',
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: 'var(--primary-color)',
              display: 'inline-block',
              animation: 'pulse-dot 1.5s ease-in-out infinite',
            }} />
              {S.ai_sorting_in_progress}({processedCount}/{totalRealJobs})
          </div>
        )}
      </div>

      {/* Badges des sources actives */}
      {activeSources.length > 0 && (
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px',
        }}>
          {activeSources.map(([source, count]) => (
            <div
              key={source}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.2)',
                borderRadius: '9999px',
                fontSize: '0.85rem',
                fontWeight: '600',
                color: 'var(--text-primary)',
              }}
            >
              <span style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: '#10b981',
                display: 'inline-block',
              }} />
              {source}
              <span style={{
                padding: '2px 8px',
                background: 'rgba(16, 185, 129, 0.2)',
                borderRadius: '9999px',
                fontSize: '0.75rem',
                fontWeight: '700',
                color: '#2e7d32',
              }}>
                {count}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Message si aucun résultat */}
      {activeSources.length === 0 && !aiProcessing && (
        <div style={{
          textAlign: 'center',
          padding: '20px',
          color: 'var(--text-muted)',
          fontSize: '0.9rem',
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🔍</div>
          <div>En attente des résultats...</div>
        </div>
      )}

      {/* Animation CSS */}
      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.7); }
        }
      `}</style>
    </div>
  );
}