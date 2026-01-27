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

## Local Development & Testing

### 1. Setup
If you are developing locally on a non-AMD64 machine (e.g., Apple Silicon M1/M2/M3), you **must** comment out the `platform: linux/amd64` line in `docker-compose.yaml` to
 avoid architecture errors.

```yaml
services:
  agent-engine:
    # ...
    # platform: linux/amd64  <-- Comment out for local ARM64 testing
```

### 2. Build and Run
We recommend using Docker Compose for local testing.

```bash
# Build the image
docker compose build

# Run the container
docker compose up
```

Alternatively, you can build manually:
```bash
docker build -t agent-engine .
docker run -p 8000:8000 agent-engine
```

### 3. Check Status
*   Liveness: `GET http://localhost:8000/health`
*   Readiness: `GET http://localhost:8000/ready`

## Your Task
Modify `app/agent_engine.py` to replace the `MockLLM` with your actual LLM integration (e.g., using vLLM, HuggingFace, or OpenAI API). Implement the logic to interpret natural language tasks and map them to tool executions.

## API Specification
*   **Endpoint**: `POST /v1/workflow`
*   **Input**: JSON containing `task_description` (str).
*   **Output**: JSON containing `status`, `steps` (trace), and `final_result`.

## Deployment on Vast.ai

To test your engine on Vast.ai (which uses Linux AMD64 GPUs), you need to push your Docker image to a container registry (GHCR) and create a Template.

### 1. Push Docker Image to GHCR (Private)

1.  **Login to GHCR**
    Create a GitHub Personal Access Token (PAT) with `write:packages` and `read:packages` permissions.
    ```bash
    export CR_PAT=YOUR_TOKEN
    echo $CR_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
    ```

2.  **Build & Push**
    Build the image specifically for `linux/amd64`.
    
    ```bash
    # Replace YOUR_GITHUB_USERNAME with your actual username
    docker build -t ghcr.io/YOUR_GITHUB_USERNAME/track1-agent:latest . --platform linux/amd64
    
    docker push ghcr.io/YOUR_GITHUB_USERNAME/track1-agent:latest
    ```

### 2. Create a Private Template on Vast.ai

1.  Log in to [Vast.ai](https://vast.ai/).
2.  Go to **Console** -> **Templates** -> **Create New Template**.
3.  **Image Path:** `ghcr.io/YOUR_GITHUB_USERNAME/track1-agent:latest`
4.  **Login Mode:** `Private Repository`
    *   **Username:** Your GitHub username.
    *   **Password:** Your PAT.
5.  **Docker Options:** Add `-p 8000:8000` to expose the port. Select "Run in background".
6.  **Launch Mode:** `ssh`.

### 3. Launch & Test
Rent an NVIDIA RTX 5080 using your template. Once running, you can tunnel the port to run benchmarks locally:
```bash
ssh -p <HOST_PORT> -L 8000:localhost:8000 root@<HOST_IP>
```
Then run the benchmark script in a separate terminal targeting `http://localhost:8000`.

## Submission Instructions

You must submit the following items to Canvas:
1.  **Full Image Name with Digest**: (e.g., `ghcr.io/username/track1-agent@sha256:abcdef...`)
2.  **Read-Only PAT**: A GitHub Personal Access Token with **only** `read:packages` permission.
3.  **Archived Code**: A `.zip` file of your project code.

### 1. Get Image Digest & Check Architecture
Ensure your image is built for `linux/amd64` and get its digest.

```bash
# Pull the image (if not local)
docker pull ghcr.io/YOUR_USERNAME/track1-agent:latest

# Inspect to get Digest and Architecture
docker inspect ghcr.io/YOUR_USERNAME/track1-agent:latest --format 'Digest: {{.RepoDigests}} | Arch: {{.Architecture}}'
```
*   **Verify**: Architecture must be `amd64`.
*   **Copy**: The full string starting with `sha256:` from the Digest output.

### 2. Generate Read-Only PAT
To allow TAs to grade your submission without full access to your account:
1.  Go to GitHub Settings -> Developer Settings -> Personal access tokens (Classic).
2.  Generate new token (classic).
3.  **Scopes**: Select **ONLY** `read:packages`.
4.  **Expiration**: Set to at least 2 weeks after the submission deadline.
5.  Generate and copy the token.

### 3. Test Your Submission Credentials
**Crucial:** Verify that the PAT works for pulling the image.

```bash
# 1. Logout of your current session
docker logout ghcr.io

# 2. Login with the READ-ONLY PAT
echo "YOUR_READ_ONLY_PAT" | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# 3. Try to pull your image
docker pull ghcr.io/YOUR_USERNAME/track1-agent@sha256:<YOUR_DIGEST>
```
If the pull succeeds, your credentials are correct.

### 4. Archive Code
Zip your `track1_agent` folder (excluding `.venv`, `__pycache__`, and large model files).
```bash
zip -r track1_agent_submission.zip . -x "*.venv*" -x "*__pycache__*"
```

**Submit the Image URI (with digest), the Read-Only PAT, and the Zip file to Canvas.**
