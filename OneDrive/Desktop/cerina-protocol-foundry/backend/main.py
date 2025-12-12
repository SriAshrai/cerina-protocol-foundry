# *** main.py ***
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import uuid
import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cerina_api")

# Import graph
try:
    from graph import graph_app
    print("✅ Successfully imported graph application")
except ImportError as e:
    print(f"❌ Graph import error: {e}. Using mock graph.")
    class MockGraphApp:
        async def astream(self, *args, **kwargs): 
            yield {"draft": "Mock draft", "iteration_count": 1}
        async def aget_state(self, *args, **kwargs):
            return type('obj', (object,), {'values': {'draft': '# Mock Exercise'}, 'next': []})()
        async def update_state(self, *args, **kwargs): 
            pass
    graph_app = MockGraphApp()

# Initialize FastAPI
api = FastAPI(
    title="Cerina Protocol Foundry API",
    description="Multi-agent CBT exercise generation system",
    version="2.0.0",
)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---
class InvokeRequest(BaseModel):
    intent: str
    thread_id: Optional[str] = None

class ResumeRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None
    edited_draft: Optional[str] = None

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# --- Task Management ---
class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.task_logs: list = []

    async def create_task(self, thread_id: str, intent: str):
        async with self.lock:
            self.tasks[thread_id] = {
                "status": "pending",
                "intent": intent,
                "created_at": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat(),
                "state": None
            }
    
    async def update_task_status(self, thread_id: str, status: str, state: Optional[Dict] = None):
        async with self.lock:
            if thread_id in self.tasks:
                self.tasks[thread_id]["status"] = status
                self.tasks[thread_id]["last_update"] = datetime.now().isoformat()
                if state is not None:
                    self.tasks[thread_id]["state"] = state

    async def get_task(self, thread_id: str):
        async with self.lock:
            return self.tasks.get(thread_id)

    def get_all_tasks(self) -> Dict[str, Dict]:
        return self.tasks

    def log_event(self, thread_id: str, action: str, details: str = ""):
        log_entry = {
            "id": len(self.task_logs) + 1,
            "thread_id": thread_id,
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.task_logs.append(log_entry)
        logger.info(f"LOG [{thread_id}]: {action} - {details}")

task_manager = TaskManager()

# --- Graph Execution Helper ---
async def execute_graph(thread_id: str, intent: str):
    logger.info(f"🚀 Starting graph execution: thread={thread_id}")
    await task_manager.update_task_status(thread_id, "running")
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "user_intent": intent,
        "iteration_count": 0,
        "draft_history": [],
        "human_approved": False,
        "supervisor_feedback": "",
        "draft": "",
        "reviews": [],
        "scores": {},
        "error": None,
        "metadata": {"created_at": datetime.now().isoformat(), "intent": intent}
    }
    
    try:
        final_state = None
        async for step in graph_app.astream(initial_state, config, stream_mode="values"):
            final_state = step

        # After stream finishes, check if we halted before 'human_review_halt'
        # When using interrupt_before=['human_review_halt'], the stream ends BEFORE that node runs.
        try:
            snapshot = await graph_app.aget_state(config)
            next_nodes = getattr(snapshot, "next", None)
        except Exception as e:
            logger.warning(f"Could not get state from graph checkpointer for {thread_id}: {e}")
            next_nodes = None

        if next_nodes and "human_review_halt" in next_nodes:
            logger.warning(f"⏸️ Graph halted for human review: thread={thread_id}")
            await task_manager.update_task_status(thread_id, "halted", state=final_state)
            return

        logger.info(f"✅ Graph finished successfully: thread={thread_id}")
        await task_manager.update_task_status(thread_id, "completed", state=final_state)

    except Exception as e:
        logger.error(f"🔥 Graph execution failed for thread {thread_id}: {e}", exc_info=True)
        await task_manager.update_task_status(thread_id, f"error: {e}")

# --- API Endpoints ---
@api.get("/", response_model=APIResponse)
async def root():
    return APIResponse(success=True, message="Cerina Protocol Foundry API is running")

@api.get("/health", response_model=APIResponse)
async def health_check():
    return APIResponse(success=True, message="Service is healthy", data={"active_tasks": len(task_manager.tasks)})

@api.get("/tasks", response_model=APIResponse)
async def get_all_tasks():
    tasks = task_manager.get_all_tasks()
    return APIResponse(success=True, message=f"Found {len(tasks)} tasks", data={"tasks": tasks})

@api.post("/invoke", response_model=APIResponse)
async def invoke_graph_endpoint(request: InvokeRequest, background_tasks: BackgroundTasks):
    if not request.intent.strip():
        raise HTTPException(status_code=400, detail="Intent cannot be empty")
    
    thread_id = request.thread_id or f"thread_{uuid.uuid4().hex[:8]}"
    await task_manager.create_task(thread_id, request.intent.strip())
    
    background_tasks.add_task(execute_graph, thread_id, request.intent.strip())
    
    return APIResponse(success=True, message="Graph execution started", data={"thread_id": thread_id})

@api.get("/state/{thread_id}", response_model=APIResponse)
async def get_state(thread_id: str):
    task = await task_manager.get_task(thread_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    config = {"configurable": {"thread_id": thread_id}}
    try:
        state_snapshot = await graph_app.aget_state(config)
        # Return both values and next if available
        current_state = getattr(state_snapshot, "values", task.get("state"))
        next_nodes = getattr(state_snapshot, "next", [])
    except Exception as e:
        logger.warning(f"Could not get state from graph checkpointer for {thread_id}: {e}")
        current_state = task.get("state")
        next_nodes = []

    return APIResponse(
        success=True,
        message=f"Task status: {task['status']}",
        data={
            "status": task["status"],
            "state": current_state,
            "next": next_nodes
        }
    )

@api.post("/resume/{thread_id}", response_model=APIResponse)
async def resume_graph(thread_id: str, request: ResumeRequest, background_tasks: BackgroundTasks):
    task = await task_manager.get_task(thread_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")
    if task["status"] != "halted":
        raise HTTPException(status_code=400, detail=f"Task is not halted (status: {task['status']})")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    if request.approved:
        task_manager.log_event(thread_id, "human_approved", f"Feedback: {request.feedback or 'N/A'}")
        
        # Prepare the state update
        update_state = {"human_approved": True}
        if request.edited_draft:
            update_state["draft"] = request.edited_draft
        
        async def continue_execution():
            try:
                await task_manager.update_task_status(thread_id, "resuming")
                # 1. Update the state in the checkpointer
                await graph_app.update_state(config, update_state)
                
                # 2. Continue the stream with None as input
                final_state = None
                async for step in graph_app.astream(None, config, stream_mode="values"):
                    final_state = step
                
                logger.info(f"✅ Graph resumed and completed: thread={thread_id}")
                await task_manager.update_task_status(thread_id, "completed", state=final_state)
            except Exception as e:
                logger.error(f"🔥 Graph resume failed for {thread_id}: {e}", exc_info=True)
                await task_manager.update_task_status(thread_id, f"error: {e}")

        background_tasks.add_task(continue_execution)
        return APIResponse(success=True, message="Graph resumed with approval", data={"thread_id": thread_id, "status": "resuming"})
    else:
        task_manager.log_event(thread_id, "human_rejected", f"Feedback: {request.feedback or 'N/A'}")
        await task_manager.update_task_status(thread_id, "rejected")
        return APIResponse(success=True, message="Graph rejected and process terminated", data={"thread_id": thread_id, "status": "rejected"})

# --- Main Execution ---
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 CERINA PROTOCOL FOUNDRY - BACKEND API")
    print("="*60)
    print("📡 Starting server... (Press CTRL+C to stop)")
    # Note: 0.0.0.0 is a bind address; open http://localhost:8000 in your browser
    print(f"🌐 API URL: http://localhost:8000")
    print(f"📚 Docs:    http://localhost:8000/docs")
    print("="*60 + "\n")
    
    uvicorn.run("main:api", host="0.0.0.0", port=8000, reload=True)
