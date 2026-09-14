import { useEffect, useState, useRef } from 'react';

// URL relative => passe par le rewrite Vercel / redirect Netlify en prod,
// par le proxy Vite en local. Ne JAMAIS retomber sur localhost en prod.
const API_BASE = (import.meta.env.VITE_API_URL || '').trim();

const MAX_ATTEMPTS = 20; // ~20 x 10s = ~3min max (large pour cold start Render)
const INTERVAL_MS = 10000;
const TIMEOUT_MS = 15000;

/**
 * useServerWakeUp — réveille le backend (Render free tier s'endort après inactivité).
 *
 * - 1er appel immédiat au montage (déclenche le cold start Render).
 * - Puis polling toutes les 10s jusqu'à réponse OK (max ~3 min).
 * - Retourne { status: 'waking' | 'online' | 'offline', attempts }.
 * - Ne bloque jamais l'UI : l'app reste utilisable pendant le réveil.
 */
export function useServerWakeUp() {
  const [status, setStatus] = useState('waking');
  const [attempts, setAttempts] = useState(0);
  const timerRef = useRef(null);
  const doneRef = useRef(false);

  useEffect(() => {
    doneRef.current = false;

    const ping = async () => {
      if (doneRef.current) return;
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);
        // /api/health est léger (pas de scraping, juste le statut des clés).
        const res = await fetch(`${API_BASE}/api/health`, {
          method: 'GET',
          headers: { Accept: 'application/json' },
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          doneRef.current = true;
          setStatus('online');
          if (timerRef.current) clearInterval(timerRef.current);
          return;
        }
      } catch {
        // Render endormi / cold start en cours : on réessaie au prochain tick.
      }
      setAttempts((a) => {
        const next = a + 1;
        if (next >= MAX_ATTEMPTS) {
          doneRef.current = true;
          setStatus('offline');
          if (timerRef.current) clearInterval(timerRef.current);
        }
        return next;
      });
    };

    ping(); // déclenche le cold start dès l'arrivée sur la page
    timerRef.current = setInterval(ping, INTERVAL_MS);
    return () => {
      doneRef.current = true;
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  return { status, attempts };
}

export default useServerWakeUp;
