/**
 * Header - En-tête simplifié pour tous les agents
 *
 * Contient :
 *   - Titre de l'agent
 *   - Toggle "Mode Sans IA"
 *   - Bouton retour au hub central (Job Bridge)
 */
import React from 'react';
import { Cpu, ArrowLeft, Sparkles, Sun, Moon, Globe } from 'lucide-react';
import { useAgent } from '../../context/AgentContext';
import { LANGS } from '../../utils/translations';

export default function Header({ onBackToHub, showAiToggle = true, onToggleDarkMode, darkMode, lang, setLang }) {
    const { noAiMode, setNoAiMode, agentConfig } = useAgent();
    const theme = agentConfig.theme;

    return (
        <header style={{
            position: 'sticky',
            top: 0,
            zIndex: 50,
            width: '100%',
            borderBottom: '1px solid var(--color-border)',
            background: 'var(--color-glass-bg)',
            backdropFilter: 'blur(12px)',
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '16px',
                padding: '12px 24px',
                maxWidth: '1280px',
                margin: '0 auto',
            }}>
                {/* Left: Back button + Title */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    flex: 1,
                    minWidth: 0,
                }}>
                    {onBackToHub && (
                        <button
                            onClick={onBackToHub}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                padding: '8px 12px',
                                fontSize: '0.875rem',
                                fontWeight: 500,
                                color: 'var(--color-text-primary)',
                                background: 'var(--color-surface)',
                                border: '1px solid var(--color-border)',
                                borderRadius: 'var(--radius-sm)',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.background = 'var(--color-surface-hover)';
                                e.currentTarget.style.borderColor = 'var(--color-text-muted)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'var(--color-surface)';
                                e.currentTarget.style.borderColor = 'var(--color-border)';
                            }}
                            title="Retour à Job Bridge"
                            aria-label="Retour au hub"
                        >
                            <ArrowLeft size={16} />
                            <span style={{ display: 'none' }} className="back-text">Back to Hub</span>
                        </button>
                    )}

                    <h1 style={{
                        fontSize: 'clamp(1.1rem, 2vw, 1.5rem)',
                        fontWeight: 700,
                        color: 'var(--color-text-primary)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                    }}>
                        {agentConfig.title}
                    </h1>
                </div>

                {/* Right: Controls */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                }}>
                    {/* Language Selector */}
                    {setLang && (
                        <select
                            value={lang}
                            onChange={(e) => setLang(e.target.value)}
                            style={{
                                padding: '8px 12px',
                                fontSize: '0.875rem',
                                fontWeight: 600,
                                color: 'var(--color-text-primary)',
                                background: 'var(--color-surface)',
                                border: '1px solid var(--color-border)',
                                borderRadius: 'var(--radius-sm)',
                                cursor: 'pointer',
                                outline: 'none',
                                transition: 'all 0.2s',
                            }}
                            onFocus={(e) => {
                                e.currentTarget.style.borderColor = 'var(--color-primary-500)';
                                e.currentTarget.style.boxShadow = '0 0 0 2px rgba(99, 102, 241, 0.15)';
                            }}
                            onBlur={(e) => {
                                e.currentTarget.style.borderColor = 'var(--color-border)';
                                e.currentTarget.style.boxShadow = 'none';
                            }}
                            aria-label="Sélectionner la langue"
                        >
                            {Object.keys(LANGS).map((key) => (
                                <option key={key} value={key}>
                                    {LANGS[key].label}
                                </option>
                            ))}
                        </select>
                    )}

                    {/* Dark Mode Toggle */}
                    {onToggleDarkMode && (
                        <button
                            onClick={onToggleDarkMode}
                            style={{
                                padding: '8px',
                                color: 'var(--color-text-primary)',
                                background: 'var(--color-surface)',
                                border: '1px solid var(--color-border)',
                                borderRadius: 'var(--radius-sm)',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.background = 'var(--color-surface-hover)';
                                e.currentTarget.style.borderColor = 'var(--color-text-muted)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'var(--color-surface)';
                                e.currentTarget.style.borderColor = 'var(--color-border)';
                            }}
                            title={darkMode ? 'Mode Clair' : 'Mode Sombre'}
                            aria-label="Basculer le mode sombre/clair"
                        >
                            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
                        </button>
                    )}

                    {/* AI Toggle */}
                    {showAiToggle && (
                        <button
                            onClick={() => setNoAiMode(!noAiMode)}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                padding: '8px 16px',
                                borderRadius: 'var(--radius-sm)',
                                fontWeight: 600,
                                fontSize: '0.875rem',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                border: noAiMode ? 'none' : '1px solid var(--color-border)',
                                background: noAiMode
                                    ? 'linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%)'
                                    : 'var(--color-surface-secondary)',
                                color: noAiMode ? '#ffffff' : 'var(--color-text-primary)',
                                boxShadow: noAiMode ? '0 1px 3px rgba(99, 102, 241, 0.25)' : 'none',
                            }}
                            onMouseEnter={(e) => {
                                if (noAiMode) {
                                    e.currentTarget.style.boxShadow = '0 2px 6px rgba(99, 102, 241, 0.35)';
                                } else {
                                    e.currentTarget.style.background = 'var(--color-surface-hover)';
                                    e.currentTarget.style.borderColor = 'var(--color-text-muted)';
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (noAiMode) {
                                    e.currentTarget.style.boxShadow = '0 1px 3px rgba(99, 102, 241, 0.25)';
                                } else {
                                    e.currentTarget.style.background = 'var(--color-surface-secondary)';
                                    e.currentTarget.style.borderColor = 'var(--color-border)';
                                }
                            }}
                            title={noAiMode ? 'Désactiver le Mode IA' : 'Activer le Mode IA'}
                            aria-pressed={noAiMode}
                        >
                            {noAiMode ? (
                                <>
                                    <Cpu size={16} />
                                    <span>Mode Sans IA</span>
                                </>
                            ) : (
                                <>
                                    <Sparkles size={16} />
                                    <span>Mode IA Actif</span>
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>
        </header>
    );
}