/**
 * Sidebar - Version refactorisée avec pipeline IA unifié
 * 
 * Changements :
 * - Regroupement "🔬 Analyse du CV" et "⚖️ Tri & Rédaction" en UN SEUL PIPELINE UNIFIÉ : "⚡ Traitement & Analyse IA"
 * - L'utilisateur choisit UN SEUL modèle actif
 * - Intégration du composant APIKeyManager pour la gestion dynamique des clés
 * - Interface claire et épurée
 */

import React, { useState, useEffect } from 'react';
import { LANGS, STRINGS } from '../utils/translations';
import { Settings, Cpu, Key, Globe, Save, ExternalLink, CheckCircle2, AlertCircle, ChevronLeft, ChevronRight, Wifi, WifiOff, Menu, X, Trash2, Zap } from 'lucide-react';
import { useAI } from '../context/AIContext';
import { AI_MODELS } from '../config/aiProviders';
import { APIKeyManager } from './APIKeyManager';

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function Sidebar({
  lang,
  setLang,
  ollamaOnline,
  searchHistory,
  savedJobs,
  onSelectHistory,
  onToggleDarkMode,
  onClearHistory,
  onClearSavedJobs,
  onClearCache
}) {
  const S = STRINGS[LANGS[lang].code];
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('settings');

  // Utiliser le contexte AI centralisé
  const { activeModel, setActiveModel, activeModelConfig, modelStatus, refreshModelStatus, apiKeys } = useAI();

  const fetchStatus = async () => {
    await refreshModelStatus();
  };

  // Fetch model status on mount
  useEffect(() => {
    fetchStatus();
  }, [refreshModelStatus]);

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
    return isAvailable ? 
      <CheckCircle2 size={14} style={{ color: 'var(--success-color)' }} /> : 
      <AlertCircle size={14} style={{ color: 'var(--error-color)' }} />;
  };

  const getStatusText = (isAvailable) => {
    if (!isAvailable) return 'Hors ligne';
    return 'En ligne';
  };

  const closeMobile = () => setMobileOpen(false);

  return (
    <>
      {/* Mobile hamburger toggle button */}
      <button
        className="sidebar-toggle-mobile"
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle sidebar"
        title={mobileOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
      >
        {mobileOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Mobile overlay backdrop */}
      {mobileOpen && (
        <div className="sidebar-overlay" onClick={closeMobile} />
      )}

      <aside
        className={`sidebar ${mobileOpen ? 'open' : ''}`}
        style={{ width: collapsed ? '60px' : '320px', transition: 'width 0.3s ease' }}
      >
      <div className="sidebar-logo" style={{ justifyContent: collapsed ? 'center' : 'space-between', padding: collapsed ? '16px 0' : '16px' }}>
        {!collapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings size={24} className="text-primary" />
            <span>Find my job AI</span>
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
            justifyContent: 'center'
          }}
          title={collapsed ? 'Développer' : 'Réduire'}
        >
          {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>

      {!collapsed ? (
        <React.Fragment>
          {/* Tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', marginBottom: '8px' }}>
            <button
              onClick={() => setActiveTab('settings')}
              style={{
                flex: 1,
                padding: '8px',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'settings' ? '2px solid var(--primary-color)' : 'none',
                color: activeTab === 'settings' ? 'var(--primary-color)' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem'
              }}
            >
              ⚙️
            </button>
            <button
              onClick={() => setActiveTab('history')}
              style={{
                flex: 1,
                padding: '8px',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'history' ? '2px solid var(--primary-color)' : 'none',
                color: activeTab === 'history' ? 'var(--primary-color)' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem',
                position: 'relative'
              }}
            >
              📋
              {searchHistory.length > 0 && (
                <span style={{
                  position: 'absolute',
                  top: '4px',
                  right: '8px',
                  background: 'var(--primary-color)',
                  color: 'white',
                  borderRadius: '50%',
                  width: '16px',
                  height: '16px',
                  fontSize: '0.7rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  {searchHistory.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('saved')}
              style={{
                flex: 1,
                padding: '8px',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'saved' ? '2px solid var(--primary-color)' : 'none',
                color: activeTab === 'saved' ? 'var(--primary-color)' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem',
                position: 'relative'
              }}
            >
              ⭐
              {savedJobs.length > 0 && (
                <span style={{
                  position: 'absolute',
                  top: '4px',
                  right: '8px',
                  background: 'var(--primary-color)',
                  color: 'white',
                  borderRadius: '50%',
                  width: '16px',
                  height: '16px',
                  fontSize: '0.7rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  {savedJobs.length}
                </span>
              )}
            </button>
          </div>

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <React.Fragment>
              {/* Language Section */}
              <div className="sidebar-section">
                <h3 className="sidebar-section-title">
                  <Globe size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                  Language
                </h3>
                <div className="form-group">
                  <select
                    className="select-control"
                    value={lang}
                    onChange={(e) => setLang(e.target.value)}
                  >
                    {Object.keys(LANGS).map((key) => (
                      <option key={key} value={key}>
                        {key}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* ⚡ PIPELINE IA UNIFIÉ - Traitement & Analyse IA */}
              <div className="sidebar-section">
                <h3 className="sidebar-section-title">
                  <Zap size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                  ⚡ Traitement & Analyse IA
                </h3>
                
                <div className="form-group" style={{ marginBottom: '12px' }}>
                  <label>🧠 Modèle IA principal</label>
                  <select
                    className="select-control"
                    value={activeModel}
                    onChange={(e) => setActiveModel(e.target.value)}
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
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginTop: '4px' }}>
                      {activeModelConfig.description}
                    </span>
                  )}
                </div>

                {/* Gestion dynamique des clés API (BYOK) */}
                <APIKeyManager compact />
              </div>

              {/* Statut des modèles AI */}
              <div className="sidebar-section">
                <h3 className="sidebar-section-title">
                  <Cpu size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                  Modèles IA configurés
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem' }}>
                  {/* Afficher uniquement les modèles avec clé personnelle ET en ligne */}
                  {AI_MODELS
                    .filter(model => {
                      // Ne montrer que les modèles qui nécessitent une clé personnelle
                      if (!model.requiresPersonalKey) return false;
                      
                      // Vérifier que la clé existe et est valide
                      const keyConfig = apiKeys[model.provider];
                      if (!keyConfig?.key || !keyConfig.isValid) return false;
                      
                      // Vérifier que le modèle est en ligne
                      return modelStatus[model.id] === true;
                    })
                    .map((model) => (
                      <div key={model.id} style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'space-between', 
                        padding: '8px 10px', 
                        background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(16, 185, 129, 0.05))',
                        border: '1px solid rgba(16, 185, 129, 0.2)',
                        borderRadius: 'var(--radius-sm)',
                        fontWeight: 600,
                      }}>
                        <span style={{ color: 'var(--text-primary)' }}>
                          {model.label}
                        </span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          {getStatusIcon(true)}
                          <span style={{ 
                            color: '#2e7d32', 
                            fontSize: '0.8rem', 
                            fontWeight: '700' 
                          }}>
                            En ligne
                          </span>
                        </div>
                      </div>
                    ))}
                  
                   {/* Message si aucun modèle configuré */}
                  {AI_MODELS.filter(model => {
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
                        Ajoutez une clé API pour utiliser Gemini, OpenAI, etc.
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
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h3 className="sidebar-section-title" style={{ margin: 0 }}>
                  📋 Historique des recherches
                </h3>
                <div style={{ display: 'flex', gap: '4px' }}>
                  {searchHistory.length > 0 && onClearHistory && (
                    <button
                      onClick={onClearHistory}
                      className="btn btn-secondary"
                      style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}
                      title="Vider l'historique"
                    >
                      <Trash2 size={12} /> Vider
                    </button>
                  )}
                  {onClearCache && (
                    <button
                      onClick={onClearCache}
                      className="btn btn-secondary"
                      style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}
                      title="Vider le cache des résultats"
                    >
                      <Trash2 size={12} /> Cache
                    </button>
                  )}
                </div>
              </div>
              {searchHistory.length === 0 ? (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                  Aucune recherche récente
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflowY: 'auto' }}>
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
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--primary-color)';
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

          {/* Saved Jobs Tab */}
          {activeTab === 'saved' && (
            <div className="sidebar-section">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h3 className="sidebar-section-title" style={{ margin: 0 }}>
                  ⭐ Offres sauvegardées
                </h3>
                {savedJobs.length > 0 && onClearSavedJobs && (
                  <button
                    onClick={onClearSavedJobs}
                    className="btn btn-secondary"
                    style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}
                    title="Vider les annonces sauvegardées"
                  >
                    <Trash2 size={12} /> Vider
                  </button>
                )}
              </div>
              {savedJobs.length === 0 ? (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                  Aucune offre sauvegardée
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflowY: 'auto' }}>
                  {savedJobs.map((job, idx) => (
                    <a
                      key={idx}
                      href={job.link}
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
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--primary-color)';
                        e.currentTarget.style.color = 'white';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'var(--glass-bg)';
                        e.currentTarget.style.color = 'var(--text-primary)';
                      }}
                    >
                      <div style={{ fontWeight: '600', fontSize: '0.8rem' }}>{job.title}</div>
                      <div style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '2px' }}>
                        {job.company}
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="sidebar-section" style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Find my work AI v2.0</span>
              {onToggleDarkMode && (
                <button
                  onClick={onToggleDarkMode}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '4px',
                    fontSize: '1.2rem',
                    title: 'Basculer mode sombre/clair'
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
          marginTop: '16px'
        }}>
          <Globe size={20} style={{ color: 'var(--text-secondary)' }} title="Language" />
          <Zap size={20} style={{ color: 'var(--text-secondary)' }} title="Traitement & Analyse IA" />
          <Key size={20} style={{ color: 'var(--text-secondary)' }} title="Clé API" />
        </div>
      )}
    </aside>
    </>
  );
}