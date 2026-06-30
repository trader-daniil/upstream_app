import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

// ── фиксированная нагрузка: 20 VU в течение 30 секунд ──
export const options = {
  vus: 20,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

// ── свои счётчики: сколько раз ответил каждый апстрим ──
const upstreamHits = {
  'up-9001': new Counter('hits_up_9001'),
  'up-9002': new Counter('hits_up_9002'),
  'up-9003': new Counter('hits_up_9003'),
};

const BASE = 'http://127.0.0.1:8888';

export default function () {
  // — GET / —
  const getRes = http.get(`${BASE}/`);
  check(getRes, {
    'GET / status 200': (r) => r.status === 200,
  });
  countUpstream(getRes);

  // — POST /echo —
  const payload = 'hello world';
  const postRes = http.post(`${BASE}/echo`, payload);
  check(postRes, {
    'POST /echo status 200': (r) => r.status === 200,
    'POST /echo body echoed': (r) => r.json('echo') === payload,
  });
  countUpstream(postRes);
}

// вытаскиваем имя апстрима из JSON-ответа и инкрементим нужный счётчик
function countUpstream(res) {
  try {
    const name = res.json('upstream');
    if (upstreamHits[name]) {
      upstreamHits[name].add(1);
    }
  } catch (e) {
    // ответ не JSON (например, ошибка прокси) — пропускаем
  }
}