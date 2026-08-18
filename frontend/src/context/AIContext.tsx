/**
 * AIContext - Contexte centralisé pour la gestion des modèles IA et clés API
 * 
 * Version BYOK Universelle :
 * - Démarrage par défaut sur Groq / Qwen 3.6 27B (clé partagée)
 * - Support de tous les grands fournisseurs : Groq, Gemini, OpenAI, Anthropic, DeepSeek, Mistral...
 * - Propagation globale de la clé à toute l'application
 * - Basculement automatique clé partagée → clé personnelle
 * - Mapping dynamique des URLs d'obtention de clés
 * - Persistance locale des clés
 * 
 * Supprime définitivement le support des modèles locaux (Ollama, Llama local, Qwen local).
 */

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import {
  AI_MODELS,
  DEFAULT_MODEL_ID,
  getModelById,
  getApiKeyUrl,
} from '../config/aiProviders';

// =============================================================================
// TYPES
// =============================================================================

export type AIProvider = 'groq' | 'gemini' | 'openai' | 'anthropic' | 'deepseek' | 'mistral' | 'cohere' | 'perplexity' | 'xai';

export interface AIModelConfig {
  id: string;
  label: string;
  provider: AIProvider;
  requiresPersonalKey: boolean;
  description: string;
  apiKeyUrl: string;
}

export interface APIKeyConfig {
  provider: AIProvider;
  key: string;
  isValid: boolean;
  lastValidated: number | null;
}

export interface AIContextValue {
  activeModel: string;
  setActiveModel: (modelId: string) => void;
  activeModelConfig: AIModelConfig | null;
  apiKeys: Record<string, APIKeyConfig>;
  setApiKey: (provider: AIProvider, key: string) => void;
  clearApiKey: (provider: AIProvider) => void;
  getActiveApiKey: () => string | null;
  modelStatus: Record<string, boolean>;
  refreshModelStatus: () => Promise<void>;
  getApiKeyUrl: (provider: AIProvider) => string;
  isUsingPersonalKey: boolean;
  requiresApiKey: boolean;
  activeProvider: AIProvider | null;
}

// =============================================================================
// CONTEXTE
// =============================================================================

const AIContext = createContext<AIContextValue | undefined>(undefined);

const API_BASE = import.meta.env.VITE_API_URL || '';

// Module-level flag to prevent multiple failed requests when backend is down
let _backendDown = false;
let _backendDownResetTimer: ReturnType<typeof setTimeout> | null = null;

const encryptKey = (key: string): string => {
  try { return btoa(encodeURIComponent(key)); } catch { return key; }
};

const decryptKey = (encrypted: string): string => {
  try { return decodeURIComponent(atob(encrypted)); } catch { return encrypted; }
};

export const AIProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [activeModel, setActiveModelState] = useState<string>(() => {
    return localStorage.getItem('ai_active_model') || DEFAULT_MODEL_ID;
  });

  const [apiKeys, setApiKeysState] = useState<Record<string, APIKeyConfig>>(() => {
    const providers: AIProvider[] = ['groq', 'gemini', 'openai', 'anthropic', 'deepseek', 'mistral', 'cohere', 'perplexity', 'xai'];
    const defaults: Record<string, APIKeyConfig> = {};
    providers.forEach(p => {
      defaults[p] = { provider: p, key: '', isValid: false, lastValidated: null };
    });
    try {
      const savedKeys = localStorage.getItem('ai_api_keys');
      if (savedKeys) {
        const parsed = JSON.parse(savedKeys);
        Object.keys(parsed).forEach((provider) => {
          if (defaults[provider] && parsed[provider].key) {
            defaults[provider].key = decryptKey(parsed[provider].key);
            defaults[provider].isValid = parsed[provider].isValid || false;
            defaults[provider].lastValidated = parsed[provider].lastValidated || null;
          }
        });
      }
    } catch (e) {
      console.error('[AIContext] Failed to load API keys:', e);
    }
    return defaults;
  });

  const [modelStatus, setModelStatus] = useState<Record<string, boolean>>({});

  const activeModelConfig = getModelById(activeModel) || null;
  const activeProvider = activeModelConfig?.provider || null;
  const requiresApiKey = activeModelConfig?.requiresPersonalKey || false;

  const setActiveModel = useCallback((modelId: string) => {
    setActiveModelState(modelId);
    localStorage.setItem('ai_active_model', modelId);
    console.log('[AIContext] Active model changed to:', modelId);
  }, []);

  const persistApiKeys = useCallback((keys: Record<string, APIKeyConfig>) => {
    try {
      const toSave: Record<string, any> = {};
      Object.keys(keys).forEach((p) => {
        if (keys[p].key) {
          toSave[p] = {
            key: encryptKey(keys[p].key),
            isValid: keys[p].isValid,
            lastValidated: keys[p].lastValidated,
          };
        }
      });
      localStorage.setItem('ai_api_keys', JSON.stringify(toSave));
    } catch (e) {
      console.error('[AIContext] Failed to persist API keys:', e);
    }
  }, []);

  const setApiKey = useCallback((provider: AIProvider, key: string) => {
    setApiKeysState(prev => {
      const updated = { ...prev, [provider]: { provider, key, isValid: false, lastValidated: null } };
      persistApiKeys(updated);
      return updated;
    });
  }, [persistApiKeys]);

  const clearApiKey = useCallback((provider: AIProvider) => {
    setApiKeysState(prev => {
      const updated = { ...prev, [provider]: { provider, key: '', isValid: false, lastValidated: null } };
      persistApiKeys(updated);
      return updated;
    });
  }, [persistApiKeys]);

  const getActiveApiKey = useCallback((): string | null => {
    if (!activeProvider) return null;
    const keyConfig = apiKeys[activeProvider];
    return keyConfig?.key || null;
  }, [activeProvider, apiKeys]);

  const isUsingPersonalKey = useCallback((): boolean => {
    if (!requiresApiKey) return false;
    return !!getActiveApiKey();
  }, [requiresApiKey, getActiveApiKey]);

  const refreshModelStatus = useCallback(async () => {
    // Skip request if backend is known to be down (prevents console spam)
    if (_backendDown) return;

    try {
      const geminiKey = apiKeys.gemini.key;
      const keyParam = geminiKey?.trim() ? '?custom_gemini_key=' + encodeURIComponent(geminiKey.trim()) : '';
      const response = await fetch(API_BASE + '/api/ai/status' + keyParam);
      if (response.ok) {
        // Backend is up - reset the flag
        _backendDown = false;
        if (_backendDownResetTimer) {
          clearTimeout(_backendDownResetTimer);
          _backendDownResetTimer = null;
        }
        const data = await response.json();
        const newStatus: Record<string, boolean> = {};
        if (data.groq) {
          newStatus['Groq / Qwen 3.6 27B'] = !!data.groq.online;
          newStatus['Groq / DeepSeek R1'] = !!data.groq.online;
          newStatus['Groq / Qwen 3 8B'] = !!data.groq.online;
        }
        if (data.gemini) {
          newStatus['Gemini 3.5 Pro'] = !!data.gemini.online;
          newStatus['Gemini 2.5 Pro'] = !!data.gemini.online;
          newStatus['Gemini 2.5 Flash'] = !!data.gemini.online;
        }
        setModelStatus(newStatus);
        if (geminiKey && data.gemini) {
          setApiKeysState(prev => ({
            ...prev,
            gemini: { ...prev.gemini, isValid: !!data.gemini.online, lastValidated: Date.now() },
          }));
        }
      }
    } catch (error) {
      // Silently handle connection errors when backend is not running
      if (error instanceof TypeError && error.message.includes('fetch')) {
        // Set flag to prevent further requests until backend is back
        _backendDown = true;
        // Reset after 30 seconds to allow retry when backend comes back
        if (_backendDownResetTimer) clearTimeout(_backendDownResetTimer);
        _backendDownResetTimer = setTimeout(() => { _backendDown = false; }, 30000);
        // Only log once per session
        if (!sessionStorage.getItem('ai_backend_down_logged')) {
          console.warn('[AIContext] Backend not reachable. Start the backend with: start_backend.bat');
          sessionStorage.setItem('ai_backend_down_logged', '1');
        }
      } else {
        console.error('[AIContext] Failed to refresh model status:', error);
      }
    }
  }, [apiKeys.gemini.key]);

  useEffect(() => { refreshModelStatus(); }, [refreshModelStatus]);

  useEffect(() => {
    if (activeModelConfig?.requiresPersonalKey && activeProvider) {
      const keyConfig = apiKeys[activeProvider];
      if (keyConfig?.key && !keyConfig.isValid) {
        refreshModelStatus();
      }
    }
  }, [activeModel, activeModelConfig, activeProvider, apiKeys, refreshModelStatus]);

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
    requiresApiKey,
    activeProvider,
  };

  return React.createElement(AIContext.Provider, { value }, children);
};

export const useAI = (): AIContextValue => {
  const context = useContext(AIContext);
  if (!context) {
    throw new Error('useAI must be used within an AIProvider');
  }
  return context;
};

export default AIContext;