/**
 * Norra — Calls API (Cloudflare Worker)
 * Pulls calls from Retell and returns them in the shape the Norra dashboard expects.
 * Your Retell API key stays server-side (never in the browser).
 *
 * DEPLOY:
 *  1. Cloudflare dashboard → Workers & Pages → Create → Worker. Paste this file. Deploy.
 *  2. Worker → Settings → Variables → add a SECRET named RETELL_API_KEY (your Retell key).
 *  3. Copy the Worker URL (e.g. https://norra-calls.<you>.workers.dev).
 *  4. In Norra-AI-Front-Desk-Customer-Dashboard.html set NORRA_API to that URL,
 *     and NORRA_AGENT to the agent_id of the client you want to show.
 *
 * Optional: in the Retell agent's "Post-call analysis", add custom fields named
 *   caller_name, appointment_type, appointment_time, language, intent, appointment_booked
 * and they'll show up automatically in the dashboard's call detail.
 */

export default {
  async fetch(request, env) {
    const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });

    const url = new URL(request.url);
    const agent = url.searchParams.get("agent");
    const body = { sort_order: "descending", limit: 50 };
    if (agent) body.filter_criteria = { agent: [{ agent_id: agent }] };

    let data;
    try {
      const r = await fetch("https://api.retellai.com/v3/list-calls", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${env.RETELL_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      data = await r.json();
      if (!r.ok) return json({ error: data }, 502, cors);
    } catch (e) {
      return json({ error: String(e) }, 502, cors);
    }

    const items = data.items || [];
    const calls = items
      .filter(c => c.call_status === "ended")
      .map(mapCall);
    return json({ calls }, 200, cors);
  },
};

function json(obj, status, cors) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });
}

function mapCall(c) {
  const a = c.call_analysis || {};
  const cd = a.custom_analysis_data || {};
  const start = c.start_timestamp ? new Date(c.start_timestamp) : null;
  const dur = c.duration_ms ? Math.round(c.duration_ms / 1000) : 0;

  let type = "lead";
  if (cd.appointment_booked === true || cd.appointment_booked === "true" || cd.appointment_type) type = "book";
  if (cd.order_total || cd.is_order === true) type = "order";
  if (c.disconnection_reason === "call_transfer" || cd.urgent === true || cd.urgent === "true") type = "urgent";

  const fields = {};
  if (cd.caller_name) fields["Name"] = cd.caller_name;
  if (cd.appointment_type) fields["Service"] = cd.appointment_type;
  if (cd.appointment_time) fields["When"] = cd.appointment_time;
  if (cd.intent) fields["Reason"] = cd.intent;
  fields["Phone"] = c.from_number || (c.call_type === "web_call" ? "Web call" : "—");

  const actions = [];
  if (a.call_summary) actions.push("Summary generated for owner");
  if (type === "book") actions.push("Appointment booked");
  if (c.disconnection_reason === "call_transfer") actions.push("Transferred to a human");
  if (c.recording_url) actions.push("Recording available");

  return {
    id: c.call_id,
    time: start ? fmtTime(start) : "—",
    caller: c.from_number || (c.call_type === "web_call" ? "Web call" : "—"),
    lang: cd.language || (a.user_sentiment ? "—" : "—"),
    type,
    after: start ? isAfterHours(start) : false,
    dur,
    value: 0,
    title: a.call_summary ? firstSentence(a.call_summary) : (cd.intent || "Call"),
    summary: a.call_summary || "Summary will appear here once Retell finishes post-call analysis.",
    fields,
    actions: actions.length ? actions : ["Call handled by Norra"],
    transcript: parseTranscript(c.transcript),
    sms: false,
  };
}

function fmtTime(d) {
  try {
    const day = d.toLocaleDateString("en-CA", { weekday: "short", timeZone: "America/Toronto" });
    const t = d.toLocaleTimeString("en-CA", { hour: "numeric", minute: "2-digit", timeZone: "America/Toronto" });
    return `${day} · ${t}`;
  } catch { return d.toISOString(); }
}

function isAfterHours(d) {
  try {
    const s = d.toLocaleString("en-CA", { timeZone: "America/Toronto", weekday: "short", hour: "2-digit", hour12: false });
    const hour = parseInt(d.toLocaleString("en-CA", { timeZone: "America/Toronto", hour: "2-digit", hour12: false }), 10);
    const wd = d.toLocaleDateString("en-CA", { timeZone: "America/Toronto", weekday: "short" });
    const weekend = wd === "Sat" || wd === "Sun";
    return weekend || hour < 8 || hour >= 18;
  } catch { return false; }
}

function firstSentence(s) {
  const m = String(s).split(/(?<=[.!?])\s/)[0];
  return m.length > 90 ? m.slice(0, 88) + "…" : m;
}

// Retell transcript is a string like "Agent: ...\nUser: ...". Best-effort parse into turns.
function parseTranscript(t) {
  if (!t || typeof t !== "string") return [];
  return t.split(/\n+/).map(line => {
    const m = line.match(/^\s*(Agent|User|Assistant)\s*:\s*(.*)$/i);
    if (!m) return null;
    const who = /user/i.test(m[1]) ? "caller" : "ai";
    return { w: who, t: m[2] };
  }).filter(Boolean);
}
