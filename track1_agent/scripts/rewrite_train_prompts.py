import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from app.prompt_template_rewriter import rewrite_prompt_template_for_prefix_caching


def main() -> None:
    input_path = REPO_ROOT / "train.json"
    output_path = REPO_ROOT / "rewritten_train_prompts.json"

    with input_path.open() as f:
        workflows = json.load(f)

    rewritten_prompts = []

    for workflow in workflows:
        for node in workflow["nodes"]:
            original_prompt_template = node["prompt_template"]
            rewritten_prompt_template = rewrite_prompt_template_for_prefix_caching(
                original_prompt_template
            )

            rewritten_prompts.append(
                {
                    "original_prompt_template": original_prompt_template,
                    "rewritten_prompt_template": rewritten_prompt_template,
                }
            )

    with output_path.open("w") as f:
        json.dump(rewritten_prompts, f, indent=2)

    print(f"Wrote rewritten prompt review file to {output_path}")


if __name__ == "__main__":
    main()
