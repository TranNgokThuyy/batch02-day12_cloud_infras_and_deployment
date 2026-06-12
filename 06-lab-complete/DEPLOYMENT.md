# Deployment Information

## Public URL

`https://agent-production-df3b.up.railway.app`

Current status: deployed and verified on Railway.

Railway CLI is installed on this machine as `railway.cmd` (`railway 5.12.0`). PowerShell blocks `railway.ps1`, so use `railway.cmd` for Railway commands.

## Platform

Railway

## Environment Variables

Set these in Railway:

- `ENVIRONMENT=production`
- `PORT=8000`
- `AGENT_API_KEY=<your-secret-key>`
- `JWT_SECRET=<your-jwt-secret>`
- `REDIS_URL=<your-redis-url>`
- `RATE_LIMIT_PER_MINUTE=10`
- `MONTHLY_BUDGET_USD=10.0`
- `LOG_LEVEL=INFO`
- `OPENAI_API_KEY=` optional; empty uses the mock LLM

## Test Commands

Set shell variables:

```bash
BASE_URL=https://agent-production-df3b.up.railway.app
API_KEY=replace-with-your-api-key
```

Health check:

```bash
curl "$BASE_URL/health"
```

Readiness check:

```bash
curl "$BASE_URL/ready"
```

Authentication should fail:

```bash
curl -X POST "$BASE_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
```

Authenticated request:

```bash
curl -X POST "$BASE_URL/ask" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"My name is Alice"}'
```

Conversation history:

```bash
curl -X POST "$BASE_URL/ask" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"What is my name?"}'
```

Rate limiting:

```bash
for i in {1..15}; do
  curl -X POST "$BASE_URL/ask" \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"rate-test\",\"question\":\"test $i\"}"
  echo
done
```

Metrics:

```bash
curl "$BASE_URL/metrics" -H "X-API-Key: $API_KEY"
```

## Windows Railway Commands

```powershell
railway.cmd login
railway.cmd init
railway.cmd variables set ENVIRONMENT=production
railway.cmd variables set AGENT_API_KEY=replace-with-a-long-secret
railway.cmd variables set JWT_SECRET=replace-with-another-long-secret
railway.cmd variables set REDIS_URL=replace-with-your-redis-url
railway.cmd variables set RATE_LIMIT_PER_MINUTE=10
railway.cmd variables set MONTHLY_BUDGET_USD=10.0
railway.cmd variables set LOG_LEVEL=INFO
railway.cmd up
railway.cmd domain
```

## Screenshots

Add Railway dashboard screenshots before final submission if your instructor requires image evidence:

- `screenshots/dashboard.png`
- `screenshots/running.png`
- `screenshots/test.png`

## Local Verification Evidence

```text
docker compose ps
06-lab-complete-agent-1   Up (healthy)   0.0.0.0:8000->8000/tcp
06-lab-complete-redis-1   Up (healthy)   6379/tcp

python check_production_ready.py
Result: 33/33 checks passed (100%)

docker images 06-lab-complete-agent
06-lab-complete-agent latest 249MB
```

## Public Verification Evidence

```text
GET /health -> 200 OK
{"status":"ok","version":"1.0.0","environment":"production",...}

GET /ready -> 200 OK
{"status":"ready","redis":"ok"}

POST /ask without X-API-Key -> 401

POST /ask with X-API-Key:
Question: What is my name?
Answer: Your name is Alice.

Rate limit test:
200,200,200,200,200,200,200,200,200,200,429

GET /metrics with X-API-Key:
{"rate_limit_per_minute":10,"monthly_budget_usd":10.0,...}
```
