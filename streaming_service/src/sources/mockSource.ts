import { Job } from '../types';

// Mock source generator that yields an initial fast batch, then subsequent pages
export async function* createMockSource(name: string, pages = 3, firstBatchSize = 6, pageSize = 5, firstDelay = 200, pageDelay = 800) {
  // Fast first batch
  await sleep(firstDelay);
  const now = Date.now();
  const first: Job[] = [];
  for (let i = 0; i < firstBatchSize; i++) {
    first.push({
      title: `${name} Job ${i + 1}`,
      company: `${name} Co`,
      location: 'Remote',
      url: `https://${name.toLowerCase()}.example/jobs/${i + 1}`,
      postedAt: new Date(now - i * 3600_000).toISOString(),
      source: name,
    });
  }
  yield { isPartial: true, jobs: first };

  // Background pagination pages
  for (let p = 1; p < pages; p++) {
    await sleep(pageDelay);
    const batch: Job[] = [];
    for (let i = 0; i < pageSize; i++) {
      const idx = p * pageSize + i + 1;
      batch.push({
        title: `${name} Job ${idx}`,
        company: `${name} Co`,
        location: 'Remote',
        url: `https://${name.toLowerCase()}.example/jobs/${idx}`,
        postedAt: new Date(now - idx * 3600_000).toISOString(),
        source: name,
      });
    }
    yield { isPartial: true, jobs: batch };
  }

  return { done: true };
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}
