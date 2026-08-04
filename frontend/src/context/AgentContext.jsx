/**
 * AgentContext - État global du multi-agent
 *
 * Gère :
 *   - L'agent actif ('job' | 'freelance' | 'recruiter')
 *   - Le mode Sans IA (noAiMode)
 *   - Les filtres actifs (spécifiques à chaque agent)
 *
 * Les 3 agents sont des CLONES : même interface, même Header, même
 * DocumentAnalyzer, même useStreamSearch. La Sidebar est dynamique et
 * générée à partir de agentsConfig.js.
 */

import React, {
    createContext,
    useContext,
    useState,
    useEffect,
    useCallback,
    ReactNode,
} from 'react';
import { AGENTS, getDefaultFilters, getAgentStorageKey } from '../config/agentsConfig';

// =============================================================================
// TYPES
// =============================================================================

/**
 * @typedef {'job' | 'freelance' | 'recruiter'} AgentType
 */

/**
 * @typedef {Object} AgentContextValue
 * @property {AgentType} activeAgent
 * @property {(agent: AgentType) => void} setActiveAgent
 * @property {boolean} noAiMode
 * @property {(value: boolean | ((prev: boolean) => boolean)) => void} setNoAiMode
 * @property {Record<string, any>} activeFilters
 * @property {(filters: Record<string, any>) => void} setActiveFilters
 * @property {(filterId: string, value: any) => void} updateFilter
 * @property {object} agentConfig
 * @property {boolean} isAiAvailable
 */

// =============================================================================
// CONTEXTE
// =============================================================================

const AgentContext = createContext(undefined);

const STORAGE_KEY_AGENT = 'agent_active';

// =============================================================================
// PROVIDER
// =============================================================================

export const AgentProvider = ({ children }) => {
    // --- Agent actif ---
    const [activeAgent, setActiveAgentState] = useState(() => {
        const saved = localStorage.getItem(STORAGE_KEY_AGENT);
        return saved && AGENTS[saved] ? saved : 'job';
    });

    // --- Mode Sans IA ---
    const [noAiMode, setNoAiModeState] = useState(() => {
        // AI mode should be active by default (noAiMode = false)
        return localStorage.getItem('noAiMode') === 'true';
    });

    // --- Filtres actifs (spécifiques à chaque agent) ---
    const [activeFilters, setActiveFiltersState] = useState(() => {
        const saved = localStorage.getItem(getAgentStorageKey(activeAgent));
        if (saved) {
            try {
                return JSON.parse(saved);
            } catch {
                return getDefaultFilters(activeAgent);
            }
        }
        return getDefaultFilters(activeAgent);
    });

    // --- Persistance agent actif ---
    useEffect(() => {
        localStorage.setItem(STORAGE_KEY_AGENT, activeAgent);
    }, [activeAgent]);

    // --- Persistance noAiMode ---
    useEffect(() => {
        localStorage.setItem('noAiMode', String(noAiMode));
    }, [noAiMode]);

    // --- Config de l'agent actif ---
    const agentConfig = AGENTS[activeAgent];

    // --- Agent-specific AI mode override ---
    // If the active agent has a forced noAiMode setting, use it
    const agentForcedNoAiMode = agentConfig?.noAiMode;
    const effectiveNoAiMode = agentForcedNoAiMode !== undefined ? agentForcedNoAiMode : noAiMode;

    // --- Persistance filtres + reset quand l'agent change ---
    useEffect(() => {
        const saved = localStorage.getItem(getAgentStorageKey(activeAgent));
        if (saved) {
            try {
                setActiveFiltersState(JSON.parse(saved));
            } catch {
                setActiveFiltersState(getDefaultFilters(activeAgent));
            }
        } else {
            setActiveFiltersState(getDefaultFilters(activeAgent));
        }
    }, [activeAgent]);

    useEffect(() => {
        localStorage.setItem(getAgentStorageKey(activeAgent), JSON.stringify(activeFilters));
    }, [activeAgent, activeFilters]);

    // --- Setters ---
    const setActiveAgent = useCallback((agent) => {
        setActiveAgentState(agent);
    }, []);

    const setNoAiMode = useCallback((value) => {
        setNoAiModeState(typeof value === 'function' ? value(noAiMode) : value);
    }, [noAiMode]);

    const setActiveFilters = useCallback((filters) => {
        setActiveFiltersState(filters);
    }, []);

    const updateFilter = useCallback((filterId, value) => {
        setActiveFiltersState(prev => ({ ...prev, [filterId]: value }));
    }, []);

    // --- Convenience : est-ce que l'IA est disponible ? ---
    // noAiMode désactive l'IA ; sinon l'IA est disponible via le backend
    // L'agent peut forcer noAiMode à false (IA toujours activé)
    const isAiAvailable = !effectiveNoAiMode;

    const value = {
        activeAgent,
        setActiveAgent,
        noAiMode: effectiveNoAiMode,
        setNoAiMode,
        activeFilters,
        setActiveFilters,
        updateFilter,
        agentConfig,
        isAiAvailable,
    };

    return React.createElement(AgentContext.Provider, { value }, children);
};

// =============================================================================
// HOOK CONSUMER
// =============================================================================

export const useAgent = () => {
    const context = useContext(AgentContext);
    if (!context) {
        throw new Error('useAgent must be used within an AgentProvider');
    }
    return context;
};

export default AgentContext;