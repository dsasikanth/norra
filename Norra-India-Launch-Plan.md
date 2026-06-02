# Norra India (Hyderabad) — Launch Plan

Goal: a localized Norra for India — Telugu, Hindi, English, Kannada, Malayalam — sold by
your local partner to clinics & hospitals. Same brand, India-localized everything.

---

## 0. FIRST — validate demand (don't build the stack yet)
Have your partner talk to **8–10 Hyderabad clinics/hospitals**, show the live demo (English
first, or Telugu once tested), and find out: would they use it, and **what would they pay in INR?**
Build the localized stack **only after** a few say yes. His eagerness is best spent on
conversations this week, not waiting on engineering.

## 1. Languages
Telugu, Hindi, English, Kannada, Malayalam — all covered by **Sarvam AI** and the open
**AI4Bharat / Bhashini** models. **Test each with local accents** before promising it.

## 2. Voice stack (managed, to start)
- **Sarvam AI (recommended)** — India-native STT + TTS + real-time, all 5 languages, low latency.
- Alternative: ElevenLabs (Telugu/Hindi) + Retell. (Sarvam is purpose-built for India.)

## 3. Telephony — Indian numbers
Use an India provider for inbound numbers + calling: **Exotel, Plivo, Knowlarity,** or **Twilio India**.
(Your Canada setup uses Twilio/Retell; India needs its own numbers + provider.)

## 4. Communication — WhatsApp, not SMS
India runs on WhatsApp. Send confirmations & call summaries via the **WhatsApp Business API**
(Gupshup, AiSensy, or Meta directly).

## 5. Booking
Google Calendar, the clinic's own system, or Practo where used.

## 6. Pricing (INR — much lower than Canada)
Indian clinics won't pay USD prices. Illustrative tiers (partner validates real numbers):
- **Starter ₹2,500/mo** — single clinic, lower volume
- **Pro ₹6,000/mo** — busy clinic *(most popular)*
- **Hospital / Multi ₹12,000+/mo** — high volume, multiple lines
- One-time setup ₹2,000–₹5,000 (waive for first/founding clients).
Indian voice + telephony costs are also lower, so margins still work at these prices.

## 7. Payments
**Razorpay** (UPI, cards, netbanking) for INR billing.

## 8. Legal & data
- Bill through a local arrangement / Indian entity (your partner) — cross-border billing is messy.
- Comply with India's **DPDP Act**; hospitals handle sensitive health data.

## 9. Self-hosting to cut cost — later, not now (see analysis below)
Possible with the open Indian stack, but not worth it until you have real volume.

## 10. Sequence
Validate demand → localized **managed** stack (Sarvam + Indian telephony + WhatsApp) →
first paid clients → optimize / self-host **later** once volume justifies it.
