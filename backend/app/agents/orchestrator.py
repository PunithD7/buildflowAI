"""
Workflow Orchestrator - LangGraph-inspired multi-agent orchestration engine
with fault isolation, failover, and observability
"""
import asyncio
import logging
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from app.agents.base_agent import AgentContext, AgentResult, AgentStatus
from app.agents.agents import (
    GoalUnderstandingAgent, PlanningAgent, ResearchAgent,
    StrategyAgent, ArchitectureAgent, TechStackAgent,
    FrontendAgent, BackendAgent, SecurityAgent,
    DocumentationAgent, MonitoringAgent, SelfHealingAgent, RollbackAgent,
)
from app.agents.code_agents import (
    FrontendCodeAgent, BackendCodeAgent, ScaffoldingAgent,
)
from app.core.config import settings
from app.core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELLED = "cancelled"


class AgentNode:
    """A node in the workflow execution graph."""
    
    def __init__(self, agent_class, depends_on: List[str] = None, is_optional: bool = False):
        self.agent_class = agent_class
        self.agent = agent_class()
        self.depends_on = depends_on or []
        self.is_optional = is_optional
        self.name = self.agent.name
        self.status = AgentStatus.IDLE
        self.result: Optional[AgentResult] = None


class WorkflowOrchestrator:
    """
    Hierarchical multi-agent orchestrator with:
    - Parallel execution where dependencies allow
    - Agent isolation (failure doesn't cascade)
    - Automatic failover
    - Real-time observability
    - Self-healing
    """
    
    def __init__(self):
        self._active_workflows: Dict[str, AgentContext] = {}
        self._workflow_statuses: Dict[str, Dict] = {}
    
    def _build_execution_graph(self) -> List[List[AgentNode]]:
        """
        Build the agent execution graph as parallel stages.
        Agents in the same stage run concurrently.
        Stage N+1 starts only after Stage N completes (or fails with isolation).
        """
        return [
            # Stage 1: Goal Understanding (always first)
            [
                AgentNode(GoalUnderstandingAgent),
            ],
            # Stage 2: Research and Planning (parallel, depends on goal)
            [
                AgentNode(PlanningAgent, depends_on=["Goal Understanding Agent"]),
                AgentNode(ResearchAgent, depends_on=["Goal Understanding Agent"]),
            ],
            # Stage 3: Strategy (depends on planning + research)
            [
                AgentNode(StrategyAgent, depends_on=["Planning Agent", "Research Agent"]),
            ],
            # Stage 4: Architecture + Tech Stack (parallel, depends on strategy)
            [
                AgentNode(ArchitectureAgent, depends_on=["Strategy Agent"]),
                AgentNode(TechStackAgent, depends_on=["Strategy Agent"]),
            ],
            # Stage 5: Implementation agents (parallel, depends on architecture)
            [
                AgentNode(FrontendAgent, depends_on=["Architecture Agent", "Tech Stack Agent"]),
                AgentNode(BackendAgent, depends_on=["Architecture Agent", "Tech Stack Agent"]),
                AgentNode(SecurityAgent, depends_on=["Architecture Agent"]),
            ],
            # Stage 6: Cross-cutting concerns (parallel, depends on implementation)
            [
                AgentNode(MonitoringAgent, depends_on=["Backend Agent"], is_optional=True),
                AgentNode(SelfHealingAgent, depends_on=["Backend Agent"], is_optional=True),
                AgentNode(RollbackAgent, depends_on=["Backend Agent"], is_optional=True),
            ],
            # Stage 7: Documentation (final, depends on everything)
            [
                AgentNode(DocumentationAgent),
            ],
            # Stage 8: Code Generation (parallel — all 3 run after Stage 7)
            [
                AgentNode(FrontendCodeAgent, depends_on=["Frontend Agent", "Tech Stack Agent"]),
                AgentNode(BackendCodeAgent, depends_on=["Backend Agent", "Tech Stack Agent"]),
                AgentNode(ScaffoldingAgent, depends_on=["Architecture Agent"]),
            ],
        ]
    
    async def execute_workflow(
        self,
        workflow_id: str,
        user_input: str,
        user_id: str,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Execute the full multi-agent workflow with isolation and observability.
        """
        logger.info(
            f"[Orchestrator] 🚀 Starting workflow | id={workflow_id} "
            f"user={user_id} input_preview={user_input[:80]!r}"
        )

        # Log which LLM providers are available before execution starts
        try:
            from app.agents.llm_client import llm_router
            real_providers = llm_router.real_providers
            all_providers = llm_router.available_providers
            logger.info(
                f"[Orchestrator] LLM providers | real={real_providers} "
                f"all_available={all_providers}"
            )
        except Exception:
            pass

        context = AgentContext(
            workflow_id=workflow_id,
            user_id=user_id,
            project_id=project_id,
        )
        context.user_input = user_input

        self._active_workflows[workflow_id] = context
        self._workflow_statuses[workflow_id] = {
            "status": WorkflowStatus.RUNNING,
            "started_at": time.time(),
            "stages_completed": 0,
            "agents_completed": 0,
            "agents_failed": 0,
            "total_agents": 16,
        }

        # Notify workflow started
        await ws_manager.send_to_workflow(workflow_id, {
            "type": "workflow_started",
            "workflow_id": workflow_id,
            "total_stages": 8,
            "total_agents": 16,
            "user_input": user_input,
            "timestamp": time.time(),
        })

        await ws_manager.send_log_entry(
            workflow_id, "info",
            f"[Orchestrator] 🚀 Workflow {workflow_id[:8]} started"
        )
        await ws_manager.send_log_entry(
            workflow_id, "info",
            f"[Orchestrator] 📋 Task: '{user_input[:120]}'"
        )
        await ws_manager.send_log_entry(
            workflow_id, "info",
            f"[Orchestrator] 🤖 Deploying 16 specialized agents across 8 stages (incl. code generation)"
        )
        
        stages = self._build_execution_graph()
        failed_critical = False
        workflow_start = time.time()

        try:
            for stage_idx, stage_agents in enumerate(stages):
                stage_num = stage_idx + 1
                agent_names = [node.name for node in stage_agents]
                stage_start = time.time()

                logger.info(
                    f"[Orchestrator] ▶ Stage {stage_num}/{len(stages)} | "
                    f"agents={agent_names}"
                )

                await ws_manager.send_to_workflow(workflow_id, {
                    "type": "stage_started",
                    "stage": stage_num,
                    "total_stages": len(stages),
                    "agents": agent_names,
                    "timestamp": time.time(),
                })

                await ws_manager.send_log_entry(
                    workflow_id, "info",
                    f"[Orchestrator] ── Stage {stage_num}/{len(stages)}: "
                    f"{' + '.join(agent_names)} ──"
                )

                # Execute all agents in this stage concurrently with isolation
                stage_results = await self._execute_stage_isolated(
                    stage_agents, context, stage_num
                )

                stage_elapsed = time.time() - stage_start
                stage_successes = sum(1 for r in stage_results if hasattr(r, 'success') and r.success)

                logger.info(
                    f"[Orchestrator] ✓ Stage {stage_num} done | "
                    f"elapsed={stage_elapsed:.2f}s "
                    f"success={stage_successes}/{len(stage_results)}"
                )

                # Check for critical failures (non-optional agents)
                for node in stage_agents:
                    if not node.is_optional and node.result and not node.result.success:
                        if node.name == "Goal Understanding Agent":
                            logger.error(
                                f"[Orchestrator] ❌ Critical agent failed: {node.name} "
                                f"error={node.result.error}"
                            )
                            failed_critical = True
                            break

                if failed_critical:
                    break

                self._workflow_statuses[workflow_id]["stages_completed"] = stage_num

                await ws_manager.send_to_workflow(workflow_id, {
                    "type": "stage_completed",
                    "stage": stage_num,
                    "elapsed": round(stage_elapsed, 2),
                    "successes": stage_successes,
                    "total": len(stage_results),
                    "timestamp": time.time(),
                })

                await ws_manager.send_log_entry(
                    workflow_id, "success" if stage_successes == len(stage_results) else "warning",
                    f"[Orchestrator] Stage {stage_num} complete: "
                    f"{stage_successes}/{len(stage_results)} succeeded in {stage_elapsed:.1f}s"
                )
            
            # Compile final outputs
            outputs = self._compile_outputs(context)
            total_elapsed = time.time() - workflow_start
            agents_ok = sum(1 for r in context.results.values() if r.success)
            agents_total = len(context.results)

            final_status = (
                WorkflowStatus.FAILED if failed_critical
                else WorkflowStatus.COMPLETED
                if all(
                    r.success for r in context.results.values()
                    if not self._is_optional_agent(r.agent_name)
                )
                else WorkflowStatus.PARTIALLY_COMPLETED
            )

            duration = time.time() - self._workflow_statuses[workflow_id]["started_at"]
            self._workflow_statuses[workflow_id].update({
                "status": final_status,
                "completed_at": time.time(),
                "duration": duration,
                "outputs": outputs,
            })

            await ws_manager.send_to_workflow(workflow_id, {
                "type": "workflow_completed",
                "workflow_id": workflow_id,
                "status": final_status.value,
                "outputs": outputs,
                "duration": round(duration, 2),
                "agents_succeeded": agents_ok,
                "agents_total": agents_total,
                "timestamp": time.time(),
            })

            await ws_manager.send_log_entry(
                workflow_id, "success",
                f"[Orchestrator] ✅ Workflow completed: {final_status.value} | "
                f"{agents_ok}/{agents_total} agents succeeded | "
                f"total={duration:.1f}s"
            )

            logger.info(
                f"[Orchestrator] ✅ Workflow {workflow_id} done | "
                f"status={final_status.value} "
                f"agents={agents_ok}/{agents_total} "
                f"elapsed={total_elapsed:.2f}s "
                f"outputs={list(outputs.keys())}"
            )

            # ── Post-stage: Write generated files to filesystem ──────────────
            all_generated_files: list = []
            code_agent_names = ["Frontend Code Agent", "Backend Code Agent", "Scaffolding Agent"]

            for agent_name in code_agent_names:
                result = context.results.get(agent_name)
                if result and result.success and isinstance(result.data, dict):
                    files = result.data.get("files", [])
                    if isinstance(files, list):
                        all_generated_files.extend(files)

            if all_generated_files:
                try:
                    from app.services.file_writer import file_writer_service
                    await ws_manager.send_log_entry(
                        workflow_id, "info",
                        f"[FileWriter] 📁 Writing {len(all_generated_files)} generated files..."
                    )
                    written_paths = await file_writer_service.write_project_files(
                        workflow_id, all_generated_files
                    )
                    outputs["generated_files"] = {
                        "count": len(written_paths),
                        "paths": written_paths[:30],
                        "download_url": f"/api/v1/artifacts/{workflow_id}/download",
                    }
                    await ws_manager.send_log_entry(
                        workflow_id, "success",
                        f"[FileWriter] ✅ {len(written_paths)} files written | "
                        f"Download: /api/v1/artifacts/{workflow_id}/download"
                    )
                    await ws_manager.send_to_workflow(workflow_id, {
                        "type": "files_ready",
                        "workflow_id": workflow_id,
                        "file_count": len(written_paths),
                        "download_url": f"/api/v1/artifacts/{workflow_id}/download",
                        "timestamp": time.time(),
                    })
                except Exception as fe:
                    logger.error(f"[Orchestrator] File writing failed: {fe}", exc_info=True)
                    await ws_manager.send_log_entry(
                        workflow_id, "warning",
                        f"[FileWriter] ⚠️ File writing failed: {str(fe)[:100]}"
                    )
            else:
                logger.info(f"[Orchestrator] No generated files to write for workflow {workflow_id[:8]}")

            # ── Post-stage: Persist to Supabase (fire-and-forget) ─────────────
            try:
                from app.services.supabase_service import supabase_service
                asyncio.create_task(
                    supabase_service.persist_workflow(
                        workflow_id=workflow_id,
                        user_id=user_id,
                        project_id=project_id,
                        user_input=user_input,
                        status=final_status.value,
                        outputs=outputs,
                        agent_results=context.results,
                        generated_files=all_generated_files,
                    ),
                    name=f"supabase-persist-{workflow_id[:8]}"
                )
                logger.info(f"[Orchestrator] Supabase persistence task queued for {workflow_id[:8]}")
            except Exception as se:
                logger.warning(f"[Orchestrator] Supabase task setup failed: {se}")

            return {"status": final_status.value, "outputs": outputs, "context": context.to_dict()}

        except Exception as e:
            logger.error(
                f"[Orchestrator] ❌ Workflow {workflow_id} crashed: {type(e).__name__}: {e}",
                exc_info=True,
            )
            self._workflow_statuses[workflow_id]["status"] = WorkflowStatus.FAILED

            await ws_manager.send_log_entry(
                workflow_id, "error",
                f"[Orchestrator] ❌ Critical orchestrator crash: {type(e).__name__}: {str(e)[:200]}"
            )

            return {"status": WorkflowStatus.FAILED.value, "error": str(e)}

        finally:
            # Keep in _active_workflows for status polling.
            # Clear replay buffer after a delay to save memory.
            async def _deferred_cleanup():
                await asyncio.sleep(300)  # Keep buffer 5 min after completion
                ws_manager.clear_workflow_buffer(workflow_id)
            asyncio.create_task(_deferred_cleanup(), name=f"cleanup-{workflow_id[:8]}")
    
    async def _execute_stage_isolated(
        self,
        stage_agents: List[AgentNode],
        context: AgentContext,
        stage_num: int,
    ) -> List[AgentResult]:
        """Execute a stage's agents concurrently with full isolation."""
        
        async def run_agent_isolated(node: AgentNode) -> AgentResult:
            """Run single agent with failure isolation."""
            try:
                await ws_manager.send_log_entry(
                    context.workflow_id, "info",
                    f"[{node.name}] ⚡ Starting execution..."
                )
                
                result = await node.agent.execute(context)
                node.result = result
                node.status = result.status
                
                status_icon = "✅" if result.success else "❌"
                await ws_manager.send_log_entry(
                    context.workflow_id,
                    "success" if result.success else "error",
                    f"[{node.name}] {status_icon} {'Completed' if result.success else 'Failed'} "
                    f"in {result.execution_time:.2f}s"
                )
                
                if result.success:
                    self._workflow_statuses[context.workflow_id]["agents_completed"] = (
                        self._workflow_statuses[context.workflow_id].get("agents_completed", 0) + 1
                    )
                else:
                    self._workflow_statuses[context.workflow_id]["agents_failed"] = (
                        self._workflow_statuses[context.workflow_id].get("agents_failed", 0) + 1
                    )
                    # Attempt failover if available
                    await self._attempt_failover(node, context)
                
                return result
            
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Complete isolation - one agent's crash doesn't affect others
                logger.error(f"[{node.name}] Isolated crash: {e}", exc_info=True)
                
                await ws_manager.send_log_entry(
                    context.workflow_id, "error",
                    f"[{node.name}] 💥 Crashed (isolated): {str(e)}"
                )
                
                from app.agents.base_agent import AgentResult, AgentStatus
                fallback_result = AgentResult(
                    agent_name=node.name,
                    status=AgentStatus.FAILED,
                    error=str(e),
                )
                node.result = fallback_result
                node.status = AgentStatus.FAILED
                context.add_result(node.name, fallback_result)
                return fallback_result
        
        # Run all agents in this stage concurrently
        tasks = [run_agent_isolated(node) for node in stage_agents]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results
    
    async def _attempt_failover(self, failed_node: AgentNode, context: AgentContext):
        """Attempt to run a backup/simplified version of a failed agent."""
        if not failed_node.agent.can_fail_over:
            return
        
        await ws_manager.send_log_entry(
            context.workflow_id, "warning",
            f"[Failover System] 🆘 Activating backup for {failed_node.name}"
        )
        
        # For this implementation, failover creates a new agent instance and retries once
        try:
            backup_agent = failed_node.agent_class()
            backup_agent.max_retries = 1
            backup_agent.timeout_seconds = max(30, failed_node.agent.timeout_seconds // 2)
            
            await ws_manager.send_log_entry(
                context.workflow_id, "info",
                f"[Failover System] 🔄 Backup {failed_node.name} attempting recovery..."
            )
            
            result = await backup_agent.execute(context)
            
            if result.success:
                failed_node.result = result
                failed_node.status = AgentStatus.FAILED_OVER
                
                await ws_manager.send_log_entry(
                    context.workflow_id, "success",
                    f"[Failover System] ✅ Backup {failed_node.name} recovered successfully!"
                )
        except Exception as e:
            await ws_manager.send_log_entry(
                context.workflow_id, "error",
                f"[Failover System] ❌ Backup {failed_node.name} also failed: {str(e)}"
            )
    
    def _is_optional_agent(self, agent_name: str) -> bool:
        """Check if an agent is optional."""
        optional_agents = {"Monitoring Agent", "Self-Healing Agent", "Rollback Agent"}
        return agent_name in optional_agents
    
    def _compile_outputs(self, context: AgentContext) -> Dict[str, Any]:
        """Compile all agent outputs into structured project deliverables."""
        outputs = {}
        
        output_mapping = {
            "Goal Understanding Agent": "goal_analysis",
            "Planning Agent": "project_plan",
            "Research Agent": "market_research",
            "Strategy Agent": "strategy",
            "Architecture Agent": "system_architecture",
            "Tech Stack Agent": "tech_stack",
            "Frontend Agent": "frontend_design",
            "Backend Agent": "backend_design",
            "Security Agent": "security_design",
            "Documentation Agent": "documentation",
            "Monitoring Agent": "monitoring_strategy",
            "Self-Healing Agent": "resilience_design",
            "Rollback Agent": "deployment_strategy",
        }
        
        for agent_name, output_key in output_mapping.items():
            result = context.results.get(agent_name)
            if result and result.success:
                outputs[output_key] = result.data
        
        return outputs
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get current workflow execution status."""
        return self._workflow_statuses.get(workflow_id)
    
    def get_active_workflows(self) -> List[str]:
        """Get list of currently active workflow IDs."""
        return list(self._active_workflows.keys())
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel an active workflow."""
        if workflow_id in self._active_workflows:
            self._workflow_statuses[workflow_id]["status"] = WorkflowStatus.CANCELLED
            return True
        return False


# Singleton orchestrator
orchestrator = WorkflowOrchestrator()
