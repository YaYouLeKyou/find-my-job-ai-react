/**
 * AIContext - Contexte centralisé pour la gestion des modèles IA et clés API
 * 
 * Fonctionnalités :
 * - Modèle IA unique unifié (pipeline unifié)
 * - Gestion dynamique des clés API multi-fournisseurs (BYOK)
 * - Basculement automatique clé partagée → clé personnelle
 * - Mapping dynamique des URLs d'obtention de clés
 * - Persistance locale chiffrée des clés
 * - Synchronisation globale (Sidebar, Hub, 3 agents)
 */

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

// =============================================================================
// TYPES & INTERFACES
// =============================================================================

export type AIProvider = 'groq' | 'gemini' | 'openai' | 'anthropic' | 'ollama' | 'xai';

export interface AIModel {
  id: string;
  label: string;
  provider: AIProvider;
  requiresPersonalKey: boolean;
  description: string;
  isLocal?: boolean;
}

export interface APIKeyConfig {
  provider: AIProvider;
  key: string;
  isValid: boolean;
  lastValidated: number | null;
}

export interface AIContextValue {
  // Modèle IA unifié
  activeModel: string;
  setActiveModel: (modelId: string) => void;
  activeModelConfig: AIModel | null;
  
  // Clés API
  apiKeys: Record<AIProvider, APIKeyConfig>;
  setApiKey: (provider: AIProvider, key: string) => void;
  clearApiKey: (provider: AIProvider) => void;
  getActiveApiKey: () => string | null;
  
  // Statut des modèles
  modelStatus: Record<string, boolean>;
  refreshModelStatus: () => Promise<void>;
  
  // URLs d'obtention de clés
  getApiKeyUrl: (provider: AIProvider) => string;
  
  // Helpers
  isUsingPersonalKey: boolean;
  requiresApiKey: boolean;
}

// =============================================================================
// CONSTANTES - Modèles IA disponibles
// =============================================================================

export const AI_MODELS: AIModel[] = [
  {
    id: 'Groq / Llama 3.3',
    label: 'Groq / Llama 3.3',
    provider: 'groq',
    requiresPersonalKey: false,
    description: 'Ultra-rapide, quota partagé de l\'application',
  },
  {
    id: 'Gemini 3.5',
    label: 'Gemini 3.5',
    provider: 'gemini',
    requiresPersonalKey: true,
    description: 'Modèle Google haute performance',
  },
  {
    id: 'Gemini 2.5',
    label: 'Gemini 2.5',
    provider: 'gemini',
    requiresPersonalKey: true,
    description: 'Modèle Google équilibré',
  },
  {
    id: 'Llama 3.2 (Local/dev)',
    label: 'Llama 3.2 (Local/dev)',
    provider: 'ollama',
    requiresPersonalKey: false,
    description: 'Modèle local via Ollama',
    isLocal: true,
  },
  {
    id: 'Llama 3.2 Vision (Local/dev)',
    label: 'Llama 3.2 Vision (Local/dev)',
    provider: 'ollama',
    requiresPersonalKey: false,
    description: 'Modèle local vision via Ollama',
    isLocal: true,
  },
  {
    id: 'Qwen 3 4B (Local/dev)',
    label: 'Qwen 3 4B (Local/dev)',
    provider: 'ollama',
    requiresPersonalKey: false,
    description: 'Modèle local léger via Ollama',
    isLocal: true,
  },
];

// Mapping dynamique des URLs d'obtention de clés API
export const API_KEY_URLS: Record<AIProvider, string> = {
  gemini: 'https://aistudio.google.com/app/apikey',
  groq: 'https://console.groq.com/keys',
  openai: 'https://platform.openai.com/api-keys',
  anthropic: 'https://console.anthropic.com/settings/keys',
  xai: 'https://console.x.ai/',
  ollama: '', // Local, pas de clé nécessaire
};

// Labels des fournisseurs pour l'affichage
export const PROVIDER_LABELS: Record<AIProvider, string> = {
  gemini: 'Google Gemini',
  groq: 'Groq',
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  xai: 'xAI (Grok)',
  ollama: 'Ollama (Local)',
};

// =============================================================================
// CONTEXTE
// =============================================================================

const AIContext = createContext<AIContextValue | undefined>(undefined);

const API_BASE = import.meta.env.VITE_API_URL || '';

// Chiffrement simple pour le stockage local (Base64 + obfuscation)
const encryptKey = (key: string): string => {
  try {
    return btoa(encodeURIComponent(key));
  } catch {
    return key;
  }
};

const decryptKey = (encrypted: string): string => {
  try {
    return decodeURIComponent(atob(encrypted));
  } catch {
    return encrypted;
  }
};

export const AIProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Modèle IA actif (par défaut: Groq / Llama 3.3 sur quota partagé)
  const [activeModel, setActiveModelState] = useState<string>(() => {
    return localStorage.getItem('ai_active_model') || 'Groq / Llama 3.3';
  });

  // Clés API stockées par fournisseur
  const [apiKeys, setApiKeys] = useState<Record<AIProvider, APIKeyConfig>>(() => {
    const defaultKeys: Record<AIProvider, APIKeyConfig> = {
      groq: { provider: 'groq', key: '', isValid: false, lastValidated: null },
      gemini: { provider: 'gemini', key: '', isValid: false, lastValidated: null },
      openai: { provider: 'openai', key: '', isValid: false, lastValidated: null },
      anthropic: { provider: 'anthropic', key: '', isValid: false, lastValidated: null },
      xai: { provider: 'xai', key: '', isValid: false, lastValidated: null },
      ollama: { provider: 'ollama', key: '', isValid: false, lastValidated: null },
    };

    // Charger les clés sauvegardées
    try {
      const savedKeys = localStorage.getItem('ai_api_keys');
      if (savedKeys) {
        const parsed = JSON.parse(savedKeys);
        Object.keys(parsed).forEach((provider) => {
          if (defaultKeys[provider as AIProvider] && parsed[provider].key) {
            defaultKeys[provider as AIProvider].key = decryptKey(parsed[provider].key);
            defaultKeys[provider as AIProvider].isValid = parsed[provider].isValid || false;
            defaultKeys[provider as AIProvider].lastValidated = parsed[provider].lastValidated || null;
          }
        });
      }
    } catch (e) {
      console.error('[AIContext] Failed to load API keys:', e);
    }

    return defaultKeys;
  });

  // Statut des modèles (en ligne/hors ligne)
  const [modelStatus, setModelStatus] = useState<Record<string, boolean>>({});

  // Configuration du modèle actif
  const activeModelConfig = AI_MODELS.find(m => m.id === activeModel) || null;

  // =============================================================================
  // PERSISTANCE
  // =============================================================================

  // Sauvegarder le modèle actif
  const setActiveModel = useCallback((modelId: string) => {
    setActiveModelState(modelId);
    localStorage.setItem('ai_active_model', modelId);
    console.log(`[AIContext] Active model changed to: ${modelId}`);
  }, []);

  // Sauvegarder une clé API
  const setApiKey = useCallback((provider: AIProvider, key: string) => {
    setApiKeys(prev => {
      const updated = {
        ...prev,
        [provider]: {
          provider,
          key,
          isValid: false,
          lastValidated: null,
        },
      };

      // Persister chiffré
      try {
        const toSave: Record<string, any> = {};
        Object.keys(updated).forEach((p) => {
          if (updated[p as AIProvider].key) {
            toSave[p] = {
              key: encryptKey(updated[p as AIProvider].key),
              isValid: updated[p as AIProvider].isValid,
              lastValidated: updated[p as AIProvider].lastValidated,
            };
          }
        });
        localStorage.setItem('ai_api_keys', JSON.stringify(toSave));
      } catch (e) {
        console.error('[AIContext] Failed to save API key:', e);
      }

      return updated;
    });
  }, []);

  // Effacer une clé API
  const clearApiKey = useCallback((provider: AIProvider) => {
    setApiKeys(prev => {
      const updated = {
        ...prev,
        [provider]: { provider, key: '', isValid: false, lastValidated: null },
      };

      // Mettre à jour le stockage
      try {
        const toSave: Record<string, any> = {};
        Object.keys(updated).forEach((p) => {
          if (updated[p as AIProvider].key) {
            toSave[p] = {
              key: encryptKey(updated[p as AIProvider].key),
              isValid: updated[p as AIProvider].isValid,
              lastValidated: updated[p as AIProvider].lastValidated,
            };
          }
        });
        localStorage.setItem('ai_api_keys', JSON.stringify(toSave));
      } catch (e) {
        console.error('[AIContext] Failed to clear API key:', e);
      }

      return updated;
    });
  }, []);

  // =============================================================================
  // HELPERS
  // =============================================================================

  // Obtenir la clé API active selon le modèle sélectionné
  const getActiveApiKey = useCallback((): string | null => {
    if (!activeModelConfig) return null;
    
    const provider = activeModelConfig.provider;
    const keyConfig = apiKeys[provider];
    
    if (keyConfig && keyConfig.key) {
      return keyConfig.key;
    }
    
    return null;
  }, [activeModelConfig, apiKeys]);

  // Vérifier si on utilise une clé personnelle
  const isUsingPersonalKey = useCallback((): boolean => {
    if (!activeModelConfig) return false;
    if (!activeModelConfig.requiresPersonalKey) return false;
    
    const key = getActiveApiKey();
    return !!key;
  }, [activeModelConfig, getActiveApiKey]);

  // Vérifier si le modèle actif nécessite une clé API
  const requiresApiKey = useCallback((): boolean => {
    if (!activeModelConfig) return false;
    return activeModelConfig.requiresPersonalKey;
  }, [activeModelConfig]);

  // Obtenir l'URL d'obtention de clé pour un fournisseur
  const getApiKeyUrl = useCallback((provider: AIProvider): string => {
    return API_KEY_URLS[provider] || '';
  }, []);

  // =============================================================================
  // VALIDATION DES CLÉS
  // =============================================================================

  const refreshModelStatus = useCallback(async () => {
    try {
      const geminiKey = apiKeys.gemini.key;
      const keyParam = geminiKey?.trim() ? `?custom_gemini_key=${encodeURIComponent(geminiKey.trim())}` : '';
      
      const response = await fetch(`${API_BASE}/api/ai/status${keyParam}`);
      
      if (response.ok) {
        const data = await response.json();
        const newStatus: Record<string, boolean> = {
          'Groq / Llama 3.3': !!data.groq?.online,
          'Gemini 3.5': !!data.gemini?.online,
          'Gemini 2.5': !!data.gemini?.online,
          'Llama 3.2 (Local/dev)': !!data.ollama?.online,
          'Llama 3.2 Vision (Local/dev)': !!data.ollama?.online,
          'Qwen 3 4B (Local/dev)': !!data.ollama?.online,
        };
        
        setModelStatus(newStatus);

        // Mettre à jour la validité des clés
        if (geminiKey && data.gemini) {
          setApiKeys(prev => ({
            ...prev,
            gemini: {
              ...prev.gemini,
              isValid: !!data.gemini.online,
              lastValidated: Date.now(),
            },
          }));
        }
      }
    } catch (error) {
      console.error('[AIContext] Failed to refresh model status:', error);
    }
  }, [apiKeys.gemini.key]);

  // =============================================================================
  // EFFETS
  // =============================================================================

  // Rafraîchir le statut au montage et quand les clés changent
  useEffect(() => {
    refreshModelStatus();
  }, [refreshModelStatus]);

  // Auto-basculement : si le modèle nécessite une clé et qu'on en a une valide, on l'utilise
  useEffect(() => {
    if (activeModelConfig && activeModelConfig.requiresPersonalKey) {
      const provider = activeModelConfig.provider;
      const keyConfig = apiKeys[provider];
      
      if (keyConfig && keyConfig.key && !keyConfig.isValid) {
        // Re-valider la clé
        refreshModelStatus();
      }
    }
  }, [activeModel, activeModelConfig, apiKeys, refreshModelStatus]);

  // =============================================================================
  // VALEUR DU CONTEXTE
  // =============================================================================

  const value: AIContextValue = {
    activeModel,
    setActiveModel,
    activeModelConfig,
    apiKeys,
    setApiKey,
    clearApiKey,
    getActiveApiKey,
    modelStatus,
    refreshModelStatus,
    getApiKeyUrl,
    isUsingPersonalKey: isUsingPersonalKey(),
    requiresApiKey: requiresApiKey(),
  };

  return <AIContext.Provider value={value}>{children}</AIContext.Provider>;
};

// =============================================================================
// HOOK
// =============================================================================

export const useAI = (): AIContextValue => {
  const context = useContext(AIContext);
  if (!context) {
    throw new Error('useAI must be used within an AIProvider');
  }
  return context;
};

export default AIContext;