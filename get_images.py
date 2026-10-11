"""Run:  python get_images.py          -> only fills in missing photos
        python get_images.py --force  -> re-downloads ALL photos (overwrites existing)
No API key needed (uses Openverse)."""
import json, os, re, sys, time, urllib.parse, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import menu, COUNTERS, slug

API = "https://api.openverse.org/v1/images/"
HEADERS = {"User-Agent": "CafeFlowCollegeProject/1.0 (student project)"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "img")
FORCE = "--force" in sys.argv

COUNTER_QUERIES = {
    "kf": ["south indian breakfast", "idli", "dosa"],
    "brew": ["masala chai", "tea", "samosa"],
    "roll": ["kathi roll", "burger", "french fries"],
}
# Better search words for dishes that match poorly by name
ALIASES = {
    "maggi": ["maggi noodles", "instant noodles"],
    "veg puff": ["veg puff pastry", "puff pastry", "samosa"],
    "cheese balls": ["cheese balls snack", "fried cheese balls"],
    "zinger burger": ["chicken burger", "fried chicken burger"],
    "veg burger": ["veggie burger", "burger"],
    "chicken mandi": ["mandi rice chicken", "arabian rice chicken"],
    "ghee pongal": ["pongal", "ven pongal"],
    "bread omelette": ["bread omelette", "omelette sandwich", "omelette"],
    "peri peri fries": ["peri peri fries", "french fries"],
    "cheese fries": ["cheese fries", "french fries"],
    "grilled cheese sandwich": ["grilled cheese sandwich", "toasted sandwich"],
}

def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print("   rate limited, waiting 20s..."); time.sleep(20)
            else:
                raise
    raise RuntimeError("too many rate-limit retries")

def search(query):
    q = urllib.parse.urlencode({"q": query, "page_size": 10})
    data = json.loads(get(API + "?" + q))
    return [r.get("thumbnail") or r.get("url") for r in data.get("results", []) if r.get("thumbnail") or r.get("url")]

def candidate_queries(name):
    clean = re.sub(r"\(.*?\)", "", name).strip().lower()
    qs = ALIASES.get(clean, []) + [clean, clean + " food"]
    first = clean.split()[0]
    if first != clean: qs.append(first)
    seen = []
    for q in qs:
        if q not in seen: seen.append(q)
    return seen

def fetch(name, queries):
    path = os.path.join(OUT, slug(name) + ".jpg")
    if os.path.exists(path) and os.path.getsize(path) > 5000 and not FORCE:
        print("skip   ", name); return
    for q in queries:
        try:
            for url in search(q):
                try:
                    img = get(url)
                    if len(img) > 5000:
                        with open(path, "wb") as f: f.write(img)
                        print("saved  ", name, "  (searched:", q + ")"); time.sleep(2); return
                except Exception:
                    continue   # try the next image
        except Exception as e:
            print("   search error for", q, "-", e)
        time.sleep(2)
    print("no match", name)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for key, qs in COUNTER_QUERIES.items():
        fetch("counter-" + key, qs)
    for item in menu.traverse():
        fetch(item["name"], candidate_queries(item["name"]))
    print("Done. Run again to retry any 'no match' items.")