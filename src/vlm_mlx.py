import mlx_vlm
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template

MODEL_PATH = "mlx-community/Qwen3-VL-4B-Instruct-4bit"

print("Loading MLX VLM:", MODEL_PATH)
print("mlx_vlm version:", getattr(mlx_vlm, "__version__", "unknown"))

model, processor = load(MODEL_PATH)

# Grab config defensively (varies by version)
config = getattr(model, "config", None) or getattr(processor, "config", None)

def _to_text(gen_out) -> str:
    """
    mlx-vlm generate() may return a string or a GenerationResult-like object.
    Normalize to plain text.
    """
    if gen_out is None:
        return ""
    if isinstance(gen_out, str):
        return gen_out

    # Common patterns across mlx-vlm versions
    for attr in ("text", "output_text", "generated_text"):
        if hasattr(gen_out, attr):
            val = getattr(gen_out, attr)
            if isinstance(val, str):
                return val

    # Sometimes it’s a list of strings
    for attr in ("texts", "output_texts", "generated_texts"):
        if hasattr(gen_out, attr):
            val = getattr(gen_out, attr)
            if isinstance(val, list) and val and isinstance(val[0], str):
                return val[0]

    # Last resort: string conversion (better than crashing)
    return str(gen_out)

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

    return _to_text(out)