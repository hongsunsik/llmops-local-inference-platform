import http from 'k6/http';
import { check, sleep } from 'k6';

// A single local Ollama instance serializes inference on one model, so it has no
// concurrent throughput to test: sending 2 req/s (the original profile) just queues
// requests behind each other and pushes p95 past 50s. Measured single-request
// latency for qwen3:8b on this hardware is ~15s, so this scenario models the
// realistic case for this platform -- one active user issuing sequential
// requests -- with headroom above that baseline.
export const options = {
  scenarios: {
    single_user: {
      executor: 'constant-vus',
      vus: 1,
      duration: '45s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<20000'],
  },
};

const baseUrl = __ENV.BASE_URL || 'http://localhost:8080';

export default function () {
  const response = http.post(
    `${baseUrl}/v1/chat/completions`,
    JSON.stringify({
      messages: [{ role: 'user', content: 'Explain one benefit of request tracing.' }],
      temperature: 0,
    }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  check(response, {
    'status is 200': (r) => r.status === 200,
    'has model': (r) => Boolean(r.json('model')),
  });
  sleep(1);
}
