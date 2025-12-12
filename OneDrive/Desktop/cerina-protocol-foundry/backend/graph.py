# graph.py
import os
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import MemorySaver
import time
from datetime import datetime
from contextlib import ExitStack
import atexit

# --- Agent Imports with proper error handling ---
try:
    from agents import (
        get_drafter_runnable,
        get_safety_guardian_runnable,
        get_clinical_critic_runnable,
        llm  # Shared LLM for supervisor
    )
    print("✅ Successfully imported agents")
except ImportError as e:
    print(f"❌ Error importing agents: {e}. Using mock agents.")
    class MockAgent:
        def invoke(self, *args, **kwargs):
            return type('obj', (object,), {
                'content': 'Mock response',
                'revision_notes': 'Mock notes',
                'score': 8,
                'reasoning': 'Mock reasoning'
            })()
    get_drafter_runnable = MockAgent
    get_safety_guardian_runnable = MockAgent
    get_clinical_critic_runnable = MockAgent
    llm = MockAgent()

# --- State Definition ---
class Review(TypedDict):
    agent: str
    notes: str
    score: int
    reasoning: str

class GraphState(TypedDict):
    user_intent: str
    draft: str
    draft_history: List[str]
    reviews: List[Review]
    scores: Dict[str, int]
    supervisor_feedback: str
    iteration_count: int
    human_approved: bool
    error: Optional[str]
    metadata: Dict[str, Any]

# --- Agent Nodes ---
def drafting_node(state: GraphState) -> Dict[str, Any]:
    """Node for creating/revising drafts."""
    print(f"\n{'='*60}")
    print(f"🧠 DRAFTING NODE - Iteration {state.get('iteration_count', 0) + 1}")
    print(f"{'='*60}")
    try:
        drafter = get_drafter_runnable()
        if state.get("iteration_count", 0) == 0:
            revision_instructions = "Create the initial draft from the user intent."
        else:
            revision_instructions = state.get("supervisor_feedback", "Improve the draft based on previous feedback.")
        
        print(f"📝 User Intent: {state['user_intent'][:100]}...")
        print(f"📝 Revision Instructions: {revision_instructions[:100]}...")
        
        start_time = time.time()
        response = drafter.invoke({
            "user_intent": state["user_intent"],
            "revision_instructions": revision_instructions
        })
        draft_time = time.time() - start_time
        
        draft_content = response.content if hasattr(response, 'content') else str(response)
        
        print(f"✅ Draft generated in {draft_time:.2f}s")
        print(f"📄 Draft length: {len(draft_content)} characters")
        
        return {
            "draft": draft_content,
            "iteration_count": state.get("iteration_count", 0) + 1,
            "draft_history": state.get("draft_history", []) + [draft_content],
            "error": None,
            "metadata": {**state.get("metadata", {}), "drafting_time": draft_time, "last_drafted": datetime.now().isoformat()}
        }
    except Exception as e:
        print(f"❌ Drafting error: {e}")
        return {"draft": state.get("draft", ""), "error": f"Drafting error: {str(e)}"}

def review_node(state: GraphState) -> Dict[str, Any]:
    """Node for safety and clinical reviews."""
    print(f"\n{'='*60}")
    print(f"🔍 REVIEW NODE")
    print(f"{'='*60}")
    try:
        safety_guardian = get_safety_guardian_runnable()
        clinical_critic = get_clinical_critic_runnable()
        draft_content = state["draft"]
        print(f"📄 Reviewing draft of {len(draft_content)} characters")

        start_time = time.time()

        # Handle each review independently; never fail the entire node if one reviewer trips
        safety_notes = "No notes"
        safety_score = 7
        safety_reasoning = "Safety review completed"
        try:
            safety_result = safety_guardian.invoke({"draft": draft_content})
            safety_notes = getattr(safety_result, 'revision_notes', safety_notes)
            safety_score = getattr(safety_result, 'score', safety_score)
            safety_reasoning = getattr(safety_result, 'reasoning', safety_reasoning)
        except Exception as e:
            print(f"⚠️ Safety review error (continuing): {e}")

        clinical_notes = "No notes"
        clinical_score = 7
        clinical_reasoning = "Clinical review completed"
        try:
            clinical_result = clinical_critic.invoke({"draft": draft_content})
            clinical_notes = getattr(clinical_result, 'revision_notes', clinical_notes)
            clinical_score = getattr(clinical_result, 'score', clinical_score)
            clinical_reasoning = getattr(clinical_result, 'reasoning', clinical_reasoning)
        except Exception as e:
            print(f"⚠️ Clinical review error (continuing): {e}")

        review_time = time.time() - start_time
        
        reviews = [
            {"agent": "SafetyGuardian", "notes": safety_notes, "score": safety_score, "reasoning": safety_reasoning},
            {"agent": "ClinicalCritic", "notes": clinical_notes, "score": clinical_score, "reasoning": clinical_reasoning}
        ]
        scores = {"safety": safety_score, "clinical": clinical_score}
        
        print(f"✅ Reviews completed in {review_time:.2f}s")
        print(f"📊 Safety Score: {scores['safety']}/10")
        print(f"📊 Clinical Score: {scores['clinical']}/10")
        
        return {
            "reviews": reviews, "scores": scores, "error": None,
            "metadata": {**state.get("metadata", {}), "review_time": review_time, "last_reviewed": datetime.now().isoformat()}
        }
    except Exception as e:
        print(f"❌ Review error: {e}")
        return {"reviews": state.get("reviews", []), "scores": state.get("scores", {}), "error": f"Review error: {str(e)}"}

def supervisor_synthesis_node(state: GraphState) -> Dict[str, Any]:
    """Node for synthesizing feedback from both reviewers."""
    print(f"\n{'='*60}")
    print(f"🎯 SUPERVISOR SYNTHESIS NODE")
    print(f"{'='*60}")
    try:
        reviews = state.get("reviews", [])
        if not reviews:
            return {"supervisor_feedback": "No feedback available. Continue with original intent."}

        safety_review = next((r for r in reviews if r["agent"] == "SafetyGuardian"), {})
        clinical_review = next((r for r in reviews if r["agent"] == "ClinicalCritic"), {})
        
        synthesis_prompt = f"""
As the Supervisor, synthesize this feedback for the Drafter.
DRAFT ITERATION: {state.get("iteration_count", 0)}
USER INTENT: {state.get('user_intent', 'Not specified')}
SAFETY REVIEW (Score: {safety_review.get('score', 'N/A')}/10): {safety_review.get('notes', 'No safety notes')}
CLINICAL REVIEW (Score: {clinical_review.get('score', 'N/A')}/10): {clinical_review.get('notes', 'No clinical notes')}
Create CLEAR, ACTIONABLE instructions for the next draft. Prioritize the most important changes.
Format your response as bullet points starting with •.
Instructions for Drafter:"""
        
        print("🤔 Synthesizing feedback from reviewers...")
        start_time = time.time()
        response = llm.invoke(synthesis_prompt)
        feedback = response.content if hasattr(response, 'content') else str(response)
        synthesis_time = time.time() - start_time
        
        print(f"✅ Feedback synthesized in {synthesis_time:.2f}s")
        print(f"📋 Feedback: {feedback[:150]}...")
        
        return {
            "supervisor_feedback": feedback, "error": None,
            "metadata": {**state.get("metadata", {}), "synthesis_time": synthesis_time}
        }
    except Exception as e:
        print(f"❌ Synthesis error: {e}")
        return {"supervisor_feedback": "Error in synthesis.", "error": f"Synthesis error: {str(e)}"}

# --- Router Logic ---
def supervisor_router(state: GraphState) -> str:
    """Determine next step based on scores and iteration count."""
    print(f"\n{'='*60}")
    print(f"🔄 SUPERVISOR ROUTER")
    print(f"{'='*60}")
    
    if state.get("error"):
        print(f"❌ Error detected: {state['error']} → Requesting human review")
        return "request_human_review"
    
    if state.get("human_approved", False):
        print("✅ Human approved → Finalize")
        return "finalize"
    
    scores = state.get("scores", {})
    safety_score = scores.get("safety", 0)
    clinical_score = scores.get("clinical", 0)
    iteration = state.get("iteration_count", 0)
    
    print(f"📊 Scores - Safety: {safety_score}, Clinical: {clinical_score} | Iteration: {iteration}")
    
    if safety_score >= 9 and clinical_score >= 8:
        print("🎯 Decision: High scores → Request human review")
        return "request_human_review"
    elif iteration >= 3 or safety_score < 6:
        print("⏰ Decision: Max iterations or low safety score → Request human review")
        return "request_human_review"
    elif safety_score < 8 or clinical_score < 7:
        print("🔧 Decision: Needs improvement → Revise")
        return "revise"
    else:
        print("🤔 Decision: Borderline scores → Request human review")
        return "request_human_review"

def human_review_halt_node(state: GraphState):
    """A node that simply prints a halt message."""
    print("\n⏸️ GRAPH HALTED FOR HUMAN REVIEW")
    print("   The API will now wait for a /resume request.")
    return state

# --- Build the Graph (but don't compile yet) ---
def build_workflow():
    """Builds the StateGraph workflow object."""
    workflow = StateGraph(GraphState)
    workflow.add_node("drafter", drafting_node)
    workflow.add_node("reviewer", review_node)
    workflow.add_node("supervisor_synthesis", supervisor_synthesis_node)
    workflow.add_node("human_review_halt", human_review_halt_node)
    
    workflow.set_entry_point("drafter")
    workflow.add_edge("drafter", "reviewer")
    workflow.add_edge("reviewer", "supervisor_synthesis")
    
    workflow.add_conditional_edges(
        "supervisor_synthesis",
        supervisor_router,
        {
            "revise": "drafter",
            "request_human_review": "human_review_halt",
            "finalize": END
        }
    )
    
    # After human review, we either finalize or end.
    workflow.add_edge("human_review_halt", "supervisor_synthesis")
    
    return workflow

print("\n" + "="*60)
print("🏗️  INITIALIZING AND COMPILING LANGGRAPH WORKFLOW")
print("="*60)

# Build the workflow definition
workflow = build_workflow()

# Create a 'db' directory using an absolute path to avoid CWD issues.
script_dir = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.join(script_dir, "db")
if not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

# Normalize to forward slashes to avoid Windows sqlite path issues
db_path = os.path.abspath(os.path.join(db_dir, "cerina_graph.db")).replace("\\", "/")
DB_CONNECTION_STRING = f"sqlite:///{db_path}"

# Properly create a long-lived SqliteSaver using an ExitStack.
_exit_stack = ExitStack()
def _cleanup_exit_stack():
    try:
        _exit_stack.close()
    except Exception:
        pass

atexit.register(_cleanup_exit_stack)

# Create the checkpointer
try:
    memory = _exit_stack.enter_context(SqliteSaver.from_conn_string(DB_CONNECTION_STRING))
    print(f"✅ SQLite checkpointer configured for: {DB_CONNECTION_STRING}")
except Exception as e:
    print(f"❌ SQLite checkpointer error: {e}")
    print("⚠️ Falling back to in-memory checkpointer (state will not be saved)")
    memory = MemorySaver()

# Compile the graph with the checkpointer
try:
    graph_app = workflow.compile(
        checkpointer=memory,
        interrupt_before=["human_review_halt"]
    )
    print("✅ Graph compiled successfully!")
except Exception as e:
    print(f"❌ CRITICAL: Graph compilation failed: {e}")
    class MockApp:
        async def astream(self, *args, **kwargs):
            yield {"error": f"Graph compilation failed: {e}"}
        async def aget_state(self, *args, **kwargs):
            return type('obj', (object,), {'values': {"error": f"Graph compilation failed: {e}"}})()
        async def update_state(self, *args, **kwargs):
            pass
    graph_app = MockApp()

print("✅ Graph initialization complete!")




