/**
 * Cloudflare Worker - joblink "API Gateway" (1:1 replacement).
 *
 * Routes exactly like the AWS HTTP API did:
 *   POST /api/scrape            -> scraper service (HF Space)
 *   everything else under /api/ -> api service (HF Space)
 * CORS mirrors the original cors_configuration.
 *
 * Vars (wrangler.toml / dashboard):
 *   API_ORIGIN     e.g. https://<user>-joblink-api.hf.space
 *   SCRAPER_ORIGIN e.g. https://<user>-joblink-scraper.hf.space
 */
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Scrape-Password',
  'Access-Control-Max-Age': '3600',
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS });
    }

    const isScrape = url.pathname === '/api/scrape' && request.method === 'POST';
    const origin = isScrape ? env.SCRAPER_ORIGIN : env.API_ORIGIN;

    const upstream = new URL(url.pathname + url.search, origin);
    const resp = await fetch(upstream, {
      method: request.method,
      headers: request.headers,
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
    });

    const out = new Response(resp.body, resp);
    for (const [k, v] of Object.entries(CORS)) out.headers.set(k, v);
    return out;
  },
};
