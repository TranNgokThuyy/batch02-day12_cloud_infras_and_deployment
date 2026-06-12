# Day 12 Codelab Solutions

## Tổng Quan Dự Án

Project hiện tại đã thay thế sample agent của Day 12 bằng **Lab09 Lab_Assignment RAG chatbot core**. Core cũ là Streamlit chatbot dùng `supervisor_answer()` để điều phối:

```text
Supervisor -> Retrieval Worker -> Evidence Worker -> Generation Worker
```

Trong Day 12, core này được productionize thành FastAPI service trong `06-lab-complete`:

- `POST /ask`: hỏi RAG chatbot, yêu cầu `X-API-Key`
- `GET /health`: liveness check
- `GET /ready`: readiness check với Redis
- Redis: lưu request history, rate limit, cost guard
- Docker + Docker Compose + Railway config
- Local RAG index: `data/local_index.json`

---

## Part 1: Localhost vs Production

### Exercise 1.1: Phát hiện anti-patterns

Các vấn đề thường gặp ở bản localhost:

1. Secret/API key hardcode trong code thay vì đọc từ environment variables.
2. Port cố định, không đọc biến `PORT` do Railway/Render inject.
3. Debug mode bật trong production.
4. Không có `/health` endpoint cho platform kiểm tra process còn sống.
5. Không có `/ready` endpoint để kiểm tra dependency như Redis hoặc vector store.
6. State lưu trong memory, mất dữ liệu khi restart và không scale được nhiều instance.
7. Logging bằng `print()` thay vì structured JSON logs.
8. Không có graceful shutdown khi platform gửi `SIGTERM`.
9. Không có authentication, ai cũng gọi được API.
10. Không có rate limit hoặc cost guard nên dễ bị spam request.

### Exercise 1.2: Chạy basic version

Basic version chạy được local, nhưng chưa production-ready vì thiếu:

- environment-based config
- health/readiness check
- authentication
- rate limiting
- cost protection
- stateless storage
- structured logs
- graceful shutdown

### Exercise 1.3: So sánh develop và production

| Feature | Develop | Production | Why Important? |
|---|---|---|---|
| Config | Hardcoded | Environment variables | Một image dùng được cho dev/staging/prod |
| Secrets | Trong code hoặc `.env` local | Platform variables | Tránh leak secret lên Git |
| Port | Fixed `8000` | Đọc `PORT` | Cloud platform tự cấp port |
| Health check | Không có | `GET /health` | Platform biết app còn sống |
| Readiness | Không có | `GET /ready` | Chỉ nhận traffic khi dependency sẵn sàng |
| Logging | `print()` | JSON logs | Dễ search, debug, monitor |
| State | In-memory | Redis/local index/platform service | Scale nhiều instance |
| Shutdown | Kill process trực tiếp | Handle `SIGTERM` | Cho request đang chạy thời gian hoàn tất |
| Security | Public endpoint | API key/JWT | Chặn truy cập trái phép |
| Cost control | Không có | Budget guard | Tránh vượt chi phí LLM |

Checkpoint Part 1: Project đã dùng `app/config.py`, `.env.example`, `/health`, `/ready`, structured logs và không hardcode secret.

---

## Part 2: Docker Containerization

### Exercise 2.1: Dockerfile cơ bản

1. Base image: `python:3.11-slim`.
2. Working directory runtime: `/app`.
3. `requirements.txt` được copy trước source code để tận dụng Docker layer cache.
4. `CMD` là command mặc định khi container chạy.
5. `EXPOSE 8000` document rằng service lắng nghe port `8000`.

### Exercise 2.2: Build và run

Command:

```bash
cd 06-lab-complete
docker compose up --build
```

Expected:

```text
agent service starts on http://localhost:8000
redis service is healthy
```

Test:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### Exercise 2.3: Multi-stage build

Dockerfile dùng 2 stage:

```text
builder -> install Python dependencies
runtime -> copy installed packages + app/src/data
```

Lợi ích:

- image nhỏ hơn
- không giữ build cache không cần thiết
- tách build-time và runtime
- chạy bằng non-root user `agent`

Requirement image size: dưới `500MB`. Project đã tối ưu bằng cách không cài `sentence-transformers` mặc định; RAG core có hash embedding fallback và dùng `data/local_index.json`.

### Exercise 2.4: Docker Compose stack

Architecture:

```text
Client
  -> agent container (FastAPI)
  -> Redis container
  -> Lab09 RAG local index
```

Redis dùng cho:

- request history
- rate limiting
- monthly cost guard
- readiness dependency check

Checkpoint Part 2:

```bash
docker compose config --quiet
python check_production_ready.py
```

Kết quả hiện tại:

```text
Result: 37/37 checks passed (100%)
PRODUCTION READY
```

---

## Part 3: Cloud Deployment

### Exercise 3.1: Deploy Railway

Project dùng `railway.toml`:

```toml
[build]
builder = "DOCKERFILE"

[deploy]
startCommand = "sh -c 'python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2'"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

Các bước deploy:

```bash
cd 06-lab-complete
railway login
railway init
railway variables set ENVIRONMENT=production
railway variables set PORT=8000
railway variables set APP_NAME="Lab09 RAG Chatbot API"
railway variables set AGENT_API_KEY=replace-with-a-long-secret
railway variables set JWT_SECRET=replace-with-another-long-secret
railway variables set REDIS_URL=replace-with-your-redis-url
railway up
railway domain
```

Windows PowerShell:

```powershell
railway.cmd login
railway.cmd init
railway.cmd up
railway.cmd domain
```

Public URL:

```text
Update in 06-lab-complete/DEPLOYMENT.md after deployment.
```

### Exercise 3.2: Railway vs Render config

| Topic | Railway | Render |
|---|---|---|
| Config file | `railway.toml` | `render.yaml` |
| Build | Dockerfile builder | Docker/native build |
| Runtime port | `PORT` env | `PORT` env |
| Env vars | Railway dashboard/CLI | Render dashboard/blueprint |
| Health check | `healthcheckPath` | `healthCheckPath` |
| Deploy style | CLI or GitHub integration | Dashboard/Git integration |

### Exercise 3.3: Cloud Run optional

Cloud Run thường cần:

- Docker image build
- push image lên registry
- deploy service
- set env vars
- configure public ingress

Trong lab này Railway đơn giản hơn vì project đã có Dockerfile và `railway.toml`.

Checkpoint Part 3:

- Dockerfile build được
- `/health` dùng làm health check
- env vars không hardcode
- URL public sẽ được note trong `DEPLOYMENT.md`

---

## Part 4: API Security

### Exercise 4.1: API Key authentication

File chính:

```text
06-lab-complete/app/auth.py
```

Logic:

- Client phải gửi header `X-API-Key`.
- API key hợp lệ phải trùng `AGENT_API_KEY`.
- Nếu thiếu hoặc sai key, API trả `401`.

Test fail:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hình phạt tàng trữ ma túy là gì?"}'
```

Expected:

```text
401 Unauthorized
```

Test success:

```bash
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hình phạt tàng trữ ma túy là gì?"}'
```

Expected:

```text
200 OK
answer + sources + trace
```

### Exercise 4.2: JWT authentication

JWT phù hợp khi:

- nhiều user đăng nhập riêng
- cần token expiry
- cần role/permission claims
- frontend cần session-based auth

Project final dùng API key vì checklist yêu cầu `X-API-Key` và use case là service-to-service/simple protected API.

### Exercise 4.3: Rate limiting

File chính:

```text
06-lab-complete/app/rate_limiter.py
```

Implementation:

- Redis sorted set theo key `rate:{user_id}`
- window mặc định: 60 giây
- limit mặc định: `10 req/min/user`
- request vượt limit trả `429`
- response có `Retry-After`

Test:

```bash
for i in {1..15}; do
  curl -X POST http://localhost:8000/ask \
    -H "X-API-Key: dev-key-change-me-in-production" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"rate-test\",\"question\":\"test $i\"}"
  echo
done
```

Expected:

```text
First 10 requests -> 200
Later requests -> 429
```

### Exercise 4.4: Cost guard

File chính:

```text
06-lab-complete/app/cost_guard.py
```

Implementation:

- estimate input/output tokens bằng word count x 2
- tính cost giả lập theo giá token
- lưu monthly usage trong Redis theo key `budget:{user_id}:{YYYY-MM}`
- nếu vượt `MONTHLY_BUDGET_USD`, trả `402`

Ý nghĩa:

- tránh abuse API
- tránh vượt ngân sách LLM
- vẫn hoạt động dù app restart vì counter nằm trong Redis

Checkpoint Part 4:

- `/ask` protected bằng API key
- rate limit trả `429`
- cost guard trả `402` khi vượt ngân sách
- không commit secret thật

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

Implemented endpoints:

```text
GET /health
GET /ready
```

`/health` kiểm tra process còn sống:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development"
}
```

`/ready` kiểm tra dependency Redis:

```json
{
  "status": "ready",
  "redis": "ok"
}
```

Nếu Redis lỗi, `/ready` trả `503`.

### Exercise 5.2: Graceful shutdown

File:

```text
06-lab-complete/app/main.py
```

Implementation:

- handle `SIGTERM`
- handle `SIGINT`
- set `_is_ready = False`
- Uvicorn dùng `timeout_graceful_shutdown=30`

Ý nghĩa:

- khi Railway/Docker restart container, app ngừng nhận traffic mới
- request đang chạy có thời gian hoàn tất

### Exercise 5.3: Stateless design

Project không phụ thuộc vào Python process memory cho state quan trọng:

- history lưu Redis
- rate limit lưu Redis
- monthly budget lưu Redis
- RAG retrieval dùng `data/local_index.json` hoặc external Weaviate/PageIndex

Nhờ đó nhiều instance FastAPI có thể cùng phục vụ request.

### Exercise 5.4: Load balancing

Local Docker Compose hiện có:

```text
Client -> FastAPI agent -> Redis
```

Khi scale production:

```text
Load Balancer
  -> agent instance 1
  -> agent instance 2
  -> agent instance N
       -> shared Redis
       -> shared RAG index/external vector store
```

Điều kiện để scale:

- app stateless
- shared Redis
- shared vector index hoặc bundled read-only local index
- no hardcoded localhost dependency

### Exercise 5.5: Test stateless

Test logic:

1. Gửi nhiều request cùng `user_id`.
2. Rate limit counter tăng trong Redis.
3. Restart app container.
4. Redis vẫn giữ counter/history/budget.
5. App mới vẫn đọc được state từ Redis.

Command gợi ý:

```bash
docker compose up --build -d

curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"stateless-test","question":"Hình phạt tàng trữ ma túy là gì?"}'

docker compose restart agent

curl http://localhost:8000/ready
```

Expected:

```text
/ready -> 200
Redis-backed state remains outside app process
```

Checkpoint Part 5:

- `/health` pass
- `/ready` pass when Redis is healthy
- graceful shutdown implemented
- app can scale horizontally because state is outside app memory

---

## Final Verification

Commands đã chạy:

```bash
python -m compileall app src check_production_ready.py
python check_production_ready.py
docker compose config --quiet
```

Kết quả:

```text
Result: 37/37 checks passed (100%)
PRODUCTION READY
```

RAG core test:

```bash
python -c "from src.supervisor_workers import supervisor_answer; r=supervisor_answer('Hình phạt tàng trữ ma túy là gì?', top_k=2, score_threshold=0.05); print(len(r['answer']), len(r['sources']), r['trace']['pattern'])"
```

Expected:

```text
answer length > 0
sources > 0
trace = supervisor_workers
```
