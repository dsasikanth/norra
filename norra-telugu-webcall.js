/**
 * Norra Telugu web-call (Cloudflare Worker)
 * Starts a session with your Pipecat Cloud agent (norra-telugu) so a website
 * visitor can TALK to the real Sarvam Telugu Norra in the browser.
 *
 * Secrets to set in the Cloudflare dashboard:
 *   PIPECAT_PUBLIC_KEY  = your Pipecat Cloud PUBLIC api key (pk_...)
 *   PIPECAT_AGENT       = norra-telugu
 *
 * POST  ->  { ok:true, room:"<daily url>", token:"<daily token>" }
 * The browser then joins that Daily room with the Daily JS SDK.
 */
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (request.method !== "POST") return json({ ok: false, error: "POST only" }, 405);
    let inBody = {};
    try { inBody = await request.json(); } catch (e) {}
    // Forward the business profile (if the demo console sent one) to the agent.
    const agentBody = { source: "website" };
    for (const k of ["language", "name", "vertical", "info", "voice", "demo", "notes"]) {
      if (inBody && inBody[k]) agentBody[k] = inBody[k];
    }
    if (!agentBody.language) agentBody.language = "Telugu";
    try {
      const agent = env.PIPECAT_AGENT || "norra-telugu";
      const r = await fetch(`https://api.pipecat.daily.co/v1/public/${agent}/start`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.PIPECAT_PUBLIC_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ createDailyRoom: true, body: agentBody }),
      });
      const data = await r.json();
      if (!r.ok) return json({ ok: false, error: data }, 502);
      return json({ ok: true, room: data.dailyRoom, token: data.dailyToken });
    } catch (e) {
      return json({ ok: false, error: String(e.message || e) }, 502);
    }
  },
};

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}
