/**
 * unifiedLLMService.js - Service LLM unifié (Unified Adapter Pattern)
 * 
 * Route dynamiquement chaque requête IA vers le bon SDK / endpoint d'API :
 * - Groq par défaut (clé partagée de l'application)
 * - Google Gemini, OpenAI, Anthropic, DeepSeek, Mistral si clé BYOK fournie
 * 
 * Supprime définitivement le support des modèles locaux (Ollama).
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// =============================================================================
// CONFIGURATION DES ENDPOINTS PAR FOURNISSEUR
// =============================================================================

const PROVIDER_ENDPOINTS = {
    groq: {
        baseUrl: 'https://api.groq.com/openai/v1',
        modelMap: {
            'Groq / Llama 3.3 70B': 'llama-3.3-70b-versatile',
            'Groq / DeepSeek R1': 'deepseek-r1-distill-llama-70b',
            'Groq / Llama 3.1 8B': 'llama-3.1-8b-instant',
        },
        defaultModel: 'llama-3.3-70b-versatile',
    },
    gemini: {
        baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
        modelMap: {
            'Gemini 3.5 Pro': 'gemini-1.5-pro',
            'Gemini 2.5 Pro': 'gemini-2.0-pro-exp',
            'Gemini 2.5 Flash': 'gemini-2.0-flash',
        },
        defaultModel: 'gemini-1.5-pro',
    },
    openai: {
        baseUrl: 'https://api.openai.com/v1',
        modelMap: {
            'OpenAI / GPT-4o': 'gpt-4o',
            'OpenAI / GPT-4o-mini': 'gpt-4o-mini',
            'OpenAI / o1': 'o1',
            'OpenAI / o3-mini': 'o3-mini',
        },
        defaultModel: 'gpt-4o',
    },
    anthropic: {
        baseUrl: 'https://api.anthropic.com/v1',
        modelMap: {
            'Anthropic / Claude 3.5 Sonnet': 'claude-3-5-sonnet-20241022',
            'Anthropic / Claude 3.5 Haiku': 'claude-3-5-haiku-20241022',
        },
        defaultModel: 'claude-3-5-sonnet-20241022',
    },
    deepseek: {
        baseUrl: 'https://api.deepseek.com/v1',
        modelMap: {
            'DeepSeek / V3': 'deepseek-chat',
            'DeepSeek / R1': 'deepseek-reasoner',
        },
        defaultModel: 'deepseek-chat',
    },
    mistral: {
        baseUrl: 'https://api.mistral.ai/v1',
        modelMap: {
            'Mistral / Large': 'mistral-large-latest',
            'Mistral / Codestral': 'codestral-latest',
            'Mistral / Pixtral': 'pixtral-large-latest',
        },
        defaultModel: 'mistral-large-latest',
    },
};

// =============================================================================
// SERVICE LLM UNIFIÉ
// =============================================================================

class UnifiedLLMService {
    constructor() {
        this._activeModel = 'Groq / Llama 3.3 70B';
        this._apiKeys = {};
    }

    /**
     * Initialise le service avec le contexte AI
     * @param {Object} aiContext - Contexte AI (useAI())
     */
    init(aiContext) {
        this._activeModel = aiContext.activeModel;
        this._apiKeys = aiContext.apiKeys;
    }

    /**
     * Met à jour la configuration
     * @param {Object} config
     */
    updateConfig(config) {
        if (config.activeModel) this._activeModel = config.activeModel;
        if (config.apiKeys) this._apiKeys = config.apiKeys;
    }

    /**
     * Récupère la configuration du fournisseur actif
     */
    _getActiveProviderConfig() {
        const modelId = this._activeModel;
        for (const [provider, config] of Object.entries(PROVIDER_ENDPOINTS)) {
            if (config.modelMap[modelId] || config.defaultModel) {
                return {
                    provider,
                    modelName: config.modelMap[modelId] || config.defaultModel,
                    baseUrl: config.baseUrl,
                    apiKey: this._apiKeys[provider]?.key || null,
                    isDefault: provider === 'groq' && !this._apiKeys[provider]?.key,
                };
            }
        }
        // Fallback sur Groq par défaut
        return {
            provider: 'groq',
            modelName: 'llama-3.3-70b-versatile',
            baseUrl: PROVIDER_ENDPOINTS.groq.baseUrl,
            apiKey: null,
            isDefault: true,
        };
    }

    /**
     * Appelle le LLM avec le bon fournisseur
     * @param {string} prompt - Le prompt à envoyer
     * @param {Object} options - Options (isJson, temperature, etc.)
     * @returns {Promise<string>} - La réponse du LLM
     */
    async call(prompt, options = {}) {
        const config = this._getActiveProviderConfig();
        const { isJson = false, temperature = 0.3, maxTokens = 4096 } = options;

        // Utiliser le backend comme proxy pour les appels LLM
        // Cela permet de gérer les clés API côté serveur
        try {
            const response = await fetch(API_BASE + '/api/ai/call', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt,
                    model: this._activeModel,
                    provider: config.provider,
                    modelName: config.modelName,
                    apiKey: config.apiKey,
                    isJson,
                    temperature,
                    maxTokens,
                }),
            });

            if (!response.ok) {
                const errorData = await response.text();
                throw new Error('LLM call failed: ' + (errorData || response.statusText));
            }

            const data = await response.json();
            return data.text || data.response || '';
        } catch (error) {
            console.error('[UnifiedLLMService] Error calling LLM:', error);
            throw error;
        }
    }

    /**
     * Appelle le LLM et parse la réponse en JSON
     * @param {string} prompt
     * @param {Object} options
     * @returns {Promise<Object>}
     */
    async callJSON(prompt, options = {}) {
        const jsonPrompt = prompt + '\n\nRéponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après.';
        const response = await this.call(jsonPrompt, { ...options, isJson: true });
        try {
            return JSON.parse(response);
        } catch {
            console.warn('[UnifiedLLMService] Failed to parse JSON response, returning raw text');
            return { text: response };
        }
    }

    /**
     * Vérifie si un modèle est disponible
     * @param {string} modelId
     * @returns {boolean}
     */
    isModelAvailable(modelId) {
        for (const config of Object.values(PROVIDER_ENDPOINTS)) {
            if (config.modelMap[modelId]) return true;
        }
        return false;
    }

    /**
     * Récupère le nom du modèle pour l'API
     * @param {string} modelId
     * @returns {string}
     */
    getModelName(modelId) {
        for (const config of Object.values(PROVIDER_ENDPOINTS)) {
            if (config.modelMap[modelId]) return config.modelMap[modelId];
        }
        return 'llama-3.3-70b-versatile';
    }
}

// Instance singleton
export const unifiedLLM = new UnifiedLLMService();

export default UnifiedLLMService;