// bestballbutts.rrr-projects.com
//   GET  *         -> proxies the GitHub Pages site (rag30.github.io/best-ball-butts), same content, nicer URL
//   POST /refresh  -> dispatches update.yml on GitHub (the "Rebuild for everyone" button)
// Holds the only credential (GH_TOKEN, a fine-grained PAT: this repo, Actions: write).

const REPO = "Rag30/best-ball-butts";
const WORKFLOW = "update.yml";
const PAGES_ORIGIN = "https://rag30.github.io";
const PAGES_BASE = "/best-ball-butts";
const ALLOWED_ORIGINS = new Set(["https://bestballbutts.rrr-projects.com", PAGES_ORIGIN]);
const COOLDOWN_MS = 2 * 60 * 1000;

const corsFor = origin => ({
  "Access-Control-Allow-Origin": ALLOWED_ORIGINS.has(origin) ? origin : "null",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Vary": "Origin",
});
const json = (obj, status, origin) =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", ...corsFor(origin) } });

async function proxyPages(request, url) {
  const path = url.pathname === "/" ? "/" : url.pathname;
  const upstream = new URL(PAGES_ORIGIN + PAGES_BASE + path + url.search);
  const resp = await fetch(upstream, { headers: { "User-Agent": "bbb-site-proxy" }, cf: { cacheTtl: 60, cacheEverything: true } });
  const headers = new Headers(resp.headers);
  headers.set("Cache-Control", "public, max-age=60");
  return new Response(resp.body, { status: resp.status, headers });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "";

    if (url.pathname !== "/refresh") {
      if (request.method !== "GET" && request.method !== "HEAD") return new Response("Method not allowed", { status: 405 });
      return proxyPages(request, url);
    }

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsFor(origin) });
    if (request.method !== "POST") return json({ error: "POST only" }, 405, origin);
    if (!ALLOWED_ORIGINS.has(origin)) return json({ error: "forbidden" }, 403, origin);

    const ghHeaders = {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "bbb-refresh-worker",
    };

    // Cooldown: GitHub itself is the source of truth — refuse if a manual run started < COOLDOWN ago
    // (or is still queued/running). No Worker state needed, so it works across colos.
    const recent = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/runs?event=workflow_dispatch&per_page=1`, { headers: ghHeaders });
    if (recent.ok) {
      const run = ((await recent.json()).workflow_runs || [])[0];
      if (run) {
        const age = Date.now() - new Date(run.created_at).getTime();
        if (run.status !== "completed" || age < COOLDOWN_MS) {
          return json({ ok: false, reason: "cooldown", retryInSeconds: Math.max(15, Math.ceil((COOLDOWN_MS - age) / 1000)), runUrl: run.html_url }, 429, origin);
        }
      }
    }

    const gh = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
      method: "POST",
      headers: { ...ghHeaders, "Content-Type": "application/json" },
      body: JSON.stringify({ ref: "main" }),
    });
    if (gh.status !== 204) return json({ ok: false, reason: "github", status: gh.status, body: await gh.text() }, 502, origin);
    return json({ ok: true, expectSeconds: 120 }, 200, origin);
  },
};
