import asyncio
import sys
import json
from datetime import datetime
from typing import Dict, Any

# Import the graph
try:
    from graph import graph_app
    print("✅ MCP Server: Graph module imported")
except ImportError as e:
    print(f"❌ MCP Server: Graph import error: {e}")
    sys.exit(1)

async def process_mcp_request(user_intent: str, thread_id: str = None) -> Dict[str, Any]:
    """
    Process an MCP request - automated version without human review.
    """
    if not thread_id:
        thread_id = f"mcp_{hash(user_intent) % 10000:08d}"
    
    print(f"\n🔧 MCP Processing: {user_intent[:50]}...")
    print(f"📋 Thread ID: {thread_id}")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # Initial state - human_approved is True for automated processing
    initial_state = {
        "user_intent": user_intent,
        "iteration_count": 0,
        "draft_history": [],
        "human_approved": True,  # Skip human review for MCP
        "supervisor_feedback": "",
        "draft": "",
        "reviews": [],
        "scores": {},
        "error": None,
        "metadata": {
            "source": "mcp_server",
            "processed_at": datetime.now().isoformat(),
            "automated": True
        }
    }
    
    final_state = None
    iterations = 0
    
    try:
        # Execute graph with no human interruption
        print("🚀 Starting automated graph execution...")
        
        async for step in graph_app.astream(initial_state, config, stream_mode="values"):
            final_state = step
            iterations = step.get("iteration_count", 0)
            
            # Print progress
            if "draft" in step and step["draft"]:
                draft_preview = step["draft"][:100].replace('\n', ' ') + "..."
                print(f"  ↪ Iteration {iterations}: {draft_preview}")
            
            # Check scores if available
            if "scores" in step:
                scores = step["scores"]
                print(f"  📊 Scores: Safety={scores.get('safety', 'N/A')}, Clinical={scores.get('clinical', 'N/A')}")
        
        # Extract result
        if final_state and "draft" in final_state:
            result = {
                "success": True,
                "thread_id": thread_id,
                "draft": final_state["draft"],
                "iterations": iterations,
                "scores": final_state.get("scores", {}),
                "reviews": final_state.get("reviews", []),
                "processing_time": datetime.now().isoformat(),
                "status": "completed"
            }
            
            print(f"\n✅ MCP Processing Complete!")
            print(f"   Iterations: {iterations}")
            print(f"   Safety Score: {result['scores'].get('safety', 'N/A')}/10")
            print(f"   Clinical Score: {result['scores'].get('clinical', 'N/A')}/10")
            print(f"   Draft Length: {len(result['draft'])} characters")
            
            return result
        else:
            return {
                "success": False,
                "error": "No draft produced",
                "thread_id": thread_id,
                "status": "failed"
            }
            
    except Exception as e:
        error_msg = f"MCP processing error: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "thread_id": thread_id,
            "status": "error"
        }

# --- Command-line Interface ---
async def interactive_cli():
    """Interactive command-line interface."""
    print("\n" + "="*60)
    print("🤖 CERINA MCP SERVER - Automated Processing")
    print("="*60)
    print("\nEnter CBT exercise intents (or 'quit' to exit):")
    
    while True:
        try:
            user_input = input("\n📝 Enter intent: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not user_input:
                print("⚠️  Please enter an intent")
                continue
            
            # Process the request
            result = await process_mcp_request(user_input)
            
            if result["success"]:
                print("\n" + "="*60)
                print("📄 FINAL DRAFT")
                print("="*60)
                print(result["draft"])
                print("\n" + "="*60)
                
                # Ask if user wants to save
                save = input("\n💾 Save to file? (y/n): ").strip().lower()
                if save == 'y':
                    filename = f"cbt_exercise_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(result["draft"])
                    print(f"✅ Saved to {filename}")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted - Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        # Process single intent from command line
        user_intent = " ".join(sys.argv[1:])
        result = asyncio.run(process_mcp_request(user_intent))
        
        if result["success"]:
            print(result["draft"])
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    else:
        # Start interactive CLI
        asyncio.run(interactive_cli())
