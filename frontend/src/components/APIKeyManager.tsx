/**
 * APIKeyManager - Composant réutilisable de gestion dynamique des clés API (BYOK)
 * 
 * Fonctionnalités :
 * - Champ de saisie de clé API dynamique selon le modèle sélectionné
 * - Lien "Obtenir une clé API" adapté automatiquement au fournisseur
 * - Basculement automatique clé partagée → clé personnelle
 * - Validation visuelle de la clé
 * - Réutilisable dans Sidebar, Hub Central, et les 3 agents
 */

import React, { useState, useEffect } from 'react';
import { Key, Save, ExternalLink, CheckCircle2, AlertCircle, X, Eye, EyeOff } from 'lucide-react';
import { useAI, AIProvider, PROVIDER_LABELS } from '../context/AIContext';

interface APIKeyManagerProps {
  /** Afficher en mode compact (pour les sidebars) */
  compact?: boolean;
  /** Callback quand une clé est sauvegardée */
  onKeySaved?: (provider: AIProvider, key: string) => void;
  /** Callback quand une clé est effacée */
  onKeyCleared?: (provider: AIProvider) => void;
  /** Style personnalisé */
  style?: React.CSSProperties;
}

export const APIKeyManager: React.FC<APIKeyManagerProps> = ({
  compact = false,
  onKeySaved,
  onKeyCleared,
  style,
}) => {
  const { activeModelConfig, apiKeys, setApiKey, clearApiKey, getApiKeyUrl, requiresApiKey, isUsingPersonalKey } = useAI();
  const [inputKey, setInputKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);

  // Mettre à jour l'input quand le modèle change
  useEffect(() => {
    if (activeModelConfig) {
      const existingKey = apiKeys[activeModelConfig.provider]?.key || '';
      setInputKey(existingKey);
      setSaved(!!existingKey);
    }
  }, [activeModelConfig, apiKeys]);

  // Si le modèle ne nécessite pas de clé, ne rien afficher
  if (!requiresApiKey || !activeModelConfig) {
    return (
      <div style={{
        padding: '12px',
        background: 'var(--bg-secondary)',
        borderRadius: 'var(--radius-sm)',
        fontSize: '0.85rem',
        color: 'var(--text-secondary)',
        ...style,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={16} style={{ color: 'var(--success-color)' }} />
          <span>
            {activeModelConfig?.isLocal 
              ? 'Modèle local - Aucune clé requise' 
              : 'Quota partagé de l\'application - Aucune clé requise'}
          </span>
        </div>
      </div>
    );
  }

  const provider = activeModelConfig.provider;
  const providerLabel = PROVIDER_LABELS[provider];
  const apiKeyUrl = getApiKeyUrl(provider);
  const currentKey = apiKeys[provider]?.key || '';
  const isKeyValid = apiKeys[provider]?.isValid;

  const handleSave = () => {
    if (inputKey.trim()) {
      setApiKey(provider, inputKey.trim());
      setSaved(true);
      onKeySaved?.(provider, inputKey.trim());
      setTimeout(() => setSaved(false), 2500);
    }
  };

  const handleClear = () => {
    clearApiKey(provider);
    setInputKey('');
    setSaved(false);
    onKeyCleared?.(provider);
  };

  return (
    <div style={{
      padding: compact ? '12px' : '16px',
      background: 'var(--glass-bg)',
      border: '1px solid var(--border-color)',
      borderRadius: 'var(--radius-md)',
      ...style,
    }}>
      {/* En-tête */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <Key size={16} style={{ color: 'var(--primary-color)' }} />
        <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
          Clé API {providerLabel}
        </span>
        {isUsingPersonalKey && (
          <span style={{
            fontSize: '0.7rem',
            padding: '2px 8px',
            background: 'var(--success-color)',
            color: 'white',
            borderRadius: '12px',
            fontWeight: 600,
          }}>
            ✓ Active
          </span>
        )}
      </div>

      {/* Description */}
      <p style={{
        fontSize: '0.8rem',
        color: 'var(--text-secondary)',
        margin: '0 0 12px 0',
      }}>
        {activeModelConfig.description}. Entrez votre clé personnelle pour utiliser ce modèle.
      </p>

      {/* Champ de saisie */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <input
            type={showKey ? 'text' : 'password'}
            className="input-control"
            style={{ width: '100%', paddingRight: '36px' }}
            placeholder={`Clé API ${providerLabel}...`}
            value={inputKey}
            onChange={(e) => {
              setInputKey(e.target.value);
              setSaved(false);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSave();
            }}
          />
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            style={{
              position: 'absolute',
              right: '8px',
              top: '50%',
              transform: 'translateY(-50%)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              padding: '4px',
            }}
            title={showKey ? 'Masquer' : 'Afficher'}
          >
            {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        <button
          className="btn btn-primary"
          style={{ padding: '8px 12px', flexShrink: 0 }}
          onClick={handleSave}
          disabled={!inputKey || !inputKey.trim()}
          title="Enregistrer la clé"
        >
          <Save size={16} />
        </button>
        {currentKey && (
          <button
            className="btn btn-secondary"
            style={{ padding: '8px 12px', flexShrink: 0 }}
            onClick={handleClear}
            title="Effacer la clé"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Statut de validation */}
      {saved && (
        <div style={{
          fontSize: '0.75rem',
          color: 'var(--success-color)',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          marginBottom: '8px',
        }}>
          <CheckCircle2 size={12} />
          Clé enregistrée - Basculement automatique activé
        </div>
      )}
      {currentKey && isKeyValid === false && (
        <div style={{
          fontSize: '0.75rem',
          color: 'var(--error-color)',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          marginBottom: '8px',
        }}>
          <AlertCircle size={12} />
          Clé invalide ou quota dépassé
        </div>
      )}

      {/* Lien d'obtention de clé - adapté au fournisseur */}
      {apiKeyUrl && (
        <a
          href={apiKeyUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            fontSize: '0.8rem',
            color: 'var(--primary-color)',
            textDecoration: 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <ExternalLink size={12} />
          Obtenir une clé API {providerLabel} gratuite
        </a>
      )}
    </div>
  );
};

export default APIKeyManager;