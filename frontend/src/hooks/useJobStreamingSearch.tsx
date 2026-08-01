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

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'sourceStatus':
      return { ...state, sources: { ...state.sources, [action.source]: { ...(state.sources[action.source] || { status: 'idle', count: 0 }), status: action.status } } };
    case 'addJobs': {
      const liveMap = { ...state.liveMap };
      const liveOrder = [...state.liveOrder];
      for (const j of action.jobs) {
        const id = j.id || `${j.source}::${j.url || j.title}`;
        if (!liveMap[id]) {
          liveMap[id] = { ...j, id } as Job;
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
    // init worker (Vite/Webpack: new URL(..., import.meta.url))
    try {
      // @ts-ignore
      workerRef.current = new Worker(new URL('../workers/ranker.worker.ts', import.meta.url), { type: 'module' });
    } catch (e) {
      // Fallback: try relative path (depends on bundler)
      workerRef.current = new Worker('/src/workers/ranker.worker.js');
    }

    const w = workerRef.current;
    w?.addEventListener('message', (ev: MessageEvent) => {
      const data = ev.data;
      if (data?.type === 'sorted') {
        // schedule apply after brief delay to avoid layout shift
        if (applyTimeout.current) window.clearTimeout(applyTimeout.current);
        applyTimeout.current = window.setTimeout(() => {
          dispatch({ type: 'applySorted', order: data.order });
        }, autoApplyDelay);
      }
    });

    return () => {
      w?.terminate();
    };
  }, [autoApplyDelay]);

  useEffect(() => {
    // connect SSE
    const url = `/sse/search?q=${encodeURIComponent(q)}`;
    dispatch({ type: 'reset' });
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => {
      // status unknown per-source until events arrive
    };

    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data);
        const { source, isPartial, jobs } = payload;
        dispatch({ type: 'sourceStatus', source, status: 'streaming' });
        dispatch({ type: 'addJobs', jobs });
        // forward to worker for dedupe + ranking
        workerRef.current?.postMessage({ type: 'add', q, jobs });
      } catch (err) {
        console.error('SSE parse error', err);
      }
    };

    es.addEventListener('end', () => {
      // all done
    });

    es.onerror = (err) => {
      console.error('SSE error', err);
      es.close();
    };

    return () => {
      es.close();
    };
  }, [q]);

  const liveItems = useMemo(() => state.liveOrder.map((id) => state.liveMap[id]), [state.liveOrder, state.liveMap]);
  const sortedItems = useMemo(() => deferredSortedOrder.map((id) => state.liveMap[id]).filter(Boolean), [deferredSortedOrder, state.liveMap]);

  return {
    liveItems,
    sortedItems,
    sources: state.sources,
    refresh: () => {
      // re-run worker ranking on current items
      workerRef.current?.postMessage({ type: 'recompute', q, jobs: Object.values(state.liveMap) });
    },
    close: () => {
      esRef.current?.close();
      workerRef.current?.terminate();
    },
  };
}
