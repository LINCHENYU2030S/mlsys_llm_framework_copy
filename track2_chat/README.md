# Track 2: Customer Chat

## Overview
This starter kit provides a scaffold for building a high-performance chat engine compatible with the OpenAI API format. Your goal is to integrate a serving engine (like vLLM) to handle chat completions efficiently.

## Project Structure
```text
.
├── app/
│   ├── main.py          # FastAPI entry point.
│   ├── schemas.py       # Pydantic models (OpenAI compatible).
│   └── chat_engine.py   # MAIN LOGIC GOES HERE.
├── Dockerfile           # Environment definition.
├── pyproject.toml       # Python dependencies.
└── README.md
```

## How to Run

### Option 1: Docker Compose (Recommended)
This method automatically handles GPU reservations and mounts the Hugging Face cache.
```bash
docker compose up --build
```

### Option 2: Manual Docker Build
    ```bash
    docker build -t chat-engine track2_chat
    ```

2.  **Run the Container**
    ```bash
    docker run --gpus all -p 8000:8000 chat-engine
    ```

3.  **Check Status**
    *   Liveness: `GET http://localhost:8000/health`
    *   Readiness: `GET http://localhost:8000/ready`

## Your Task
Modify `app/chat_engine.py` to replace the mock generation logic with a real inference engine.

## API Specification
*   **Endpoint**: `POST /v1/chat/completions`
*   **Input**: Standard OpenAI Chat Completion JSON (messages, model, etc.).
*   **Output**: Standard OpenAI Chat Completion Response.
