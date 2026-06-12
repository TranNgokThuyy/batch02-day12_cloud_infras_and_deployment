# Deployment Information

## Project

Lab09 `Lab_Assignment` RAG chatbot core, productionized for Day 12.

The original project was a Streamlit RAG chatbot for Vietnamese drug-law and
related-news questions. This version exposes the same core supervisor-workers
pipeline through a FastAPI API.

## Public URL

Update after Railway deployment:

```text
https://your-lab09-rag-chatbot.up.railway.app
```

## Platform

Railway

## Runtime Architecture

```text
Client
  -> FastAPI /ask
  -> API key auth
  -> Redis rate limit + monthly cost guard
  -> Lab09 RAG supervisor
  -> Retrieval worker
  -> Evidence worker
  -> Generation worker
  -> cited answer + sources + trace
```

## Environment Variables

Required:

- `ENVIRONMENT=production`
- `PORT=8000`
- `APP_NAME=Lab09 RAG Chatbot API`
- `AGENT_API_KEY=<your-secret-key>`
- `JWT_SECRET=<your-jwt-secret>`
- `REDIS_URL=<your-redis-url>`

Recommended:

- `RATE_LIMIT_PER_MINUTE=10`
- `MONTHLY_BUDGET_USD=10.0`
- `LOG_LEVEL=INFO`
- `RAG_TOP_K=5`
- `RAG_SCORE_THRESHOLD=0.05`

Optional integrations:

- `OPENAI_API_KEY=<optional>`
- `OPENAI_MODEL=gpt-4o-mini`
- `JINA_API_KEY=<optional-reranker-key>`
- `PAGEINDEX_API_KEY=<optional>`
- `PAGEINDEX_DOC_ID=<optional>`
- `WEAVIATE_URL=<optional>`
- `WEAVIATE_API_KEY=<optional>`

If optional services are not configured, the API uses the local RAG index and
extractive generation fallback.

## Local Verification

```bash
docker compose up --build
python check_production_ready.py
```

Expected readiness check:

```text
Result: 37/37 checks passed (100%)
PRODUCTION READY
```

## Public Test Commands

Set shell variables:

```bash
BASE_URL=https://your-lab09-rag-chatbot.up.railway.app
API_KEY=replace-with-your-api-key
```

Health:

```bash
curl "$BASE_URL/health"
```

Readiness:

```bash
curl "$BASE_URL/ready"
```

Authentication should fail:

```bash
curl -X POST "$BASE_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hình phạt tàng trữ ma túy là gì?"}'
```

Authenticated RAG request:

```bash
curl -X POST "$BASE_URL/ask" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hình phạt tàng trữ ma túy là gì?"}'
```

Expected response fields:

```text
answer
sources
trace
cost_usd
```

Metrics:

```bash
curl "$BASE_URL/metrics" -H "X-API-Key: $API_KEY"
```

## Notes

Keep API keys and platform tokens in Railway variables only. Do not commit
secrets into the repository.
