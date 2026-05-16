"""
Code Generation Agents — Stage 8

Fixes applied:
  - Schema instructions now appear at the TOP of every prompt (before context)
  - _normalize_file_response() handles missing/miskeyed 'files' without crashing
  - Static fallback files ensure orchestration never fails from bad LLM output
  - Validation logs warnings instead of raising ValueError on retryable issues
"""
import json
import logging
from typing import Any, Dict, List

from app.agents.base_agent import BaseAgent, AgentContext
from app.agents.llm_client import llm_router

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Schema instruction — MUST appear at the TOP of every prompt so the LLM
# sees the output requirement BEFORE the planning context, not after.
# ──────────────────────────────────────────────────────────────────────────────

_SCHEMA_HEADER = """\
YOUR ONLY JOB: Return a JSON object with this EXACT structure — nothing else:
{
  "files": [
    {"path": "relative/path/file.ext", "content": "complete file content"}
  ],
  "summary": "one-line description"
}

RULES:
- Output RAW JSON only. No markdown. No ```json blocks. No explanations.
- "files" MUST be a non-empty array of {path, content} objects.
- Each "content" value is a JSON string: escape newlines as \\n, quotes as \\"
- Generate REAL, RUNNABLE code — not stubs, not todos, not planning text.

"""

# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────

def _extract_context(context: AgentContext) -> Dict[str, Any]:
    def _get(name: str) -> Dict:
        r = context.get_result(name)
        return r.data if r else {}
    return {
        "goal": _get("Goal Understanding Agent"),
        "tech_stack": _get("Tech Stack Agent"),
        "frontend_design": _get("Frontend Agent"),
        "backend_design": _get("Backend Agent"),
        "architecture": _get("Architecture Agent"),
        "security": _get("Security Agent"),
    }


def _brief(data: Any, limit: int = 600) -> str:
    """Compact summary of planning data for injection into code-gen prompts."""
    try:
        return json.dumps(data, default=str)[:limit]
    except Exception:
        return str(data)[:limit]


def _project_name(context: AgentContext, goal_data: Dict) -> str:
    name = goal_data.get("primary_goal") or goal_data.get("goal") or context.user_input
    if isinstance(name, dict):
        name = str(list(name.values())[0]) if name else context.user_input
    return str(name)[:80]


def _normalize_file_response(raw: Any, agent_name: str,
                             fallback_fn) -> Dict[str, Any]:
    """
    Extract a valid {files:[...]} dict from whatever the LLM returned.
    Tries 4 strategies before using the static fallback.
    Never raises — always returns a usable result.
    """
    # Strategy 1: correct structure already
    if isinstance(raw, dict):
        for key in ("files", "generated_files", "project_files", "output_files", "artifacts"):
            candidate = raw.get(key)
            if isinstance(candidate, list):
                valid = [f for f in candidate
                         if isinstance(f, dict) and f.get("path") and f.get("content")]
                if valid:
                    logger.info(f"[{agent_name}] Parsed {len(valid)} files (key={key!r})")
                    return {"files": valid, "summary": raw.get("summary", "")}

        # Strategy 2: flat dict where values look like file content
        # e.g. {"src/App.tsx": "import React..."} — some models output this
        flat_files = []
        for k, v in raw.items():
            if isinstance(v, str) and "/" in k and len(v) > 20:
                flat_files.append({"path": k, "content": v})
        if len(flat_files) >= 2:
            logger.info(f"[{agent_name}] Recovered {len(flat_files)} files from flat dict")
            return {"files": flat_files, "summary": "recovered from flat dict"}

    # Strategy 3: LLM returned a list directly
    if isinstance(raw, list):
        valid = [f for f in raw
                 if isinstance(f, dict) and f.get("path") and f.get("content")]
        if valid:
            logger.info(f"[{agent_name}] Parsed {len(valid)} files from bare list")
            return {"files": valid, "summary": ""}

    # Strategy 4: static fallback
    logger.warning(f"[{agent_name}] Could not extract files from response "
                   f"(type={type(raw).__name__}, keys="
                   f"{list(raw.keys()) if isinstance(raw, dict) else 'N/A'}). "
                   f"Using static fallback.")
    return {"files": fallback_fn(), "summary": "static fallback"}




# ──────────────────────────────────────────────────────────────────────────────
# Static fallback file generators
# Used when all LLM parsing strategies fail — ensures orchestration never crashes
# ──────────────────────────────────────────────────────────────────────────────

def _frontend_fallback(project_name: str = "MyApp") -> List[Dict]:
    return [
        {"path": "package.json", "content": f'{{"name":"{project_name.lower().replace(" ","-")}","version":"0.1.0","scripts":{{"dev":"vite","build":"vite build"}},"dependencies":{{"react":"^18.2.0","react-dom":"^18.2.0","react-router-dom":"^6.14.0","axios":"^1.4.0"}},"devDependencies":{{"@types/react":"^18.2.0","typescript":"^5.0.0","vite":"^4.4.0","@vitejs/plugin-react":"^4.0.0"}}}}'},
        {"path": "index.html", "content": f'<!DOCTYPE html>\n<html lang="en">\n<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{project_name}</title></head>\n<body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>\n</html>'},
        {"path": "vite.config.ts", "content": 'import { defineConfig } from "vite";\nimport react from "@vitejs/plugin-react";\nexport default defineConfig({ plugins: [react()], server: { port: 5173, proxy: { "/api": "http://localhost:8000" } } });'},
        {"path": "src/main.tsx", "content": 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport { BrowserRouter } from "react-router-dom";\nimport App from "./App";\nimport "./index.css";\nReactDOM.createRoot(document.getElementById("root")!).render(\n  <React.StrictMode><BrowserRouter><App /></BrowserRouter></React.StrictMode>\n);'},
        {"path": "src/App.tsx", "content": f'import {{ Routes, Route }} from "react-router-dom";\nimport HomePage from "./pages/HomePage";\nimport DashboardPage from "./pages/DashboardPage";\nexport default function App() {{\n  return <Routes>\n    <Route path="/" element={{<HomePage />}} />\n    <Route path="/dashboard" element={{<DashboardPage />}} />\n  </Routes>;\n}}'},
        {"path": "src/index.css", "content": "* { box-sizing: border-box; margin: 0; padding: 0; }\nbody { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }"},
        {"path": "src/pages/HomePage.tsx", "content": f'export default function HomePage() {{\n  return (\n    <div style={{{{minHeight:"100vh",display:"flex",alignItems:"center",justifyContent:"center"}}}}>\n      <div style={{{{textAlign:"center"}}}}>\n        <h1 style={{{{fontSize:"3rem",fontWeight:"bold",marginBottom:"1rem"}}}}>Welcome to {project_name}</h1>\n        <p style={{{{fontSize:"1.2rem",opacity:0.7}}}}>Your AI-powered application</p>\n      </div>\n    </div>\n  );\n}}'},
        {"path": "src/pages/DashboardPage.tsx", "content": 'import { useEffect, useState } from "react";\nexport default function DashboardPage() {\n  const [data, setData] = useState<any[]>([]);\n  return (\n    <div style={{padding:"2rem"}}>\n      <h2 style={{fontSize:"1.5rem",marginBottom:"1rem"}}>Dashboard</h2>\n      <p>Connected and ready.</p>\n    </div>\n  );\n}'},
        {"path": "src/services/api.ts", "content": 'import axios from "axios";\nconst api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "/api/v1" });\napi.interceptors.request.use(cfg => {\n  const token = localStorage.getItem("token");\n  if (token) cfg.headers.Authorization = `Bearer ${token}`;\n  return cfg;\n});\nexport default api;'},
        {"path": ".env.example", "content": "VITE_API_URL=http://localhost:8000/api/v1\n"},
    ]


def _backend_fallback(project_name: str = "MyApp") -> List[Dict]:
    return [
        {"path": "backend/requirements.txt", "content": "fastapi==0.115.0\nuvicorn[standard]==0.30.6\npydantic==2.9.2\npydantic-settings==2.5.2\npython-jose[cryptography]==3.3.0\npasslib[bcrypt]==1.7.4\nsqlalchemy==2.0.35\naiosqlite==0.20.0\npython-multipart==0.0.9\nhttpx==0.27.2\n"},
        {"path": "backend/main.py", "content": f'from fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\n\napp = FastAPI(title="{project_name} API", version="1.0.0")\napp.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])\n\n@app.get("/health")\ndef health(): return {{"status": "ok", "service": "{project_name}"}}\n\n@app.get("/api/v1/status")\ndef status(): return {{"status": "operational"}}\n'},
        {"path": "backend/app/__init__.py", "content": ""},
        {"path": "backend/app/core/config.py", "content": 'from pydantic_settings import BaseSettings\nfrom pydantic import Field\nclass Settings(BaseSettings):\n    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./app.db")\n    SECRET_KEY: str = Field(default="change-me-in-production")\n    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60\n    class Config:\n        env_file = ".env"\nsettings = Settings()'},
        {"path": "backend/app/core/security.py", "content": 'from datetime import datetime, timedelta\nfrom jose import jwt\nfrom passlib.context import CryptContext\nfrom app.core.config import settings\npwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")\ndef hash_password(p: str) -> str: return pwd_context.hash(p)\ndef verify_password(p: str, h: str) -> bool: return pwd_context.verify(p, h)\ndef create_token(sub: str) -> str:\n    exp = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)\n    return jwt.encode({"sub": sub, "exp": exp}, settings.SECRET_KEY, algorithm="HS256")'},
        {"path": "backend/Dockerfile", "content": "FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nEXPOSE 8000\nCMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\n"},
        {"path": "backend/.env.example", "content": "DATABASE_URL=sqlite+aiosqlite:///./app.db\nSECRET_KEY=change-me-in-production\nACCESS_TOKEN_EXPIRE_MINUTES=60\n"},
    ]


def _scaffolding_fallback(project_name: str = "MyApp") -> List[Dict]:
    safe = project_name.lower().replace(" ", "-")
    return [
        {"path": "docker-compose.yml", "content": f'version: "3.9"\nservices:\n  backend:\n    build: ./backend\n    ports: ["8000:8000"]\n    environment:\n      - DATABASE_URL=postgresql+asyncpg://user:pass@db/app\n    depends_on: [db, redis]\n  frontend:\n    build: ./frontend\n    ports: ["3000:80"]\n    depends_on: [backend]\n  db:\n    image: postgres:16-alpine\n    environment: {{POSTGRES_USER: user, POSTGRES_PASSWORD: pass, POSTGRES_DB: app}}\n    volumes: [pgdata:/var/lib/postgresql/data]\n  redis:\n    image: redis:7-alpine\nvolumes:\n  pgdata:\n'},
        {"path": ".gitignore", "content": "node_modules/\n__pycache__/\n*.pyc\n.env\n.venv/\nvenv/\ndist/\nbuild/\n.DS_Store\n*.egg-info/\n.pytest_cache/\ncoverage/\n*.db\n*.log\n"},
        {"path": ".env.example", "content": f"# {project_name} Environment Variables\n\n# Backend\nDATABASE_URL=postgresql+asyncpg://user:password@localhost/app\nSECRET_KEY=change-me-in-production-use-openssl-rand-hex-32\n\n# Frontend\nVITE_API_URL=http://localhost:8000/api/v1\n\n# Redis\nREDIS_URL=redis://localhost:6379\n"},
        {"path": "Makefile", "content": f".PHONY: dev build test clean\ndev:\n\tdocker compose -f docker-compose.dev.yml up\nbuild:\n\tdocker compose build\ntest:\n\tcd backend && python -m pytest\n\tcd frontend && npm test\nclean:\n\tdocker compose down -v\n"},
        {"path": "README.md", "content": f"# {project_name}\n\nAI-generated full-stack application.\n\n## Quick Start\n\n```bash\ncp .env.example .env\ndocker compose up --build\n```\n\nFrontend: http://localhost:3000  \nBackend API: http://localhost:8000  \nAPI Docs: http://localhost:8000/docs\n\n## Architecture\n\n- **Frontend**: React + TypeScript + Vite\n- **Backend**: FastAPI + SQLAlchemy\n- **Database**: PostgreSQL\n- **Cache**: Redis\n"},
    ]


# ──────────────────────────────────────────────────────────────────────────────
# 1. FRONTEND CODE AGENT
# ──────────────────────────────────────────────────────────────────────────────

class FrontendCodeAgent(BaseAgent):
    name = "Frontend Code Agent"
    description = "Generate a complete React + TypeScript frontend codebase"
    timeout_seconds = 180
    max_retries = 2

    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        ctx = _extract_context(context)
        goal_data = ctx["goal"]
        pname = _project_name(context, goal_data)

        # Brief spec summaries — keep short so the schema header dominates
        fe_spec = _brief(ctx["frontend_design"], 400)
        ts_spec = _brief(ctx["tech_stack"], 300)

        system = (
            "You are a senior React/TypeScript engineer. "
            "Output ONLY the JSON file manifest requested — no explanations."
        )
        prompt = (
            f"{_SCHEMA_HEADER}"
            f"Generate a React + TypeScript frontend for: {pname}\n"
            f"User request: {context.user_input[:200]}\n\n"
            f"Frontend spec: {fe_spec}\nTech stack: {ts_spec}\n\n"
            "Generate these files (complete, runnable code):\n"
            "- package.json  - index.html  - vite.config.ts  - tailwind.config.js\n"
            "- src/main.tsx  - src/App.tsx (routing)  - src/index.css\n"
            "- src/components/Navbar.tsx  - src/components/Layout.tsx\n"
            "- src/pages/HomePage.tsx  - src/pages/DashboardPage.tsx\n"
            "- src/services/api.ts (axios)  - src/hooks/useAuth.ts\n"
            "- .env.example\n\n"
            "Return the JSON object now:"
        )

        raw = await llm_router.complete_json(prompt, system=system)
        result = _normalize_file_response(raw, self.name,
                                          lambda: _frontend_fallback(pname))
        logger.info(f"[{self.name}] Returning {len(result['files'])} files")
        return result


# ──────────────────────────────────────────────────────────────────────────────
# 2. BACKEND CODE AGENT
# ──────────────────────────────────────────────────────────────────────────────

class BackendCodeAgent(BaseAgent):
    name = "Backend Code Agent"
    description = "Generate a complete Python FastAPI backend codebase"
    timeout_seconds = 180
    max_retries = 2

    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        ctx = _extract_context(context)
        goal_data = ctx["goal"]
        pname = _project_name(context, goal_data)

        be_spec = _brief(ctx["backend_design"], 400)
        ts_spec = _brief(ctx["tech_stack"], 300)
        sec_spec = _brief(ctx["security"], 300)

        system = (
            "You are a senior FastAPI/Python engineer. "
            "Output ONLY the JSON file manifest requested — no explanations."
        )
        prompt = (
            f"{_SCHEMA_HEADER}"
            f"Generate a FastAPI Python backend for: {pname}\n"
            f"User request: {context.user_input[:200]}\n\n"
            f"Backend spec: {be_spec}\nTech: {ts_spec}\nSecurity: {sec_spec}\n\n"
            "Generate these files (complete, syntactically correct Python):\n"
            "- requirements.txt  - main.py (FastAPI, CORS, lifespan)\n"
            "- app/core/config.py (pydantic-settings)  - app/core/security.py (JWT)\n"
            "- app/core/database.py (SQLAlchemy async)  - app/models/user.py\n"
            "- app/schemas/user.py (UserCreate, UserResponse, Token)\n"
            "- app/api/v1/auth.py (login, register)  - app/api/v1/router.py\n"
            "- app/services/auth_service.py  - Dockerfile  - .env.example\n\n"
            "Return the JSON object now:"
        )

        raw = await llm_router.complete_json(prompt, system=system)
        result = _normalize_file_response(raw, self.name,
                                          lambda: _backend_fallback(pname))

        # Ensure all paths are under backend/ prefix
        fixed = []
        for f in result["files"]:
            path = f.get("path", "")
            if path and not path.startswith("backend/"):
                f = {**f, "path": f"backend/{path}"}
            fixed.append(f)
        result["files"] = fixed

        logger.info(f"[{self.name}] Returning {len(result['files'])} files")
        return result


# ──────────────────────────────────────────────────────────────────────────────
# 3. SCAFFOLDING AGENT
# ──────────────────────────────────────────────────────────────────────────────

class ScaffoldingAgent(BaseAgent):
    name = "Scaffolding Agent"
    description = "Generate project-level configs: docker-compose, CI/CD, README"
    timeout_seconds = 120
    max_retries = 2

    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        ctx = _extract_context(context)
        goal_data = ctx["goal"]
        pname = _project_name(context, goal_data)

        arch_spec = _brief(ctx["architecture"], 400)
        ts_spec = _brief(ctx["tech_stack"], 300)

        system = (
            "You are a DevOps/platform engineer. "
            "Output ONLY the JSON file manifest requested — no explanations."
        )
        prompt = (
            f"{_SCHEMA_HEADER}"
            f"Generate project scaffolding for: {pname}\n"
            f"User request: {context.user_input[:200]}\n\n"
            f"Architecture: {arch_spec}\nTech: {ts_spec}\n\n"
            "Generate these files (complete, immediately usable):\n"
            "- docker-compose.yml (frontend + backend + postgres + redis)\n"
            "- docker-compose.dev.yml (dev overrides, hot-reload)\n"
            "- .github/workflows/ci.yml (lint, test, build)\n"
            "- .gitignore (Node.js + Python monorepo)\n"
            "- .env.example (all env vars with descriptions)\n"
            "- Makefile (dev, build, test, deploy targets)\n"
            "- README.md (overview, setup, architecture, deployment)\n"
            "- DEPLOYMENT.md (step-by-step production guide)\n\n"
            "Return the JSON object now:"
        )

        raw = await llm_router.complete_json(prompt, system=system)
        result = _normalize_file_response(raw, self.name,
                                          lambda: _scaffolding_fallback(pname))
        logger.info(f"[{self.name}] Returning {len(result['files'])} files")
        return result

