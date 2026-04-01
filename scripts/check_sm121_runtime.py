import torch

print("torch version:", torch.__version__)
print("cuda available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("device name:", torch.cuda.get_device_name(0))
    print("device capability:", torch.cuda.get_device_capability(0))
    print("torch arch list:", torch.cuda.get_arch_list())

tests = [
    ("int64_prod", lambda: torch.tensor([[1, 2, 3]], device="cuda", dtype=torch.int64).prod(-1)),
    ("int32_prod", lambda: torch.tensor([[1, 2, 3]], device="cuda", dtype=torch.int32).prod(-1)),
    ("float32_prod", lambda: torch.tensor([[1.0, 2.0, 3.0]], device="cuda", dtype=torch.float32).prod(-1)),
    ("bfloat16_prod", lambda: torch.tensor([[1.0, 2.0, 3.0]], device="cuda", dtype=torch.bfloat16).prod(-1)),
    ("cumsum", lambda: torch.tensor([[1, 2, 3]], device="cuda", dtype=torch.int64).cumsum(-1)),
    ("amax", lambda: torch.tensor([[1, 2, 3]], device="cuda", dtype=torch.int64).amax(-1)),
]

for name, fn in tests:
    try:
        out = fn()
        print(f"{name}: OK -> {out} | device={out.device}")
    except Exception as e:
        print(f"{name}: FAIL -> {repr(e)}")