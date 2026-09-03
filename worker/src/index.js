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
    if (request.method === "GET") {
      return new Response(
        "bbb-refresh relay is up.\n\nThis endpoint is used by the \"Rebuild for everyone\" button on\nhttps://rag30.github.io/best-ball-butts/ — nothing to see here.\n",
        { headers: { "Content-Type": "text/plain; charset=utf-8" } });
    }
    if (url.pathname !== "/refresh") return json({ error: "not found" }, 404);
    if (request.method !== "POST") return json({ error: "POST only" }, 405);
    if (request.headers.get("Origin") !== ALLOWED_ORIGIN) return json({ error: "forbidden" }, 403);

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
          return json({ ok: false, reason: "cooldown", retryInSeconds: Math.max(15, Math.ceil((COOLDOWN_MS - age) / 1000)), runUrl: run.html_url }, 429);
        }
      }
    }

    const gh = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
      method: "POST",
      headers: { ...ghHeaders, "Content-Type": "application/json" },
      body: JSON.stringify({ ref: "main" }),
    });
    if (gh.status !== 204) return json({ ok: false, reason: "github", status: gh.status, body: await gh.text() }, 502);
    return json({ ok: true, expectSeconds: 120 });
  },
};
