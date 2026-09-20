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
 * @typedef {'groq' | 'gemini' | 'openai' | 'anthropic' | 'deepseek' | 'mistral' | 'cohere' | 'perplexity' | 'xai' | 'openrouter'} AIProvider
 */

/**
 * @typedef {Object} AIModel
 * @property {string} id - Identifiant unique du modèle
 * @property {string} label - Nom affiché dans l'UI
 * @property {AIProvider} provider - Fournisseur
 * @property {boolean} requiresPersonalKey - Nécessite une clé personnelle
 * @property {'daily'|'signup'|'paid'} quotaCategory - Catégorie de quota
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
    openrouter: 'https://openrouter.ai/keys',
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
    openrouter: 'OpenRouter',
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
    openrouter: '#10a37f',
};

// =============================================================================
// MODÈLES DISPONIBLES
// =============================================================================

/** @type {AIModel[]} */
export const AI_MODELS = [
    // ═════════════════════════════════════════════════════════════════
    // QUOTAS GRATUITS QUOTIDIENS
    // ═════════════════════════════════════════════════════════════════
    {
        id: 'Groq / Qwen 3.6 27B',
        label: 'Groq / Qwen 3.6 27B',
        provider: 'groq',
        requiresPersonalKey: true,
        quotaCategory: 'daily',
        description: '🚀 DÉFAUT - Ultra-rapide. Vous pouvez utiliser la clé partagée de l\'application ou votre propre clé.',
        apiKeyUrl: 'https://console.groq.com/keys',
    },
    {
        id: 'Groq / DeepSeek R1',
        label: 'Groq / DeepSeek R1',
        provider: 'groq',
        requiresPersonalKey: true,
        quotaCategory: 'daily',
        description: 'Raisonnement avancé via Groq',
        apiKeyUrl: 'https://console.groq.com/keys',
    },
    {
        id: 'Groq / Qwen 3 8B',
        label: 'Groq / Qwen 3 8B',
        provider: 'groq',
        requiresPersonalKey: true,
        quotaCategory: 'daily',
        description: 'Modèle léger rapide via Groq',
        apiKeyUrl: 'https://console.groq.com/keys',
    },
    {
        id: 'Gemini 3.5 Pro',
        label: 'Gemini 3.5 Pro',
        provider: 'gemini',
        requiresPersonalKey: true,
        quotaCategory: 'daily',
        description: 'Modèle Google haute performance',
        apiKeyUrl: 'https://aistudio.google.com/app/apikey',
    },
    {
        id: 'Gemini 2.5 Pro',
        label: 'Gemini 2.5 Pro',
        provider: 'gemini',
        requiresPersonalKey: true,
        quotaCategory: 'daily',
        description: 'Modèle Google équilibré',
        apiKeyUrl: 'https://aistudio.google.com/app/apikey',
    },
    {
        id: 'Gemini 2.5 Flash',
        label: 'Gemini 2.5 Flash',
        provider: 'gemini',
        requiresPersonalKey: true,
        quotaCategory: 'daily',
        description: 'Modèle Google rapide et économique',
        apiKeyUrl: 'https://aistudio.google.com/app/apikey',
    },
    {
        id: 'DeepSeek / V3',
        label: 'DeepSeek / V3',
        provider: 'deepseek',
        requiresPersonalKey: true,
        quotaCategory: 'daily',
        description: 'Modèle DeepSeek généraliste',
        apiKeyUrl: 'https://platform.deepseek.com/api_keys',
    },
    {
        id: 'DeepSeek / R1',
        label: 'DeepSeek / R1',
        provider: 'deepseek',
        requiresPersonalKey: true,
        quotaCategory: 'daily',
        description: 'Raisonnement avancé DeepSeek',
        apiKeyUrl: 'https://platform.deepseek.com/api_keys',
    },

    // ═════════════════════════════════════════════════════════════════
    // QUOTAS UNIQUEMENT À LA CRÉATION
    // ═════════════════════════════════════════════════════════════════
    {
        id: 'Mistral / Large',
        label: 'Mistral / Large',
        provider: 'mistral',
        requiresPersonalKey: true,
        quotaCategory: 'signup',
        description: 'Modèle généraliste haute performance',
        apiKeyUrl: 'https://console.mistral.ai/api-keys/',
    },
    {
        id: 'Mistral / Codestral',
        label: 'Mistral / Codestral',
        provider: 'mistral',
        requiresPersonalKey: true,
        quotaCategory: 'signup',
        description: 'Modèle spécialisé code',
        apiKeyUrl: 'https://console.mistral.ai/api-keys/',
    },
    {
        id: 'Mistral / Pixtral',
        label: 'Mistral / Pixtral',
        provider: 'mistral',
        requiresPersonalKey: true,
        quotaCategory: 'signup',
        description: 'Modèle multimodal',
        apiKeyUrl: 'https://console.mistral.ai/api-keys/',
    },
    {
        id: 'OpenRouter / Claude 3.5 Sonnet',
        label: 'OpenRouter / Claude 3.5 Sonnet',
        provider: 'openrouter',
        requiresPersonalKey: true,
        quotaCategory: 'signup',
        description: 'Claude via OpenRouter — crédits offerts à la création',
        apiKeyUrl: 'https://openrouter.ai/keys',
    },
    {
        id: 'OpenRouter / Llama 3 70B',
        label: 'OpenRouter / Llama 3 70B',
        provider: 'openrouter',
        requiresPersonalKey: true,
        quotaCategory: 'signup',
        description: 'Llama 3 70B via OpenRouter',
        apiKeyUrl: 'https://openrouter.ai/keys',
    },

    // ═════════════════════════════════════════════════════════════════
    // UNIQUEMENT PLAN PAYANT
    // ═════════════════════════════════════════════════════════════════
    {
        id: 'OpenAI / GPT-4o',
        label: 'OpenAI / GPT-4o',
        provider: 'openai',
        requiresPersonalKey: true,
        quotaCategory: 'paid',
        description: 'Modèle phare OpenAI',
        apiKeyUrl: 'https://platform.openai.com/api-keys',
    },
    {
        id: 'OpenAI / GPT-4o-mini',
        label: 'OpenAI / GPT-4o-mini',
        provider: 'openai',
        requiresPersonalKey: true,
        quotaCategory: 'paid',
        description: 'OpenAI rapide et économique',
        apiKeyUrl: 'https://platform.openai.com/api-keys',
    },
    {
        id: 'OpenAI / o1',
        label: 'OpenAI / o1',
        provider: 'openai',
        requiresPersonalKey: true,
        quotaCategory: 'paid',
        description: 'Raisonnement avancé OpenAI',
        apiKeyUrl: 'https://platform.openai.com/api-keys',
    },
    {
        id: 'OpenAI / o3-mini',
        label: 'OpenAI / o3-mini',
        provider: 'openai',
        requiresPersonalKey: true,
        quotaCategory: 'paid',
        description: 'OpenAI raisonnement compact',
        apiKeyUrl: 'https://platform.openai.com/api-keys',
    },
    {
        id: 'Anthropic / Claude 3.5 Sonnet',
        label: 'Anthropic / Claude 3.5 Sonnet',
        provider: 'anthropic',
        requiresPersonalKey: true,
        quotaCategory: 'paid',
        description: 'Claude 3.5 Sonnet — plan payant',
        apiKeyUrl: 'https://console.anthropic.com/settings/keys',
    },
    {
        id: 'Anthropic / Claude 3.5 Haiku',
        label: 'Anthropic / Claude 3.5 Haiku',
        provider: 'anthropic',
        requiresPersonalKey: true,
        quotaCategory: 'paid',
        description: 'Claude 3.5 Haiku — rapide et payant',
        apiKeyUrl: 'https://console.anthropic.com/settings/keys',
    },
    {
        id: 'xAI / Grok Beta',
        label: 'xAI / Grok Beta',
        provider: 'xai',
        requiresPersonalKey: true,
        quotaCategory: 'paid',
        description: 'Grok Beta par xAI',
        apiKeyUrl: 'https://console.x.ai/',
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

const QUOTA_CATEGORY_CONFIG = {
    daily: { label: '🆓 Quota quotidien', color: '#10b981' },
    signup: { label: '🎁 Quota à la création', color: '#f59e0b' },
    paid: { label: '💳 Plan payant', color: '#ef4444' },
};

/**
 * Récupère le libellé d'une catégorie de quota
 * @param {'daily'|'signup'|'paid'} category
 * @returns {string}
 */
export function getQuotaCategoryLabel(category) {
    return QUOTA_CATEGORY_CONFIG[category]?.label || '';
}

/**
 * Récupère la couleur d'une catégorie de quota
 * @param {'daily'|'signup'|'paid'} category
 * @returns {string}
 */
export function getQuotaCategoryColor(category) {
    return QUOTA_CATEGORY_CONFIG[category]?.color || '#666';
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