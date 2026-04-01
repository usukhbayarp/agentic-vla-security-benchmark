from __future__ import annotations

import os
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
import time
from typing import Any, Dict, Optional, Tuple

import torch
from transformers import AutoModelForImageTextToText, AutoProcessor

MODEL_PATH = os.environ.get("QWEN_VL_MODEL", "Qwen/Qwen3-VL-4B-Instruct")
MODEL_REVISION = os.environ.get("QWEN_VL_REVISION", "ebb281ec70b05090aa6165b016eac8ec08e71b17")

print("Loading Torch VLM:", MODEL_PATH)
print("torch version:", torch.__version__)

# -----------------------------
# Device / dtype selection
# -----------------------------
if torch.cuda.is_available():
    _DTYPE = torch.bfloat16
    _DEVICE = "cuda"
elif torch.backends.mps.is_available():
    _DTYPE = torch.float32
    _DEVICE = "mps"
else:
    _DTYPE = torch.float32
    _DEVICE = "cpu"

print("Torch backend device:", _DEVICE)
print("Torch backend dtype:", _DTYPE)

_GPU_CAPABILITY = None
_TORCH_ARCH_LIST = None
if torch.cuda.is_available():
    _GPU_CAPABILITY = torch.cuda.get_device_capability(0)
    _TORCH_ARCH_LIST = torch.cuda.get_arch_list()
    print("GPU capability:", _GPU_CAPABILITY)
    print("Torch arch list:", _TORCH_ARCH_LIST)

# -----------------------------
# Generation config
# -----------------------------
GEN_CONFIG: Dict[str, Any] = {
    "max_new_tokens": 32,
    "do_sample": False,
    "temperature": None,
}


def _load_model_and_processor():
    """
    Load processor and model once at module import time.

    We try flash_attention_2 on CUDA first, and fall back cleanly if unavailable.
    """
    processor = AutoProcessor.from_pretrained(
        MODEL_PATH,
        revision=MODEL_REVISION,
        trust_remote_code=True,
        min_pixels=224 * 224,
        max_pixels=512 * 512,
    )

    common_kwargs = dict(
        torch_dtype=_DTYPE,
        device_map="auto" if _DEVICE == "cuda" else None,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )

    model = None
    attn_impl = "eager"

    if _DEVICE == "cuda":
        try:
            model = AutoModelForImageTextToText.from_pretrained(
                MODEL_PATH,
                revision=MODEL_REVISION,
                attn_implementation="flash_attention_2",
                **common_kwargs,
            )
            attn_impl = "flash_attention_2"
            print("Loaded model with flash_attention_2")
        except Exception as e:
            print("flash_attention_2 unavailable, falling back:", e)

    if model is None:
        model = AutoModelForImageTextToText.from_pretrained(
            MODEL_PATH,
            revision=MODEL_REVISION,
            **common_kwargs,
        )
        print("Loaded model without flash_attention_2")

    if _DEVICE != "cuda":
        model = model.to(_DEVICE)

    model.eval()
    return model, processor, attn_impl


model, processor, ATTN_IMPLEMENTATION = _load_model_and_processor()


def _build_messages(
    screenshot_path: Optional[str],
    system_prompt: str,
) -> list[dict[str, Any]]:
    """
    Build a single-turn chat message for Qwen3-VL.

    - Vision / SoM mode: include image + text
    - DOM mode: include only text
    """
    if screenshot_path is not None:
        return [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": screenshot_path},
                    {"type": "text", "text": system_prompt},
                ],
            }
        ]

    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": system_prompt},
            ],
        }
    ]


def _prepare_inputs(
    screenshot_path: Optional[str],
    system_prompt: str,
):
    """
    Convert chat messages into model-ready tensors.
    """
    messages = _build_messages(screenshot_path, system_prompt)

    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    )

    if _DEVICE == "cuda":
        inputs = inputs.to(model.device)
    else:
        inputs = inputs.to(_DEVICE)

    return inputs


def _decode_generated_text(inputs, generated_ids) -> str:
    """
    Decode only newly generated tokens, excluding the input prompt.
    """
    input_ids = inputs["input_ids"]
    trimmed = []

    for in_ids, out_ids in zip(input_ids, generated_ids):
        trimmed.append(out_ids[len(in_ids):])

    text = processor.batch_decode(
        trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )

    if isinstance(text, list):
        return text[0].strip()

    return str(text).strip()


def vlm_choose_action(
    screenshot_path: Optional[str],
    system_prompt: str,
) -> str:
    """
    Return raw model output text only.
    """
    inputs = _prepare_inputs(screenshot_path, system_prompt)

    with torch.no_grad():
        generated_ids = model.generate(**inputs, **GEN_CONFIG)

    return _decode_generated_text(inputs, generated_ids)


def vlm_choose_action_with_logprobs(
    screenshot_path: Optional[str],
    system_prompt: str,
) -> Tuple[str, Dict[str, Any]]:
    """
    Benchmark-compatible wrapper.

    Returns:
        (raw_model_text, mi_dict)

    We don't compute true token logprobs yet. Instead, we return
    lightweight metadata useful for debugging and later MI work.
    """
    t0 = time.perf_counter()

    inputs = _prepare_inputs(screenshot_path, system_prompt)
    input_len = int(inputs["input_ids"].shape[-1])

    gen_kwargs = dict(
        **GEN_CONFIG,
        return_dict_in_generate=True,
        output_scores=False,
    )

    with torch.no_grad():
        out = model.generate(**inputs, **gen_kwargs)

    text = _decode_generated_text(inputs, out.sequences)
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    mi = {
        "backend": "torch",
        "model_name": MODEL_PATH,
        "model_revision": MODEL_REVISION,
        "device": str(model.device) if hasattr(model, "device") else _DEVICE,
        "dtype": str(_DTYPE),
        "attn_implementation": ATTN_IMPLEMENTATION,
        "input_tokens": input_len,
        "generated_tokens": int(out.sequences.shape[-1] - input_len),
        "latency_ms": latency_ms,
        "image_provided": screenshot_path is not None,
        "generation_config": dict(GEN_CONFIG),
        "gpu_capability": list(_GPU_CAPABILITY) if _GPU_CAPABILITY is not None else None,
        "torch_arch_list": list(_TORCH_ARCH_LIST) if _TORCH_ARCH_LIST is not None else None,
    }

    return text, mi