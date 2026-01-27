from app.schemas import WorkflowRequest, WorkflowResponse, ExecutionStep
from app.constants import MAX_STEPS, MODEL_NAME, MAX_MODEL_LENGTH
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm.sampling_params import SamplingParams, StructuredOutputsParams
from vllm.utils import random_uuid

class AgentEngine:
    def __init__(self):
        self.model_name = MODEL_NAME
        self.engine = None
        self.tokenizer = None
        self.is_ready = False

    async def initialize(self):
        if self.is_ready:
            return
            
        print(f"Initializing Agent Engine with model: {self.model_name}...")
        
        engine_args = AsyncEngineArgs(
            model=self.model_name,
            gpu_memory_utilization=0.9,
            max_model_len=MAX_MODEL_LENGTH,
            trust_remote_code=True,
        )
        
        self.engine = AsyncLLMEngine.from_engine_args(engine_args)
        self.tokenizer = await self.engine.get_tokenizer()
        
        self.is_ready = True
        print("Agent Engine initialized and ready.")

    async def _generate_text(self, prompt: str, temperature: float, max_tokens: int, allowed_choices: list[str] | None = None) -> str:
        structured_params = None
        
        if allowed_choices:
            # Enforce structured output if choices are provided
            structured_params = StructuredOutputsParams(choice=allowed_choices)

        sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            structured_outputs=structured_params
        )
        
        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

        results_generator = self.engine.generate(
            formatted_prompt,
            sampling_params,
            random_uuid(),
        )

        final_output = None
        async for request_output in results_generator:
            final_output = request_output

        if final_output is None:
            return ""
        return final_output.outputs[0].text

    async def run(self, request: WorkflowRequest) -> WorkflowResponse:
        if not self.is_ready:
            raise Exception("Engine is still initializing")

        node_map = {n.id: n for n in request.nodes}
        current_node_id = request.start_node_id
        context = request.inputs.copy()
        trace = []
        
        steps_count = 0
        
        loop_counters = {}

        # Resolve global defaults
        default_temp = request.temperature
        default_max_tokens = request.max_tokens

        while current_node_id and steps_count < MAX_STEPS:
            node = node_map.get(current_node_id)
            if not node:
                break
            
            steps_count += 1
            
            current_temp = node.temperature if node.temperature is not None else default_temp
            current_max_tokens = node.max_tokens if node.max_tokens is not None else default_max_tokens

            # 1. Handle ECHO nodes (direct output, no LLM)
            if node.type == "echo":
                try:
                    output = node.prompt_template.format(**context)
                except Exception as e:
                    output = f"Echo Error: {e}"
                
                context["last_output"] = output
                trace.append(ExecutionStep(
                    node_id=node.id,
                    node_type=node.type,
                    input_context=str(context),
                    output=output
                ))
                current_node_id = node.next_node_id
                continue

            # 2. Prepare Prompt
            try:
                prompt = node.prompt_template.format(**context)
            except Exception as e:
                prompt = f"Error formatting prompt: {e}"

            # 3. Determine Constraints
            allowed_choices = None
            if node.type in ["condition", "loop"]:
                allowed_choices = ["yes", "no"]

            # 4. Execute LLM Node
            output = await self._generate_text(
                prompt, 
                temperature=current_temp, 
                max_tokens=current_max_tokens, 
                allowed_choices=allowed_choices
            )
            
            # Only update last_output for tasks to preserve context through logic checks
            if node.type == "task":
                context["last_output"] = output
            
            trace.append(ExecutionStep(
                node_id=node.id,
                node_type=node.type,
                input_context=str(context),
                output=output
            ))

            if allowed_choices:
                assert output in allowed_choices, f"Output '{output}' not in allowed choices {allowed_choices}"

            # 5. Flow Control
            if node.type == "task":
                current_node_id = node.next_node_id
            
            elif node.type == "condition":
                current_node_id = node.yes_node_id if output == "yes" else node.no_node_id
            
            elif node.type == "loop":
                max_rounds = node.max_loop_rounds if node.max_loop_rounds is not None else 3
                count = loop_counters.get(node.id, 0)
                
                # Logic: 'yes' means loop again, 'no' means continue to next section.
                # Increment counter only on 'yes'. Reset counter on exit.
                if output == "yes" and count < max_rounds:
                    loop_counters[node.id] = count + 1
                    current_node_id = node.yes_node_id
                else:
                    loop_counters.pop(node.id, None)
                    current_node_id = node.no_node_id

            else:
                raise Exception(f"Unknown node type: {node.type}")

        return WorkflowResponse(
            workflow_id=request.workflow_id,
            status="completed" if current_node_id is None else "running",
            trace=trace,
            final_output=context["last_output"]
        )