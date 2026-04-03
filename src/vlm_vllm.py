from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional, Tuple

from PIL import Image
from vllm import LLM, SamplingParams

MODEL_PATH = os.environ.get("QWEN_VL_MODEL", "Qwen/Qwen3-VL-4B-Instruct")
MODEL_REVISION = os.environ.get("QWEN_VL_REVISION", "ebb281ec70b05090aa6165b016eac8ec08e71b17")

# Match the current Torch backend's deterministic-ish settings as closely as possible.
_SAMPLING_PARAMS = SamplingParams(
    temperature=0.0,
    max_tokens=32,
    seed=42,
)

print("Loading vLLM VLM:", MODEL_PATH)

# Match the Torch backend's image pixel bounds to reduce preprocessing drift.
_LLM = LLM(
    model=MODEL_PATH,
    revision=MODEL_REVISION,
    trust_remote_code=True,
    max_model_len=4096,
    dtype="bfloat16",
    seed=42,
    mm_processor_kwargs={
        "min_pixels": 224 * 224,
        "max_pixels": 512 * 512,
    },
)

print("vLLM backend ready.")


def _build_messages(
    screenshot_path: Optional[str],
    system_prompt: str,
) -> list[dict[str, Any]]:
    """
    Build chat-style messages for vLLM.

    - DOM mode: text only
    - Vision / SoM: image + text

    We use image_pil for in-process offline inference.
    """
    if screenshot_path is not None:
        image = Image.open(screenshot_path).convert("RGB")
        return [
            {
                "role": "user",
                "content": [
                    {"type": "image_pil", "image_pil": image},
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


def vlm_choose_action_with_logprobs(
    screenshot_path: Optional[str],
    system_prompt: str,
) -> Tuple[str, Dict[str, Any]]:
    """
    Mirror the public contract used by the existing backends:
        input:  screenshot_path | None, prompt
        output: generated_text, metadata_dict
    """
    t0 = time.perf_counter()

    messages = _build_messages(screenshot_path, system_prompt)
    outputs = _LLM.chat(messages, _SAMPLING_PARAMS)

    text = outputs[0].outputs[0].text.strip()
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    mi: Dict[str, Any] = {
        "backend": "vllm",
        "model_name": MODEL_PATH,
        "model_revision": MODEL_REVISION,
        "input_tokens": len(outputs[0].prompt_token_ids),
        "generated_tokens": len(outputs[0].outputs[0].token_ids),
        "latency_ms": latency_ms,
        "image_provided": screenshot_path is not None,
        "generation_config": {
            "max_new_tokens": _SAMPLING_PARAMS.max_tokens,
            "temperature": _SAMPLING_PARAMS.temperature,
            "seed": _SAMPLING_PARAMS.seed,
        },
    }

    return text, mi