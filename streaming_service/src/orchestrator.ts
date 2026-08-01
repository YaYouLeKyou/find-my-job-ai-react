import { StreamMessage, SearchParams } from './types';
import { createMockSource } from './sources/mockSource';

type SourceGen = AsyncGenerator<{ isPartial: boolean; jobs: any[] }, any, any>;

// For production, replace createMockSource with real scrapers / API callers
export function getSources(params: SearchParams): { name: string; gen: () => SourceGen }[] {
  // Example 6 sources
  return [
    { name: 'LinkedIn', gen: () => createMockSource('LinkedIn', 4, 8, 6, 150, 700) },
    { name: 'Indeed', gen: () => createMockSource('Indeed', 3, 6, 5, 100, 900) },
    { name: 'Glassdoor', gen: () => createMockSource('Glassdoor', 3, 5, 5, 200, 800) },
    { name: 'RemoteOK', gen: () => createMockSource('RemoteOK', 2, 6, 4, 120, 600) },
    { name: 'APIJobs', gen: () => createMockSource('APIJobs', 3, 7, 6, 130, 750) },
    { name: 'LocalDB', gen: () => createMockSource('LocalDB', 2, 10, 8, 50, 400) },
  ];
}

// Async generator that yields StreamMessage as soon as any source produces a batch
export async function* streamSearch(params: SearchParams): AsyncGenerator<StreamMessage> {
  const sources = getSources(params).map((s) => ({ name: s.name, iter: s.gen() }));

  // map to pending next promises
  const pending = new Map<number, Promise<any>>();
  for (let i = 0; i < sources.length; i++) {
    pending.set(i, sources[i].iter.next());
  }

  while (pending.size > 0) {
    // wait for any source to yield
    const entries = Array.from(pending.entries());
    const raced = await Promise.race(entries.map(([i, p]) => p.then((res) => ({ i, res }))));
    const { i, res } = raced as { i: number; res: any };
    if (res.done) {
      pending.delete(i);
      continue;
    }
    // res.value: { isPartial, jobs }
    yield {
      source: sources[i].name,
      isPartial: !!res.value.isPartial,
      jobs: res.value.jobs,
    };

    // queue next for that source
    pending.set(i, sources[i].iter.next());
  }
}
