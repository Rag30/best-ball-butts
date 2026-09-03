// bestballbutts.rrr-projects.com
// Serves the GitHub Pages site (rag30.github.io/best-ball-butts) under the league's own domain.
// No credentials, no state — the page itself fetches live data from Sleeper in the browser.

const PAGES_ORIGIN = "https://rag30.github.io";
const PAGES_BASE = "/best-ball-butts";

export default {
  async fetch(request) {
    if (request.method !== "GET" && request.method !== "HEAD") return new Response("Method not allowed", { status: 405 });
    const url = new URL(request.url);
    const upstream = new URL(PAGES_ORIGIN + PAGES_BASE + url.pathname + url.search);
    const resp = await fetch(upstream, { headers: { "User-Agent": "bbb-site-proxy" }, cf: { cacheTtl: 60, cacheEverything: true } });
    const headers = new Headers(resp.headers);
    headers.set("Cache-Control", "public, max-age=60");
    return new Response(resp.body, { status: resp.status, headers });
  },
};
