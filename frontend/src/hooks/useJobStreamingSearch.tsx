import { useEffect, useMemo, useReducer, useRef, useState, useDeferredValue } from 'react';
import type { Job } from '../../../../streaming_service/src/types';

type SourceStatus = 'idle' | 'loading' | 'streaming' | 'success' | 'error';

type State = {
  sources: Record<string, { status: SourceStatus; count: number }>;
  liveMap: Record<string, Job>; // id -> job
  liveOrder: string[]; // order of arrival (ids)
  sortedOrder: string[]; // worker-provided order
};

type Action =
  | { type: 'sourceStatus'; source: string; status: SourceStatus }
  | { type: 'addJobs'; jobs: Job[] }
  | { type: 'applySorted'; order: string[] }
  | { type: 'reset' };

function normalizeText(value?: string) {
  return (value || '').toLowerCase().trim().replace(/\s+/g, ' ');
}

function createJobFingerprint(job: Partial<Job>) {
  const title = normalizeText(job.title);
  const company = normalizeText(job.company);
  const location = normalizeText(job.location);
  const url = normalizeText(job.url);
  return `${title}|${company}|${location}|${url}`;
}

function createStableJobId(job: Partial<Job>) {
  const fingerprint = createJobFingerprint(job);
  let hash = 0;
  for (let i = 0; i < fingerprint.length; i += 1) {
    hash = (hash << 5) - hash + fingerprint.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash).toString(36).padStart(8, '0');
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'sourceStatus':
      return {
        ...state,
        sources: {
          ...state.sources,
          [action.source]: {
            ...(state.sources[action.source] || { status: 'idle', count: 0 }),
            status: action.status,
          },
        },
      };
    case 'addJobs': {
      const liveMap = { ...state.liveMap };
      const liveOrder = [...state.liveOrder];
      for (const job of action.jobs) {
        const id = createStableJobId(job);
        if (!liveMap[id]) {
          liveMap[id] = { ...job, id } as Job;
          liveOrder.push(id);
        }
      }
      return { ...state, liveMap, liveOrder };
    }
    case 'applySorted':
      return { ...state, sortedOrder: action.order };
    case 'reset':
      return { sources: {}, liveMap: {}, liveOrder: [], sortedOrder: [] };
    default:
      return state;
  }
}

// Hook
export function useJobStreamingSearch(q: string, options?: { autoApplySortedDelayMs?: number }) {
  const [state, dispatch] = useReducer(reducer, { sources: {}, liveMap: {}, liveOrder: [], sortedOrder: [] });
  const workerRef = useRef<Worker | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const autoApplyDelay = options?.autoApplySortedDelayMs ?? 2000;
  const applyTimeout = useRef<number | null>(null);

  // expose deferred value to avoid UI jank during heavy updates
  const deferredSortedOrder = useDeferredValue(state.sortedOrder);

  useEffect(() => {
    try {
      // @ts-ignore
      workerRef.current = new Worker(new URL('../workers/ranker.worker.ts', import.meta.url), { type: 'module' });
    } catch (e) {
      workerRef.current = new Worker('/src/workers/ranker.worker.js');
    }

    const worker = workerRef.current;
    worker?.addEventListener('message', (ev: MessageEvent) => {
      const payload = ev.data;
      if (payload?.type === 'sorted') {
        if (applyTimeout.current) window.clearTimeout(applyTimeout.current);
        applyTimeout.current = window.setTimeout(() => {
          dispatch({ type: 'applySorted', order: payload.order });
        }, autoApplyDelay);
      }
    });

    return () => {
      worker?.terminate();
    };
  }, [autoApplyDelay]);

  useEffect(() => {
    if (!q) {
      dispatch({ type: 'reset' });
      return;
    }

    dispatch({ type: 'reset' });
    const url = `/api/jobs/stream?query=${encodeURIComponent(q)}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => {
      // nothing to do yet
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const source = data.source || 'unknown';

        if (data.type === 'STARTED') {
          dispatch({ type: 'sourceStatus', source: 'global', status: 'loading' });
          return;
        }

        if (data.type === 'SOURCE_RESULT') {
          dispatch({ type: 'sourceStatus', source, status: data.is_partial ? 'streaming' : 'success' });

          const jobs: Job[] = (data.jobs || []).map((job: Job) => ({
            ...job,
            source,
            id: createStableJobId({ ...job, source }),
          }));

          dispatch({ type: 'addJobs', jobs });
          workerRef.current?.postMessage({ type: 'add', q, jobs });
          return;
        }

        if (data.type === 'SCORES_UPDATED') {
          if (data.jobs && Array.isArray(data.jobs)) {
            const jobsWithIds = data.jobs.map((job: Job) => ({
              ...job,
              id: createStableJobId(job),
            }));
            workerRef.current?.postMessage({ type: 'recompute', q, jobs: jobsWithIds });
          }
          return;
        }

        if (data.type === 'COMPLETED') {
          dispatch({ type: 'sourceStatus', source: 'global', status: 'success' });
          if (data.jobs && Array.isArray(data.jobs)) {
            const jobs: Job[] = data.jobs.map((job: Job) => ({
              ...job,
              id: createStableJobId(job),
            }));
            dispatch({ type: 'addJobs', jobs });
            workerRef.current?.postMessage({ type: 'recompute', q, jobs });
          }
          return;
        }
      } catch (error) {
        console.error('SSE parse error', error);
      }
    };

    es.onerror = (err) => {
      console.error('SSE error', err);
      es.close();
    };

    return () => {
      es.close();
    };
  }, [q]);

  const liveItems = useMemo(
    () => state.liveOrder.map((id) => state.liveMap[id]),
    [state.liveOrder, state.liveMap]
  );

  const sortedItems = useMemo(
    () => deferredSortedOrder.map((id) => state.liveMap[id]).filter(Boolean),
    [deferredSortedOrder, state.liveMap]
  );

  return {
    liveItems,
    sortedItems,
    sources: state.sources,
    refresh: () => {
      workerRef.current?.postMessage({ type: 'recompute', q, jobs: Object.values(state.liveMap) });
    },
    close: () => {
      esRef.current?.close();
      workerRef.current?.terminate();
    },
  };
}
