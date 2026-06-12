# Day 12 - Cloud Infrastructure and Deployment

Repository thuc hanh cho bai Day 12: dua mot AI agent tu localhost len moi
truong production.

Noi dung tap trung vao:

- Khac biet giua development va production
- Docker va Docker Compose
- Deploy len Railway, Render, hoac Cloud Run
- API security, rate limiting, cost guard
- Health check, readiness check, stateless design
- Final project trong `06-lab-complete`

## Project Structure

```text
batch02-day12_cloud_infras_and_deployment/
  01-localhost-vs-production/
    develop/
    production/
  02-docker/
    develop/
    production/
  03-cloud-deployment/
    railway/
    render/
    production-cloud-run/
  04-api-gateway/
    develop/
    production/
  05-scaling-reliability/
    develop/
    production/
  06-lab-complete/
    app/
    Dockerfile
    docker-compose.yml
    railway.toml
    render.yaml
    README.md
    DEPLOYMENT.md
  utils/
```

## Quick Start

Final project nam trong:

```bash
cd batch02-day12_cloud_infras_and_deployment/06-lab-complete
```

Chay local bang Docker Compose:

```bash
docker compose up --build
```

Kiem tra service:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Gui request co API key:

```bash
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
```

## Requirements

- Python 3.11+
- Docker
- Docker Compose
- Railway CLI, neu deploy len Railway

Khong can OpenAI API key that cho lab nay. Code mac dinh dung mock LLM de co
the chay offline.

## Main Lab Materials

- `CODE_LAB.md`: huong dan lab chi tiet
- `QUICK_START.md`: chay nhanh trong vai phut
- `QUICK_REFERENCE.md`: cheat sheet lenh va pattern
- `TROUBLESHOOTING.md`: loi thuong gap va cach sua
- `INSTRUCTOR_GUIDE.md`: huong dan cham diem

## Manual Deployment

Repository nay uu tien deploy thu cong de de debug trong qua trinh hoc.

Railway flow co ban:

```bash
cd 06-lab-complete
npm i -g @railway/cli
railway login
railway init
railway variables set ENVIRONMENT=production
railway variables set PORT=8000
railway variables set AGENT_API_KEY=replace-with-a-long-secret
railway variables set JWT_SECRET=replace-with-another-long-secret
railway up
railway domain
```

Tren Windows PowerShell, neu `railway.ps1` bi chan boi execution policy, dung:

```powershell
railway.cmd login
railway.cmd init
railway.cmd up
railway.cmd domain
```

Sau khi deploy, cap nhat URL va bang chung test trong
`06-lab-complete/DEPLOYMENT.md`.

## Final Submission Checklist

- Docker Compose chay duoc local
- `python check_production_ready.py` pass
- Public URL deploy thanh cong
- `/health` va `/ready` tra ve 200
- `/ask` yeu cau `X-API-Key`
- Rate limit va Redis-backed state hoat dong
- `DEPLOYMENT.md` co URL va lenh test
