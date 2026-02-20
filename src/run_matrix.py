import shutil
import subprocess
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[0]
    ui_assets = root / "sandbox_ui" / "assets"
    variants_dir = root / "attack_variants"

    assert ui_assets.exists()
    assert variants_dir.exists(), "Create attack_variants/ with injection_*.png files"

    target = ui_assets / "injection.png"

    # baseline first (clean)
    clean = variants_dir / "clean.png"
    if clean.exists():
        shutil.copyfile(clean, target)
        subprocess.run(["python", "agent_sandbox.py"], check=False)

    # attack variants
    for p in sorted(variants_dir.glob("injection_*.png")):
        shutil.copyfile(p, target)
        subprocess.run(["python", "agent_sandbox.py"], check=False)

if __name__ == "__main__":
    main()