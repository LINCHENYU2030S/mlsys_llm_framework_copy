#!/bin/bash
# Test script for Track 1: Agent Engine
BASE_URL=${1:-"http://localhost:8000"}

echo "--- Testing Track 1: Agent ---"
echo "Health check:"
curl -s "$BASE_URL/health" | uv run python -m json.tool
echo ""

echo "Waiting for engine to be ready..."
max_retries=30
count=0
while [ $count -lt $max_retries ]; do
  status_code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/ready")
  if [ "$status_code" -eq 200 ]; then
    echo "Engine is ready!"
    break
  fi
  echo "Engine not ready yet (HTTP $status_code)... retrying in 2s ($((count+1))/$max_retries)"
  sleep 2
  count=$((count+1))
done

if [ $count -eq $max_retries ]; then
  echo "Timeout waiting for engine to be ready."
  exit 1
fi

echo ""
echo "Running complex workflow (Task -> Loop -> Condition -> Echo):"

# Using a variable to avoid shell quote nesting issues
PAYLOAD=$(cat <<EOF
{
  "workflow_id": "complex_flow",
  "start_node_id": "init",
  "inputs": {"topic": "Space"},
  "max_tokens": 100,
  "nodes": [
    {
      "id": "init",
      "type": "task",
      "temperature": 0.9,
      "prompt_template": "Generate a comma-separated list of 3 keywords related to {topic}.",
      "next_node_id": "loop_check"
    },
    {
      "id": "loop_check",
      "type": "loop",
      "prompt_template": "Current list: {last_output}. Do I have less than 5 keywords? Answer yes or no.",
      "yes_node_id": "generate_more",
      "no_node_id": "finalize",
      "max_loop_rounds": 3
    },
    {
      "id": "generate_more",
      "type": "task",
      "prompt_template": "Current list: {last_output}. Add 1 more keyword related to {topic} to the list. Output the FULL updated comma-separated list only.",
      "next_node_id": "loop_check"
    },
    {
      "id": "finalize",
      "type": "condition",
      "prompt_template": "Is this a list of keywords? Answer yes or no.",
      "yes_node_id": "good_end",
      "no_node_id": "bad_end"
    },
    {
      "id": "good_end",
      "type": "echo",
      "prompt_template": "Workflow Complete: {last_output}",
      "next_node_id": null
    },
    {
      "id": "bad_end",
      "type": "echo",
      "prompt_template": "Something went wrong.",
      "next_node_id": null
    }
  ]
}
EOF
)

curl -s -X POST "$BASE_URL/v1/workflow" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | uv run python -m json.tool
echo ""
