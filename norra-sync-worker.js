/**
 * Norra — Knowledge → Retell sync (Cloudflare Worker)
 * Secret needed:  RETELL_API_KEY
 * POST { client:{ retell_llm_id, retell_agent_id }, knowledge:{...}, publish:true }
 *      -> { ok:true, llm_id }
 * Rebuilds the agent's prompt from the knowledge and PATCHes the Retell LLM.
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
    let body;
    try { body = await request.json(); } catch { return json({ ok: false, error: "Invalid JSON" }, 400); }
    try {
      const result = await syncClient(body.client, body.knowledge, env.RETELL_API_KEY, { publish: !!body.publish });
      return json({ ok: true, llm_id: result.llm_id, warning: result.warning || null });
    } catch (e) {
      console.log("sync error:", String(e.message || e));
      return json({ ok: false, error: String(e.message || e) }, 502);
    }
  },
};

function json(obj, status) {
  return new Response(JSON.stringify(obj), { status: status || 200, headers: { ...CORS, "Content-Type": "application/json" } });
}

function buildPrompt(k) {
  return [
    `You are Norra, the friendly virtual assistant for ${k.business_name || "this business"}` +
      (k.business_type ? `, a ${k.business_type}` : "") + ".",
    "",
    "MANNER: Warm, natural, and unhurried — like a great front-desk person. Short sentences. Use the caller's first name once you know it. Never sound scripted.",
    "",
    `IDENTITY & HONESTY: Greet the caller and identify yourself as a virtual assistant (e.g. "Thanks for calling ${k.business_name || "us"}, this is Norra, the virtual assistant — calls may be recorded to help with your request. How can I help?"). If asked whether you are a real person, say honestly that you are the virtual assistant, and offer to connect a team member.`,
    "",
    "GREETING LANGUAGE: Begin by greeting the caller warmly in {{language}} (use English if {{language}} is empty), then continue in that language. If the caller switches to another language, follow them.",
    "",
    k.languages ? `LANGUAGES: If the caller speaks ${k.languages}, continue in that language.` : "",
    "",
    "BOOKING: Find out what they need and their preferred day/time. Use the booking tool to check REAL availability — never invent a time the tool hasn't confirmed. Collect their name and mobile number. Read the appointment back to confirm, then send an SMS confirmation.",
    "",
    "GUARDRAILS: Only state facts from the knowledge base below. If you don't know something, say so and offer to take a message or book a visit. Do not give professional, medical, legal, or financial advice. If a caller describes an emergency, tell them to hang up and call their local emergency number.",
    "",
    "TRANSFER: If the caller is upset, has a complex issue, or asks for a person, offer to transfer or take a detailed message" +
      (k.transfer_number ? ` (transfer to ${k.transfer_number}).` : "."),
    "",
    "--- BUSINESS KNOWLEDGE BASE ---",
    renderKnowledge(k),
  ].filter(Boolean).join("\n");
}

function renderKnowledge(k) {
  const lines = [];
  if (k.business_name) lines.push(`Business: ${k.business_name}${k.address ? ", " + k.address : ""}.`);
  if (k.hours) lines.push(`Hours: ${k.hours}.`);
  if (k.service_area) lines.push(`Service area: ${k.service_area}.`);
  if (k.languages) lines.push(`Languages: ${k.languages}.`);
  const services = Array.isArray(k.services) ? k.services : [];
  if (services.length) {
    lines.push("Services (name — duration — price — provider):");
    services.forEach(s => lines.push(`- ${s.name || ""}${s.duration ? " — " + s.duration : ""}${s.price ? " — " + s.price : ""}${s.provider ? " — " + s.provider : ""}`));
  }
  const faqs = Array.isArray(k.faqs) ? k.faqs : [];
  if (faqs.length) {
    lines.push("FAQs:");
    faqs.forEach(f => lines.push(`- Q: ${f.q}  A: ${f.a}`));
  }
  if (k.policies) lines.push(`Policies: ${k.policies}`);
  return lines.join("\n");
}

async function updateRetellLLM(llmId, generalPrompt, apiKey) {
  const res = await fetch(`https://api.retellai.com/update-retell-llm/${llmId}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ general_prompt: generalPrompt }),
  });
  if (!res.ok) throw new Error(`Retell update failed (${res.status}): ${await res.text()}`);
  return res.json();
}

async function publishAgent(agentId, apiKey) {
  const res = await fetch(`https://api.retellai.com/publish-agent/${agentId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`Publish failed (${res.status}): ${await res.text()}`);
  return res.json();
}

async function syncClient(client, knowledge, apiKey, opts) {
  const prompt = buildPrompt(knowledge);
  const result = await updateRetellLLM(client.retell_llm_id, prompt, apiKey);
  let warning = null;
  // Publishing is best-effort — if it fails, the knowledge still updated, so don't fail the whole call.
  if (opts && opts.publish && client.retell_agent_id) {
    try { await publishAgent(client.retell_agent_id, apiKey); }
    catch (e) { warning = "Knowledge updated; publish step failed: " + String(e.message || e); }
  }
  return { llm_id: result.llm_id, warning };
}
