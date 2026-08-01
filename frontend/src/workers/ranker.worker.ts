// Web Worker to dedupe and rank jobs in background
type Job = {
  id?: string;
  title: string;
  company?: string;
  location?: string;
  url?: string;
  postedAt?: string;
  source?: string;
};

function normalize(s?: string) {
  if (!s) return '';
  return s.toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, ' ').trim();
}

function fingerprint(job: Partial<Job>) {
  const key = `${normalize(job.title)}|${normalize(job.company)}|${normalize(job.location)}`;
  // simple djb2
  let hash = 5381;
  for (let i = 0; i < key.length; i++) hash = ((hash << 5) + hash) + key.charCodeAt(i);
  return (hash >>> 0).toString(36);
}

function scoreJob(job: Job, q?: string) {
  let score = 0;
  // freshness: newer -> higher
  if (job.postedAt) {
    const ageHours = (Date.now() - new Date(job.postedAt).getTime()) / 36e5;
    score += Math.max(0, 48 - ageHours) / 48; // 0..1
  }
  // simple keyword match
  if (q) {
    const terms = q.split(/\s+/).map(t => normalize(t));
    const hay = normalize(`${job.title} ${job.company} ${job.location} ${job.url}`);
    for (const t of terms) if (t && hay.includes(t)) score += 0.5;
  }
  // source preference (example)
  if (job.source && /localdb/i.test(job.source)) score += 0.3;
  return score;
}

const store = new Map<string, Job>();
const order: string[] = [];

self.addEventListener('message', (ev) => {
  const data = ev.data;
  if (data?.type === 'add') {
    const jobs: Job[] = data.jobs || [];
    let changed = false;
    for (const j of jobs) {
      const id = j.id || fingerprint(j);
      if (!store.has(id)) {
        store.set(id, { ...j, id });
        order.push(id);
        changed = true;
      }
    }
    if (changed) {
      // compute scores and return sorted order (non-destructive)
      const scored = order.map(id => ({ id, score: scoreJob(store.get(id) as Job, data.q) }));
      scored.sort((a, b) => b.score - a.score);
      const sortedOrder = scored.map(s => s.id);
      self.postMessage({ type: 'sorted', order: sortedOrder });
    }
  } else if (data?.type === 'recompute') {
    const jobs: Job[] = data.jobs || [];
    store.clear();
    order.length = 0;
    for (const j of jobs) {
      const id = j.id || fingerprint(j);
      store.set(id, { ...j, id });
      order.push(id);
    }
    const scored = order.map(id => ({ id, score: scoreJob(store.get(id) as Job, data.q) }));
    scored.sort((a, b) => b.score - a.score);
    const sortedOrder = scored.map(s => s.id);
    self.postMessage({ type: 'sorted', order: sortedOrder });
  }
});
