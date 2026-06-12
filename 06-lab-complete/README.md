# Day 12 - Complete Production Agent

This folder is the final submission project for the Day 12 cloud infrastructure
and deployment lab. It combines the production concepts from the lab into one
FastAPI service.

## Features

- REST API agent with `POST /ask`
- API key authentication using `X-API-Key`
- Redis-backed conversation history by `user_id`
- Redis sliding-window rate limiting, default `10 req/min/user`
- Redis monthly cost guard, default `$10/user/month`
- `GET /health` liveness check
- `GET /ready` readiness check with Redis ping
- Structured JSON logs
- Graceful shutdown signal handling
- Multi-stage Dockerfile
- Docker Compose stack with agent and Redis
- Railway deployment config

## Project Structure

```text
06-lab-complete/
  app/
    main.py
    config.py
    auth.py
    rate_limiter.py
    cost_guard.py
  Dockerfile
  docker-compose.yml
  railway.toml
  render.yaml
  .env.example
  .dockerignore
  requirements.txt
  MISSION_ANSWERS.md
  DEPLOYMENT.md
```

## Local Setup

```bash
cd batch02-day12_cloud_infras_and_deployment/06-lab-complete
cp .env.example .env
```

Edit `.env` if needed. For local Docker Compose, `.env.example` is already used
as a safe template and no real OpenAI key is required because the app uses the
provided mock LLM.

## Run With Docker Compose

```bash
docker compose up --build
```

The agent is available at:

```text
http://localhost:8000
```

## Quick Tests

Health:

```bash
curl http://localhost:8000/health
```

Readiness:

```bash
curl http://localhost:8000/ready
```

Authentication should fail without an API key:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"test\",\"question\":\"Hello\"}"
```

Authenticated request:

```bash
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"test\",\"question\":\"My name is Alice\"}"
```

Conversation history check:

```bash
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"test\",\"question\":\"What is my name?\"}"
```

Rate limit check:

```bash
for /L %i in (1,1,15) do curl -X POST http://localhost:8000/ask -H "X-API-Key: dev-key-change-me-in-production" -H "Content-Type: application/json" -d "{\"user_id\":\"rate-test\",\"question\":\"test %i\"}"
```

On macOS/Linux shells, use:

```bash
for i in {1..15}; do
  curl -X POST http://localhost:8000/ask \
    -H "X-API-Key: dev-key-change-me-in-production" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"rate-test\",\"question\":\"test $i\"}"
done
```

## Production Readiness Check

```bash
python check_production_ready.py
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
npm.cmd i -g @railway/cli
railway.cmd login
railway.cmd init
```

Set environment variables:

```bash
railway variables set ENVIRONMENT=production
railway variables set PORT=8000
railway variables set AGENT_API_KEY=replace-with-a-long-secret
railway variables set JWT_SECRET=replace-with-another-long-secret
railway variables set REDIS_URL=redis://your-redis-url
railway variables set RATE_LIMIT_PER_MINUTE=10
railway variables set MONTHLY_BUDGET_USD=10.0
railway variables set LOG_LEVEL=INFO
```

Deploy:

```bash
railway up
railway domain
```

PowerShell equivalent:

```powershell
railway.cmd up
railway.cmd domain
```

Update `DEPLOYMENT.md` with the public URL and screenshots after deployment.

Current Railway URL:

```text
https://agent-production-df3b.up.railway.app
```

## GitHub CI/CD

This repository includes a GitHub Actions workflow:

```text
.github/workflows/day12-ci-cd.yml
```

What it does:

- On pull requests and pushes to `main`, it installs dependencies, compiles Python, runs `check_production_ready.py`, validates Docker Compose, and builds the Docker image.
- On pushes to `main`, it deploys `06-lab-complete` to the Railway `agent` service.
- After deploy, it checks the public `/health` and `/ready` endpoints.
- If `DEPLOYED_API_KEY` is set, it also runs an authenticated `/ask` smoke test.

Required GitHub secrets:

```text
RAILWAY_TOKEN
```

Optional GitHub secret:

```text
DEPLOYED_API_KEY
```

To add secrets:

1. Open your GitHub repository.
2. Go to `Settings` -> `Secrets and variables` -> `Actions`.
3. Add `RAILWAY_TOKEN`.
4. Optionally add `DEPLOYED_API_KEY` with the same value as Railway `AGENT_API_KEY`.

Create a Railway token from Railway dashboard:

```text
Account Settings -> Tokens -> Create Token
```
