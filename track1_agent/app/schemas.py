from pydantic import BaseModel
from typing import Any, Literal

class WorkflowNode(BaseModel):
    id: str
    type: Literal["task", "condition", "loop", "echo"]
    # Prompt
    prompt_template: str
    
    next_node_id: str | None = None # Default next step
    yes_node_id: str | None = None # Branching
    no_node_id: str | None = None # Branching
    max_loop_rounds: int = 3
    
    # Generation Config
    temperature: float | None = None
    max_tokens: int | None = None

class WorkflowRequest(BaseModel):
    workflow_id: str
    nodes: list[WorkflowNode]
    start_node_id: str
    inputs: dict[str, Any] # e.g. {"topic": "AI"}
    
    # Global Generation Config
    temperature: float = 0.7
    max_tokens: int = 512

class ExecutionStep(BaseModel):
    node_id: str
    node_type: str
    input_context: str
    output: str
    logprobs: list[float]

class WorkflowResponse(BaseModel):
    workflow_id: str
    status: Literal["completed", "failed", "running"]
    trace: list[ExecutionStep]
    final_output: str
    final_logprobs: list[float]
