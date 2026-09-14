// The launcher contract, exercised end to end against the real fetch handler:
//   - a guest's X-Rrr-Assertion (RS256, signed by a throwaway launcher key served
//     through the injectable JWKS fetcher) trims GET /data to their tabs;
//   - a bare X-Rrr-Tabs header is never authority;
//   - forged, unsigned, expired, wrong-audience or unknown-key assertions are 403;
//   - POST /refresh needs role "write".
//
//   cd worker && npm test          (plain node:test, no dependencies)

import { test } from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync, sign as cryptoSign } from "node:crypto";
import { readFileSync } from "node:fs";
import worker from "../src/index.js";
import { resetJwksCache } from "../src/launcher-identity.js";

const ISSUER = "https://id.rrr-projects.com";
const AUD = "bestballbutts";
const fixture = JSON.parse(readFileSync(new URL("../../data/derived/seasons.json", import.meta.url), "utf8"));

// A pretend launcher: one signing key, published as a JWKS through the injectable fetcher.
const KID = "test-key-1";
const launcher = generateKeyPairSync("rsa", { modulusLength: 2048 });
const impostor = generateKeyPairSync("rsa", { modulusLength: 2048 });
const JWKS = { keys: [{ ...launcher.publicKey.export({ format: "jwk" }), kid: KID, alg: "RS256", use: "sig" }] };
let jwksFetches = 0;
async function fetchJwks(url) {
  assert.equal(url, `${ISSUER}/oidc/jwks`);
  jwksFetches++;
  return JWKS;
}

const b64u = b => Buffer.from(b).toString("base64url");
function assertion(claims = {}, { key = launcher.privateKey, kid = KID, alg = "RS256" } = {}) {
  const now = Math.floor(Date.now() / 1000);
  const h = b64u(JSON.stringify({ alg, kid, typ: "JWT" }));
  const p = b64u(JSON.stringify({ iss: ISSUER, aud: AUD, sub: "u-guest", email: "guest@example.com", name: "Guest",
                                  role: "read", iat: now, exp: now + 120, jti: "j-" + now, ...claims }));
  const s = alg === "none" ? "" : b64u(cryptoSign("RSA-SHA256", Buffer.from(`${h}.${p}`), key));
  return `${h}.${p}.${s}`;
}

// Just enough KV: get(key, "json") and put.
function kv(initial = {}) {
  const store = new Map(Object.entries(initial));
  return {
    store,
    async get(k, type) { const v = store.get(k); if (v == null) return null; return type === "json" ? JSON.parse(v) : v; },
    async put(k, v) { store.set(k, String(v)); },
  };
}
const makeEnv = () => ({ DATA: kv({ snapshot: JSON.stringify(fixture) }), LAUNCHER_JWKS_FETCH: fetchJwks });
const req = (path, init = {}) => new Request(`https://bestballbutts.rrr-projects.com${path}`, init);
const signed = (jwt, init = {}) => ({ ...init, headers: { ...(init.headers || {}), "x-rrr-assertion": jwt } });

const SCORED = ["2024", "2025"];   // seasons in the fixture with real tables (2026 is pre-season)
const LUCK = ["ui3", "ui4", "ui5", "sum3", "sum4", "sum5", "flips3", "flips4", "flips5", "projected", "projMean"];
const STANDINGS = ["standings", "medianStandings", "oppScores", "results", "medianResults", "weeklyMedian", "margin", "seasonAvg"];
const has = (obj, keys) => keys.filter(k => k in obj);

test("guest with tabs [standings]: luck, sos and reports are gone; standings stay", async () => {
  resetJwksCache();
  const r = await worker.fetch(req("/data", signed(assertion({ tabs: ["standings"] }))), makeEnv());
  assert.equal(r.status, 200);
  const body = await r.json();
  assert.deepEqual(body.tabs, ["standings"]);
  assert.deepEqual(body.career, []);
  for (const yr of SCORED) {
    const s = body.seasons[yr];
    assert.deepEqual(has(s, [...LUCK, "sos", "weeklyReports"]), [], `${yr} still carries luck/sos/reports keys`);
    assert.deepEqual(has(s, [...STANDINGS, "scores", "opponents"]), [...STANDINGS, "scores", "opponents"], `${yr} lost a standings key`);
    assert.ok(Array.isArray(s.standings) && s.standings.length > 0);
    assert.ok(Array.isArray(s.medianStandings) && s.medianStandings.length > 0);
  }
  assert.ok("schedule" in body.seasons["2026"], "pre-season schedule is a standings key");
});

test("guest with only luck-sos: sos stays, the other luck fields and all standings go", async () => {
  const r = await worker.fetch(req("/data", signed(assertion({ tabs: ["luck", "luck-sos"] }))), makeEnv());
  assert.equal(r.status, 200);
  const body = await r.json();
  for (const yr of SCORED) {
    const s = body.seasons[yr];
    assert.ok(s.sos && Object.keys(s.sos).length > 0, `${yr} lost sos`);
    assert.deepEqual(has(s, [...LUCK, ...STANDINGS, "weeklyReports"]), [], `${yr} leaked a key`);
    // The luck tooltips say "scored X vs Y", so scores/opponents ride along with the luck tab.
    assert.ok(s.scores && s.opponents);
  }
  assert.equal("schedule" in body.seasons["2026"], false);
  assert.equal("rosters" in body.seasons["2026"], false);
});

test("guest with no tabs at all gets no tables", async () => {
  const r = await worker.fetch(req("/data", signed(assertion({ tabs: [] }))), makeEnv());
  assert.equal(r.status, 200);
  const body = await r.json();
  assert.deepEqual(body.tabs, []);
  for (const yr of SCORED) {
    assert.deepEqual(has(body.seasons[yr], [...LUCK, ...STANDINGS, "sos", "weeklyReports", "scores", "opponents"]), []);
  }
});

test("X-Rrr-Tabs alone is a hint, never authority: the verified claim wins", async () => {
  const r = await worker.fetch(req("/data", signed(assertion({ tabs: ["standings"] }), { headers: { "x-rrr-tabs": "standings,luck,reports" } })), makeEnv());
  const body = await r.json();
  assert.deepEqual(body.tabs, ["standings"]);
  assert.deepEqual(has(body.seasons["2025"], [...LUCK, "weeklyReports"]), []);
});

test("no assertion = a public viewer forwarded by the gate: the whole feed", async () => {
  const r = await worker.fetch(req("/data"), makeEnv());
  assert.equal(r.status, 200);
  const body = await r.json();
  assert.equal("tabs" in body, false);
  assert.ok(body.career.length > 0);
  assert.deepEqual(has(body.seasons["2025"], [...LUCK, ...STANDINGS, "sos", "weeklyReports"]), [...LUCK, ...STANDINGS, "sos", "weeklyReports"]);
});

test("a whole-app assertion (no tabs claim) gets everything", async () => {
  const r = await worker.fetch(req("/data", signed(assertion({ tabs: undefined }))), makeEnv());
  const body = await r.json();
  assert.equal("tabs" in body, false);
  assert.ok(body.seasons["2025"].ui5 && body.seasons["2025"].standings);
});

test("forged assertion (another key, same kid) is refused", async () => {
  const r = await worker.fetch(req("/data", signed(assertion({ tabs: ["standings"] }, { key: impostor.privateKey }))), makeEnv());
  assert.equal(r.status, 403);
});

test("unsigned assertion (alg none) is refused", async () => {
  const r = await worker.fetch(req("/data", signed(assertion({ tabs: ["standings"] }, { alg: "none" }))), makeEnv());
  assert.equal(r.status, 403);
});

test("garbage in the header is refused, not treated as public", async () => {
  const r = await worker.fetch(req("/data", signed("not.a.jwt")), makeEnv());
  assert.equal(r.status, 403);
  const r2 = await worker.fetch(req("/data", signed("x")), makeEnv());
  assert.equal(r2.status, 403);
});

test("expired assertion is refused", async () => {
  const past = Math.floor(Date.now() / 1000) - 10;
  const r = await worker.fetch(req("/data", signed(assertion({ exp: past }))), makeEnv());
  assert.equal(r.status, 403);
});

test("assertion for another app (aud) or another issuer is refused", async () => {
  assert.equal((await worker.fetch(req("/data", signed(assertion({ aud: "ledger" }))), makeEnv())).status, 403);
  assert.equal((await worker.fetch(req("/data", signed(assertion({ iss: "https://evil.example" }))), makeEnv())).status, 403);
});

test("unknown kid refetches the JWKS at most once a minute, then refuses", async () => {
  const before = jwksFetches;
  assert.equal((await worker.fetch(req("/data", signed(assertion({}, { kid: "rotated" }))), makeEnv())).status, 403);
  assert.equal((await worker.fetch(req("/data", signed(assertion({}, { kid: "rotated" }))), makeEnv())).status, 403);
  assert.equal(jwksFetches - before, 1);
});

test("env can override issuer and aud", async () => {
  const env = { ...makeEnv(), LAUNCHER_ISSUER: "https://id.example", LAUNCHER_AUD: "bbb-staging" };
  // The stub still answers at <issuer>/oidc/jwks; relax the URL check for this one.
  env.LAUNCHER_JWKS_FETCH = async () => JWKS;
  resetJwksCache();
  const good = await worker.fetch(req("/data", signed(assertion({ iss: "https://id.example", aud: "bbb-staging", tabs: ["reports"] }))), env);
  assert.equal(good.status, 200);
  assert.deepEqual((await good.json()).tabs, ["reports"]);
  const wrong = await worker.fetch(req("/data", signed(assertion({ tabs: ["reports"] }))), env);   // production iss/aud
  assert.equal(wrong.status, 403);
  resetJwksCache();
});

test("POST /refresh: no assertion or role read is refused with {error:'read only'}", async () => {
  const anon = await worker.fetch(req("/refresh", { method: "POST" }), makeEnv());
  assert.equal(anon.status, 403);
  assert.deepEqual(await anon.json(), { error: "read only" });
  const env = makeEnv();
  const reader = await worker.fetch(req("/refresh", signed(assertion({ role: "read" }), { method: "POST" })), env);
  assert.equal(reader.status, 403);
  assert.deepEqual(await reader.json(), { error: "read only" });
  assert.equal(env.DATA.store.has("lastRefresh"), false, "a refused refresh must not touch KV");
});

test("POST /refresh: role write proceeds to Sleeper and writes KV", async () => {
  const realFetch = globalThis.fetch;
  const seen = [];
  globalThis.fetch = async (url) => {
    const u = String(url); seen.push(u);
    if (u.endsWith("/v1/state/nfl")) return Response.json({ season: "2025", week: 3 });
    if (u.includes("/v1/user/raghavr7")) return Response.json({ user_id: "1" });
    if (u.includes("/leagues/nfl/")) return Response.json([]);      // no leagues found: nothing to compute
    throw new Error("unexpected fetch " + u);
  };
  try {
    const env = makeEnv();
    const r = await worker.fetch(req("/refresh", signed(assertion({ role: "write" }), { method: "POST" })), env);
    const text = await r.text();
    assert.equal(r.status, 200, text);
    const body = JSON.parse(text);
    assert.equal(body.ok, true);
    assert.ok(env.DATA.store.has("lastRefresh"), "refresh stamped the cooldown");
    assert.ok(env.DATA.store.has("leagues"), "refresh cached the league map");
    assert.ok(seen.some(u => u.endsWith("/v1/state/nfl")), "refresh asked Sleeper for the NFL state");
  } finally {
    globalThis.fetch = realFetch;
  }
});

test("GET /.rrr/manifest is public and names every tab the trim knows", async () => {
  const r = await worker.fetch(req("/.rrr/manifest"), makeEnv());
  assert.equal(r.status, 200);
  const m = await r.json();
  assert.equal(m.app, AUD);
  const ids = m.tabs.flatMap(t => [t.id, ...(t.children || []).map(c => c.id)]);
  assert.deepEqual(ids, ["standings", "luck", "luck-net", "luck-schedule", "luck-roster", "luck-sos", "reports"]);
});
