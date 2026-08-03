/**
 * Header - En-tête simplifié pour tous les agents
 *
 * Contient :
 *   - Titre de l'agent
 *   - Toggle "Mode Sans IA"
 *   - Bouton retour au hub central (Job Bridge)
 */
import React from 'react';
import { Cpu, ArrowLeft, Sparkles, Sun, Moon, Globe, Mail } from 'lucide-react';
import { useAgent } from '../../context/AgentContext';
import { LANGS, STRINGS } from '../../utils/translations';

export default function Header({ onBackToHub, showAiToggle = true, onToggleDarkMode, darkMode, lang, setLang }) {
    const { noAiMode, setNoAiMode, agentConfig } = useAgent();
    const theme = agentConfig.theme;
    const S = STRINGS[LANGS[lang]?.code || 'fr'];

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
                            title={S.back_to_hub}
                            aria-label={S.back_to_hub_aria}
                        >
                            <ArrowLeft size={16} />
                            <span className="back-text">{S.back_to_hub}</span>
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
                    {/* Feedback Button */}
                    <a
                        href="mailto:findmyworkai@gmail.com"
                        style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '8px 14px',
                            fontSize: '0.875rem',
                            fontWeight: 600,
                            color: 'var(--color-text-primary)',
                            background: 'var(--color-surface)',
                            border: '1px solid var(--color-border)',
                            borderRadius: 'var(--radius-sm)',
                            cursor: 'pointer',
                            textDecoration: 'none',
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
                        title={S.feedback}
                    >
                        <Mail size={16} />
                        <span className="feedback-text">{S.feedback}</span>
                    </a>

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
                            aria-label={S.language_aria}
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
                            title={darkMode ? S.light_mode : S.dark_mode}
                            aria-label={S.dark_mode_aria}
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
                            title={noAiMode ? S.disable_ai : S.enable_ai}
                            aria-pressed={noAiMode}
                        >
                            {noAiMode ? (
                                <>
                                    <Cpu size={16} />
                                    <span className="ai-toggle-text">{S.no_ai_mode}</span>
                                </>
                            ) : (
                                <>
                                    <Sparkles size={16} />
                                    <span className="ai-toggle-text">{S.ai_mode_active}</span>
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>
        </header>
    );
}