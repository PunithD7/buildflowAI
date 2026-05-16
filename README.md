# 🚀 BuildFlow Secure AI
## Secure Autonomous Digital Execution Platform

> Transform high-level ideas into actionable execution systems using secure autonomous multi-agent orchestration.

![BuildFlow Banner](./docs/banner.png)

## 🌟 Overview

BuildFlow Secure AI is a production-quality autonomous multi-agent platform that understands goals, plans workflows, researches technologies, generates architecture, creates roadmaps, and coordinates multiple AI agents securely.

## 🏗️ Architecture

```
buildflow-secure-ai/
├── frontend/          # React + TypeScript + Vite + Tailwind
├── backend/           # FastAPI + Python 3.11+
├── docker/            # Docker configurations
├── docs/              # Documentation
└── scripts/           # Setup and utility scripts
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Python 3.11+
- Gemini API Key
- Supabase Project

### Local Development

```bash
# Clone and setup
git clone <repo>
cd buildflow-secure-ai

# Start with one command (Windows)
.\start_platform.bat

# Or using Docker Compose
docker-compose up -d

# Manual setup:
# Backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

## 🗄️ Database Setup (Supabase)

1. Create a new project on [Supabase](https://supabase.com).
2. Go to the **SQL Editor**.
3. Copy the contents of `docs/supabase_schema.sql` and run it.
4. Update your `backend/.env` with `SUPABASE_URL` and `SUPABASE_KEY`.

## 🐳 Docker Deployment

The platform is fully containerized. You can run the entire stack using:

```bash
docker-compose up --build
```

This starts:
- **Backend**: FastAPI on port 8000
- **Frontend**: Vite/React on port 5173
- **Redis**: Cache/Queue on port 6379

## 🤖 Multi-Agent System

| Agent | Role |
|-------|------|
| Goal Understanding | Extract structured requirements |
| Planning | Create execution DAG |
| Research | Analyze technologies & competitors |
| Strategy | Prioritize MVP scope |
| Architecture | Generate system design |
| Tech Stack | Choose & explain technologies |
| Frontend | Generate React UI |
| Backend | Generate FastAPI APIs |
| Security | JWT, RBAC, secret isolation |
| Documentation | README, architecture docs |
| Monitoring | Track failures & health |
| Self-Healing | Detect & recover from failures |
| Rollback | Restore stable execution state |

## 🔒 Security Features

- TEE-inspired secure execution environments
- Agent failure isolation
- DDoS simulation & protection
- Rate limiting with abuse prevention
- JWT authentication & RBAC

## 📊 Observability

- Real-time agent execution monitoring
- Workflow DAG visualization
- Security event dashboard
- Live terminal logging
- Performance metrics

## 📄 License

MIT License - See LICENSE for details
