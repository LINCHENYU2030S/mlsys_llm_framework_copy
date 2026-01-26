# Track 1: Dynamic Agentic Workflow

## Overview
This starter kit provides a scaffold for building an agentic LLM engine. Your goal is to implement an engine that can receive high-level tasks, break them down into steps, execute tools, and return a final result.

## Project Structure
```text
.
├── app/
│   ├── main.py          # FastAPI entry point.
│   ├── schemas.py       # Pydantic models for request/response.
│   └── agent_engine.py  # MAIN LOGIC GOES HERE.
├── Dockerfile           # Environment definition.
├── pyproject.toml       # Python dependencies.
└── README.md
```

## How to Run

### Option 1: Docker Compose (Recommended)
This method automatically mounts the Hugging Face cache and sets up the environment.
```bash
docker compose up --build
```

### Option 2: Manual Docker Build
    ```bash
    docker build -t agent-engine .
    ```

2.  **Run the Container**
    ```bash
    docker run -p 8000:8000 agent-engine
    ```

3.  **Check Status**
    *   Liveness: `GET http://localhost:8000/health`
    *   Readiness: `GET http://localhost:8000/ready`

## Your Task
Modify `app/agent_engine.py` to replace the `MockLLM` with your actual LLM integration (e.g., using vLLM, HuggingFace, or OpenAI API). Implement the logic to interpret natural language tasks and map them to tool executions.

## API Specification
*   **Endpoint**: `POST /v1/workflow`
*   **Input**: JSON containing `task_description` (str).
*   **Output**: JSON containing `status`, `steps` (trace), and `final_result`.
