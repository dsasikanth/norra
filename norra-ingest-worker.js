/**
 * Norra — Website ingest (Cloudflare Worker) — robust v2
 * Secret needed:  OPENAI_API_KEY   (optional: JINA_API_KEY for higher read limits)
 * POST { url: "clinic.com" }  ->  { ok:true, knowledge:{...} }
 */
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};
const PATHS = ["", "services", "about", "pricing", "contact"];

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (request.method !== "POST") return json({ ok: false, error: "POST only" }, 405);
    let body;
    try { body = await request.json(); } catch { return json({ ok: false, error: "Invalid JSON" }, 400); }
    try {
      const knowledge = await ingestWebsite(body.url, env.OPENAI_API_KEY, env.JINA_API_KEY);
      return json({ ok: true, knowledge });
    } catch (e) {
      return json({ ok: false, error: String(e.message || e) }, 502);
    }
  },
};

function json(obj, status) {
  return new Response(JSON.stringify(obj), { status: status || 200, headers: { ...CORS, "Content-Type": "application/json" } });
}

function buildUrls(root) {
  let base = root.trim().replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(base)) base = "https://" + base;
  return PATHS.map(p => (p ? base + "/" + p : base));
}

// Jina Reader (renders JS); returns {content, status}
async function readViaJina(url, jinaKey) {
  const headers = {};
  if (jinaKey) headers["Authorization"] = `Bearer ${jinaKey}`;
  try {
    const r = await fetch("https://r.jina.ai/" + url, { headers });
    if (!r.ok) return { content: "", status: r.status };
    return { content: (await r.text()).slice(0, 8000), status: 200 };
  } catch (e) { return { content: "", status: "err" }; }
}

// Fallback: fetch the page directly and strip HTML to text
async function readDirect(url) {
  try {
    const r = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0 (NorraBot)" } });
    if (!r.ok) return "";
    let html = await r.text();
    html = html.replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<style[\s\S]*?<\/style>/gi, " ");
    return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 16000);
  } catch { return ""; }
}

async function gatherSiteText(root, jinaKey) {
  const urls = buildUrls(root);
  let text = "";
  const notes = [];
  // sequential Jina reads (no burst)
  for (const u of urls) {
    const { content, status } = await readViaJina(u, jinaKey);
    if (content) text += content + "\n\n";
    else notes.push(`${u.replace(/^https?:\/\//, "")} -> ${status}`);
    if (text.length > 16000) break;
  }
  // fallback to direct fetch of homepage if Jina gave nothing
  if (!text) {
    const direct = await readDirect(urls[0]);
    if (direct) text = direct;
    else notes.push("direct-fetch -> empty");
  }
  return { text: text.slice(0, 24000), notes };
}

const EXTRACTION_SYSTEM = `You extract structured business information from website text for an AI phone receptionist.
Return ONLY a JSON object with these keys:
{
 "business_name": string, "business_type": string, "address": string, "hours": string,
 "service_area": string, "languages": string,
 "services": [ { "name": string, "duration": string, "price": string, "provider": string } ],
 "faqs": [ { "q": string, "a": string } ],
 "policies": string
}
RULES: Only include facts that actually appear in the text. If something is not stated, use "" (or [] for lists).
NEVER invent prices, hours, or phone numbers. Keep values concise. Generate up to 8 likely FAQs from the content.`;

async function extractKnowledge(siteText, openaiKey) {
  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { Authorization: `Bearer ${openaiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      temperature: 0,
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: EXTRACTION_SYSTEM },
        { role: "user", content: "Website text:\n\n" + siteText },
      ],
    }),
  });
  if (!res.ok) throw new Error(`OpenAI extract failed (${res.status}): ${(await res.text()).slice(0, 300)}`);
  const data = await res.json();
  return JSON.parse(data.choices?.[0]?.message?.content || "{}");
}

async function ingestWebsite(rootUrl, openaiKey, jinaKey) {
  if (!rootUrl) throw new Error("No URL provided.");
  const { text, notes } = await gatherSiteText(rootUrl, jinaKey);
  if (!text) throw new Error("Could not read that website. Reads: " + (notes.join("; ") || "none") +
    ". Try a different URL, or add a JINA_API_KEY secret (free at jina.ai/reader).");
  const k = await extractKnowledge(text, openaiKey);
  k.services = Array.isArray(k.services) ? k.services : [];
  k.faqs = Array.isArray(k.faqs) ? k.faqs : [];
  return k;
}
