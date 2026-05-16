"""
LLM Client - Multi-provider AI model routing (Gemini, OpenAI, Claude, Ollama)

FIXES APPLIED:
  - GeminiClient.complete(): generate_content() is synchronous; wrapped in asyncio.to_thread()
    so it no longer blocks the uvicorn event loop.
  - complete_json(): Added JSON repair logic + raise ValueError on parse failure
    so the BaseAgent retry mechanism triggers instead of storing garbage data.
"""
import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMResponse:
    """Standardized LLM response."""

    def __init__(self, content: str, model: str, tokens_used: int = 0, provider: str = ""):
        self.content = content
        self.model = model
        self.tokens_used = tokens_used
        self.provider = provider
        self.timestamp = time.time()


class GeminiClient:
    """Google Gemini API client."""

    def __init__(self):
        self.available = False
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._model = genai.GenerativeModel(settings.GEMINI_MODEL)
                self._genai = genai
                self.available = True
                logger.info(f"✅ Gemini client initialized: {settings.GEMINI_MODEL}")
            except ImportError:
                logger.warning("google-generativeai not installed")
            except Exception as e:
                logger.warning(f"Gemini init error: {e}")

    async def complete(self, prompt: str, system: str = None, **kwargs) -> LLMResponse:
        """
        Generate completion using Gemini.

        CRITICAL FIX: google.generativeai's generate_content() is a SYNCHRONOUS
        blocking call. Running it directly in an async function blocks the entire
        uvicorn event loop, preventing WebSocket events from being emitted and
        freezing all concurrent agents. We offload it to a thread pool via
        asyncio.to_thread() to keep the event loop free.
        """
        if not self.available:
            raise RuntimeError("Gemini not available")

        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 8192)

        logger.debug(
            f"[LLM:Gemini] Sending request | model={settings.GEMINI_MODEL} "
            f"prompt_len={len(full_prompt)} max_tokens={max_tokens}"
        )
        t0 = time.time()

        # FIX: Offload blocking SDK call to thread pool — keeps event loop free
        def _blocking_generate():
            return self._model.generate_content(
                full_prompt,
                generation_config=self._genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )

        try:
            response = await asyncio.to_thread(_blocking_generate)
        except Exception as e:
            logger.error(f"[LLM:Gemini] API call failed after {time.time()-t0:.2f}s: {e}")
            raise

        content = response.text
        tokens = getattr(response.usage_metadata, "total_token_count", 0)
        elapsed = time.time() - t0

        logger.info(
            f"[LLM:Gemini] ✅ Response received | tokens={tokens} "
            f"elapsed={elapsed:.2f}s content_len={len(content)}"
        )

        return LLMResponse(
            content=content,
            model=settings.GEMINI_MODEL,
            tokens_used=tokens,
            provider="gemini",
        )


class OpenAIClient:
    """OpenAI API client."""

    def __init__(self):
        self.available = False
        if settings.OPENAI_API_KEY:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                self.available = True
                logger.info(f"✅ OpenAI client initialized: {settings.OPENAI_MODEL}")
            except ImportError:
                logger.warning("openai package not installed")
            except Exception as e:
                logger.warning(f"OpenAI init error: {e}")

    async def complete(self, prompt: str, system: str = None, **kwargs) -> LLMResponse:
        """Generate completion using OpenAI."""
        if not self.available:
            raise RuntimeError("OpenAI not available")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        logger.debug(
            f"[LLM:OpenAI] Sending request | model={settings.OPENAI_MODEL} "
            f"messages={len(messages)}"
        )
        t0 = time.time()

        try:
            response = await self._client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
            )
        except Exception as e:
            logger.error(f"[LLM:OpenAI] API call failed after {time.time()-t0:.2f}s: {e}")
            raise

        content = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        elapsed = time.time() - t0

        logger.info(
            f"[LLM:OpenAI] ✅ Response received | tokens={tokens} "
            f"elapsed={elapsed:.2f}s content_len={len(content)}"
        )

        return LLMResponse(
            content=content,
            model=settings.OPENAI_MODEL,
            tokens_used=tokens,
            provider="openai",
        )


class AnthropicClient:
    """Anthropic Claude API client."""

    def __init__(self):
        self.available = False
        if settings.ANTHROPIC_API_KEY:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                self.available = True
                logger.info(f"✅ Anthropic client initialized: {settings.ANTHROPIC_MODEL}")
            except ImportError:
                logger.warning("anthropic package not installed")
            except Exception as e:
                logger.warning(f"Anthropic init error: {e}")

    async def complete(self, prompt: str, system: str = None, **kwargs) -> LLMResponse:
        """Generate completion using Claude."""
        if not self.available:
            raise RuntimeError("Anthropic not available")

        logger.debug(
            f"[LLM:Anthropic] Sending request | model={settings.ANTHROPIC_MODEL}"
        )
        t0 = time.time()

        try:
            message = await self._client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=kwargs.get("max_tokens", 4096),
                system=system or "You are a helpful AI assistant.",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            logger.error(f"[LLM:Anthropic] API call failed after {time.time()-t0:.2f}s: {e}")
            raise

        content = message.content[0].text
        tokens = message.usage.input_tokens + message.usage.output_tokens
        elapsed = time.time() - t0

        logger.info(
            f"[LLM:Anthropic] ✅ Response received | tokens={tokens} "
            f"elapsed={elapsed:.2f}s content_len={len(content)}"
        )

        return LLMResponse(
            content=content,
            model=settings.ANTHROPIC_MODEL,
            tokens_used=tokens,
            provider="anthropic",
        )


class MockLLMClient:
    """Mock LLM fallback provider."""

    def __init__(self):
        self.available = True
        logger.info("Mock LLM registered as fallback provider")
        
    async def complete(self, prompt: str, system: str = None, **kwargs) -> LLMResponse:
        """Return structured mock responses based on prompt content."""
        prompt_lower = prompt.lower()

        if "goal" in prompt_lower or "understand" in prompt_lower or "requirement" in prompt_lower:
            content = json.dumps({
                "goal": "Build an AI-powered platform",
                "problem_statement": "Users need an intelligent solution to automate workflows",
                "target_users": ["developers", "startups", "enterprises"],
                "core_requirements": ["AI integration", "Real-time processing", "Scalable architecture"],
                "success_metrics": ["User adoption", "Processing speed", "System reliability"],
                "domain": "AI / SaaS",
                "complexity": "high",
                "estimated_timeline_weeks": 12,
            })
        elif "plan" in prompt_lower or "task" in prompt_lower or "milestone" in prompt_lower:
            content = json.dumps({
                "phases": [
                    {"phase": 1, "name": "Foundation", "duration_weeks": 2, "tasks": ["Setup infrastructure", "Auth system", "Database schema"]},
                    {"phase": 2, "name": "Core Features", "duration_weeks": 4, "tasks": ["API development", "AI integration", "Frontend MVP"]},
                    {"phase": 3, "name": "Advanced Features", "duration_weeks": 4, "tasks": ["Multi-agent system", "Analytics", "Testing"]},
                    {"phase": 4, "name": "Launch", "duration_weeks": 2, "tasks": ["Optimization", "Documentation", "Deployment"]},
                ],
                "milestones": ["MVP ready", "Beta launch", "Production release"],
                "total_weeks": 12,
                "team_size_recommended": 4,
            })
        elif "research" in prompt_lower or "competitor" in prompt_lower or "market" in prompt_lower:
            content = json.dumps({
                "market_size": "$45B TAM",
                "growth_rate": "32% YoY",
                "competitors": [
                    {"name": "Competitor A", "strengths": ["Market leader", "Strong brand"], "weaknesses": ["Expensive", "Complex"], "market_share": "35%"},
                    {"name": "Competitor B", "strengths": ["Easy to use", "Affordable"], "weaknesses": ["Limited features", "Poor scalability"], "market_share": "20%"},
                ],
                "market_gaps": ["AI-native approach", "No-code automation", "Better observability"],
                "differentiators": ["Autonomous agents", "Real-time monitoring", "Self-healing"],
                "recommended_positioning": "Premium AI-first solution for tech-forward teams",
            })
        elif "architecture" in prompt_lower or "system" in prompt_lower or "schema" in prompt_lower:
            content = json.dumps({
                "system_design": {
                    "frontend": {"framework": "React + TypeScript", "state_management": "Zustand"},
                    "backend": {"framework": "FastAPI", "language": "Python 3.11", "async": "AsyncIO + WebSockets"},
                    "database": {"primary": "PostgreSQL", "cache": "Redis"},
                    "ai": {"models": ["Gemini 2.0 Flash", "GPT-4o", "Claude 3.5"]},
                },
                "api_design": {"style": "RESTful + WebSocket", "auth": "JWT Bearer tokens", "versioning": "/api/v1/"},
                "scalability": {"horizontal_scaling": "Stateless API with Redis", "caching_strategy": "Redis for hot data"},
            })
        elif "tech stack" in prompt_lower or "technology" in prompt_lower:
            content = json.dumps({
                "frontend": {"framework": "React 18", "language": "TypeScript", "build_tool": "Vite", "styling": "Tailwind CSS"},
                "backend": {"framework": "FastAPI", "language": "Python 3.11", "orm": "SQLAlchemy"},
                "database": {"relational": "PostgreSQL", "cache": "Redis 7"},
                "ai_ml": {"primary_model": "Gemini 2.0 Flash", "fallback": "GPT-4o"},
                "infrastructure": {"containerization": "Docker", "compose": "Docker Compose"},
                "rationale": "Selected for developer experience, performance, and AI ecosystem compatibility",
            })
        elif "security" in prompt_lower or "auth" in prompt_lower or "rbac" in prompt_lower:
            content = json.dumps({
                "authentication": {"method": "JWT + Refresh tokens", "mfa": "TOTP-based (future)"},
                "authorization": {"model": "RBAC", "roles": ["admin", "developer", "viewer"]},
                "vulnerabilities_addressed": ["SQL injection", "XSS", "CSRF", "Path traversal", "Rate abuse"],
                "compliance_considerations": ["GDPR data handling", "SOC2 audit trail"],
                "rate_limiting": {"per_user": "60 req/min", "burst": "10 req/s"},
            })
        elif "monitor" in prompt_lower or "observ" in prompt_lower or "metric" in prompt_lower:
            content = json.dumps({
                "metrics": ["response_time_p99", "error_rate", "throughput_rps", "agent_completion_rate"],
                "logging": {"format": "structured JSON", "levels": ["DEBUG", "INFO", "WARNING", "ERROR"]},
                "alerting": {"latency_threshold_ms": 500, "error_rate_threshold": 0.01},
                "sla": {"availability": "99.9%", "p99_latency_ms": 200},
            })
        elif "heal" in prompt_lower or "fault" in prompt_lower or "resilience" in prompt_lower:
            content = json.dumps({
                "failure_detection": ["health checks every 10s", "circuit breakers", "dead letter queues"],
                "retry_strategies": {"max_attempts": 3, "backoff": "exponential", "jitter": True},
                "rto": "< 5 minutes",
                "rpo": "< 1 minute",
            })
        elif "rollback" in prompt_lower or "deployment" in prompt_lower or "deploy" in prompt_lower:
            content = json.dumps({
                "deployment_strategy": "blue-green",
                "rollback_triggers": ["error_rate > 5%", "p99_latency > 2s", "health_check_failure"],
                "smoke_tests": ["GET /health", "POST /api/v1/auth/login", "WebSocket connectivity"],
                "rollback_time_target": "< 2 minutes",
            })
        elif "readme" in prompt_lower or "documentation" in prompt_lower or "docs" in prompt_lower:
            content = json.dumps({
                "executive_summary": "AI-powered multi-agent orchestration platform for autonomous project planning.",
                "quick_start": ["git clone", "cp .env.example .env", "docker compose up -d"],
                "architecture_summary": "React frontend + FastAPI backend + 13 specialized AI agents + Redis + WebSockets",
                "api_endpoints": ["/api/v1/workflows", "/api/v1/projects", "/api/v1/agents", "/ws/{workflow_id}"],
                "implementation_roadmap": {"week1_2": "Foundation", "week3_6": "Core features", "week7_10": "Advanced", "week11_12": "Launch"},
            })
        else:
            content = json.dumps({
                "summary": "Analysis complete",
                "recommendations": [
                    "Implement core features first",
                    "Focus on user experience",
                    "Build for scalability from day one",
                    "Implement comprehensive testing",
                ],
                "next_steps": ["Define MVP scope", "Set up development environment", "Begin sprint planning"],
                "confidence": 0.92,
            })

        await asyncio.sleep(0.3)  # Simulate minimal latency

        logger.info(f"[LLM:Mock] ✅ Mock response generated | content_len={len(content)}")

        return LLMResponse(
            content=content,
            model="mock-llm-v1",
            tokens_used=len(content.split()) * 2,
            provider="mock",
        )


class OllamaClient:
    """Ollama local AI model client."""

    def __init__(self):
        self.available = False
        self.base_url = settings.OLLAMA_BASE_URL
        if self.base_url:
            self.available = True
            logger.info(f"✅ Ollama client initialized: {self.base_url}")

    async def complete(self, prompt: str, system: str = None, **kwargs) -> LLMResponse:
        """Generate completion using Ollama."""
        import httpx

        url = f"{self.base_url}/api/generate"
        model = kwargs.get("model", "deepseek-coder:6.7b")

        payload = {
            "model": model,
            "prompt": f"{system}\n\n{prompt}" if system else prompt,
            "stream": False,
            "options": {"temperature": kwargs.get("temperature", 0.7)},
        }

        logger.debug(f"[LLM:Ollama] Sending request | model={model} url={url}")
        t0 = time.time()

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                content = data.get("response", "")
                elapsed = time.time() - t0
                logger.info(f"[LLM:Ollama] ✅ Response received | elapsed={elapsed:.2f}s")

                return LLMResponse(
                    content=content,
                    model=model,
                    tokens_used=data.get("eval_count", 0),
                    provider="ollama",
                )
            except Exception as e:
                logger.error(f"[LLM:Ollama] Call failed after {time.time()-t0:.2f}s: {e}")
                raise


def _repair_json(content: str) -> Optional[str]:
    """
    Attempt to repair malformed JSON from LLM responses.
    Tries several common repair strategies before giving up.
    """
    # Strategy 1: Extract from markdown code blocks
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if match:
        candidate = match.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # Strategy 2: Find outermost JSON object/array
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = content.find(start_char)
        end = content.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            candidate = content[start:end + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                # Strategy 3: Remove trailing commas and retry
                cleaned = re.sub(r',\s*([}\]])', r'\1', candidate)
                try:
                    json.loads(cleaned)
                    return cleaned
                except json.JSONDecodeError:
                    pass

    return None


class LLMRouter:
    """
    Multi-provider LLM router with automatic failover.
    Priority: Gemini → OpenAI → Claude → Ollama → Mock (last resort only)
    """

    def __init__(self):
        self._providers = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize all configured providers."""
        self._providers["gemini"] = GeminiClient()
        self._providers["openai"] = OpenAIClient()
        self._providers["anthropic"] = AnthropicClient()
        self._providers["ollama"] = OllamaClient()
        self._providers["mock"] = MockLLMClient()

        real_providers = [
            name for name, client in self._providers.items()
            if client.available and name != "mock"
        ]
        logger.info(f"✅ LLM providers available: {[name for name, c in self._providers.items() if c.available]}")
        if not real_providers:
            logger.warning(
                "⚠️  No real LLM providers configured! "
                "Set GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY in backend/.env"
            )

    async def complete(
        self,
        prompt: str,
        system: str = None,
        preferred_provider: str = None,
        **kwargs,
    ) -> LLMResponse:
        """Route completion request with automatic failover."""

        # Build provider priority order — real providers before mock
        primary = preferred_provider or settings.PRIMARY_MODEL_PROVIDER
        real_order = [p for p in ["gemini", "openai", "anthropic", "ollama"] if p != primary]
        order = [primary] + real_order + ["mock"]

        last_error = None
        for provider_name in order:
            provider = self._providers.get(provider_name)
            if provider and provider.available:
                try:
                    logger.info(f"[LLMRouter] Attempting provider: {provider_name}")
                    result = await provider.complete(prompt, system=system, **kwargs)
                    logger.info(
                        f"[LLMRouter] ✅ Success via {provider_name} | "
                        f"model={result.model} tokens={result.tokens_used}"
                    )
                    return result
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"[LLMRouter] ❌ Provider {provider_name} failed: {e}. "
                        f"Trying next provider..."
                    )

        # All real providers failed — use mock as absolute last resort
        logger.error(
            f"[LLMRouter] ❌ All real providers failed (last error: {last_error}). "
            f"Falling back to mock LLM."
        )
        return await self._providers["mock"].complete(prompt, system=system, **kwargs)

    async def complete_json(
        self,
        prompt: str,
        system: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Complete and parse a JSON response from the LLM.

        FIX: Previously, parse failures were silently returned as
        {"raw_response": ..., "parse_error": True}, causing the BaseAgent
        to treat garbage data as a successful completion and never retry.

        Now: raises ValueError on parse failure so BaseAgent.execute() retries.
        """
        json_instruction = (
            "\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "No markdown formatting, no code blocks, no explanation text — just the raw JSON object."
        )
        response = await self.complete(prompt + json_instruction, system=system, **kwargs)

        content = response.content.strip()
        provider = response.provider

        logger.debug(f"[LLMRouter] Parsing JSON response from {provider} | content_len={len(content)}")

        # Attempt 1: Direct parse
        try:
            result = json.loads(content)
            logger.debug(f"[LLMRouter] ✅ JSON parsed successfully (direct) | provider={provider}")
            return result
        except json.JSONDecodeError:
            pass

        # Attempt 2: Repair strategies
        logger.warning(
            f"[LLMRouter] JSON parse failed (direct). Attempting repair... "
            f"provider={provider} content_preview={content[:200]!r}"
        )
        repaired = _repair_json(content)
        if repaired:
            try:
                result = json.loads(repaired)
                logger.info(f"[LLMRouter] ✅ JSON repaired successfully | provider={provider}")
                return result
            except json.JSONDecodeError:
                pass

        # All repair attempts failed — raise so retry kicks in
        logger.error(
            f"[LLMRouter] ❌ JSON parse failed after all repair attempts | "
            f"provider={provider} content_preview={content[:300]!r}"
        )
        raise ValueError(
            f"LLM ({provider}) returned non-parseable JSON after repair attempts. "
            f"Content preview: {content[:200]!r}"
        )

    @property
    def available_providers(self) -> list[str]:
        return [name for name, client in self._providers.items() if client.available]

    @property
    def real_providers(self) -> list[str]:
        """Return only real (non-mock) available providers."""
        return [
            name for name, client in self._providers.items()
            if client.available and name != "mock"
        ]


# Singleton
llm_router = LLMRouter()
