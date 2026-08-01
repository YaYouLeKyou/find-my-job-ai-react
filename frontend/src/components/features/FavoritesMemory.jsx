import React from 'react';
import ResultCard from './ResultCard';
import { LANGS, STRINGS } from '../../utils/translations';

export default function FavoritesMemory({
    lang,
    favorites,
    onRemove,
    onClear,
    resultType,
    cvData,
    rankingEngine,
    customGeminiKey,
    onStartInterview,
}) {
    const S = STRINGS[LANGS[lang]?.code || 'fr'];

    if (!favorites || favorites.length === 0) {
        return (
            <div className="card" style={{
                background: 'var(--color-surface)',
                border: '1px dashed var(--color-border)',
                padding: '24px',
                textAlign: 'center',
            }}>
                <div style={{ marginBottom: '12px', opacity: 0.5 }}>
                    <span style={{ fontSize: '2rem' }}>⭐</span>
                </div>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-text-primary)', margin: '0 0 8px' }}>
                    {S.no_favorites}
                </h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', margin: 0 }}>
                    {S.no_favorites_desc}
                </p>
            </div>
        );
    }

    return (
        <div className="card" style={{ background: 'var(--color-surface)' }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '16px',
            }}>
                <span style={{ fontSize: '1rem' }}>⭐</span>
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-text-primary)', margin: 0 }}>
                    {S.saved_favorites || 'Favoris sauvegardés'}
                </h3>
                <span style={{
                    marginLeft: 'auto',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: 'var(--color-text-secondary)',
                    background: 'var(--color-surface-secondary)',
                    padding: '2px 10px',
                    borderRadius: '9999px',
                }}>
                    {favorites.length}
                </span>
                {onClear && (
                    <button
                        onClick={onClear}
                        style={{
                            marginLeft: '8px',
                            padding: '4px 10px',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--color-border)',
                            background: 'var(--color-surface)',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            color: '#ef4444',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                        }}
                    >
                        🗑️ {S.clear_all || 'Tout effacer'}
                    </button>
                )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {favorites.map((fav) => (
                    <ResultCard
                        key={fav.id}
                        item={fav}
                        resultType={resultType}
                        onSave={onRemove}
                        isSaved={true}
                        aiScore={fav.pertinence_ai}
                        aiProcessed={fav.ai_scored || false}
                        cvData={cvData}
                        rankingEngine={rankingEngine}
                        customGeminiKey={customGeminiKey}
                        onStartInterview={onStartInterview}
                        lang={lang}
                    />
                ))}
            </div>
        </div>
    );
}
