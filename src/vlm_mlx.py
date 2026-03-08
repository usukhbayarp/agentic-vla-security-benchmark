# src/vlm_mlx.py
import mlx_vlm
from mlx_vlm import generate, load

MODEL_PATH = "mlx-community/Qwen3-VL-4B-Instruct-4bit"

print("Loading MLX VLM:", MODEL_PATH)
print("mlx_vlm version:", getattr(mlx_vlm, "__version__", "unknown"))

# ------------------------------------------------------------
# Patch Transformers AutoProcessor to force use_fast=False.
# This avoids the video_processing_auto NoneType crash,
# while keeping mlx-vlm's own processor object (with detokenizer).
# ------------------------------------------------------------
try:
    from transformers import AutoProcessor

    _orig_from_pretrained = AutoProcessor.from_pretrained

    def _patched_from_pretrained(*args, **kwargs):
        # Force use_fast=False unless user explicitly sets it
        kwargs.setdefault("use_fast", False)
        # Qwen processors often need this
        kwargs.setdefault("trust_remote_code", True)
        return _orig_from_pretrained(*args, **kwargs)

    AutoProcessor.from_pretrained = _patched_from_pretrained
    print("Patched AutoProcessor.from_pretrained(use_fast=False)")
except Exception as e:
    print("Warning: failed to patch AutoProcessor:", e)

# load via mlx-vlm normally (it will call AutoProcessor internally)
model, processor = load(MODEL_PATH)

config = getattr(model, "config", None)


def _format_prompt(system_prompt: str) -> str:
    try:
        from mlx_vlm.prompt_utils import apply_chat_template
        return apply_chat_template(processor, config, system_prompt, num_images=1)
    except Exception:
        return system_prompt


def _extract_text(out) -> str:
    if isinstance(out, str):
        return out
    for attr in ("text", "output_text", "generated_text"):
        if hasattr(out, attr):
            return getattr(out, attr)
    if hasattr(out, "texts") and out.texts:
        return out.texts[0]
    return str(out)


def vlm_choose_action(screenshot_path: str | None, system_prompt: str) -> str:
    prompt = _format_prompt(system_prompt)

    # Vision mode (image provided)
    if screenshot_path is not None:
        print("[VISION MODE] Sending prompt with image to model.")
        out = generate(
            model,
            processor,
            prompt,
            image=screenshot_path,   # vision input
            max_tokens=30,
            temperature=0.0,
            verbose=False,
        )

    # DOM / text-only mode
    else:
        print("[DOM MODE] Sending text-only prompt to model.")
        out = generate(
            model,
            processor,
            prompt,
            max_tokens=30,
            temperature=0.0,
            verbose=False,
        )

    return _extract_text(out)


def vlm_choose_action_with_logprobs(screenshot_path: str | None, system_prompt: str):
    """
    Wrapper used by the agent loop.
    Currently returns empty MI dict (can extend later).
    """
    text = vlm_choose_action(screenshot_path, system_prompt)

    # placeholder for MI-lite instrumentation later
    mi = {}

    return text, mi