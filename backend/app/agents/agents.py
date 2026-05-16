"""
All BuildFlow Agents - Concrete implementations
"""
import json
import logging
from typing import Any, Dict

from app.agents.base_agent import BaseAgent, AgentContext
from app.agents.llm_client import llm_router

logger = logging.getLogger(__name__)


# ============================================================
# 1. GOAL UNDERSTANDING AGENT
# ============================================================

class GoalUnderstandingAgent(BaseAgent):
    name = "Goal Understanding Agent"
    description = "Understand user intent and extract structured requirements"
    timeout_seconds = 60
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        system = """You are an elite business analyst and product manager AI.
        Analyze user input and extract precise, structured requirements.
        Focus on: goals, target users, core features, success metrics, technical complexity."""
        
        prompt = f"""Analyze this project request and extract structured requirements:

USER REQUEST: {context.user_input}

Extract:
1. Primary goal and vision
2. Problem being solved
3. Target users/customers
4. Core requirements (must-have)
5. Nice-to-have features
6. Success metrics
7. Technical domain
8. Estimated complexity (low/medium/high/enterprise)
9. Estimated timeline
10. Key risks and challenges"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# 2. PLANNING AGENT
# ============================================================

class PlanningAgent(BaseAgent):
    name = "Planning Agent"
    description = "Create execution DAG, milestones, and task breakdown"
    timeout_seconds = 90
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        goal_data = context.get_result("Goal Understanding Agent")
        goal_context = json.dumps(goal_data.data) if goal_data else "{}"
        
        system = """You are a senior engineering project manager and agile coach.
        Create detailed execution plans with clear phases, milestones, and task breakdowns.
        Focus on practical, achievable execution with proper dependencies."""
        
        prompt = f"""Create a comprehensive execution plan for this project:

GOAL ANALYSIS: {goal_context}
USER REQUEST: {context.user_input}

Generate a detailed project plan with:
1. Development phases (with durations)
2. Milestones for each phase
3. Specific tasks per milestone
4. Task dependencies (as DAG)
5. Team roles needed
6. Risk mitigation plan
7. Sprint breakdown (2-week sprints)
8. Definition of Done for MVP"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# 3. RESEARCH AGENT
# ============================================================

class ResearchAgent(BaseAgent):
    name = "Research Agent"
    description = "Research competitors, technologies, and market trends"
    timeout_seconds = 120
    max_retries = 2
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        goal_data = context.get_result("Goal Understanding Agent")
        
        system = """You are a market research analyst and technology intelligence expert.
        Provide data-driven competitive analysis and technology recommendations."""
        
        prompt = f"""Conduct thorough research for this project:

PROJECT: {context.user_input}
DOMAIN: {goal_data.data.get('domain', 'Technology') if goal_data else 'Technology'}

Research and provide:
1. Market size (TAM/SAM/SOM estimates)
2. Market growth rate
3. Top 5 competitors with detailed SWOT
4. Market gaps and opportunities
5. Technology trends in this space
6. Customer pain points
7. Recommended positioning strategy
8. Go-to-market approach
9. Pricing strategy benchmarks
10. Key success factors"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# 4. STRATEGY AGENT
# ============================================================

class StrategyAgent(BaseAgent):
    name = "Strategy Agent"
    description = "Prioritize MVP scope and recommend execution strategy"
    timeout_seconds = 90
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        outputs = context.get_previous_outputs()
        
        system = """You are a startup strategist and product strategy expert.
        Define focused MVP strategy that maximizes user value and minimizes time-to-market."""
        
        prompt = f"""Define the execution strategy based on all research:

PREVIOUS ANALYSIS: {json.dumps(outputs)[:3000]}
PROJECT: {context.user_input}

Provide:
1. MVP feature set (strict must-haves)
2. Features cut for v1 (with rationale)
3. Technical architecture strategy
4. Launch strategy (beta → GA)
5. Customer acquisition strategy
6. Revenue model recommendation
7. Key partnerships to pursue
8. Build vs Buy analysis for major components
9. 90-day execution roadmap
10. Success KPIs for each phase"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# 5. ARCHITECTURE AGENT
# ============================================================

class ArchitectureAgent(BaseAgent):
    name = "Architecture Agent"
    description = "Generate system architecture, database schema, and API design"
    timeout_seconds = 120
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        outputs = context.get_previous_outputs()
        
        system = """You are a principal software architect with expertise in distributed systems,
        cloud architecture, and scalable system design. Generate production-ready architectures."""
        
        prompt = f"""Design the complete system architecture:

PROJECT: {context.user_input}
CONTEXT: {json.dumps(outputs)[:2000]}

Generate complete architecture including:
1. High-level system design (components and interactions)
2. Microservices breakdown (if applicable)
3. Database schema (tables, relationships, indexes)
4. API design (endpoints, auth, versioning)
5. Data flow diagrams
6. Caching strategy
7. Message queue design
8. Security architecture
9. Deployment topology
10. Scalability considerations
11. Disaster recovery plan
12. Monitoring and observability design"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# 6. TECH STACK AGENT
# ============================================================

class TechStackAgent(BaseAgent):
    name = "Tech Stack Agent"
    description = "Select and justify technology choices"
    timeout_seconds = 60
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        arch_data = context.get_result("Architecture Agent")
        
        system = """You are a senior CTO and technology advisor.
        Select technology stacks based on project requirements, team expertise, and ecosystem maturity."""
        
        prompt = f"""Select and justify the complete technology stack:

PROJECT: {context.user_input}
ARCHITECTURE: {json.dumps(arch_data.data)[:2000] if arch_data else 'Standard web application'}

For each layer, provide:
1. Chosen technology + version
2. Rationale (why this over alternatives)
3. Alternatives considered
4. Learning curve assessment
5. Community support rating
6. License compatibility

Cover: Frontend, Backend, Database, Cache, Queue, Auth, CI/CD, Monitoring, Testing, Deployment"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# 7. FRONTEND AGENT
# ============================================================

class FrontendAgent(BaseAgent):
    name = "Frontend Agent"
    description = "Generate React UI architecture and component specifications"
    timeout_seconds = 120
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        outputs = context.get_previous_outputs()
        
        system = """You are a senior React/TypeScript architect and UI/UX expert.
        Design modern, responsive, and accessible user interfaces with premium aesthetics."""
        
        prompt = f"""Design the complete frontend architecture:

PROJECT: {context.user_input}
CONTEXT: {json.dumps(outputs)[:2000]}

Generate:
1. React component hierarchy (component tree)
2. Page structure and routing
3. State management strategy
4. UI component library choices
5. Design system tokens (colors, typography, spacing)
6. Key screens/views (with layout descriptions)
7. Real-time features (WebSocket integration)
8. Responsive design breakpoints
9. Accessibility considerations
10. Performance optimization strategy
11. Key user flows
12. Sample component code snippets"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# 8. BACKEND AGENT
# ============================================================

class BackendAgent(BaseAgent):
    name = "Backend Agent"
    description = "Generate FastAPI backend architecture and API specifications"
    timeout_seconds = 120
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        outputs = context.get_previous_outputs()
        
        system = """You are a senior backend engineer specializing in FastAPI, Python, and distributed systems.
        Design scalable, secure, and maintainable APIs."""
        
        prompt = f"""Design the complete backend architecture:

PROJECT: {context.user_input}
CONTEXT: {json.dumps(outputs)[:2000]}

Generate:
1. FastAPI application structure
2. API endpoint specifications (all routes)
3. Data models / Pydantic schemas
4. Database models (SQLAlchemy)
5. Authentication middleware design
6. Business logic layer design
7. Background task system
8. WebSocket implementation
9. Error handling strategy
10. Logging and observability
11. Testing strategy (unit/integration)
12. Sample endpoint code"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# 9. SECURITY AGENT
# ============================================================

class SecurityAgent(BaseAgent):
    name = "Security Agent"
    description = "Implement JWT auth, RBAC, secret isolation, and security hardening"
    timeout_seconds = 90
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        outputs = context.get_previous_outputs()
        
        system = """You are a cybersecurity architect and penetration tester.
        Design comprehensive security architectures for production systems."""
        
        prompt = f"""Design the complete security architecture:

PROJECT: {context.user_input}
SYSTEM CONTEXT: {json.dumps(outputs)[:2000]}

Provide comprehensive security design:
1. Authentication system (JWT, OAuth2, session management)
2. Authorization model (RBAC matrix with all roles and permissions)
3. API security (rate limiting, input validation, CORS)
4. Secret management strategy
5. Encryption requirements (at rest, in transit)
6. OWASP Top 10 mitigations
7. Dependency security scanning
8. Audit logging requirements
9. Incident response playbook
10. Security testing checklist
11. Compliance considerations (GDPR, SOC2)
12. Infrastructure security (network policies, firewall rules)"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# 10. DOCUMENTATION AGENT
# ============================================================

class DocumentationAgent(BaseAgent):
    name = "Documentation Agent"
    description = "Generate README, architecture docs, and implementation roadmap"
    timeout_seconds = 120
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        outputs = context.get_previous_outputs()
        
        system = """You are a technical writer and documentation specialist.
        Create clear, comprehensive, and professional technical documentation."""
        
        prompt = f"""Generate complete project documentation:

PROJECT: {context.user_input}
ALL ANALYSIS: {json.dumps(outputs)[:3000]}

Generate:
1. Executive Summary (1-page)
2. Technical README (full)
3. System Architecture Document
4. API Reference outline
5. Development Setup Guide
6. Deployment Guide
7. Contributing Guidelines
8. Changelog template
9. Security Policy
10. License recommendation
11. Pitch deck outline (10 slides)
12. Implementation roadmap (with weeks)"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# 11. MONITORING AGENT
# ============================================================

class MonitoringAgent(BaseAgent):
    name = "Monitoring Agent"
    description = "Design observability, monitoring, and alerting systems"
    timeout_seconds = 60
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        system = """You are a site reliability engineer (SRE) and observability expert.
        Design comprehensive monitoring systems for production applications."""
        
        prompt = f"""Design the observability and monitoring strategy:

PROJECT: {context.user_input}

Design:
1. Metrics to track (business + technical)
2. Logging strategy (structured logs, log levels)
3. Distributed tracing setup
4. Alerting rules and thresholds
5. Dashboard layout (what to visualize)
6. SLA/SLO targets
7. On-call runbooks
8. Error budget policy
9. Performance baselines
10. Incident severity definitions"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# 12. SELF-HEALING AGENT
# ============================================================

class SelfHealingAgent(BaseAgent):
    name = "Self-Healing Agent"
    description = "Design fault tolerance, retry strategies, and recovery mechanisms"
    timeout_seconds = 60
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        system = """You are a resilience engineering expert specializing in fault-tolerant distributed systems."""
        
        prompt = f"""Design the fault tolerance and self-healing architecture:

PROJECT: {context.user_input}

Design:
1. Failure detection mechanisms
2. Circuit breaker patterns
3. Retry strategies with backoff
4. Failover procedures for each component
5. Health check implementations
6. Chaos engineering recommendations
7. Recovery time objectives (RTO/RPO)
8. Data consistency during failures
9. Rollback triggers and procedures
10. Post-incident review process"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# 13. ROLLBACK AGENT
# ============================================================

class RollbackAgent(BaseAgent):
    name = "Rollback Agent"
    description = "Restore stable execution state and manage deployment rollbacks"
    timeout_seconds = 60
    
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        system = """You are a DevOps engineer specializing in deployment strategies and rollback management."""
        
        prompt = f"""Design deployment and rollback strategy:

PROJECT: {context.user_input}

Design:
1. Deployment strategy (blue-green, canary, rolling)
2. Rollback triggers (automatic + manual)
3. Database migration rollback plan
4. Feature flag strategy for safe deployments
5. Smoke test suite post-deployment
6. Rollback time targets
7. State management during rollbacks
8. Communication plan during incidents
9. Post-rollback validation steps
10. Lessons learned integration"""
        
        result = await llm_router.complete_json(prompt, system=system)
        return result


# ============================================================
# AGENT REGISTRY
# ============================================================

AGENT_REGISTRY = {
    "goal_understanding": GoalUnderstandingAgent,
    "planning": PlanningAgent,
    "research": ResearchAgent,
    "strategy": StrategyAgent,
    "architecture": ArchitectureAgent,
    "tech_stack": TechStackAgent,
    "frontend": FrontendAgent,
    "backend": BackendAgent,
    "security": SecurityAgent,
    "documentation": DocumentationAgent,
    "monitoring": MonitoringAgent,
    "self_healing": SelfHealingAgent,
    "rollback": RollbackAgent,
}


def create_agent(agent_type: str) -> BaseAgent:
    """Factory function to create agent instances."""
    agent_class = AGENT_REGISTRY.get(agent_type)
    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(AGENT_REGISTRY.keys())}")
    return agent_class()
