# Norra

**Reception with a human touch, powered by AI.** An AI phone receptionist for local
businesses — answers every call, books appointments, captures leads, and texts the
owner a summary. Built on Retell (engine) with a custom multi-tenant wrapper.

## Repo layout

| Path | What it is |
|------|------------|
| `Norra-Website.html` | Marketing site (deploys to norrahq.com) |
| `Norra-Logo.svg` | Brand logo |
| `aws/` | Terraform — website hosting (S3 + CloudFront + Route 53) |
| `AWS-DEPLOY-RUNBOOK.md` | Step-by-step AWS deploy |
| `norra-sync.js` | Knowledge → Retell sync (PATCH update-retell-llm) |
| `norra-ingest.js` | Crawl a customer website → structured knowledge |
| `norra-calls-worker.js` | Pull calls from Retell for the dashboard |
| `Norra-Knowledge-Editor.html` | Self-serve knowledge editor (with website import) |
| `AI-Front-Desk-Customer-Dashboard.html` | Customer call dashboard |
| `norra-db-schema.sql` | Postgres schema (clients, knowledge, calls) |
| `Norra-Sample-Clinic-Config.md` | Sample agent config for testing |

## Architecture (short)
Retell runs the call (speech → LLM → voice → tools). Norra is the layer on top:
a dashboard + database + the sync that pushes customer knowledge into Retell, plus
the website. See `AWS-DEPLOY-RUNBOOK.md` to deploy.

## Secrets
Keys (Retell, Cal.com, OpenAI) live in env vars / AWS Parameter Store — never in this repo.
