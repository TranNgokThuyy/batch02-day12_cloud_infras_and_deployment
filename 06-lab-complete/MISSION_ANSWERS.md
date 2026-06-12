# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. Secrets are hardcoded instead of loaded from environment variables.
2. The port is fixed in code, so cloud platforms cannot inject `PORT`.
3. Debug mode is suitable for local development, not production.
4. There is no health check for orchestration platforms.
5. There is no readiness check for dependencies.
6. State is stored in process memory, which breaks horizontal scaling.
7. Logging uses simple output instead of structured logs.
8. There is no graceful shutdown behavior.

### Exercise 1.2: Basic version run result

The basic version can respond locally, but it is not production-ready because it lacks environment-based config, health checks, authentication, rate limiting, cost protection, and stateless storage.

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
|---|---|---|---|
| Config | Hardcoded values | Environment variables | Same image can run in dev, staging, and production. |
| Secrets | Stored in code | Stored in platform env vars | Prevents leaking API keys in Git history. |
| Port | Fixed port | Reads `PORT` | Railway/Render inject the runtime port. |
| Health check | Missing | `/health` | Platform can detect a live process. |
| Readiness | Missing | `/ready` checks Redis | Traffic only reaches a ready instance. |
| Logging | `print()` | JSON logs | Logs are easier to search and aggregate. |
| State | In memory | Redis | Multiple app instances can share user state. |
| Shutdown | Abrupt | Handles SIGTERM | In-flight work has time to finish. |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image: `python:3.11-slim`.
2. Working directory: `/app` in runtime, `/build` in builder.
3. `requirements.txt` is copied before application code so dependency layers are cached.
4. `CMD` provides the default command and can be overridden; `ENTRYPOINT` is the fixed executable.

### Exercise 2.3: Image size comparison

- Production image: `06-lab-complete-agent:latest` is `249MB`.
- Requirement: below `500MB`.
- Result: pass. Multi-stage builds keep the final image smaller by copying only runtime dependencies and source code into the runtime stage.

### Exercise 2.4: Architecture diagram

```text
Client -> Agent container (FastAPI) -> Redis container
```

The agent exposes HTTP endpoints. Redis stores rate-limit windows, monthly cost usage, and conversation history.

### Exercise 2.2: Build and run result

`docker compose up --build -d` successfully built and started:

```text
06-lab-complete-agent-1   Up (healthy)   0.0.0.0:8000->8000/tcp
06-lab-complete-redis-1   Up (healthy)   6379/tcp
```

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- Platform: Railway
- URL: `https://agent-production-df3b.up.railway.app`
- Status: deployed successfully on Railway.
- Screenshot: add dashboard screenshots under `screenshots/` if image evidence is required.
- Local deployment readiness: Docker Compose stack is healthy and `check_production_ready.py` passes `33/33`.
- Public readiness: `/health` and `/ready` both return `200`.

### Exercise 3.2: Railway vs Render config

Railway uses `railway.toml` with Dockerfile builder and deploy settings. Render uses `render.yaml` as a blueprint for web services and environment variables. Both need environment variables for secrets and Redis.

## Part 4: API Security

### Exercise 4.1: API key authentication

The app checks the `X-API-Key` header in `app/auth.py`. Missing or invalid keys return `401`. Keys are rotated by changing `AGENT_API_KEY` in the deployment platform and redeploying or restarting the service.

Local test result:

```text
POST /ask without X-API-Key -> 401
POST /ask with X-API-Key -> 200
```

Public Railway test result:

```text
POST /ask without X-API-Key -> 401
POST /ask with X-API-Key -> 200
```

### Exercise 4.2: JWT authentication

JWT is useful when many users need their own signed sessions. This final app uses API key authentication because the grading checklist requires `X-API-Key`.

### Exercise 4.3: Rate limiting

The app uses a Redis sorted-set sliding window in `app/rate_limiter.py`. Default limit is `10 requests/minute/user`. When the limit is exceeded, the API returns `429` with `Retry-After`.

Local test result:

```text
200,200,200,200,200,200,200,200,200,200,429
```

Public Railway test result:

```text
200,200,200,200,200,200,200,200,200,200,429
```

### Exercise 4.4: Cost guard implementation

The app estimates input and output token cost, tracks monthly spending in Redis by `user_id`, and blocks requests with `402` if the next request would exceed the configured monthly budget.

Local unit test result: `MonthlyCostGuard` returns `402` when a configured low budget is exceeded.

## Part 5: Scaling & Reliability

### Exercise 5.1: Health and readiness

- `/health` returns process liveness.
- `/ready` pings Redis and returns `503` if Redis is unavailable.

### Exercise 5.2: Graceful shutdown

The app handles `SIGTERM` and `SIGINT`, marks itself unready, and lets Uvicorn use its graceful shutdown timeout.

### Exercise 5.3: Stateless design

Conversation history, rate limits, and budget counters are stored in Redis, not Python memory. This allows multiple app instances to serve the same users.

### Exercise 5.4: Load balanced stack

The Docker Compose stack can scale the `agent` service when port publishing is adjusted or a load balancer is added. Redis remains the shared backing service.

### Exercise 5.5: Stateless test

Send a message with one `user_id`, then send a follow-up request with the same `user_id`. The history is loaded from Redis, so the second request can use the first message even if handled by another instance.

Local test result:

```text
Question: What is my name?
Answer: Your name is Alice.
```

Public Railway test result:

```text
Question: What is my name?
Answer: Your name is Alice.
```

## Final Production Readiness

```text
python check_production_ready.py
Result: 33/33 checks passed (100%)
PRODUCTION READY
```
