/**
 * Norra — Web call token (Cloudflare Worker)
 * Creates a Retell web call so visitors can TALK to Norra in the browser (no phone needed).
 * Secrets:  RETELL_API_KEY,  RETELL_AGENT_ID  (your demo agent's id)
 * POST { language: "Telugu" }  ->  { ok:true, access_token, call_id }
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
    let body = {};
    try { body = await request.json(); } catch {}
    const language = (body && body.language) || "English";
    try {
      const r = await fetch("https://api.retellai.com/v2/create-web-call", {
        method: "POST",
        headers: { Authorization: `Bearer ${env.RETELL_API_KEY}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_id: env.RETELL_AGENT_ID,
          retell_llm_dynamic_variables: { language: language },
        }),
      });
      const data = await r.json();
      if (!r.ok) return json({ ok: false, error: data }, 502);
      return json({ ok: true, access_token: data.access_token, call_id: data.call_id });
    } catch (e) {
      return json({ ok: false, error: String(e.message || e) }, 502);
    }
  },
};

function json(obj, status) {
  return new Response(JSON.stringify(obj), { status: status || 200, headers: { ...CORS, "Content-Type": "application/json" } });
}
