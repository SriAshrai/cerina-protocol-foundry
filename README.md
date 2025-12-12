# Cerina Protocol Foundry API

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![Framework: FastAPI](https://img.shields.io/badge/Framework-FastAPI-green.svg)

The Cerina Protocol Foundry is a robust, multi-agent system for generating high-quality Cognitive Behavioral Therapy (CBT) exercises. It leverages a collaborative workflow of drafting, reviewing, and supervision agents to ensure content is safe, clinically sound, and effective, with a human-in-the-loop for final approval.

## ✨ Key Features

*   **Multi-Agent Collaboration**: Utilizes specialized agents (Drafter, Safety Guardian, Clinical Critic, Supervisor) for a sophisticated content creation pipeline.
*   **Stateful, Resumable Workflows**: Built on [LangGraph](https://github.com/langchain-ai/langgraph), allowing processes to be paused for human review and resumed seamlessly.
*   **Persistent State**: Uses a SQLite backend to save graph state, ensuring no work is lost between server restarts.
*   **Robust Structured Output**: Employs Pydantic models and custom parsing logic in `agents.py` to handle unreliable JSON outputs from LLMs gracefully.
*   **Human-in-the-Loop**: The graph intelligently halts for human approval when content scores are high, revision limits are met, or safety scores are low.
*   **Dual-Interface**: Provides both a REST API (via FastAPI) for web applications and a command-line interface (`mcp_server.py`) for automated, headless content generation.
*   **Configurable LLMs**: Easily integrates with any OpenAI-compatible API, with first-class support for [OpenRouter.ai](https://openrouter.ai/).

## 🏛️ System Architecture

The core of the system is a cyclical graph where a draft is iteratively refined until it meets the required quality standards.

```mermaid
graph TD
    subgraph "API / External Trigger"
        A[POST /invoke] --> B{drafter};
        H_Resume[POST /resume] --> F;
    end

    subgraph "LangGraph Workflow"
        B -- "Draft v1" --> C[reviewer\n(Safety & Clinical Agents)];
        C -- "Scores & Notes" --> D{supervisor_synthesis};
        D -- "Synthesized Feedback" --> E{supervisor_router};

        E -- "Needs Revision\n(Low Scores)" --> B;
        E -- "High Scores / Max Iterations / Error" --> F[human_review_halt\n(PAUSE)];
        F -- "State updated via API" --> D;
        E -- "Human Approved" --> G((END));
    end

    style F fill:#f9f,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
Of course. Based on the comprehensive backend code you've provided, here is a detailed prompt for generating the system topology and a complete, professional README.md file for your GitHub repository.

1. Prompt for Generating System Topology
This prompt is designed to be used with a capable AI model (like GPT-4, Claude 3, etc.) to generate a Mermaid diagram that accurately represents your multi-agent system's architecture and logic.

The Prompt:

You are an expert systems architect specializing in creating clear topology diagrams for complex multi-agent workflows. Your task is to generate a Mermaid graph TD (Top-Down) diagram based on the following detailed specification of a LangGraph-based system.

System Overview:
The system is a multi-agent workflow designed to generate high-quality Cognitive Behavioral Therapy (CBT) exercises. It uses a cycle of drafting, reviewing, and supervision to refine content until it meets specific quality and safety standards, at which point it can be approved by a human.

Key Components:

Shared State (GraphState): This is the central data structure passed between all nodes. It contains:

user_intent: The initial user request.
draft: The current version of the CBT exercise.
reviews: A list of feedback objects from reviewer agents.
scores: A dictionary holding scores (e.g., safety, clinical).
supervisor_feedback: Synthesized, actionable instructions for the drafter.
iteration_count: Tracks the number of revision cycles.
human_approved: A boolean flag set to True to finalize the process.
error: An optional string for capturing errors.
Agent Nodes:

drafter: The entry point. It creates the initial draft from user_intent or revises an existing draft based on supervisor_feedback.
reviewer: A parallel processing step where two independent agents, a SafetyGuardian and a ClinicalCritic, review the draft and produce scores and reviews.
supervisor_synthesis: This node analyzes the reviews and scores to generate consolidated supervisor_feedback for the drafter.
human_review_halt: A special interruption node. The graph pauses here to await external input.
END: The final state of the graph.
Workflow Logic and Edges:

The process starts at the drafter node.
After drafting, the state moves to the reviewer node.
After reviewing, the state moves to the supervisor_synthesis node.
After synthesis, the state is passed to a conditional router, the supervisor_router.
Router Logic (supervisor_router):
This is the critical decision point. Based on the current state, it routes to one of four paths:

Condition: An error is present in the state.
Outcome: Route to human_review_halt.
Condition: human_approved is True.
Outcome: Route to END (finalize).
Condition: safety_score >= 9 AND clinical_score >= 8.
Outcome: Route to human_review_halt for final approval.
Condition: iteration_count >= 3 OR safety_score < 6.
Outcome: Route to human_review_halt for mandatory human intervention.
Condition (Default/Revise): safety_score < 8 OR clinical_score < 7.
Outcome: Route back to the drafter node for another revision cycle.
Condition (Default/Halt): Any other case (e.g., borderline scores).
Outcome: Route to human_review_halt.
Human-in-the-Loop:

The human_review_halt node is where the system pauses.
An external API call (/resume) provides a boolean approved signal.
If approved, the human_approved flag in the state is set to True.
The graph then resumes, re-entering the supervisor_synthesis node, where the supervisor_router will now see human_approved is True and route to END.
Diagram Requirements:

Use Mermaid graph TD syntax.
Use rectangular boxes for agent nodes (e.g., drafter, reviewer).
Use a diamond shape for the supervisor_router conditional logic.
Use a circle or rounded box for the END state.
Use a box with a different style (e.g., dotted border or different color) for human_review_halt to indicate it's an interrupt point.
Clearly label all edges, especially the conditional paths from the router (e.g., "Needs Revision", "High Scores", "Max Iterations").
Show the main feedback loop clearly.
Now, generate the Mermaid code for this system topology.

2. Professional README.md File Content
This content is structured to be clear, comprehensive, and welcoming to new users or contributors.


          

markdown


# Cerina Protocol Foundry API

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![Framework: FastAPI](https://img.shields.io/badge/Framework-FastAPI-green.svg)

The Cerina Protocol Foundry is a robust, multi-agent system for generating high-quality Cognitive Behavioral Therapy (CBT) exercises. It leverages a collaborative workflow of drafting, reviewing, and supervision agents to ensure content is safe, clinically sound, and effective, with a human-in-the-loop for final approval.

## ✨ Key Features

*   **Multi-Agent Collaboration**: Utilizes specialized agents (Drafter, Safety Guardian, Clinical Critic, Supervisor) for a sophisticated content creation pipeline.
*   **Stateful, Resumable Workflows**: Built on [LangGraph](https://github.com/langchain-ai/langgraph), allowing processes to be paused for human review and resumed seamlessly.
*   **Persistent State**: Uses a SQLite backend to save graph state, ensuring no work is lost between server restarts.
*   **Robust Structured Output**: Employs Pydantic models and custom parsing logic in `agents.py` to handle unreliable JSON outputs from LLMs gracefully.
*   **Human-in-the-Loop**: The graph intelligently halts for human approval when content scores are high, revision limits are met, or safety scores are low.
*   **Dual-Interface**: Provides both a REST API (via FastAPI) for web applications and a command-line interface (`mcp_server.py`) for automated, headless content generation.
*   **Configurable LLMs**: Easily integrates with any OpenAI-compatible API, with first-class support for [OpenRouter.ai](https://openrouter.ai/).

## 🏛️ System Architecture

The core of the system is a cyclical graph where a draft is iteratively refined until it meets the required quality standards.

```mermaid
graph TD
    subgraph "API / External Trigger"
        A[POST /invoke] --> B{drafter};
        H_Resume[POST /resume] --> F;
    end

    subgraph "LangGraph Workflow"
        B -- "Draft v1" --> C[reviewer\n(Safety & Clinical Agents)];
        C -- "Scores & Notes" --> D{supervisor_synthesis};
        D -- "Synthesized Feedback" --> E{supervisor_router};

        E -- "Needs Revision\n(Low Scores)" --> B;
        E -- "High Scores / Max Iterations / Error" --> F[human_review_halt\n(PAUSE)];
        F -- "State updated via API" --> D;
        E -- "Human Approved" --> G((END));
    end

    style F fill:#f9f,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5


                
🛠️ Technology Stack
Backend Framework: FastAPI
Orchestration: LangGraph
LLM Interaction: LangChain
Data Validation: Pydantic
LLM Provider: OpenRouter.ai (configurable)
Database: SQLite for state checkpointing

🚀 Getting Started
Prerequisites
Python 3.9+
An API key from OpenRouter.ai or another OpenAI-compatible service.
## 🛠️ Technology Stack
- Backend Framework: FastAPI
- Orchestration: LangGraph
- LLM Interaction: LangChain
- Data Validation: Pydantic
- LLM Provider: OpenRouter.ai (configurable)
- Database: SQLite (for LangGraph state checkpointing)
## 🚀 Getting Started
### Prerequisites
- Python 3.9+
- An API key from OpenRouter.ai or another OpenAI-compatible provider
### Installation
#### 1. Clone the repository
```bash
git clone https://github.com/your-username/cerina-protocol-foundry.git
cd cerina-protocol-foundry
2. Create and activate a virtual environment
bash
Copy code
python -m venv venv
source venv/bin/activate
On Windows:

bash
Copy code
venv\Scripts\activate
3. Install dependencies
bash
Copy code
pip install -r requirements.txt
4. Configure environment variables
bash
Copy code
cp .env.example .env
Edit the .env file:

env
Copy code
OPENROUTER_API_KEY="your-openrouter-api-key"
OPENROUTER_REFERRER="http://localhost:3000"
# OPENROUTER_MODEL="openai/gpt-4o"
▶️ Running the Application
API Server (for web clients)
bash
Copy code
uvicorn main:api --reload
API URL: http://localhost:8000
Swagger UI: http://localhost:8000/docs

MCP Server (for automated CLI generation)
bash
Copy code
python mcp_server.py
Follow the CLI prompts to enter an intent.

⚙️ API Usage Example
Start a new generation process
bash
Copy code
curl -X POST "http://localhost:8000/invoke" -H "Content-Type: application/json" -d '{"intent":"Create a CBT exercise to help with procrastination"}'
Response:

json
Copy code
{"success":true,"message":"Graph execution started","data":{"thread_id":"thread_xxxxxxxx"}}
Check process status
bash
Copy code
curl http://localhost:8000/state/thread_xxxxxxxx
Example halted response:

json
Copy code
{"success":true,"message":"Task status: halted","data":{"status":"halted","state":{"user_intent":"...","draft":"## Draft Content..."},"next":["human_review_halt"]}}
Resume after human review
bash
Copy code
curl -X POST "http://localhost:8000/resume/thread_xxxxxxxx" -H "Content-Type: application/json" -d '{"approved":true}'
Response:

json
Copy code
{"success":true,"message":"Graph resumed with approval","data":{"thread_id":"thread_xxxxxxxx","status":"resuming"}}
📁 Project Structure
graphql
Copy code
.
├── db/                     # SQLite database for LangGraph checkpointer
├── agents.py               # LLM-powered agents and prompts
├── graph.py                # LangGraph workflow and state logic
├── main.py                 # FastAPI app and API endpoints
├── mcp_server.py           # CLI-based generation server
├── test_endpoints.py       # API health tests
├── test_graph_manual.py    # Manual graph execution
├── .env.example            # Environment variable template
└── requirements.txt        # Python dependencies

🧪 Testing
Test API endpoints
bash
Copy code
python test_endpoints.py
Test graph manually
bash
Copy code
python test_graph_manual.py

🤝 Contributing
Contributions are welcome. Please open an issue or submit a pull request for bug fixes, improvements, or feature requests.


          


                

