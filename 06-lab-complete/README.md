# Lab09 RAG Chatbot - Productionized for Day 12

This folder replaces the original Day 12 sample agent with the Lab09
`Lab_Assignment` RAG chatbot core. The original Streamlit app used
`src.supervisor_workers.supervisor_answer()` to coordinate retrieval,
evidence validation, and citation-style generation. For Day 12, that core is
wrapped in a production-ready FastAPI service.

## What Was Productionized

- Lab09 RAG supervisor-workers core
- Hybrid retrieval pipeline: semantic search + BM25 + reranking
- Local `data/local_index.json` fallback for deployment without Weaviate
- Citation-style answer generation with optional OpenAI
- FastAPI API with `POST /ask`
- API key authentication using `X-API-Key`
- Redis-backed request history, rate limiting, and monthly cost guard
- `GET /health` and `GET /ready`
- Structured JSON logs
- Graceful shutdown signal handling
- Multi-stage Dockerfile
- Docker Compose stack with API and Redis
- Railway deployment config

## Project Structure

```text
06-lab-complete/
  app/                 # Day12 production API wrapper
  src/                 # Lab09 RAG chatbot core
  data/local_index.json
  Dockerfile
  docker-compose.yml
  railway.toml
  .env.example
  check_production_ready.py
  DEPLOYMENT.md
  MISSION_ANSWERS.md
```

## Local Setup

```bash
cd batch02-day12_cloud_infras_and_deployment/06-lab-complete
cp .env.example .env
```

For local testing, the default API key is:

```text
dev-key-change-me-in-production
```

## Run With Docker Compose

```bash
docker compose up --build
```

The API is available at:

```text
http://localhost:8000
```

## API Tests

Health:

```bash
curl http://localhost:8000/health
```

Readiness:

```bash
curl http://localhost:8000/ready
```

Ask the RAG chatbot:

```bash
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo","question":"Hình phạt tàng trữ ma túy là gì?"}'
```

The response includes:

- `answer`
- `sources`
- `trace`
- `cost_usd`

## Production Readiness Check

```bash
python check_production_ready.py
```

Expected:

```text
PRODUCTION READY
```

## Railway Deployment

Install and log in:

```bash
npm i -g @railway/cli
railway login
railway init
```

On Windows PowerShell, use `railway.cmd` if script execution policy blocks
`railway.ps1`:

```powershell
railway.cmd login
railway.cmd init
```

Set Railway variables:

```bash
railway variables set ENVIRONMENT=production
railway variables set PORT=8000
railway variables set APP_NAME="Lab09 RAG Chatbot API"
railway variables set AGENT_API_KEY=replace-with-a-long-secret
railway variables set JWT_SECRET=replace-with-another-long-secret
railway variables set REDIS_URL=replace-with-your-redis-url
railway variables set RATE_LIMIT_PER_MINUTE=10
railway variables set MONTHLY_BUDGET_USD=10.0
railway variables set RAG_TOP_K=5
railway variables set RAG_SCORE_THRESHOLD=0.05
```

Optional:

```bash
railway variables set OPENAI_API_KEY=sk-...
railway variables set OPENAI_MODEL=gpt-4o-mini
railway variables set JINA_API_KEY=...
```

Deploy:

```bash
railway up
railway domain
```

After deployment, update `DEPLOYMENT.md` with the public API URL.
