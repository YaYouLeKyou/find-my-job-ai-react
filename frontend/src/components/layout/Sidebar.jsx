/**
 * Sidebar - Sidebar dynamique générée à partir de agentsConfig.js
 *
 * La Sidebar est IDENTIQUE en structure pour les 3 agents. La SEULE différence
 * réside dans les filtres affichés, qui sont générés dynamiquement à partir
 * de la configuration de l'agent actif (agentsConfig.js).
 *
 * Sections partagées :
 *   - ⚙️ Paramètres (langue, modèle IA, clé API)
 *   - 📋 Historique des recherches
 *   - ⭐ Éléments sauvegardés
 *   - [Agent-specific] Filtres métier (TJM, salaire, etc.)
 */

import React, { useState, useEffect } from 'react';
import {
    Settings, Cpu, Key, Globe, Save, ExternalLink,
    CheckCircle2, AlertCircle, ChevronLeft, ChevronRight,
    Wifi, WifiOff, Menu, X, Trash2, Zap, Filter,
} from 'lucide-react';
import { useAgent } from '../../context/AgentContext';
import { useAI } from '../../context/AIContext';
import { AI_MODELS } from '../../config/aiProviders';
import { APIKeyManager } from '../APIKeyManager';
import { LANGS, STRINGS } from '../../utils/translations';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Sidebar({
    lang,
    setLang,
    searchHistory,
    savedItems,
    onSelectHistory,
    onToggleDarkMode,
    onClearHistory,
    onClearSavedItems,
    onClearCache,
}) {
    const { activeAgent, agentConfig, activeFilters, updateFilter, noAiMode } = useAgent();
    const { activeModel, setActiveModel, activeModelConfig, modelStatus, refreshModelStatus, apiKeys } = useAI();

    const [collapsed, setCollapsed] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [activeTab, setActiveTab] = useState('settings');

    const theme = agentConfig.theme;
    const primaryColor = theme.primary;
    const S = STRINGS[LANGS[lang]?.code || 'fr'];

    // Close mobile sidebar on window resize above breakpoint
    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth > 599 && mobileOpen) {
                setMobileOpen(false);
            }
        };
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, [mobileOpen]);

    const getStatusIcon = (isAvailable) => {
        return isAvailable
            ? <CheckCircle2 size={14} style={{ color: 'var(--success-color)' }} />
            : <AlertCircle size={14} style={{ color: 'var(--error-color)' }} />;
    };

    const closeMobile = () => setMobileOpen(false);

    // --- Build tabs dynamically based on agent config ---
    // Note: "Filtres" tab removed from sidebar - filters are now in the main body
    // to avoid duplication with the "Filtres rapides" section.
    const tabs = [
        { id: 'settings', icon: '⚙️', label: 'Paramètres' },
        { id: 'history', icon: '📋', label: 'Historique', count: searchHistory?.length },
        { id: 'saved', icon: '⭐', label: 'Sauvegardés', count: savedItems?.length },
    ];

    // Add agent-specific tabs
    if (activeAgent === 'freelance') {
        tabs.push({ id: 'tjm', icon: '💰', label: 'TJM' });
    }
    if (activeAgent === 'recruiter') {
        tabs.push({ id: 'salary', icon: '💰', label: 'Salaire' });
    }

    // --- Render a single filter field based on its type ---
    const renderFilterField = (filter) => {
        const value = activeFilters[filter.id];
        const commonInputStyle = {
            width: '100%',
            padding: '8px 12px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--surface-secondary)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)',
            fontSize: '0.85rem',
        };

        switch (filter.type) {
            case 'select':
                return (
                    <div className="form-group" key={filter.id} style={{ marginBottom: '12px' }}>
                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.8rem', fontWeight: 600 }}>
                            {filter.label}
                        </label>
                        <select
                            className="select-control"
                            value={value || ''}
                            onChange={(e) => updateFilter(filter.id, e.target.value)}
                            style={commonInputStyle}
                        >
                            {filter.placeholder && (
                                <option value="">{filter.placeholder}</option>
                            )}
                            {filter.options.map((opt) => (
                                <option key={opt} value={opt}>{opt}</option>
                            ))}
                        </select>
                    </div>
                );

            case 'text':
                return (
                    <div className="form-group" key={filter.id} style={{ marginBottom: '12px' }}>
                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.8rem', fontWeight: 600 }}>
                            {filter.label}
                        </label>
                        <input
                            type="text"
                            className="input-control"
                            placeholder={filter.placeholder || ''}
                            value={value || ''}
                            onChange={(e) => updateFilter(filter.id, e.target.value)}
                            style={commonInputStyle}
                        />
                    </div>
                );

            case 'number':
                return (
                    <div className="form-group" key={filter.id} style={{ marginBottom: '12px' }}>
                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.8rem', fontWeight: 600 }}>
                            {filter.label}
                        </label>
                        <input
                            type="number"
                            className="input-control"
                            placeholder={filter.placeholder || ''}
                            value={value || ''}
                            onChange={(e) => updateFilter(filter.id, e.target.value)}
                            min={filter.min}
                            step={filter.step}
                            style={commonInputStyle}
                        />
                    </div>
                );

            case 'checkbox':
                return (
                    <div className="form-group" key={filter.id} style={{ marginBottom: '8px' }}>
                        <label style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            cursor: 'pointer',
                            fontSize: '0.85rem',
                        }}>
                            <input
                                type="checkbox"
                                checked={!!value}
                                onChange={(e) => updateFilter(filter.id, e.target.checked)}
                                style={{ accentColor: primaryColor }}
                            />
                            {filter.label}
                        </label>
                    </div>
                );

            case 'range':
                return (
                    <div className="form-group" key={filter.id} style={{ marginBottom: '12px' }}>
                        <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: '4px',
                        }}>
                            <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                                {filter.label}
                            </label>
                            <span style={{
                                fontWeight: 800,
                                color: primaryColor,
                                fontSize: '1rem',
                            }}>
                                {value || filter.default}
                            </span>
                        </div>
                        <input
                            type="range"
                            min={filter.min}
                            max={filter.max}
                            step={filter.step}
                            value={value || filter.default}
                            onChange={(e) => updateFilter(filter.id, parseInt(e.target.value))}
                            style={{
                                accentColor: primaryColor,
                                cursor: 'pointer',
                                height: '8px',
                                borderRadius: 'var(--radius-full)',
                                marginTop: '10px',
                            }}
                        />
                    </div>
                );

            case 'tags':
                return (
                    <div className="form-group" key={filter.id} style={{ marginBottom: '12px' }}>
                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.8rem', fontWeight: 600 }}>
                            {filter.label}
                        </label>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                            {filter.options.map((skill) => {
                                const isSelected = (value || []).includes(skill);
                                return (
                                    <button
                                        key={skill}
                                        type="button"
                                        onClick={() => {
                                            const current = value || [];
                                            const updated = isSelected
                                                ? current.filter(s => s !== skill)
                                                : [...current, skill];
                                            updateFilter(filter.id, updated);
                                        }}
                                        style={{
                                            padding: '4px 10px',
                                            borderRadius: '20px',
                                            border: `1px solid ${isSelected ? primaryColor : 'var(--border-color)'}`,
                                            background: isSelected ? `${primaryColor}20` : 'transparent',
                                            color: isSelected ? primaryColor : 'var(--text-secondary)',
                                            fontSize: '0.8rem',
                                            cursor: 'pointer',
                                            transition: 'all 0.2s',
                                        }}
                                    >
                                        {skill}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                );

            default:
                return null;
        }
    };

    return (
        <>
            {/* Mobile hamburger toggle button */}
            <button
                className="sidebar-toggle-mobile"
                onClick={() => setMobileOpen(!mobileOpen)}
                aria-label="Toggle sidebar"
                title={mobileOpen ? S.close_menu : S.open_menu}
            >
                {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>

            {/* Mobile overlay backdrop */}
            {mobileOpen && (
                <div
                    className="sidebar-overlay"
                    onClick={closeMobile}
                />
            )}

            <aside
                className={`sidebar ${mobileOpen ? 'open' : ''}`}
                style={{
                    width: collapsed ? '60px' : '320px',
                    transition: 'width 0.3s ease',
                    background: 'var(--surface-color)',
                    borderRight: '1px solid var(--border-color)',
                }}
            >
                <div
                    className="sidebar-logo"
                    style={{
                        justifyContent: collapsed ? 'center' : 'space-between',
                        padding: collapsed ? '16px 0' : '16px',
                    }}
                >
                    {!collapsed && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '1.3rem' }}>{agentConfig.emoji}</span>
                            <span
                                style={{
                                    background: agentConfig.theme.gradient,
                                    WebkitBackgroundClip: 'text',
                                    WebkitTextFillColor: 'transparent',
                                    fontWeight: '800',
                                    fontSize: '1rem',
                                }}
                            >
                                {agentConfig.title}
                            </span>
                        </div>
                    )}
                    <button
                        onClick={() => setCollapsed(!collapsed)}
                        style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}
                        title={collapsed ? S.expand : S.collapse}
                    >
                        {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
                    </button>
                </div>

                {!collapsed ? (
                    <React.Fragment>
                        {/* Tabs */}
                        <div style={{
                            display: 'flex',
                            borderBottom: '1px solid var(--border-color)',
                            marginBottom: '8px',
                        }}>
                            {tabs.map((tab) => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    style={{
                                        flex: 1,
                                        padding: '8px',
                                        background: 'none',
                                        border: 'none',
                                        borderBottom: activeTab === tab.id
                                            ? `2px solid ${primaryColor}`
                                            : 'none',
                                        color: activeTab === tab.id
                                            ? primaryColor
                                            : 'var(--text-secondary)',
                                        cursor: 'pointer',
                                        fontWeight: '600',
                                        fontSize: '0.85rem',
                                        position: 'relative',
                                        transition: 'color 0.2s',
                                    }}
                                    title={tab.label}
                                >
                                    {tab.icon}
                                    {tab.count > 0 && (
                                        <span style={{
                                            position: 'absolute',
                                            top: '4px',
                                            right: '4px',
                                            background: primaryColor,
                                            color: 'white',
                                            borderRadius: '50%',
                                            width: '16px',
                                            height: '16px',
                                            fontSize: '0.7rem',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                        }}>
                                            {tab.count}
                                        </span>
                                    )}
                                </button>
                            ))}
                        </div>

                        {/* Settings Tab */}
                        {activeTab === 'settings' && (
                            <React.Fragment>
                                {/* Language Section */}
                                <div className="sidebar-section">
                                    <h3 className="sidebar-section-title" style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                        padding: '12px 16px',
                                        fontSize: '0.85rem',
                                        fontWeight: 700,
                                        color: 'var(--text-primary)',
                                    }}>
                                        <Globe size={14} />
                                        Langue
                                    </h3>
                                    <div className="form-group" style={{ padding: '0 16px', marginBottom: '12px' }}>
                                        <select
                                            className="select-control"
                                            value={lang}
                                            onChange={(e) => setLang(e.target.value)}
                                            style={{
                                                width: '100%',
                                                padding: '8px 12px',
                                                borderRadius: 'var(--radius-sm)',
                                                background: 'var(--surface-secondary)',
                                                border: '1px solid var(--border-color)',
                                                color: 'var(--text-primary)',
                                                fontSize: '0.85rem',
                                            }}
                                        >
                                            {Object.keys(LANGS).map((key) => (
                                                <option key={key} value={key}>
                                                    {key}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                {/* ⚡ PIPELINE IA UNIFIÉ */}
                                <div className="sidebar-section">
                                    <h3 className="sidebar-section-title" style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                        padding: '12px 16px',
                                        fontSize: '0.85rem',
                                        fontWeight: 700,
                                        color: 'var(--text-primary)',
                                    }}>
                                        <Zap size={14} />
                                        ⚡ Traitement & Analyse IA
                                    </h3>

                                    <div className="form-group" style={{ padding: '0 16px', marginBottom: '12px' }}>
                                        <label style={{
                                            display: 'block',
                                            marginBottom: '4px',
                                            fontSize: '0.8rem',
                                            fontWeight: 600,
                                        }}>
                                            🧠 Modèle IA principal
                                        </label>
                                        <select
                                            className="select-control"
                                            value={activeModel}
                                            onChange={(e) => setActiveModel(e.target.value)}
                                            style={{
                                                width: '100%',
                                                padding: '8px 12px',
                                                borderRadius: 'var(--radius-sm)',
                                                background: 'var(--surface-secondary)',
                                                border: '1px solid var(--border-color)',
                                                color: 'var(--text-primary)',
                                                fontSize: '0.85rem',
                                            }}
                                        >
                                            {AI_MODELS.map((model) => (
                                                <option key={model.id} value={model.id}>
                                                    {model.label}
                                                    {model.isLocal ? ' 🏠' : ''}
                                                    {model.requiresPersonalKey ? ' 🔑' : ''}
                                                </option>
                                            ))}
                                        </select>
                                        {activeModelConfig && (
                                            <span style={{
                                                fontSize: '0.75rem',
                                                color: 'var(--text-muted)',
                                                display: 'block',
                                                marginTop: '4px',
                                            }}>
                                                {activeModelConfig.description}
                                            </span>
                                        )}
                                    </div>

                                    {/* Gestion dynamique des clés API (BYOK) */}
                                    <div style={{ padding: '0 16px', marginBottom: '12px' }}>
                                        <APIKeyManager compact />
                                    </div>
                                </div>

                                {/* Statut des modèles AI */}
                                <div className="sidebar-section">
                                    <h3 className="sidebar-section-title" style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                        padding: '12px 16px',
                                        fontSize: '0.85rem',
                                        fontWeight: 700,
                                        color: 'var(--text-primary)',
                                    }}>
                                        <Cpu size={14} />
                                        Modèles IA configurés
                                    </h3>
                                    <div style={{
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: '10px',
                                        fontSize: '0.85rem',
                                        padding: '0 16px 16px',
                                    }}>
                                        {AI_MODELS
                                            .filter((model) => {
                                                if (!model.requiresPersonalKey) return false;
                                                const keyConfig = apiKeys[model.provider];
                                                if (!keyConfig?.key || !keyConfig.isValid) return false;
                                                return modelStatus[model.id] === true;
                                            })
                                            .map((model) => (
                                                <div
                                                    key={model.id}
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'space-between',
                                                        padding: '8px 10px',
                                                        background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(16, 185, 129, 0.05))',
                                                        border: '1px solid rgba(16, 185, 129, 0.2)',
                                                        borderRadius: 'var(--radius-sm)',
                                                        fontWeight: 600,
                                                    }}
                                                >
                                                    <span style={{ color: 'var(--text-primary)' }}>
                                                        {model.label}
                                                    </span>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                        {getStatusIcon(true)}
                                                        <span style={{
                                                            color: '#2e7d32',
                                                            fontSize: '0.8rem',
                                                            fontWeight: '700',
                                                        }}>
                                                            En ligne
                                                        </span>
                                                    </div>
                                                </div>
                                            ))}

                                        {AI_MODELS.filter((model) => {
                                            if (!model.requiresPersonalKey) return false;
                                            const keyConfig = apiKeys[model.provider];
                                            return keyConfig?.key && keyConfig.isValid && modelStatus[model.id] === true;
                                        }).length === 0 && (
                                            <div style={{
                                                padding: '12px',
                                                background: 'var(--surface-secondary)',
                                                borderRadius: 'var(--radius-sm)',
                                                fontSize: '0.8rem',
                                                color: 'var(--text-muted)',
                                                textAlign: 'center',
                                            }}>
                                                <div style={{ marginBottom: '8px' }}>🔑</div>
                                                <div>Aucun modèle personnel configuré</div>
                                                <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>
                                                    Ajoutez une clé API pour utiliser Gemini, Mistral, etc.
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </React.Fragment>
                        )}

                        {/* History Tab */}
                        {activeTab === 'history' && (
                            <div className="sidebar-section">
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: '12px 16px',
                                    marginBottom: '8px',
                                }}>
                                    <h3 className="sidebar-section-title" style={{ margin: 0 }}>
                                        📋 Historique des recherches
                                    </h3>
                                    <div style={{ display: 'flex', gap: '4px' }}>
                                        {searchHistory?.length > 0 && onClearHistory && (
                                            <button
                                                onClick={onClearHistory}
                                                className="btn btn-secondary"
                                                style={{
                                                    padding: '4px 8px',
                                                    fontSize: '0.75rem',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '4px',
                                                    cursor: 'pointer',
                                                }}
                                                 title={S.clear_history}
                                            >
                                                <Trash2 size={12} /> Vider
                                            </button>
                                        )}
                                        {onClearCache && (
                                            <button
                                                onClick={onClearCache}
                                                className="btn btn-secondary"
                                                style={{
                                                    padding: '4px 8px',
                                                    fontSize: '0.75rem',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '4px',
                                                    cursor: 'pointer',
                                                }}
                                                 title={S.clear_results_cache}
                                            >
                                                <Trash2 size={12} /> Cache
                                            </button>
                                        )}
                                    </div>
                                </div>
                                {!searchHistory?.length ? (
                                    <p style={{
                                        fontSize: '0.85rem',
                                        color: 'var(--text-muted)',
                                        textAlign: 'center',
                                        padding: '16px',
                                    }}>
                                        Aucune recherche récente
                                    </p>
                                ) : (
                                    <div style={{
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: '8px',
                                        maxHeight: '300px',
                                        overflowY: 'auto',
                                        padding: '0 16px 16px',
                                    }}>
                                        {searchHistory.map((item, idx) => (
                                            <button
                                                key={idx}
                                                onClick={() => onSelectHistory(item.query)}
                                                style={{
                                                    padding: '8px 12px',
                                                    background: 'var(--glass-bg)',
                                                    border: '1px solid var(--border-color)',
                                                    borderRadius: 'var(--radius-sm)',
                                                    cursor: 'pointer',
                                                    textAlign: 'left',
                                                    fontSize: '0.85rem',
                                                    color: 'var(--text-primary)',
                                                    transition: 'all 0.2s',
                                                }}
                                                onMouseEnter={(e) => {
                                                    e.currentTarget.style.background = primaryColor;
                                                    e.currentTarget.style.color = 'white';
                                                }}
                                                onMouseLeave={(e) => {
                                                    e.currentTarget.style.background = 'var(--glass-bg)';
                                                    e.currentTarget.style.color = 'var(--text-primary)';
                                                }}
                                            >
                                                <div style={{ fontWeight: '600' }}>{item.query}</div>
                                                <div style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '2px' }}>
                                                    {new Date(item.time).toLocaleDateString('fr-FR')} - {item.count} résultats
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Saved Items Tab */}
                        {activeTab === 'saved' && (
                            <div className="sidebar-section">
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: '12px 16px',
                                    marginBottom: '8px',
                                }}>
                                    <h3 className="sidebar-section-title" style={{ margin: 0 }}>
                                        ⭐ Éléments sauvegardés
                                    </h3>
                                    {savedItems?.length > 0 && onClearSavedItems && (
                                        <button
                                            onClick={onClearSavedItems}
                                            className="btn btn-secondary"
                                            style={{
                                                padding: '4px 8px',
                                                fontSize: '0.75rem',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '4px',
                                                cursor: 'pointer',
                                            }}
                                             title={S.clear_saved_items}
                                        >
                                            <Trash2 size={12} /> Vider
                                        </button>
                                    )}
                                </div>
                                {!savedItems?.length ? (
                                    <p style={{
                                        fontSize: '0.85rem',
                                        color: 'var(--text-muted)',
                                        textAlign: 'center',
                                        padding: '16px',
                                    }}>
                                        Aucun élément sauvegardé
                                    </p>
                                ) : (
                                    <div style={{
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: '8px',
                                        maxHeight: '350px',
                                        overflowY: 'auto',
                                        padding: '0 16px 16px',
                                    }}>
                                        {savedItems.map((item, idx) => (
                                            <a
                                                key={idx}
                                                href={item.link}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                style={{
                                                    padding: '8px 12px',
                                                    background: 'var(--glass-bg)',
                                                    border: '1px solid var(--border-color)',
                                                    borderRadius: 'var(--radius-sm)',
                                                    textDecoration: 'none',
                                                    fontSize: '0.85rem',
                                                    color: 'var(--text-primary)',
                                                    display: 'block',
                                                    transition: 'all 0.2s',
                                                }}
                                                onMouseEnter={(e) => {
                                                    e.currentTarget.style.background = primaryColor;
                                                    e.currentTarget.style.color = 'white';
                                                }}
                                                onMouseLeave={(e) => {
                                                    e.currentTarget.style.background = 'var(--glass-bg)';
                                                    e.currentTarget.style.color = 'var(--text-primary)';
                                                }}
                                            >
                                                <div style={{ fontWeight: '600', fontSize: '0.8rem' }}>
                                                    {item.title}
                                                </div>
                                                <div style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '2px' }}>
                                                    {item.company || item.client || 'Non spécifié'}
                                                </div>
                                            </a>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* TJM Calculator Tab (Freelance only) */}
                        {activeTab === 'tjm' && activeAgent === 'freelance' && (
                            <div className="sidebar-section" style={{ padding: '16px' }}>
                                <h3 className="sidebar-section-title" style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    marginBottom: '16px',
                                    fontSize: '0.85rem',
                                    fontWeight: 700,
                                    color: 'var(--text-primary)',
                                }}>
                                    💰 Calculateur TJM
                                </h3>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                    <div className="form-group">
                                        <label style={{
                                            display: 'block',
                                            marginBottom: '4px',
                                            fontSize: '0.8rem',
                                            fontWeight: 600,
                                        }}>
                                            TJM minimum (€/jour)
                                        </label>
                                        <input
                                            type="number"
                                            className="input-control"
                                            placeholder="ex: 350"
                                            value={activeFilters.tjmMin || ''}
                                            onChange={(e) => updateFilter('tjmMin', e.target.value)}
                                            min="0"
                                            step="50"
                                            style={{
                                                width: '100%',
                                                padding: '8px 12px',
                                                borderRadius: 'var(--radius-sm)',
                                                background: 'var(--surface-secondary)',
                                                border: '1px solid var(--border-color)',
                                                color: 'var(--text-primary)',
                                                fontSize: '0.85rem',
                                            }}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label style={{
                                            display: 'block',
                                            marginBottom: '4px',
                                            fontSize: '0.8rem',
                                            fontWeight: 600,
                                        }}>
                                            TJM maximum (€/jour)
                                        </label>
                                        <input
                                            type="number"
                                            className="input-control"
                                            placeholder="ex: 800"
                                            value={activeFilters.tjmMax || ''}
                                            onChange={(e) => updateFilter('tjmMax', e.target.value)}
                                            min="0"
                                            step="50"
                                            style={{
                                                width: '100%',
                                                padding: '8px 12px',
                                                borderRadius: 'var(--radius-sm)',
                                                background: 'var(--surface-secondary)',
                                                border: '1px solid var(--border-color)',
                                                color: 'var(--text-primary)',
                                                fontSize: '0.85rem',
                                            }}
                                        />
                                    </div>
                                    <div style={{
                                        padding: '12px',
                                        background: 'rgba(0,0,0,0.03)',
                                        borderRadius: '10px',
                                        fontSize: '0.78rem',
                                        color: 'var(--text-muted)',
                                        lineHeight: '1.6',
                                    }}>
                                        💡 Analysez votre CV pour obtenir un TJM recommandé selon votre profil et les tendances du marché freelance.
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Salary Calculator Tab (Recruiter only) */}
                        {activeTab === 'salary' && activeAgent === 'recruiter' && (
                            <div className="sidebar-section" style={{ padding: '16px' }}>
                                <h3 className="sidebar-section-title" style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    marginBottom: '16px',
                                    fontSize: '0.85rem',
                                    fontWeight: 700,
                                    color: 'var(--text-primary)',
                                }}>
                                    💰 Calculateur de salaire
                                </h3>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                    <div className="form-group">
                                        <label style={{
                                            display: 'block',
                                            marginBottom: '4px',
                                            fontSize: '0.8rem',
                                            fontWeight: 600,
                                        }}>
                                            Salaire minimum (€/mois)
                                        </label>
                                        <input
                                            type="number"
                                            className="input-control"
                                            placeholder="ex: 2000"
                                            value={activeFilters.salaryMin || ''}
                                            onChange={(e) => updateFilter('salaryMin', e.target.value)}
                                            min="0"
                                            step="100"
                                            style={{
                                                width: '100%',
                                                padding: '8px 12px',
                                                borderRadius: 'var(--radius-sm)',
                                                background: 'var(--surface-secondary)',
                                                border: '1px solid var(--border-color)',
                                                color: 'var(--text-primary)',
                                                fontSize: '0.85rem',
                                            }}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label style={{
                                            display: 'block',
                                            marginBottom: '4px',
                                            fontSize: '0.8rem',
                                            fontWeight: 600,
                                        }}>
                                            Salaire maximum (€/mois)
                                        </label>
                                        <input
                                            type="number"
                                            className="input-control"
                                            placeholder="ex: 8000"
                                            value={activeFilters.salaryMax || ''}
                                            onChange={(e) => updateFilter('salaryMax', e.target.value)}
                                            min="0"
                                            step="100"
                                            style={{
                                                width: '100%',
                                                padding: '8px 12px',
                                                borderRadius: 'var(--radius-sm)',
                                                background: 'var(--surface-secondary)',
                                                border: '1px solid var(--border-color)',
                                                color: 'var(--text-primary)',
                                                fontSize: '0.85rem',
                                            }}
                                        />
                                    </div>
                                    <div style={{
                                        padding: '12px',
                                        background: 'rgba(0,0,0,0.03)',
                                        borderRadius: '10px',
                                        fontSize: '0.78rem',
                                        color: 'var(--text-muted)',
                                        lineHeight: '1.6',
                                    }}>
                                        💡 Analysez votre profil pour obtenir un salaire recommandé selon votre niveau d'expérience et les tendances du marché de l'emploi.
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Footer */}
                        <div className="sidebar-section" style={{
                            marginTop: 'auto',
                            paddingTop: '16px',
                            borderTop: '1px solid var(--border-color)',
                            padding: '16px',
                        }}>
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                            }}>
                                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                                    {agentConfig.title} v2.0
                                </span>
                                {onToggleDarkMode && (
                                    <button
                                        onClick={onToggleDarkMode}
                                         title={S.toggle_dark_mode}
                                        style={{
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer',
                                            padding: '4px',
                                            fontSize: '1.2rem',
                                        }}
                                    >
                                        🌓
                                    </button>
                                )}
                            </div>
                        </div>
                    </React.Fragment>
                ) : (
                    <div style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '16px',
                        marginTop: '16px',
                    }}>
                         <Globe size={20} style={{ color: 'var(--text-secondary)' }} title={S.language} />
                         <Zap size={20} style={{ color: 'var(--text-secondary)' }} title={S.ai_processing} />
                         <Key size={20} style={{ color: 'var(--text-secondary)' }} title={S.api_key} />
                         <Filter size={20} style={{ color: primaryColor }} title={S.filters} />
                    </div>
                )}
            </aside>
        </>
    );
}
