import React from 'react';
import { LANGS, STRINGS } from '../utils/translations';
import { User, Award, List, AlertCircle, ArrowUpRight, Shuffle, Lightbulb } from 'lucide-react';

export default function CvProfile({
  lang,
  cvData,
  onSelectJobQuery
}) {
  if (!cvData) return null;

  const S = STRINGS[LANGS[lang].code];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Header Profile */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingBottom: '16px', borderBottom: '1px solid var(--border-color)' }}>
        <h2 style={{ fontSize: '1.8rem', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <User size={28} className="text-primary" />
          {cvData.nom_complet || "Candidat"}
        </h2>
        {cvData.contact && (
          <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
            📩 {cvData.contact}
          </span>
        )}
      </div>

      {/* Grid Profil & Pistes */}
      <div className="profile-container">
        
        {/* Mon Profil */}
        <div className="card">
          <div className="card-title">
            <Award size={20} style={{ color: 'var(--primary-color)' }} />
            <span>{S.profile}</span>
          </div>
          
          <div className="card-content">
            <div style={{ fontSize: '0.95rem', lineHeight: '1.6' }}>
              <p><strong>{S.metier} :</strong> {cvData.metier || "Non spécifié"}</p>
              <p><strong>{S.exp} :</strong> {cvData.annees_experience || 0} an(s)</p>
            </div>
            
            {cvData.resume && (
              <div className="alert alert-info" style={{ margin: '8px 0', fontSize: '0.85rem' }}>
                <Lightbulb size={18} style={{ flexShrink: 0 }} />
                <span>{cvData.resume}</span>
              </div>
            )}

            {cvData.mots_cles && cvData.mots_cles.length > 0 && (
              <div style={{ marginTop: '8px' }}>
                <div className="tag-list">
                  {cvData.mots_cles.map((kw, i) => (
                    <span key={i} className="tag">`{kw}`</span>
                  ))}
                </div>
              </div>
            )}

            {cvData.suggestions_amelioration && cvData.suggestions_amelioration.length > 0 && (
              <div style={{ marginTop: '16px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
                <h4 style={{ fontSize: '0.9rem', fontWeight: '700', marginBottom: '8px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertCircle size={14} />
                  {S.advice}
                </h4>
                <ul style={{ paddingLeft: '16px', fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {cvData.suggestions_amelioration.map((sug, i) => (
                    <li key={i}>{sug}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Pistes d'évolution */}
        <div className="card">
          <div className="card-title">
            <ArrowUpRight size={20} style={{ color: 'var(--primary-color)' }} />
            <span>{S.pistes}</span>
          </div>

          <div className="card-content" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Recommandations métiers */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {cvData.recommandations_metiers && cvData.recommandations_metiers.map((r, i) => (
                <button
                  key={i}
                  className="suggest-button"
                  onClick={() => onSelectJobQuery(r)}
                >
                  <span>🔍 {r}</span>
                  <ArrowUpRight size={14} style={{ color: 'var(--text-muted)' }} />
                </button>
              ))}
            </div>

            {/* Métiers alternatifs */}
            {cvData.metiers_alternatifs && cvData.metiers_alternatifs.length > 0 && (
              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <h4 style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                  <Shuffle size={14} />
                  {S.alt}
                </h4>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>
                  Basés sur vos compétences transférables
                </span>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {cvData.metiers_alternatifs.map((r, i) => (
                    <button
                      key={i}
                      className="suggest-button"
                      onClick={() => onSelectJobQuery(r)}
                    >
                      <span>🔄 {r}</span>
                      <ArrowUpRight size={14} style={{ color: 'var(--text-muted)' }} />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
