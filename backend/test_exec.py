import asyncio, json, sys, time
sys.path.insert(0, '/app')

async def full_test():
    from app.agents.orchestrator import orchestrator
    from app.core.websocket_manager import ws_manager
    from app.agents.llm_client import llm_router

    print("=== FULL EXECUTION PIPELINE TEST ===")
    print()
    print("LLM providers:", llm_router.available_providers)
    print("Real providers:", llm_router.real_providers)
    print()

    wf_id = "test-workflow-e2e"
    print(f"Starting workflow: {wf_id}")
    t0 = time.time()

    result = await orchestrator.execute_workflow(
        workflow_id=wf_id,
        user_input="Build a simple task management app",
        user_id="test-user",
        project_id="test-project",
    )

    elapsed = time.time() - t0
    print()
    status = result.get("status", "unknown")
    print(f"=== WORKFLOW COMPLETED in {elapsed:.1f}s ===")
    print(f"Status: {status}")
    outputs = result.get("outputs", {})
    print(f"Output keys: {list(outputs.keys())}")
    print(f"Total output sections: {len(outputs)}")
    print()

    buf = list(ws_manager._replay_buffers.get(wf_id, []))
    print(f"Replay buffer events: {len(buf)}")
    event_types = [e.get("type") for e in buf]
    print(f"Event types: {event_types[:30]}")
    print()

    ctx = result.get("context", {})
    results_dict = ctx.get("results", {})
    for name, r in results_dict.items():
        s = r.get("status", "?")
        et = r.get("execution_time", 0)
        dk = list(r.get("data", {}).keys())[:5]
        print(f"  {s:10s} | {et:5.1f}s | {name} | keys={dk}")

asyncio.run(full_test())
