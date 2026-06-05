# Norra Agent — Design

**Goal:** one AI receptionist that's genuinely excellent for *any* Indian business — clinic, real
estate, restaurant, salon, services — Telugu-first, multilingual, warm and human (not robotic),
and fast to configure per customer.

## The problem with the old approach
We kept editing a single hard-coded persona. That doesn't scale across verticals and drifts in
quality. The product isn't "a clinic bot" — it's a **configurable receptionist platform**.

## The architecture — three layers build every call

```
   CORE  (shared: warmth, honesty, confirm-back, safety, never-invent, human voice)
     +
 PLAYBOOK (per vertical: the call GOAL + the FLOW — clinic books, real-estate qualifies…)
     +
 PROFILE  (this business: name, hours, doctors/agents, offerings, prices, location)
     ↓
  a top-quality, consistent system prompt for THIS business
```

- **CORE** — one spec, applied to every business, so quality and warmth are consistent. It enforces
  the "golden behaviours": confirm phone numbers, read bookings back, never invent facts, hand off
  honestly, handle emergencies, sound human in the caller's language.
- **PLAYBOOK** — the industry call-flow (the value): clinics → book appointments; real estate →
  qualify + schedule a site visit; restaurant → reservations; salon → service booking; home/auto →
  capture the job. Adding a vertical = adding one playbook.
- **PROFILE** — the specific business's facts. Swapping the customer = swapping the profile.

## Voice & language
- **Engine:** Google **Gemini Live** — one model does listening + thinking + a natural voice, with
  Gemini's *affective dialog* on for warm, expressive delivery.
- **Telugu-first**, plus Hindi, English, Tamil, Kannada, Malayalam — set per session.
- **Selectable voice/accent per business** (Gemini voices: Aoede, Kore, Leda, Zephyr, Puck, Charon).

## How a session is configured
The caller's session passes a small JSON body:
- `language` — Telugu (default), English, Hindi, …
- `demo` — `clinic` | `real_estate` | `sales` → a built-in sample (for instant demos)
- or a full profile: `name`, `vertical`, `info`, `voice` → any real customer
- no body → Norra's **sales agent** (the website "Talk to Norra")

So **one deployment** powers the website sales agent *and* every clinic/real-estate/etc. demo.

## What this unlocks
- **Sell anywhere:** demo a real-estate office or restaurant as easily as a clinic — just change the profile.
- **Onboard fast:** a new customer = fill a profile (or ingest their website/Google listing into `info`).
- **Consistent quality:** every Nora inherits the same excellent CORE behaviours.
- **Per-customer voice/accent** without code changes.

## Next steps
1. Tune CORE + the priority playbooks on real calls (Telugu).
2. Onboarding: a simple form (or website ingest) that produces a profile.
3. Capture the call outcome (booking/lead) → WhatsApp + a simple dashboard.
4. Wire the same agent to the phone (Exotel AgentStream) for live customer calls.
