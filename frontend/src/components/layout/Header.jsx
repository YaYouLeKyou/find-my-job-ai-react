/**
 * Header - En-tête pour tous les agents
 *
 * Structure :
 *   - Ligne 1 : Bouton flèche (gauche) + Titre (centré, plus grand) + Dark mode (droite)
 *   - Ligne 2 : Feedback (avec texte) + Langue + Toggle AI (même hauteur)
 *   - Non flottant, aligné avec le contenu en dessous
 */
import React from 'react';
import { Cpu, ArrowLeft, Sparkles, Sun, Moon, Mail } from 'lucide-react';
import { useAgent } from '../../context/AgentContext';
import { LANGS, STRINGS } from '../../utils/translations';

export default function Header({ onBackToHub, showAiToggle = true, onToggleDarkMode, darkMode, lang, setLang }) {
    const { noAiMode, setNoAiMode, agentConfig } = useAgent();
    const theme = agentConfig.theme;
    const S = STRINGS[LANGS[lang]?.code || 'fr'];

    return (
        <header style={{
            width: '100%',
            borderBottom: '1px solid var(--color-border)',
            background: 'var(--color-glass-bg)',
            backdropFilter: 'blur(12px)',
            // Removed sticky positioning to make header non-floating
        }}>
            <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                padding: '12px 24px',
                maxWidth: '1280px',
                margin: '0 auto',
            }}>
                {/* Row 1: Arrow (left) + Title (center, larger) + Dark Mode (right) */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '8px',
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
                                height: '40px', // Match height with box below
                                boxSizing: 'border-box',
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
                            <span className="back-text" style={{ display: 'none' }}>{S.back_to_hub}</span>
                        </button>
                    )}

                    <h1 style={{
                        fontSize: 'clamp(1.3rem, 3vw, 1.8rem)', // Larger title on laptop
                        fontWeight: 700,
                        color: 'var(--color-text-primary)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        textAlign: 'center',
                        flex: 1,
                        minWidth: 0,
                    }}>
                        {agentConfig.title}
                    </h1>

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
                                flexShrink: 0,
                                height: '40px', // Match height with box below
                                boxSizing: 'border-box',
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
                </div>

                {/* Row 2: Feedback (with text) + Language (center) + AI Toggle (right) - All same height */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '8px',
                    flexWrap: 'wrap',
                }}>
                    {/* Feedback Button - Envelope icon with "feedbacks" text */}
                    <a
                        href="mailto:findmyworkai@gmail.com"
                        style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '8px 12px',
                            borderRadius: 'var(--radius-sm)',
                            color: 'var(--color-text-primary)',
                            background: 'var(--color-surface)',
                            border: '1px solid var(--color-border)',
                            cursor: 'pointer',
                            textDecoration: 'none',
                            transition: 'all 0.2s ease',
                            flexShrink: 0,
                            height: '38px',
                            boxSizing: 'border-box',
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
                        aria-label={S.feedback}
                    >
                        <Mail size={16} />
                        <span className="feedback-text">feedbacks</span>
                    </a>

                    {/* Language Selector - Centered */}
                    <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
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
                                height: '38px',
                                boxSizing: 'border-box',
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
                    </div>

                    {/* AI Toggle - Right aligned */}
                    <div style={{ flexShrink: 0 }}>
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
                                    ? 'var(--color-surface-secondary)'
                                    : 'linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%)',
                                color: noAiMode ? 'var(--color-text-primary)' : '#ffffff',
                                boxShadow: noAiMode ? 'none' : '0 1px 3px rgba(99, 102, 241, 0.25)',
                                height: '38px',
                                boxSizing: 'border-box',
                            }}
                            onMouseEnter={(e) => {
                                if (noAiMode) {
                                    e.currentTarget.style.background = 'var(--color-surface-hover)';
                                    e.currentTarget.style.borderColor = 'var(--color-text-muted)';
                                } else {
                                    e.currentTarget.style.boxShadow = '0 2px 6px rgba(99, 102, 241, 0.35)';
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (noAiMode) {
                                    e.currentTarget.style.background = 'var(--color-surface-secondary)';
                                    e.currentTarget.style.borderColor = 'var(--color-border)';
                                } else {
                                    e.currentTarget.style.boxShadow = '0 1px 3px rgba(99, 102, 241, 0.25)';
                                }
                            }}
                            title={noAiMode ? S.disable_ai : S.enable_ai}
                            aria-pressed={noAiMode}
                        >
                            {noAiMode ? (
                                <>
                                    <Cpu size={16} />
                                    <span className="ai-toggle-text">{S.ai_disabled}</span>
                                </>
                            ) : (
                                <>
                                    <Sparkles size={16} />
                                    <span className="ai-toggle-text">{S.ai_enabled}</span>
                                </>
                            )}
                        </button>
                    )}
                    </div>
                </div>
            </div>
        </header>
    );
}