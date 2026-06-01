/**
 * Norra — Website ingest
 * --------------------------------------------------------------
 * Give it a customer's website URL. It reads the key pages, asks an LLM to
 * extract structured business knowledge, and returns JSON in the SAME shape
 * the Knowledge Editor / norra-sync.js use. The customer then reviews & edits.
 *
 * Fetching: uses Jina Reader (https://r.jina.ai/<url>) which renders the page
 *   and returns clean text — handles most JS sites, no headless browser needed.
 *   (Swap for Firecrawl/ScrapingBee if you prefer.)
 * Extraction: OpenAI chat completions in JSON mode.
 *
 * Env: OPENAI_API_KEY  (and optionally JINA_API_KEY for higher limits)
 */

const COMMON_PATHS = ["", "about", "services", "pricing", "prices", "book", "contact", "faq", "faqs", "hours"];

async function readPage(url) {
  const headers = {};
  if (process.env.JINA_API_KEY) headers["Authorization"] = `Bearer ${process.env.JINA_API_KEY}`;
  try {
    const r = await fetch("https://r.jina.ai/" + url, { headers });
    if (!r.ok) return "";
    const txt = await r.text();
    return txt.slice(0, 8000); // cap per page
  } catch { return ""; }
}

function buildUrls(root) {
  let base = root.trim().replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(base)) base = "https://" + base;
  return COMMON_PATHS.map(p => (p ? base + "/" + p : base));
}

async function gatherSiteText(root) {
  const urls = buildUrls(root);
  const pages = await Promise.all(urls.map(readPage));
  // keep only pages that returned something, join with markers, cap total
  return pages.filter(Boolean).join("\n\n----- PAGE BREAK -----\n\n").slice(0, 24000);
}

const EXTRACTION_SYSTEM = `You extract structured business information from website text for an AI phone receptionist.
Return ONLY a JSON object with these keys:
{
 "business_name": string,
 "business_type": string,                // e.g. "physiotherapy & massage clinic", "Italian restaurant", "auto repair shop"
 "address": string,
 "hours": string,
 "service_area": string,
 "languages": string,                    // only if stated; else ""
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
  if (!res.ok) throw new Error(`OpenAI extract failed (${res.status}): ${await res.text()}`);
  const data = await res.json();
  const content = data.choices?.[0]?.message?.content || "{}";
  return JSON.parse(content);
}

// Main: URL -> knowledge JSON
async function ingestWebsite(rootUrl, openaiKey) {
  const siteText = await gatherSiteText(rootUrl);
  if (!siteText) throw new Error("Could not read any content from that website.");
  const knowledge = await extractKnowledge(siteText, openaiKey);
  // normalize shape
  knowledge.services = Array.isArray(knowledge.services) ? knowledge.services : [];
  knowledge.faqs = Array.isArray(knowledge.faqs) ? knowledge.faqs : [];
  return knowledge;
}

// AWS Lambda / API Gateway handler. POST { url: "clinic.com" }  ->  { ok, knowledge }
exports.handler = async (event) => {
  try {
    const body = typeof event.body === "string" ? JSON.parse(event.body) : event.body;
    const knowledge = await ingestWebsite(body.url, process.env.OPENAI_API_KEY);
    return {
      statusCode: 200,
      headers: { "Access-Control-Allow-Origin": "*", "Content-Type": "application/json" },
      body: JSON.stringify({ ok: true, knowledge }),
    };
  } catch (e) {
    return { statusCode: 500, headers: { "Access-Control-Allow-Origin": "*" }, body: JSON.stringify({ ok: false, error: String(e.message || e) }) };
  }
};

module.exports = { ingestWebsite, gatherSiteText, extractKnowledge };
