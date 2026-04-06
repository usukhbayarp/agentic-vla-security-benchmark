from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple


VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://vllm:8000/v1").rstrip("/")
VLLM_API_KEY = os.environ.get("VLLM_API_KEY", "token-abc123")
VLLM_MODEL = os.environ.get(
    "VLLM_MODEL",
    os.environ.get("QWEN_VL_MODEL", "Qwen/Qwen3-VL-4B-Instruct"),
)
# Informational only: revision is enforced server-side and recorded here for trace parity.
VLLM_MODEL_REVISION = os.environ.get("QWEN_VL_REVISION") or None


def _image_to_data_url(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode("utf-8")
    mime, _ = mimetypes.guess_type(path)
    mime = mime or "image/png"
    return f"data:{mime};base64,{b64}"


def _build_messages(
    screenshot_path: Optional[str],
    system_prompt: str,
) -> list[dict[str, Any]]:
    if screenshot_path is not None:
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": _image_to_data_url(screenshot_path)},
                    },
                    {
                        "type": "text",
                        "text": system_prompt,
                    },
                ],
            }
        ]

    return [
        {
            "role": "user",
            "content": system_prompt,
        }
    ]


def _extract_text(choice_message: dict[str, Any]) -> str:
    content = choice_message.get("content", "")
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(p for p in parts if p).strip()

    return str(content).strip()


def vlm_choose_action_with_logprobs(
    screenshot_path: Optional[str],
    system_prompt: str,
) -> Tuple[str, Dict[str, Any]]:
    """
    HTTP client backend for a separate vLLM server.
    Contract:
      input:  screenshot_path | None, prompt
      output: generated_text, metadata_dict
    """
    t0 = time.perf_counter()

    payload: dict[str, Any] = {
        "model": VLLM_MODEL,
        "messages": _build_messages(screenshot_path, system_prompt),
        "temperature": 0.0,
        "max_tokens": 32,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    req = urllib.request.Request(
        url=f"{VLLM_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VLLM_API_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        choice = data["choices"][0]["message"]
        text = _extract_text(choice)

        usage = data.get("usage", {})
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")

        mi: Dict[str, Any] = {
            "backend": "vllm_http",
            "model_name": VLLM_MODEL,
            "model_revision": VLLM_MODEL_REVISION,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            # Torch-compatible aliases
            "input_tokens": prompt_tokens,
            "generated_tokens": completion_tokens,
            "latency_ms": latency_ms,
            "image_provided": screenshot_path is not None,
            "generation_config": {
                "temperature": 0.0,
                "max_tokens": 32,
                "enable_thinking": False,
            },
            "server_base_url": VLLM_BASE_URL,
            "http_status": 200,
            "error": None,
        }

        return text, mi

    except urllib.error.HTTPError as e:
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = "<unable to read body>"

        mi = {
            "backend": "vllm_http",
            "model_name": VLLM_MODEL,
            "model_revision": VLLM_MODEL_REVISION,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "input_tokens": None,
            "generated_tokens": None,
            "latency_ms": latency_ms,
            "image_provided": screenshot_path is not None,
            "generation_config": None,
            "server_base_url": VLLM_BASE_URL,
            "http_status": e.code,
            "error": f"HTTPError: {e.code} {e.reason}",
            "response_body": body,
        }
        return "", mi

    except urllib.error.URLError as e:
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        mi = {
            "backend": "vllm_http",
            "model_name": VLLM_MODEL,
            "model_revision": VLLM_MODEL_REVISION,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "input_tokens": None,
            "generated_tokens": None,
            "latency_ms": latency_ms,
            "image_provided": screenshot_path is not None,
            "generation_config": None,
            "server_base_url": VLLM_BASE_URL,
            "http_status": None,
            "error": f"URLError: {e}",
        }
        return "", mi

    except Exception as e:
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        mi = {
            "backend": "vllm_http",
            "model_name": VLLM_MODEL,
            "model_revision": VLLM_MODEL_REVISION,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "input_tokens": None,
            "generated_tokens": None,
            "latency_ms": latency_ms,
            "image_provided": screenshot_path is not None,
            "generation_config": None,
            "server_base_url": VLLM_BASE_URL,
            "http_status": None,
            "error": f"{type(e).__name__}: {e}",
        }
        return "", mi