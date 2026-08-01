import Fastify from 'fastify';
import cors from 'fastify-cors';
import { streamSearch } from './orchestrator';
import { fingerprint } from './utils/fingerprint';
import { SearchParams } from './types';

const server = Fastify({ logger: true });
server.register(cors, { origin: true });

// Simple SSE endpoint: GET /sse/search?q=...&location=...
server.get('/sse/search', async (req, reply) => {
  const params: SearchParams = req.query as any;

  // prepare SSE response
  reply.raw.setHeader('Content-Type', 'text/event-stream');
  reply.raw.setHeader('Cache-Control', 'no-cache');
  reply.raw.setHeader('Connection', 'keep-alive');
  reply.raw.flushHeaders?.();

  // keep track of fingerprints to avoid sending duplicates
  const seen = new Set<string>();

  try {
    for await (const message of streamSearch(params)) {
      // Server-side lightweight dedupe
      const uniqueJobs = message.jobs.filter((j: any) => {
        const id = j.id || fingerprint(j);
        if (seen.has(id)) return false;
        seen.add(id);
        return true;
      });

      const payload = JSON.stringify({ source: message.source, isPartial: message.isPartial, jobs: uniqueJobs });
      reply.raw.write(`data: ${payload}\n\n`);
    }
    // final event
    reply.raw.write(`event: end\n` + `data: {"status":"complete"}\n\n`);
  } catch (err) {
    const payload = JSON.stringify({ error: String(err) });
    reply.raw.write(`event: error\n` + `data: ${payload}\n\n`);
  }

  // We won't call reply.send() because we used raw streaming
});

const PORT = process.env.PORT ? Number(process.env.PORT) : 3421;
server.listen({ port: PORT, host: '0.0.0.0' }).then(() => {
  server.log.info(`Streaming SSE service listening on ${PORT}`);
});
