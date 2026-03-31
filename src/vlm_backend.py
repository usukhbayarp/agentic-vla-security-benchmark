from typing import Any, Callable, Dict, Optional, Tuple

BackendFn = Callable[[Optional[str], str], Tuple[str, Dict[str, Any]]]


def load_backend(
    name: str,
    script: Optional[list[str]] = None,
) -> tuple[BackendFn, Dict[str, str]]:
    """
    Load a model backend and return:
      1. callable inference function
      2. model metadata for trace logging
    """

    if name == "stub":
        from vlm_stub import set_stub_script, vlm_choose_action_with_logprobs

        if script is not None:
            set_stub_script(script)

        meta = {
            "provider": "stub",
            "name": "stub-policy",
        }
        return vlm_choose_action_with_logprobs, meta

    if name == "mlx":
        from vlm_mlx import vlm_choose_action_with_logprobs

        meta = {
            "provider": "mlx_vlm",
            "name": "Qwen3-VL-4B-Instruct-4bit",
        }
        return vlm_choose_action_with_logprobs, meta

    if name == "torch":
        from vlm_torch import (
            vlm_choose_action_with_logprobs,
            MODEL_PATH,
            MODEL_REVISION,
        )

        meta = {
            "provider": "torch_vlm",
            "name": MODEL_PATH,
            "revision": MODEL_REVISION,
        }
        return vlm_choose_action_with_logprobs, meta

    raise ValueError(f"Unknown backend: {name}")