/**
 * agentsConfig.js - Configuration séparée pour 3 agents et de leurs filtres
 *
 * Chaque agent a son propre analyseur, ces propres filtres, sa propre searchbar.
 *
 * Les 3 agents partagent :
 *   - Le même Header (sélection d'agent + toggle Mode Sans IA)
 *   - Le meme design

 */

// =============================================================================
// AGENTS
// =============================================================================

export const AGENTS = {
    job: {
        id: 'job',
        name: 'Job Seeker',
        emoji: '🔍',
        title: 'Find my job AI',
        subtitle: "Trouvez votre prochain emploi avec l'aide de l'IA",
        description: "Analysez votre CV, recevez des recommandations de carrière IA, et trouvez les meilleures offres sur 10+ plateformes en un clic.",
        noAiMode: false,
        theme: {
            primary: '#7c4dff',
            gradient: 'linear-gradient(135deg, #7c4dff 0%, #448aff 100%)',
            glowColor: 'rgba(124, 77, 255, 0.25)',
            tagBg: 'rgba(124, 77, 255, 0.12)',
            tagColor: '#7c4dff',
            badgeBg: 'rgba(124, 77, 255, 0.08)',
            badgeBorder: 'rgba(124, 77, 255, 0.2)',
            footerBg: 'rgba(124, 77, 255, 0.05)',
            footerBorder: 'rgba(124, 77, 255, 0.15)',
            alertBg: 'linear-gradient(135deg, rgba(124,77,255,0.12), rgba(68,138,255,0.08))',
            alertBorder: 'rgba(124, 77, 255, 0.25)',
        },
        sources: ['LinkedIn', 'France Travail', 'Google Jobs', 'Adzuna', 'Enhanced', 'JobSpy'],
        resultType: 'job',
        searchEndpoint: '/api/search-jobs-stream',
        // Filtres spécifiques au Job Seeker
        filters: [
            {
                id: 'contract',
                type: 'select',
                label: 'Type de contrat',
                icon: '📋',
                options: ['CDI', 'CDD', 'Alternance', 'Stage', 'Intérim'],
                default: 'CDI',
            },
            {
                id: 'location',
                type: 'text',
                label: '📍 Ville / Pays',
                placeholder: 'Ex: Paris, France...',
                default: 'Paris, France',
            },
            {
                id: 'remote',
                type: 'checkbox',
                label: 'Télétravail uniquement',
                default: false,
            },
            {
                id: 'globalSearch',
                type: 'checkbox',
                label: '🌍 Recherche mondiale',
                default: false,
                dependsOn: 'remote',
            },
            {
                id: 'numAds',
                type: 'select',
                label: "Nombre d'annonces affiché par source",
                options: [5, 10, 15, 20, 25, 50, 100, "Max"],
                default: '10',
            },
            {
                id: 'sortOption',
                type: 'select',
                label: 'Trier par',
                options: ['Pertinence (IA)', 'Plus récentes', 'Plus proches'],
                default: 'Pertinence (IA)',
            },
        ],
    },

    freelance: {
        id: 'freelance',
        name: 'Freelance',
        emoji: '🚀',
        title: 'Find my freelance mission AI',
        subtitle: 'Trouvez des missions freelance adaptées à votre profil grâce à l\'IA',
        description: "Trouvez des missions freelance adaptées à vos compétences, calculez votre TJM optimal et générez des propositions commerciales percutantes.",
        noAiMode: false,
        theme: {
            primary: '#00bcd4',
            gradient: 'linear-gradient(135deg, #00bcd4 0%, #00897b 100%)',
            glowColor: 'rgba(0, 188, 212, 0.25)',
            tagBg: 'rgba(0, 188, 212, 0.12)',
            tagColor: '#00897b',
            badgeBg: 'rgba(0, 188, 212, 0.08)',
            badgeBorder: 'rgba(0, 188, 212, 0.2)',
            footerBg: 'rgba(0, 188, 212, 0.05)',
            footerBorder: 'rgba(0, 188, 212, 0.15)',
            alertBg: 'linear-gradient(135deg, rgba(0,188,212,0.1), rgba(0,137,123,0.06))',
            alertBorder: 'rgba(0, 188, 212, 0.25)',
        },
        sources: ['Free-Work', 'LinkedIn', 'Enhanced', 'JobSpy'],
        resultType: 'mission',
        searchEndpoint: '/api/freelance/search',
        // Filtres spécifiques au Freelance
        filters: [
            {
                id: 'missionType',
                type: 'select',
                label: '🎯 Type de mission',
                options: ['Développement', 'Design', 'Conseil', 'Rédaction', 'Marketing', 'Data', 'DevOps', 'Mobile'],
                default: '',
                placeholder: 'Tous types',
            },
            {
                id: 'duration',
                type: 'select',
                label: '⏱️ Durée de mission',
                options: ['Court terme (< 1 mois)', 'Moyen terme (1-3 mois)', 'Long terme (> 3 mois)', 'Récurrent'],
                default: '',
                placeholder: 'Toutes durées',
            },
            {
                id: 'remote',
                type: 'select',
                label: '🏠 Mode de travail',
                options: ['Remote', 'Hybride', 'Présentiel'],
                default: 'Remote',
            },
            {
                id: 'tjmMin',
                type: 'number',
                label: '💰 TJM min (€/j)',
                placeholder: 'ex: 350',
                min: 0,
                step: 50,
                default: '',
            },
            {
                id: 'tjmMax',
                type: 'number',
                label: '💰 TJM max (€/j)',
                placeholder: 'ex: 800',
                min: 0,
                step: 50,
                default: '',
            },
            {
                id: 'location',
                type: 'text',
                label: '📍 Localisation',
                placeholder: 'France, Paris...',
                default: 'France',
            },
            {
                id: 'numAds',
                type: 'range',
                label: '📊 Nombre de résultats',
                min: 5,
                max: 50,
                step: 5,
                default: 10,
            },
        ],
    },

    recruiter: {
        id: 'recruiter',
        name: 'Recruteur',
        emoji: '👷',
        title: 'Find my worker AI',
        subtitle: 'Trouvez les meilleurs talents pour vos postes à pourvoir',
        description: "Publiez vos offres et trouvez le candidat idéal grâce au matching IA. Gérez les candidatures en un clic.",
        noAiMode: false,
        theme: {
            primary: '#ff6f00',
            gradient: 'linear-gradient(135deg, #ff6f00 0%, #ff8f00 100%)',
            glowColor: 'rgba(255, 111, 0, 0.25)',
            tagBg: 'rgba(255, 111, 0, 0.12)',
            tagColor: '#e65100',
            badgeBg: 'rgba(255, 111, 0, 0.08)',
            badgeBorder: 'rgba(255, 111, 0, 0.2)',
            footerBg: 'rgba(255, 111, 0, 0.05)',
            footerBorder: 'rgba(255, 111, 0, 0.15)',
            alertBg: 'linear-gradient(135deg, rgba(255,111,0,0.1), rgba(255,143,0,0.06))',
            alertBorder: 'rgba(255, 111, 0, 0.25)',
        },
        sources: ['LinkedIn', 'Indeed', 'France Travail', 'Apec', 'Monster', 'Malt'],
        resultType: 'candidate',
        searchEndpoint: '/api/recruiter/search',
        // Filtres spécifiques au Recruteur
        filters: [
            {
                id: 'contract',
                type: 'select',
                label: '📋 Type de contrat',
                options: ['CDI', 'CDD', 'Stage', 'Alternance', 'Intérim', 'Temps partiel'],
                default: 'CDI',
            },
            {
                id: 'experience',
                type: 'select',
                label: "📊 Niveau d'expérience",
                options: ['Débutant', 'Junior (1-3 ans)', 'Confirmé (3-5 ans)', 'Senior (5-10 ans)', 'Expert (10+ ans)'],
                default: '',
                placeholder: 'Tous niveaux',
            },
            {
                id: 'location',
                type: 'text',
                label: '📍 Localisation',
                placeholder: 'France, Paris...',
                default: 'France',
            },
            {
                id: 'remote',
                type: 'checkbox',
                label: '🏠 Profils en télétravail uniquement',
                default: false,
            },
            {
                id: 'salaryMin',
                type: 'number',
                label: '💰 Salaire min (€/mois)',
                placeholder: 'ex: 2000',
                min: 0,
                step: 100,
                default: '',
            },
            {
                id: 'salaryMax',
                type: 'number',
                label: '💰 Salaire max (€/mois)',
                placeholder: 'ex: 8000',
                min: 0,
                step: 100,
                default: '',
            },
            {
                id: 'skills',
                type: 'tags',
                label: '🎯 Compétences requises',
                options: ['JavaScript', 'Python', 'React', 'Node.js', 'Java', 'SQL', 'AWS', 'Docker', 'Kubernetes', 'Git', 'Agile', 'Marketing', 'Vente', 'Communication'],
                default: [],
            },
            {
                id: 'numAds',
                type: 'range',
                label: '📊 Nombre de résultats',
                min: 5,
                max: 50,
                step: 5,
                default: 10,
            },
        ],
    },
};

// =============================================================================
// AGENT LIST (ordered for UI display)
// =============================================================================

export const AGENT_LIST = [AGENTS.job, AGENTS.freelance, AGENTS.recruiter];

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Retrieve a full agent configuration by its id.
 * @param {string} agentId - 'job' | 'freelance' | 'recruiter'
 * @returns {object|undefined}
 */
export function getAgentConfig(agentId) {
    return AGENTS[agentId];
}

/**
 * Build the default filter values for a given agent from its config.
 * @param {string} agentId
 * @returns {Record<string, any>}
 */
export function getDefaultFilters(agentId) {
    const config = getAgentConfig(agentId);
    if (!config) return {};
    const defaults = {};
    config.filters.forEach(f => {
        defaults[f.id] = f.default !== undefined ? f.default : (f.type === 'checkbox' ? false : '');
    });
    return defaults;
}

/**
 * Get the storage key prefix for an agent's persisted filters.
 * @param {string} agentId
 * @returns {string}
 */
export function getAgentStorageKey(agentId) {
    return `agent_${agentId}_filters`;
}
