/**
 * SearchBar - Barre de recherche partagée
 *
 * Ce composant est IDENTIQUE pour les 3 agents. Il gère :
 *   - L'input de recherche textuelle
 *   - Le bouton de lancement
 *   - L'état de chargement
 *   - Le bouton d'annulation
 *
 * Les chips (suggestions depuis le CV) sont passés en prop.
 */
import React from 'react';
import { Search, Loader2, Sparkles } from 'lucide-react';
import { LANGS, STRINGS } from '../../utils/translations';
import { useAgent } from '../../context/AgentContext';

function SearchBar({
    searchQuery,
    setSearchQuery,
    onSearch,
    loading,
    chips = [],
    onSelectChip,
    placeholder,
    lang = 'Français',
}) {
    const { agentConfig } = useAgent();
    const currentLangCode = LANGS[lang].code;
    const S = STRINGS[currentLangCode];
    const primaryColor = agentConfig.theme.primary;

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            onSearch();
        }
    };

    const getTitle = () => {
        if (agentConfig.resultType === 'mission') return S.mission_search;
        if (agentConfig.resultType === 'candidate') return S.candidate_search;
        return S.opportunity_search;
    };

    const getDescription = () => {
        if (agentConfig.resultType === 'mission') {
            return S.mission_search_desc;
        }
        if (agentConfig.resultType === 'candidate') {
            return S.candidate_search_desc;
        }
        return S.search_info;
    };

    return (
        <div style={{
            background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-secondary) 100%)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: '28px',
            boxShadow: 'var(--shadow-md)',
            transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
        }}>
            {/* Header with icon and title */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                paddingBottom: '16px',
                borderBottom: '1px solid var(--color-border)',
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '48px',
                    height: '48px',
                    borderRadius: 'var(--radius-sm)',
                    background: 'linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%)',
                    color: '#ffffff',
                    flexShrink: 0,
                    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.25)',
                }}>
                    <Search size={22} />
                </div>
                <div style={{ flex: 1 }}>
                    <h3 style={{
                        fontSize: '1.2rem',
                        fontWeight: 700,
                        color: 'var(--color-text-primary)',
                        letterSpacing: '-0.01em',
                        margin: 0,
                    }}>
                        {getTitle()}
                    </h3>
                    <p style={{
                        fontSize: '0.85rem',
                        color: 'var(--color-text-secondary)',
                        marginTop: '4px',
                        margin: 0,
                    }}>
                        {getDescription()}
                    </p>
                </div>
            </div>

            {/* Chips/Suggestions */}
            {chips.length > 0 && (
                <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '8px',
                }}>
                    {chips.map((chip, idx) => (
                        <button
                            key={idx}
                            onClick={() => onSelectChip(chip)}
                            style={{
                                padding: '8px 16px',
                                fontSize: '0.8rem',
                                fontWeight: 600,
                                borderRadius: 'var(--radius-full)',
                                background: 'rgba(99, 102, 241, 0.08)',
                                color: 'var(--color-primary-500)',
                                border: '1px solid rgba(99, 102, 241, 0.15)',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                fontFamily: 'var(--font-sans)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.background = 'rgba(99, 102, 241, 0.15)';
                                e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.3)';
                                e.currentTarget.style.boxShadow = '0 2px 8px rgba(99, 102, 241, 0.15)';
                                e.currentTarget.style.transform = 'translateY(-1px)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'rgba(99, 102, 241, 0.08)';
                                e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.15)';
                                e.currentTarget.style.boxShadow = 'none';
                                e.currentTarget.style.transform = 'translateY(0)';
                            }}
                        >
                            <Sparkles size={14} />
                            {chip}
                        </button>
                    ))}
                </div>
            )}

            {/* Search Input and Button */}
            <div style={{
                display: 'flex',
                gap: '12px',
                alignItems: 'stretch',
            }}>
                <div style={{
                    position: 'relative',
                    flex: 1,
                }}>
                    <div style={{
                        position: 'absolute',
                        top: '50%',
                        left: '14px',
                        transform: 'translateY(-50%)',
                        color: 'var(--color-text-muted)',
                        pointerEvents: 'none',
                        zIndex: 1,
                        display: 'flex',
                        alignItems: 'center',
                    }}>
                        <Search size={18} />
                    </div>
                    <input
                        type="text"
                        style={{
                            width: '100%',
                            padding: '14px 16px 14px 44px',
                            fontSize: '0.95rem',
                            color: 'var(--color-text-primary)',
                            background: 'var(--color-surface)',
                            border: '2px solid var(--color-border)',
                            borderRadius: 'var(--radius-sm)',
                            outline: 'none',
                            transition: 'all 0.2s ease',
                            fontFamily: 'var(--font-sans)',
                            lineHeight: '1.5',
                        }}
                        onFocus={(e) => {
                            e.currentTarget.style.borderColor = 'var(--color-primary-500)';
                            e.currentTarget.style.boxShadow = '0 0 0 4px rgba(99, 102, 241, 0.1)';
                        }}
                        onBlur={(e) => {
                            e.currentTarget.style.borderColor = 'var(--color-border)';
                            e.currentTarget.style.boxShadow = 'none';
                        }}
                        placeholder={placeholder || S.search_placeholder}
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
                    />
                </div>
                <button
                    onClick={onSearch}
                    disabled={loading}
                    style={{
                        padding: '14px 32px',
                        background: loading
                            ? 'linear-gradient(135deg, var(--color-primary-400) 0%, var(--color-primary-500) 100%)'
                            : 'linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%)',
                        color: 'white',
                        borderRadius: 'var(--radius-sm)',
                        fontWeight: 700,
                        fontSize: '0.95rem',
                        border: 'none',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s ease',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        opacity: loading ? 0.7 : 1,
                        boxShadow: '0 4px 14px rgba(99, 102, 241, 0.25)',
                        fontFamily: 'var(--font-sans)',
                        whiteSpace: 'nowrap',
                        minWidth: '140px',
                    }}
                    onMouseEnter={(e) => {
                        if (!loading) {
                            e.currentTarget.style.transform = 'translateY(-2px)';
                            e.currentTarget.style.boxShadow = '0 6px 20px rgba(99, 102, 241, 0.35)';
                        }
                    }}
                    onMouseLeave={(e) => {
                        if (!loading) {
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.boxShadow = '0 4px 14px rgba(99, 102, 241, 0.25)';
                        }
                    }}
                >
                    {loading ? (
                        <>
                            <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
                            {S.searching}
                        </>
                    ) : (
                        <>
                            <Search size={18} />
                            {S.search}
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}

export default SearchBar;