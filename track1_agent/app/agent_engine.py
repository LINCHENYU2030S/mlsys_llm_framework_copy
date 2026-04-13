from collections import OrderedDict

from app.schemas import WorkflowRequest, WorkflowResponse, ExecutionStep
from app.constants import MAX_STEPS, MODEL_NAME, MAX_MODEL_LENGTH
from app.prompt_template_rewriter import rewrite_prompt_template_for_prefix_caching
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
        self.memoized_generations = OrderedDict()
        self.max_memoized_generations = 2048

    async def initialize(self):
        if self.is_ready:
            return

        print(f"Initializing Agent Engine with model: {self.model_name}...")

        engine_args = AsyncEngineArgs(
            model=self.model_name,
            gpu_memory_utilization=0.9,
            max_model_len=MAX_MODEL_LENGTH,
            kv_cache_dtype="fp8",
            calculate_kv_scales=True,
            enable_prefix_caching=True,
            disable_log_stats=False,
            trust_remote_code=True,
            max_num_seqs=10,
        )

        self.engine = AsyncLLMEngine.from_engine_args(engine_args)
        self.tokenizer = await self.engine.get_tokenizer()

        self.is_ready = True
        print("Agent Engine initialized and ready.")

    def _should_memoize(self, temperature: float) -> bool:
        return temperature == 0.0

    def _memoization_key(
        self,
        formatted_prompt: str,
        temperature: float,
        max_tokens: int,
        allowed_choices: list[str] | None,
    ) -> tuple[str, float, int, tuple[str, ...] | None]:
        choices_key = tuple(allowed_choices) if allowed_choices else None
        return (formatted_prompt, temperature, max_tokens, choices_key)

    def _get_memoized_result(
        self,
        key: tuple[str, float, int, tuple[str, ...] | None],
    ) -> tuple[str, list[float]] | None:
        cached = self.memoized_generations.get(key)
        if cached is None:
            return None

        self.memoized_generations.move_to_end(key)
        text, logprobs = cached
        return text, list(logprobs)

    def _store_memoized_result(
        self,
        key: tuple[str, float, int, tuple[str, ...] | None],
        text: str,
        logprobs: list[float],
    ) -> None:
        self.memoized_generations[key] = (text, tuple(logprobs))
        self.memoized_generations.move_to_end(key)

        if len(self.memoized_generations) > self.max_memoized_generations:
            self.memoized_generations.popitem(last=False)

    async def _generate_text(self, prompt: str, temperature: float, max_tokens: int, allowed_choices: list[str] | None = None) -> tuple[str, list[float]]:
        structured_params = None

        if allowed_choices:
            # Enforce structured output if choices are provided
            structured_params = StructuredOutputsParams(choice=allowed_choices)

        sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            structured_outputs=structured_params,
            logprobs=1
        )

        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

        memoization_key = None
        if self._should_memoize(temperature):
            memoization_key = self._memoization_key(
                formatted_prompt,
                temperature,
                max_tokens,
                allowed_choices,
            )
            cached_result = self._get_memoized_result(memoization_key)
            if cached_result is not None:
                return cached_result

        results_generator = self.engine.generate(
            formatted_prompt,
            sampling_params,
            random_uuid(),
        )

        final_output = None
        async for request_output in results_generator:
            final_output = request_output

        if final_output is None:
            return "", []

        text = final_output.outputs[0].text
        output_data = final_output.outputs[0]

        if output_data.logprobs is None:
            raise RuntimeError("logprobs are missing from vLLM output")

        if not output_data.token_ids:
            raise RuntimeError("token_ids is empty, cannot provide logprobs")

        logprobs: list[float] = []
        for i, token_id in enumerate(output_data.token_ids):
            if i < len(output_data.logprobs):
                step_logprobs = output_data.logprobs[i]
                if token_id in step_logprobs:
                    logprobs.append(step_logprobs[token_id].logprob)
                else:
                    raise RuntimeError(f"Token ID {token_id} not found in logprobs at step {i}")

        if memoization_key is not None:
            self._store_memoized_result(memoization_key, text, logprobs)

        return text, logprobs

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
                    output=output,
                    logprobs=None
                ))
                current_node_id = node.next_node_id
                continue

            # 2. Prepare Prompt
            try:
                optimized_prompt_template = rewrite_prompt_template_for_prefix_caching(
                    node.prompt_template
                )
                prompt = optimized_prompt_template.format(**context)
            except Exception as e:
                prompt = f"Error formatting prompt: {e}"

            # 3. Determine Constraints
            allowed_choices = None
            if node.type in ["condition", "loop"]:
                allowed_choices = ["yes", "no"]

            # 4. Execute LLM Node
            output, logprobs = await self._generate_text(
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
                output=output,
                logprobs=logprobs
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
            final_output=context["last_output"],
        )
