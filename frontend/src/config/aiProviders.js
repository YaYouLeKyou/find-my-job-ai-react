/**
 * aiProviders.js - Configuration centralisée des fournisseurs IA
 * 
 * Définit TOUS les grands modèles supportés, leurs URLs d'obtention de clés,
 * et le fournisseur par défaut (Groq / Qwen 3.6 27B).
 * 
 * Supprime définitivement le support des modèles locaux (Ollama, Llama local, Qwen local).
 */

// =============================================================================
// TYPES
// =============================================================================

/**
 * @typedef {'groq' | 'gemini' | 'openai' | 'anthropic' | 'deepseek' | 'mistral' | 'cohere' | 'perplexity' | 'xai'} AIProvider
 */

/**
 * @typedef {Object} AIModel
 * @property {string} id - Identifiant unique du modèle
 * @property {string} label - Nom affiché dans l'UI
 * @property {AIProvider} provider - Fournisseur
 * @property {boolean} requiresPersonalKey - Nécessite une clé personnelle
 * @property {string} description - Description courte
 * @property {string} apiKeyUrl - URL pour obtenir une clé API
 * @property {string} [endpoint] - Endpoint API optionnel
 */

// =============================================================================
// FOURNISSEURS ET MODÈLES
// =============================================================================

/** @type {Record<AIProvider, string>} */
export const API_KEY_URLS = {
    groq: 'https://console.groq.com/keys',
    gemini: 'https://aistudio.google.com/app/apikey',
    openai: 'https://platform.openai.com/api-keys',
    anthropic: 'https://console.anthropic.com/settings/keys',
    deepseek: 'https://platform.deepseek.com/api_keys',
    mistral: 'https://console.mistral.ai/api-keys/',
    cohere: 'https://dashboard.cohere.com/api-keys',
    perplexity: 'https://www.perplexity.ai/settings/api',
    xai: 'https://console.x.ai/',
};

/** @type {Record<AIProvider, string>} */
export const PROVIDER_LABELS = {
    groq: 'Groq',
    gemini: 'Google Gemini',
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    deepseek: 'DeepSeek',
    mistral: 'Mistral AI',
    cohere: 'Cohere',
    perplexity: 'Perplexity',
    xai: 'xAI (Grok)',
};

/** @type {Record<AIProvider, string>} */
export const PROVIDER_COLORS = {
    groq: '#f97316',
    gemini: '#4285f4',
    openai: '#10a37f',
    anthropic: '#d4a574',
    deepseek: '#4f46e5',
    mistral: '#7c3aed',
    cohere: '#0891b2',
    perplexity: '#6366f1',
    xai: '#000000',
};

// =============================================================================
// MODÈLES DISPONIBLES
// =============================================================================

/** @type {AIModel[]} */
export const AI_MODELS = [
    // ═════════════════════════════════════════════════════════════════
    // GROQ - DÉFAUT SYSTÈME (clé partagée de l'application)
    // ═════════════════════════════════════════════════════════════════
    {
        id: 'Groq / Qwen 3.6 27B',
        label: 'Groq / Qwen 3.6 27B',
        provider: 'groq',
        requiresPersonalKey: false,
        description: '🚀 DÉFAUT - Ultra-rapide, quota partagé de l\'application',
        apiKeyUrl: 'https://console.groq.com/keys',
    },
    {
        id: 'Groq / DeepSeek R1',
        label: 'Groq / DeepSeek R1',
        provider: 'groq',
        requiresPersonalKey: false,
        description: 'Modèle de raisonnement via Groq',
        apiKeyUrl: 'https://console.groq.com/keys',
    },
    {
        id: 'Groq / Qwen 3 8B',
        label: 'Groq / Qwen 3 8B',
        provider: 'groq',
        requiresPersonalKey: false,
        description: 'Modèle léger rapide via Groq',
        apiKeyUrl: 'https://console.groq.com/keys',
    },

    // ═════════════════════════════════════════════════════════════════
    // GOOGLE GEMINI
    // ═════════════════════════════════════════════════════════════════
    {
        id: 'Gemini 3.5 Pro',
        label: 'Gemini 3.5 Pro',
        provider: 'gemini',
        requiresPersonalKey: true,
        description: 'Modèle Google haute performance',
        apiKeyUrl: 'https://aistudio.google.com/app/apikey',
    },
    {
        id: 'Gemini 2.5 Pro',
        label: 'Gemini 2.5 Pro',
        provider: 'gemini',
        requiresPersonalKey: true,
        description: 'Modèle Google équilibré',
        apiKeyUrl: 'https://aistudio.google.com/app/apikey',
    },
    {
        id: 'Gemini 2.5 Flash',
        label: 'Gemini 2.5 Flash',
        provider: 'gemini',
        requiresPersonalKey: true,
        description: 'Modèle Google rapide et économique',
        apiKeyUrl: 'https://aistudio.google.com/app/apikey',
    },

    // ═════════════════════════════════════════════════════════════════
    // MISTRAL AI
    // ════════════════════════════════════════════════════════════════
    {
        id: 'Mistral / Large',
        label: 'Mistral / Large',
        provider: 'mistral',
        requiresPersonalKey: true,
        description: 'Modèle généraliste haute performance',
        apiKeyUrl: 'https://console.mistral.ai/api-keys/',
    },
    {
        id: 'Mistral / Codestral',
        label: 'Mistral / Codestral',
        provider: 'mistral',
        requiresPersonalKey: true,
        description: 'Modèle spécialisé code',
        apiKeyUrl: 'https://console.mistral.ai/api-keys/',
    },
    {
        id: 'Mistral / Pixtral',
        label: 'Mistral / Pixtral',
        provider: 'mistral',
        requiresPersonalKey: true,
        description: 'Modèle multimodal',
        apiKeyUrl: 'https://console.mistral.ai/api-keys/',
    },
];

// =============================================================================
// DÉFAUT SYSTÈME
// =============================================================================

/** Identifiant du modèle par défaut (Groq / Qwen 3.6 27B) */
export const DEFAULT_MODEL_ID = 'Groq / Qwen 3.6 27B';

/** Fournisseur par défaut */
export const DEFAULT_PROVIDER = 'groq';

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Récupère la configuration complète d'un modèle par son ID
 * @param {string} modelId
 * @returns {AIModel|undefined}
 */
export function getModelById(modelId) {
    return AI_MODELS.find(m => m.id === modelId);
}

/**
 * Récupère l'URL d'obtention de clé pour un fournisseur
 * @param {AIProvider} provider
 * @returns {string}
 */
export function getApiKeyUrl(provider) {
    return API_KEY_URLS[provider] || '';
}

/**
 * Récupère le label d'un fournisseur
 * @param {AIProvider} provider
 * @returns {string}
 */
export function getProviderLabel(provider) {
    return PROVIDER_LABELS[provider] || provider;
}

/**
 * Récupère la couleur d'un fournisseur
 * @param {AIProvider} provider
 * @returns {string}
 */
export function getProviderColor(provider) {
    return PROVIDER_COLORS[provider] || '#666';
}

/**
 * Vérifie si un modèle nécessite une clé personnelle
 * @param {string} modelId
 * @returns {boolean}
 */
export function modelRequiresKey(modelId) {
    const model = getModelById(modelId);
    return model ? model.requiresPersonalKey : false;
}

/**
 * Groupe les modèles par fournisseur
 * @returns {Record<AIProvider, AIModel[]>}
 */
export function getModelsByProvider() {
    const groups = {};
    AI_MODELS.forEach(model => {
        if (!groups[model.provider]) groups[model.provider] = [];
        groups[model.provider].push(model);
    });
    return groups;
}