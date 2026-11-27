// k6 script: register a team through POST /api/register/team (operation under test).
//
//   k6 run -e VUS=1 scripts/perf_register.js      one simulated user
//   k6 run -e VUS=5 scripts/perf_register.js      five at the same time
//
// Each run has a warm-up phase (not measured) and a measured phase that starts only once all users
// are running. Only requests of the measured phase count towards the limits. Limits (set BEFORE the
// runs, see docs/performance.md): p95 response time and unexpected-failure rate below.
//
// An "unexpected failure" is any response that is not HTTP 200 with {"success": true}. Every team
// name is unique, so no business rule should reject a request.
import http from 'k6/http';
import { check } from 'k6';
import { Rate, Counter } from 'k6/metrics';

const BASE = __ENV.BASE_URL || 'http://127.0.0.1:5056';
const VUS = Number.parseInt(__ENV.VUS || '1', 10);
const P95_MS = Number.parseInt(__ENV.P95_MS || '500', 10);
const MAX_FAIL = Number.parseFloat(__ENV.MAX_FAIL || '0.01');
const WARMUP = __ENV.WARMUP || '10s';
const MEASURE = __ENV.MEASURE || '60s';
const HEADERS = { headers: { 'Content-Type': 'application/json' } };

export const unexpected = new Rate('unexpected_failures');
export const registered = new Counter('registered_ok');

export const options = {
  scenarios: {
    warmup: { executor: 'constant-vus', vus: VUS, duration: WARMUP, exec: 'register', tags: { phase: 'warmup' } },
    measure: { executor: 'constant-vus', vus: VUS, duration: MEASURE, startTime: WARMUP, exec: 'register',
               tags: { phase: 'measure' } },
  },
  thresholds: {
    'http_req_duration{phase:measure}': [`p(95)<${P95_MS}`],
    'unexpected_failures{phase:measure}': [`rate<${MAX_FAIL}`],
    'http_reqs{phase:measure}': ['count>=0'],   // listed so the summary reports the measured request count
    'registered_ok': ['count>=0'],
  },
};

function registeredCount() {
  const r = http.post(`${BASE}/api/register/validate-code`, JSON.stringify({ code: 'PERF01' }), HEADERS);
  return r.json('tournament.registered_teams');
}

export function setup() {
  return { start: registeredCount() };
}

export function register() {
  const body = JSON.stringify({
    code: 'PERF01', team_name: `K${__VU}-${__ITER}`, player1: 'Ann', player2: 'Bob',
  });
  const res = http.post(`${BASE}/api/register/team`, body, HEADERS);
  const ok = check(res, {
    'status is 200': (r) => r.status === 200,
    'success is true': (r) => r.status === 200 && r.json('success') === true,
  });
  unexpected.add(!ok);
  if (ok) registered.add(1);
}

export function teardown(data) {
  // read back the shared record: the server's count must equal what k6 saw succeed (see run_perf.py)
  console.log(`READBACK start=${data.start} end=${registeredCount()}`);
}
