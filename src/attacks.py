import shutil
import time


def apply_attack_if_needed(driver, project_root, attack_config: dict, step: int):
    assets_dir = project_root / "sandbox_ui" / "assets"

    target_top = assets_dir / "injection.png"
    target_confirm = assets_dir / "injection_confirm.png"

    clean_top = assets_dir / "clean.png"
    clean_confirm = assets_dir / "clean_confirm.png"

    variant = attack_config.get("variant")
    attack_type = attack_config.get("type")
    start_step = attack_config.get("start_step", 0)

    attack_active = (
        attack_type != "none"
        and variant is not None
        and step >= start_step
    )

    if attack_active:
        if variant.startswith("channel_conflict_confirm_overlay"):
            source_top = assets_dir / "safety_mimicry.png"
            source_confirm = assets_dir / f"{variant}.png"
        else:
            source_top = assets_dir / f"{variant}.png"
            source_confirm = clean_confirm
    else:
        source_top = clean_top
        source_confirm = clean_confirm

    if not source_top.exists():
        raise FileNotFoundError(f"Missing top asset: {source_top}")
    if not source_confirm.exists():
        raise FileNotFoundError(f"Missing confirm asset: {source_confirm}")

    shutil.copyfile(source_top, target_top)
    shutil.copyfile(source_confirm, target_confirm)

    driver.execute_script(
        "if (window.refreshInjectionImage) { window.refreshInjectionImage(); }"
    )
    time.sleep(0.05)

    return {
        "top": source_top.name,
        "confirm": source_confirm.name,
        "attack_active": attack_active,
    }