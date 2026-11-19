"""Patch app.py: no secrets in the code, and data.json is built from data.seed.json.

Run from the CafeFlow folder:   python patch_app.py
A backup is saved as app.py.bak. Safe to run once; it refuses to run twice.
"""
import re, sys, shutil

SRC = "app.py"
raw = open(SRC, encoding="utf-8", newline="").read()
crlf = "\r\n" in raw
t = raw.replace("\r\n", "\n")

if "_need(" in t:
    sys.exit("app.py already patched. Nothing to do.")

def swap(text, old, new, label):
    if text.count(old) != 1:
        sys.exit(f"STOPPED: could not find '{label}' exactly once. app.py was NOT changed.")
    return text.replace(old, new)

# 1. secret key + helpers
t = swap(t, 'app.secret_key = "cafeflow-secret"', '''import secrets as _secrets
_CFG = {}                                                   # optional local file, never committed (see .gitignore)
if os.path.exists("local_config.json"):
    with open("local_config.json", encoding="utf-8") as _f: _CFG = json.load(_f)
def _secret(env, *path):                                    # environment variable first, then local_config.json
    v = os.environ.get(env)
    if v: return v
    cur = _CFG
    for p in path: cur = cur.get(p) if isinstance(cur, dict) else None
    return cur or None
def _need(env, label, *path):                               # a password that must exist; if none is set, use a temporary one and print it
    v = _secret(env, *path)
    if not v:
        v = _secrets.token_urlsafe(8); print(f"[CafeFlow] {label}: no password configured, temporary password for this run: {v}")
    return v
app.secret_key = _secret("SECRET_KEY", "secret_key") or _secrets.token_hex(32)''', "secret_key")

# 2. admin login
t = swap(t, 'ADMIN_NAME, ADMIN_PASS = "admin", "admin123"',
 'ADMIN_NAME = (_secret("ADMIN_NAME", "admin_name") or "admin").lower()\n'
 'ADMIN_PASS = _need("ADMIN_PASS", "admin", "admin_pass")\n'
 'ADMIN_HASH = generate_password_hash(ADMIN_PASS)', "ADMIN_NAME, ADMIN_PASS")
t = swap(t, "pw == ADMIN_PASS", "check_password_hash(ADMIN_HASH, pw)", "admin login check")

# 3. counter logins
t, n = re.subn(r'VENDOR_LOGINS = \{[^}]*\}\n', '''_VENDOR_BASE = {"campusfeast": (1, "kf"), "zamorin1": (1, "brew"), "slurrpp": (1, "roll"),
                "annaprada": (2, "kf"), "zamorin2": (2, "brew"), "delhibite": (2, "roll")}
VENDOR_LOGINS = {u: (f, k, _need(f"PW_{u.upper()}", f"counter '{u}'", "vendors", u)) for u, (f, k) in _VENDOR_BASE.items()}
''', t, count=1)
if n != 1: sys.exit("STOPPED: could not find VENDOR_LOGINS. app.py was NOT changed.")

# 4. build data.json from the clean seed on first run
t = swap(t, 'DB = "data.json"\n', '''DB = "data.json"
if not os.path.exists(DB) and os.path.exists("data.seed.json"):     # first run or fresh deploy: start from the clean seed
    import shutil as _sh; _sh.copy("data.seed.json", DB)
''', "DB = data.json")

# 5. keep dish ids unique when starting from the seed
t = swap(t, '    count.update(d["count"])\n', '''    count.update(d["count"])
    count["item"] = max([count.get("item", 0)] + [m["id"] for m in d["menu"]])   # ids stay unique even if the seed has no counters
''', "count.update")

if crlf: t = t.replace("\n", "\r\n")
shutil.copy(SRC, SRC + ".bak")
open(SRC, "w", encoding="utf-8", newline="").write(t)

# 6. keep private files out of git
try: gi = open(".gitignore", encoding="utf-8").read()
except FileNotFoundError: gi = ""
add = [x for x in ("data.json", "local_config.json", "__pycache__/", ".env") if x not in gi.split()]
if add: open(".gitignore", "a", encoding="utf-8").write(("\n" if gi and not gi.endswith("\n") else "") + "\n".join(add) + "\n")

print("app.py patched (backup: app.py.bak).")
print("Next: copy local_config.example.json to local_config.json and fill in NEW passwords.")
