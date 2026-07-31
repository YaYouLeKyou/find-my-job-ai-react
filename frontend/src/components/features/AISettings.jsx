/**
 * AISettings - Configuration IA au-dessus de l'analyzer
 *
 * Ce composant remplace la sidebar pour afficher :
 *   - Sélection du modèle IA
 *   - Gestion des clés API personnelles
 *   - Information sur le mode par défaut (Groq partagé)
 */
import React, { useState } from 'react';
import { useAI } from '../../context/AIContext';
import { AI_MODELS, getApiKeyUrl, getProviderLabel, PROVIDER_COLORS } from '../../config/aiProviders';
import { APIKeyManager } from '../APIKeyManager';
import { Cpu, Key, Info, ExternalLink, Zap, AlertTriangle, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';

export default function AISettings() {
    const { activeModel, setActiveModel, activeModelConfig, isUsingPersonalKey, modelStatus } = useAI();
    const [showApiInfo, setShowApiInfo] = useState(false);

    const currentModel = AI_MODELS.find(m => m.id === activeModel);
    const isGroqDefault = currentModel?.provider === 'groq' && !currentModel?.requiresPersonalKey;

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
            {/* Header */}
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
                    <Cpu size={22} />
                </div>
                <div style={{ flex: 1 }}>
                    <h3 style={{
                        fontSize: '1.2rem',
                        fontWeight: 700,
                        color: 'var(--color-text-primary)',
                        letterSpacing: '-0.01em',
                        margin: 0,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                    }}>
                        ⚡ Configuration IA
                    </h3>
                </div>
                <button
                    onClick={() => setShowApiInfo(!showApiInfo)}
                    style={{
                        padding: '10px',
                        color: 'var(--color-text-secondary)',
                        background: 'var(--color-surface-secondary)',
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
                        e.currentTarget.style.color = 'var(--color-text-primary)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'var(--color-surface-secondary)';
                        e.currentTarget.style.color = 'var(--color-text-secondary)';
                    }}
                    title="Informations sur les clés API"
                >
                    <Info size={18} />
                </button>
            </div>

            {/* Info Banner */}
            <div style={{
                padding: '16px',
                borderRadius: 'var(--radius-sm)',
                background: isGroqDefault && !isUsingPersonalKey
                    ? 'linear-gradient(135deg, rgba(255, 152, 0, 0.08), rgba(255, 193, 7, 0.05))'
                    : 'linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(16, 185, 129, 0.05))',
                border: '1px solid',
                borderColor: isGroqDefault && !isUsingPersonalKey
                    ? 'rgba(255, 152, 0, 0.2)'
                    : 'rgba(16, 185, 129, 0.2)',
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '12px',
                }}>
                    <span style={{
                        fontSize: '1.2rem',
                        flexShrink: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '32px',
                        height: '32px',
                    }}>
                        {isGroqDefault && !isUsingPersonalKey ? '⚠️' : '✅'}
                    </span>
                    <div style={{ flex: 1 }}>
                        {isGroqDefault && !isUsingPersonalKey ? (
                            <>
                                <p style={{
                                    fontSize: '0.9rem',
                                    fontWeight: 700,
                                    color: 'var(--color-text-primary)',
                                    margin: 0,
                                    marginBottom: '6px',
                                }}>
                                    Mode par défaut : Groq (ressource partagée)
                                </p>
                                <p style={{
                                    fontSize: '0.8rem',
                                    color: 'var(--color-text-secondary)',
                                    margin: 0,
                                    lineHeight: '1.6',
                                }}>
                                    Vous utilisez le quota partagé de l'application. Les performances peuvent être limitées selon le trafic. Pour une meilleure expérience, sélectionnez un modèle IA et ajoutez votre propre clé API dans l'emplacement prévu à cet effet (ou activez le <strong style={{ color: 'var(--color-text-primary)' }}>Mode Sans IA</strong>).
                                </p>
                            </>
                        ) : (
                            <>
                                <p style={{
                                    fontSize: '0.9rem',
                                    fontWeight: 700,
                                    color: 'var(--color-text-primary)',
                                    margin: 0,
                                    marginBottom: '6px',
                                }}>
                                    Modèle personnel actif
                                </p>
                                <p style={{
                                    fontSize: '0.8rem',
                                    color: 'var(--color-text-secondary)',
                                    margin: 0,
                                    lineHeight: '1.6',
                                }}>
                                    Vous utilisez votre propre clé API. Merci de votre soutien ! 🎉
                                </p>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* API Key Info Panel */}
            {showApiInfo && (
                <div style={{
                    padding: '16px',
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm)',
                    animation: 'slideDown 0.2s ease',
                }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        marginBottom: '12px',
                        color: 'var(--color-text-primary)',
                        fontWeight: 700,
                    }}>
                        <Key size={16} />
                        <span style={{ fontSize: '0.85rem' }}>Comment obtenir une clé API personnelle ?</span>
                    </div>
                    <ol style={{
                        fontSize: '0.8rem',
                        color: 'var(--color-text-secondary)',
                        margin: 0,
                        paddingLeft: '20px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                    }}>
                        <li>Choisissez un fournisseur IA ci-dessous (Gemini, OpenAI, etc.)</li>
                        <li>Cliquez sur le lien pour créer un compte sur le site du fournisseur</li>
                        <li>Générez une clé API dans votre tableau de bord</li>
                        <li>Collez votre clé dans le champ "Clé API personnelle" ci-dessous</li>
                        <li>Votre clé est stockée localement dans votre navigateur (jamais envoyée à nos serveurs)</li>
                    </ol>
                    <div style={{
                        marginTop: '12px',
                        padding: '12px',
                        background: 'rgba(99, 102, 241, 0.08)',
                        border: '1px solid rgba(99, 102, 241, 0.15)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.8rem',
                        color: 'var(--color-text-secondary)',
                    }}>
                        <strong>💡 Astuce :</strong> Sans clé personnelle, l'application utilise Groq en mode partagé (limité). Pour des performances optimales, ajoutez votre clé Gemini (gratuit) ou OpenAI.
                    </div>
                </div>
            )}

            {/* Model Selection */}
            <div>
                <label style={{
                    display: 'block',
                    fontSize: '0.9rem',
                    fontWeight: 700,
                    color: 'var(--color-text-primary)',
                    marginBottom: '10px',
                }}>
                    🧠 Modèle IA
                </label>
                <select
                    value={activeModel}
                    onChange={(e) => setActiveModel(e.target.value)}
                    className="select-control"
                    style={{
                        width: '100%',
                        padding: '12px 14px',
                        fontSize: '0.9rem',
                        appearance: 'auto',
                        cursor: 'pointer',
                    }}
                >
                    {AI_MODELS.map((model) => {
                        const isActive = modelStatus[model.id];
                        return (
                            <option key={model.id} value={model.id}>
                                {model.label} {model.requiresPersonalKey ? '🔑' : '🚀'} {!model.requiresPersonalKey && !isActive ? '(partagé)' : ''}
                            </option>
                        );
                    })}
                </select>
                {activeModelConfig && (
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        marginTop: '8px',
                        fontSize: '0.8rem',
                        color: 'var(--color-text-secondary)',
                    }}>
                        <span style={{
                            display: 'inline-block',
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: PROVIDER_COLORS[activeModelConfig.provider] || 'var(--color-primary-500)',
                            flexShrink: 0,
                        }} />
                        <span>
                            {activeModelConfig.description}
                            {!activeModelConfig.requiresPersonalKey && (
                                <span style={{ color: 'var(--color-text-muted)', marginLeft: '4px' }}>
                                    — Quota partagé de l'application - Aucune clé requise
                                </span>
                            )}
                        </span>
                    </div>
                )}
            </div>

            {/* API Key Manager */}
            <div style={{
                padding: '16px',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm)',
            }}>
                <APIKeyManager compact={false} />
            </div>
        </div>
    );
}