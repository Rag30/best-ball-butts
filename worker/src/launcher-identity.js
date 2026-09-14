// worker/src/launcher-identity.js — who the launcher says this is.
//
// The rrr-projects launcher fronts every hostname of this app and forwards an
// admitted request with X-Rrr-Assertion: an RS256 JWT (two-minute life) naming
// the person, their role and, for this filterable app, the tabs they may use.
// This module verifies it against the launcher's JWKS with WebCrypto. Nothing
// else on the request is identity: X-Rrr-Tabs / X-Rrr-Email / X-Rrr-Role are
// convenience mirrors of the claim, never something the Worker decides by.
// Contract: AI Tools repo, auth&sharing guidelines.md §5–§7.

const DEFAULT_ISSUER = "https://id.rrr-projects.com";
const DEFAULT_AUD = "bestballbutts";           // the catalog id
const JWKS_FRESH_MS = 10 * 60_000;             // reuse fetched keys this long
const JWKS_RETRY_MS = 60_000;                  // an unknown kid (or a failed fetch) refetches at most this often

let jwks = null;   // { issuer, keys: Map<kid, CryptoKey>, at, missAt }

function b64urlToBytes(s) {
  const pad = s.length % 4 === 2 ? "==" : s.length % 4 === 3 ? "=" : "";
  const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/") + pad);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
const decodeJson = s => JSON.parse(new TextDecoder().decode(b64urlToBytes(s)));

async function defaultFetchJwks(url) {
  const r = await fetch(url, { headers: { "User-Agent": "bbb-worker" } });
  if (!r.ok) throw new Error(`jwks ${r.status}`);
  return r.json();
}

async function loadKeys(issuer, fetchJwks) {
  const body = await fetchJwks(`${issuer}/oidc/jwks`);
  const keys = new Map();
  for (const k of (body && body.keys) || []) {
    if (!k || k.kty !== "RSA" || typeof k.kid !== "string") continue;
    if (k.alg && k.alg !== "RS256") continue;
    try {
      keys.set(k.kid, await crypto.subtle.importKey("jwk", { kty: "RSA", n: k.n, e: k.e, alg: "RS256", ext: true },
        { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]));
    } catch { /* skip a malformed key; the others still count */ }
  }
  return keys;
}

async function reload(issuer, fetchJwks, now, afterMiss) {
  try {
    jwks = { issuer, keys: await loadKeys(issuer, fetchJwks), at: now, missAt: afterMiss ? now : 0 };
  } catch (e) {
    // Launcher unreachable: keep the keys we have and try again in a minute rather than hammer it.
    if (jwks && jwks.issuer === issuer) { jwks.at = now - JWKS_FRESH_MS + JWKS_RETRY_MS; jwks.missAt = now; }
    else throw e;
  }
}

async function keyFor(kid, issuer, fetchJwks) {
  const now = Date.now();
  if (!jwks || jwks.issuer !== issuer || now - jwks.at > JWKS_FRESH_MS) await reload(issuer, fetchJwks, now, false);
  if (!jwks.keys.has(kid) && now - jwks.missAt > JWKS_RETRY_MS) await reload(issuer, fetchJwks, now, true);
  return jwks.keys.get(kid) || null;
}

/**
 * Verify the request's X-Rrr-Assertion.
 *
 * Returns { sub, email, name, role: "read"|"write", tabs: string[]|null } — tabs is
 * null for a whole-app share — or null when the header is absent, malformed, forged,
 * expired, or not for this app. A caller that must tell "absent" from "bad" checks
 * the header itself; the two are deliberately the same answer here.
 *
 * opts: issuer (LAUNCHER_ISSUER), aud (LAUNCHER_AUD), fetchJwks(url) -> Promise<{keys}>
 * (injectable so tests can serve their own keys).
 */
export async function launcherIdentity(request, { issuer = DEFAULT_ISSUER, aud = DEFAULT_AUD, fetchJwks = defaultFetchJwks } = {}) {
  const headers = request && request.headers ? request.headers : request;
  const jwt = headers && typeof headers.get === "function" ? headers.get("x-rrr-assertion") : null;
  if (!jwt) return null;
  try {
    const parts = jwt.split(".");
    if (parts.length !== 3) return null;
    const [h, p, s] = parts;
    const header = decodeJson(h);
    if (!header || header.alg !== "RS256" || typeof header.kid !== "string") return null;
    const key = await keyFor(header.kid, issuer, fetchJwks);
    if (!key) return null;
    const ok = await crypto.subtle.verify({ name: "RSASSA-PKCS1-v1_5" }, key, b64urlToBytes(s), new TextEncoder().encode(`${h}.${p}`));
    if (!ok) return null;
    const payload = decodeJson(p);
    if (!payload || payload.iss !== issuer) return null;
    if (!(Array.isArray(payload.aud) ? payload.aud.includes(aud) : payload.aud === aud)) return null;
    const now = Math.floor(Date.now() / 1000);
    if (typeof payload.exp !== "number" || payload.exp <= now) return null;
    if (typeof payload.email !== "string" || !payload.email) return null;
    return {
      sub: typeof payload.sub === "string" ? payload.sub : null,
      email: payload.email,
      name: payload.name ? String(payload.name) : null,
      role: payload.role === "write" ? "write" : "read",
      tabs: Array.isArray(payload.tabs) ? payload.tabs.map(String) : null,
    };
  } catch {
    return null;
  }
}

/** Forget cached keys (tests). */
export function resetJwksCache() { jwks = null; }
