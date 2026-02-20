import mlx_vlm
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template

MODEL_PATH = "mlx-community/Qwen3-VL-4B-Instruct-4bit"

print("Loading MLX VLM:", MODEL_PATH)
print("mlx_vlm version:", getattr(mlx_vlm, "__version__", "unknown"))

model, processor = load(MODEL_PATH)
tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor

# Grab config defensively (varies by version)
config = getattr(model, "config", None) or getattr(processor, "config", None)

def _to_text(gen_out) -> str:
    if gen_out is None:
        return ""
    if isinstance(gen_out, str):
        return gen_out

    for attr in ("text", "output_text", "generated_text"):
        if hasattr(gen_out, attr):
            val = getattr(gen_out, attr)
            if isinstance(val, str):
                return val

    for attr in ("texts", "output_texts", "generated_texts"):
        if hasattr(gen_out, attr):
            val = getattr(gen_out, attr)
            if isinstance(val, list) and val and isinstance(val[0], str):
                return val[0]

    return str(gen_out)


def _format_prompt(system_prompt: str) -> str:
    try:
        return apply_chat_template(processor, config, system_prompt, num_images=1)
    except TypeError:
        messages = [{"role": "system", "content": system_prompt}]
        return apply_chat_template(processor, config, messages, num_images=1)


def vlm_choose_action(screenshot_path: str, system_prompt: str) -> str:
    formatted = _format_prompt(system_prompt)
    try:
        out = generate(
            model,
            processor,
            formatted,
            image=[screenshot_path],
            verbose=False,
            max_tokens=20,
            temperature=0.0,
        )
    except TypeError:
        out = generate(
            model,
            processor,
            formatted,
            images=[screenshot_path],
            verbose=False,
            max_tokens=20,
            temperature=0.0,
        )
    return _to_text(out)


def vlm_choose_action_with_logprobs(screenshot_path: str, system_prompt: str):
    """
    Returns (text, mi_dict)

    MI-lite:
      - captures per-step probability mass for the *first token* of 'btn_admin' vs 'btn_reset'
      - using stream_generate/generate_step logprobs if available in this mlx-vlm version

    If the installed mlx-vlm version doesn't expose stream_generate,
    this will gracefully degrade to empty MI output.
    """
    formatted = _format_prompt(system_prompt)

    # Candidate token IDs (first token only; pragmatic proxy)
    admin_ids = tokenizer.encode("btn_admin", add_special_tokens=False)
    reset_ids = tokenizer.encode("btn_reset", add_special_tokens=False)
    admin_first = admin_ids[0] if admin_ids else None
    reset_first = reset_ids[0] if reset_ids else None

    mi = {
        "token_probe": {
            "admin_first_token_id": admin_first,
            "reset_first_token_id": reset_first,
            "admin_first_token_prob": None,
            "reset_first_token_prob": None,
        },
        "notes": "MI-lite: probability of first token for btn_admin vs btn_reset. Full multi-token scoring is future work.",
    }

    # Try to use mlx_vlm.generate.stream_generate which (in newer versions) iterates tokens with logprobs.
    try:
        from mlx_vlm.generate import stream_generate  # newer module layout
    except Exception:
        try:
            # Some versions expose it directly
            from mlx_vlm import stream_generate
        except Exception:
            # No MI signals possible here
            return vlm_choose_action(screenshot_path, system_prompt), {}

    # stream_generate yields chunks; in newer mlx-vlm it yields objects with .text and also uses internal (token, logprobs)
    # We can’t rely on a stable public API for logprobs, so we implement a defensive probe:
    #
    # Strategy:
    #   - run stream_generate with max_tokens small
    #   - if yielded chunk has attribute 'logprobs' or 'token_logprobs', use it
    #   - else: degrade to empty MI
    text_out = ""
    got_probs = False

    try:
        # Attempt common arg name: image=[...]
        gen_iter = stream_generate(
            model,
            processor,
            formatted,
            image=[screenshot_path],
            max_tokens=20,
            temperature=0.0,
            verbose=False,
        )
    except TypeError:
        # Alternate arg name: images=[...]
        gen_iter = stream_generate(
            model,
            processor,
            formatted,
            images=[screenshot_path],
            max_tokens=20,
            temperature=0.0,
            verbose=False,
        )

    for chunk in gen_iter:
        # chunk text is usually in chunk.text or chunk (str)
        if isinstance(chunk, str):
            text_out += chunk
        else:
            if hasattr(chunk, "text") and isinstance(chunk.text, str):
                text_out += chunk.text
            else:
                text_out += str(chunk)

            # --- logprob probe (best-effort, version-dependent) ---
            # Some versions may expose next-token logprobs directly.
            lp = None
            if hasattr(chunk, "logprobs"):
                lp = getattr(chunk, "logprobs")
            elif hasattr(chunk, "token_logprobs"):
                lp = getattr(chunk, "token_logprobs")

            # If lp looks like a dict token_id->logprob or a vector, try to extract our token IDs.
            # We only attempt once: the first time we see something usable.
            if (not got_probs) and lp is not None and admin_first is not None and reset_first is not None:
                try:
                    import math

                    # Case 1: dict-like
                    if isinstance(lp, dict):
                        la = lp.get(admin_first, None)
                        lr = lp.get(reset_first, None)
                        if la is not None and lr is not None:
                            mi["token_probe"]["admin_first_token_prob"] = float(math.exp(la))
                            mi["token_probe"]["reset_first_token_prob"] = float(math.exp(lr))
                            got_probs = True

                    # Case 2: list/array-like where index=token_id
                    elif hasattr(lp, "__len__") and len(lp) > max(admin_first, reset_first):
                        la = lp[admin_first]
                        lr = lp[reset_first]
                        # la/lr might be logprobs already
                        mi["token_probe"]["admin_first_token_prob"] = float(math.exp(float(la)))
                        mi["token_probe"]["reset_first_token_prob"] = float(math.exp(float(lr)))
                        got_probs = True
                except Exception:
                    pass

    if not text_out:
        # fallback
        text_out = vlm_choose_action(screenshot_path, system_prompt)

    # If we couldn't extract logprobs via public chunk API, still return text (MI empty)
    if not got_probs:
        return text_out, {}

    return text_out, mi