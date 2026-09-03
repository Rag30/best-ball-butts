// bbb-refresh: lets the public page trigger a shared rebuild.
//   POST https://bbb-refresh.rrr-projects.com/refresh  -> dispatches update.yml on GitHub
// Holds the only credential (GH_TOKEN, a fine-grained PAT: this repo, Actions: write).
// Rate-limited to one dispatch per 2 minutes so a stuck finger can't spam Actions.

const REPO = "Rag30/best-ball-butts";
const WORKFLOW = "update.yml";
const ALLOWED_ORIGIN = "https://rag30.github.io";
const COOLDOWN_MS = 2 * 60 * 1000;

const cors = {
  "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", ...cors } });

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (url.pathname !== "/refresh") return json({ error: "not found" }, 404);
    if (request.method !== "POST") return json({ error: "POST only" }, 405);
    if (request.headers.get("Origin") !== ALLOWED_ORIGIN) return json({ error: "forbidden" }, 403);

    // Cooldown via the Cache API (per-colo, good enough for a rate limit)
    const cache = caches.default;
    const key = new Request("https://bbb-refresh.internal/last-dispatch");
    const last = await cache.match(key);
    if (last) {
      const at = Number(await last.text());
      const wait = Math.ceil((at + COOLDOWN_MS - Date.now()) / 1000);
      if (wait > 0) return json({ ok: false, reason: "cooldown", retryInSeconds: wait }, 429);
    }

    const gh = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GH_TOKEN}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "bbb-refresh-worker",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: "main" }),
    });
    if (gh.status !== 204) return json({ ok: false, reason: "github", status: gh.status, body: await gh.text() }, 502);

    await cache.put(key, new Response(String(Date.now()), { headers: { "Cache-Control": `max-age=${COOLDOWN_MS / 1000}` } }));
    return json({ ok: true, expectSeconds: 120 });
  },
};
