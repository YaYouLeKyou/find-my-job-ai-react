/**
 * useNoAiMode - Hook for managing the "Mode Sans IA" (No-AI Mode) state.
 *
 * This hook provides a simple boolean toggle that, when enabled, forces the
 * application to use local regex-based parsing instead of AI models.
 * The state is persisted to localStorage so it survives page reloads.
 *
 * It is consumed by:
 *   - components/layout/Header.jsx  (toggle button)
 *   - components/features/DocumentAnalyzer.jsx  (force fallback mode)
 *   - hooks/useStreamSearch.js  (skip AI scoring)
 */

import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'noAiMode';

export function useNoAiMode() {
    const [noAiMode, setNoAiModeState] = useState(() => {
        try {
            return localStorage.getItem(STORAGE_KEY) === 'true';
        } catch {
            return false;
        }
    });

    useEffect(() => {
        try {
            localStorage.setItem(STORAGE_KEY, String(noAiMode));
        } catch {
            // ignore
        }
    }, [noAiMode]);

    const setNoAiMode = useCallback((value) => {
        setNoAiModeState(typeof value === 'function' ? value(noAiMode) : value);
    }, [noAiMode]);

    const toggleNoAiMode = useCallback(() => {
        setNoAiModeState(prev => !prev);
    }, []);

    return { noAiMode, setNoAiMode, toggleNoAiMode };
}

export default useNoAiMode;
