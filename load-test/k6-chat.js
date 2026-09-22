import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    steady_load: {
      executor: 'constant-arrival-rate',
      rate: 2,
      timeUnit: '1s',
      duration: '30s',
      preAllocatedVUs: 2,
      maxVUs: 4,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<10000'],
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
