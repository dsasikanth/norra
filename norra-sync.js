/**
 * Norra — Knowledge → Retell sync engine
 * --------------------------------------------------------------
 * Rebuilds an agent's prompt from a customer's knowledge and pushes it to
 * Retell with PATCH /update-retell-llm/{llm_id} (the `general_prompt` field).
 *
 * This is the "magic" piece: when a customer edits their info in the Norra
 * dashboard and saves, you call syncClient(...) and the live agent updates.
 *
 * Runs anywhere Node runs — AWS Lambda, a server, Vercel, Cloudflare (with fetch).
 * Keep your Retell API key in an env var / AWS Secrets Manager (never in code).
 */

// ---- 1. Build the prompt from structured knowledge ----
function buildPrompt(k) {
  return [
    `You are Ava, the friendly virtual assistant for ${k.business_name || "this business"}` +
      (k.business_type ? `, a ${k.business_type}` : "") + ".",
    "",
    "MANNER: Warm, natural, and unhurried — like a great front-desk person. Short sentences. Use the caller's first name once you know it. Never sound scripted. Acknowledge what the caller says before moving on.",
    "",
    `IDENTITY & HONESTY: Greet the caller and identify yourself as a virtual assistant (e.g. "Thanks for calling ${k.business_name || "us"}, this is Ava, the virtual assistant — calls may be recorded to help with your request. How can I help?"). If anyone asks whether you are a real person, say honestly that you are the virtual assistant, and offer to connect them to a team member.`,
    "",
    k.languages ? `LANGUAGES: If the caller speaks ${k.languages}, continue the conversation in that language.` : "",
    "",
    "WHAT YOU DO: Book, reschedule, and cancel appointments; answer questions about services, pricing, hours, and location; take messages; capture customer details.",
    "",
    "BOOKING: Find out what they need and their preferred day/time. Use the booking tool to check REAL availability — never invent or promise a time the tool hasn't confirmed. Collect their name and mobile number. Read the appointment back to confirm, then send an SMS confirmation.",
    "",
    "GUARDRAILS: Only state facts from the knowledge base below. If you don't know something, say so and offer to take a message or book a visit — never guess. Do not give professional, medical, legal, or financial advice you are not qualified to give; offer to book or take a message instead. If a caller describes an emergency, tell them to hang up and call their local emergency number.",
    "",
    "TRANSFER: If the caller is upset, has a complex/billing issue, or asks for a person, offer to transfer or take a detailed message" +
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
    services.forEach(s => lines.push(
      `- ${s.name || ""}${s.duration ? " — " + s.duration : ""}${s.price ? " — " + s.price : ""}${s.provider ? " — " + s.provider : ""}`
    ));
  }

  const faqs = Array.isArray(k.faqs) ? k.faqs : [];
  if (faqs.length) {
    lines.push("FAQs:");
    faqs.forEach(f => lines.push(`- Q: ${f.q}  A: ${f.a}`));
  }

  if (k.policies) lines.push(`Policies: ${k.policies}`);
  return lines.join("\n");
}

// ---- 2. Push the prompt to Retell ----
async function updateRetellLLM(llmId, generalPrompt, apiKey) {
  const res = await fetch(`https://api.retellai.com/update-retell-llm/${llmId}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ general_prompt: generalPrompt }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Retell update failed (${res.status}): ${body}`);
  }
  return res.json();
}

// Optional: publish the agent so the change goes live on phone calls.
async function publishAgent(agentId, apiKey) {
  const res = await fetch(`https://api.retellai.com/publish-agent/${agentId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`Publish failed (${res.status}): ${await res.text()}`);
  return res.json();
}

// ---- 3. One call to sync a customer ----
// client = { retell_llm_id, retell_agent_id }, knowledge = the edited fields
async function syncClient(client, knowledge, apiKey, { publish = false } = {}) {
  const prompt = buildPrompt(knowledge);
  const result = await updateRetellLLM(client.retell_llm_id, prompt, apiKey);
  if (publish && client.retell_agent_id) await publishAgent(client.retell_agent_id, apiKey);
  return result;
}

// ---- 4. AWS Lambda / API Gateway handler ----
// POST body: { client: {retell_llm_id, retell_agent_id}, knowledge: {...} }
// In production: load `client` + `knowledge` from your DB by client_id instead of trusting the body.
exports.handler = async (event) => {
  try {
    const body = typeof event.body === "string" ? JSON.parse(event.body) : event.body;
    const apiKey = process.env.RETELL_API_KEY; // from Secrets Manager / env
    const result = await syncClient(body.client, body.knowledge, apiKey, { publish: !!body.publish });
    return { statusCode: 200, body: JSON.stringify({ ok: true, llm_id: result.llm_id }) };
  } catch (e) {
    return { statusCode: 500, body: JSON.stringify({ ok: false, error: String(e.message || e) }) };
  }
};

module.exports = { buildPrompt, renderKnowledge, updateRetellLLM, publishAgent, syncClient };
