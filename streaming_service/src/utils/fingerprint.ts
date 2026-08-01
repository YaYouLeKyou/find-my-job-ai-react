import crypto from 'crypto';

export function normalizeText(s?: string) {
  if (!s) return '';
  return s
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[\u2018\u2019\u201c\u201d]/g, "'")
    .replace(/[^a-z0-9\s]/g, '')
    .trim();
}

export function fingerprint(job: { title?: string; company?: string; location?: string }) {
  const key = `${normalizeText(job.title)}|${normalizeText(job.company)}|${normalizeText(job.location)}`;
  return crypto.createHash('sha256').update(key).digest('hex').slice(0, 12);
}
