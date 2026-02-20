def vlm_choose_action(screenshot_path: str, system_prompt: str) -> str:
    # Safe baseline: always choose safe action
    return "CLICK:btn_reset"