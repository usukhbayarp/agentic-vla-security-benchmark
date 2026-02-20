import mlx_vlm
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template

MODEL_PATH = "mlx-community/Qwen3-VL-4B-Instruct-4bit"

print("Loading MLX VLM:", MODEL_PATH)
print("mlx_vlm version:", getattr(mlx_vlm, "__version__", "unknown"))

model, processor = load(MODEL_PATH)

# Grab config defensively (varies by version)
config = getattr(model, "config", None) or getattr(processor, "config", None)

def vlm_choose_action(screenshot_path: str, system_prompt: str) -> str:
    """
    Screenshot + prompt -> model output string (expected: CLICK:<id>)
    """
    # Build prompt (signature may vary)
    try:
        formatted = apply_chat_template(processor, config, system_prompt, num_images=1)
    except TypeError:
        # Some versions accept messages instead of raw string
        messages = [{"role": "system", "content": system_prompt}]
        formatted = apply_chat_template(processor, config, messages, num_images=1)

    # Generate (arg name may vary)
    try:
        out = generate(
            model,
            processor,
            formatted,
            image=[screenshot_path],
            verbose=False,
            max_tokens=20,
        )
    except TypeError:
        out = generate(
            model,
            processor,
            formatted,
            images=[screenshot_path],
            verbose=False,
            max_tokens=20,
        )

    return out