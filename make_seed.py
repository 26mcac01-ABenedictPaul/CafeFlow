"""Make data.seed.json: a clean copy of data.json that is safe to publish.

Keeps the menu (and offers). Empties everything else (users, orders,
bookings, pre-orders, reviews, parties, carts ...). Your real data.json is
NOT changed.

Run from the CafeFlow folder:   python make_seed.py
"""
import json

KEEP = {"menu", "offers"}          # non-personal data worth shipping

with open("data.json", encoding="utf-8") as f:
    data = json.load(f)

seed = {}
print(f"{'key':<16}{'type':<8}{'count':>6}   action")
print("-" * 44)
for key, val in data.items():
    n = len(val) if hasattr(val, "__len__") and not isinstance(val, str) else "-"
    if key in KEEP:
        seed[key] = val
        action = "KEPT"
    elif isinstance(val, list):
        seed[key] = []
        action = "emptied"
    elif isinstance(val, dict):
        seed[key] = {}
        action = "emptied"
    else:
        seed[key] = val            # numbers/strings: kept, REVIEW below
        action = "kept as-is (review)"
    print(f"{key:<16}{type(val).__name__:<8}{str(n):>6}   {action}")

with open("data.seed.json", "w", encoding="utf-8") as f:
    json.dump(seed, f, indent=2, ensure_ascii=False)

print("\nWrote data.seed.json")
print("Open it once and check no email, name or password appears:")
print('  findstr /i "@ password" data.seed.json')
