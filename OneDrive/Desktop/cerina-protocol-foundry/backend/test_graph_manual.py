import asyncio
from graph import graph_app

async def test_full_workflow():
    print("🧪 Testing complete workflow")
    
    config = {"configurable": {"thread_id": "manual_test_001"}}
    
    initial_state = {
        "user_intent": "Create exercise for test anxiety",
        "iteration_count": 0,
        "draft_history": [],
        "human_approved": False,
        "supervisor_feedback": "",
        "draft": "",
        "reviews": [],
        "scores": {},
        "error": None,
        "metadata": {"source": "test_graph_manual"}
    }
    
    try:
        print("1. Starting graph stream...")
        final_state = None
        async for step in graph_app.astream(initial_state, config, stream_mode="values"):
            final_state = step
            print(f"\n📦 Step received:")
            print(f"   Iteration: {step.get('iteration_count')}")
            print(f"   Draft preview: {step.get('draft', '')[:80]}...")
            print(f"   Scores: {step.get('scores', {})}")
            print(f"   Reviews: {len(step.get('reviews', []))}")

        # Optional: Check snapshot to see if halted
        snapshot = await graph_app.aget_state(config)
        next_nodes = getattr(snapshot, "next", [])
        if next_nodes and "human_review_halt" in next_nodes:
            print("\n⏸️ Graph halted for human review (as expected when interrupt_before is set).")
        else:
            print("\n✅ Graph execution completed (no halts).")
        
    except Exception as e:
        print(f"❌ Graph failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_workflow())
