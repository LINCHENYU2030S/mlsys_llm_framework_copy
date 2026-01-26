import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from app.schemas import WorkflowRequest, WorkflowResponse
from app.agent_engine import AgentEngine

engine = AgentEngine()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize engine in background
    asyncio.create_task(engine.initialize())
    yield
    # Shutdown
    pass

app = FastAPI(title="Track 1: Agent Engine", lifespan=lifespan)

@app.post("/v1/workflow", response_model=WorkflowResponse)
async def run_workflow(request: WorkflowRequest):
    if not engine.is_ready:
        raise HTTPException(status_code=503, detail="Engine is still initializing")
    try:
        response = await engine.run(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    if engine.is_ready:
        return {"status": "ready", "message": "Agent engine is initialized and ready."}
    else:
        raise HTTPException(status_code=503, detail="Engine is initializing")