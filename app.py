import os, re, io, csv, json, time, random, smtplib, threading, textwrap
from datetime import datetime, timedelta, date
from urllib.parse import quote
from email.message import EmailMessage
from collections import Counter
from flask import Flask, render_template, request, redirect, session, flash, abort, jsonify, Response, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from ds import LinkedList, Stack, Queue, BST, Graph, balanced, eval_postfix
from ds import linear_search, binary_search, insertion_sort, merge_sort
from mining import apriori
from chatbot import reply as bot_reply, staff_reply
from algos import make_change, budget_knapsack, seat_groups, balance_stations
try:
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas as pdfcanvas
except ImportError:
    pdfcanvas = None

app = Flask(__name__)
app.secret_key = "cafeflow-secret"
app.permanent_session_lifetime = timedelta(days=30)        # "Remember me" keeps a login for 30 days
ADMIN_NAME, ADMIN_PASS = "admin", "admin123"
DB = "data.json"
FLOORS = [1, 2]                         # two floors, each canteen has the same 3 counters
# ---- counter names per floor (the menu key stays kf / brew / roll underneath) ----
FLOOR_NAMES = {1: {"kf": "Campus Feast", "brew": "Cafe Zamorin", "roll": "Slurrpp"},
               2: {"kf": "Annaprada",    "brew": "Cafe Zamorin", "roll": "Delhi Bite"}}
# ---- one login per counter: username -> (floor, counter key, password). Change them here. ----
VENDOR_LOGINS = {"campusfeast": (1, "kf", "feast123"), "zamorin1": (1, "brew", "zamorin123"), "slurrpp": (1, "roll", "slurrpp123"),
                 "annaprada": (2, "kf", "anna123"),    "zamorin2": (2, "brew", "zamorin456"), "delhibite": (2, "roll", "delhi123")}
VENDOR_HASH = {u: generate_password_hash(p) for u, (f, k, p) in VENDOR_LOGINS.items()}
# ---- seat booking ----
DAY_START, DAY_END = 8 * 60, 20 * 60    # canteen hours in minutes
STEP = 30                               # booking start times every 30 minutes
DURATIONS = [30, 60, 90, 120]
# Seating units drawn on the floor plan (x, y, w, h are % of the plan picture)
UNITS = ([{"id": f"S{i+1}", "kind": "sofa", "seats": 4, "x": 3.5, "y": 16 + i * 13, "w": 12, "h": 10.5} for i in range(5)] +
         [{"id": f"S{i+6}", "kind": "sofa", "seats": 4, "x": 17 + i * 13.2, "y": 80, "w": 11.5, "h": 12} for i in range(4)] +
         [{"id": f"T{r*3+c+1}", "kind": "table", "seats": 6, "x": 27 + c * 20, "y": 22 + r * 20, "w": 13, "h": 11} for r in range(3) for c in range(3)])
UNIT_BY_ID = {u["id"]: u for u in UNITS}
PAY_LABELS = {"gpay": "Google Pay", "phonepe": "PhonePe", "paytm": "Paytm", "upi": "UPI QR scan", "cod": "Cash on Delivery"}

# ---- merged-build settings (edit these) ----
PURE_VEG_FLOORS = {1: True, 2: False}   # True = that floor is veg-only, False = veg + non-veg. Change it, restart, the menu is rebuilt (users and orders kept)
def pure(floor): return PURE_VEG_FLOORS.get(int(floor), False)
UPI_MERCHANT = {"vpa": "cafeflow@upi", "name": "CafeFlow Canteen"}   # SAMPLE: put your real UPI ID here and the QR on the cart page becomes real
GST_PERCENT = 5         # GST printed on the bill. It is already INCLUDED in the menu prices, so totals never change. Set 0 to hide the line.
BUSINESS = {"name": "CAFEFLOW CANTEEN", "line1": "Campus Canteen", "phone": ""}   # header of every bill; the floor and counter are added automatically

COUNTERS = {
 "kf":   {"no": 1, "name": "KF", "tag": "South Indian meals, pongal, rice and Indo-Chinese fast food", "emoji": "🥞", "c1": "#ff9a3c", "c2": "#e8472f", "sections": ["Breakfast", "Lunch", "Fast Food"]},
 "brew": {"no": 2, "name": "Brew", "tag": "Tea, coffee, snacks, desserts and fresh pastries", "emoji": "☕", "c1": "#27b58a", "c2": "#0d7a62", "sections": ["Tea and Coffee", "Snacks", "Desserts", "Pastries"]},
 "roll": {"no": 3, "name": "Roll", "tag": "Loaded rolls, burgers, fries and cheesy bites", "emoji": "🌯", "c1": "#f0658a", "c2": "#8a4fd6", "sections": ["Rolls", "Burgers and Fries"]},
}
def cname(floor, key): return FLOOR_NAMES.get(int(floor), FLOOR_NAMES[1]).get(key, key)
def counters_for(floor): return {k: {**c, "name": cname(floor, k)} for k, c in COUNTERS.items()}
MENU_VERSION = 6                        # bump this number after changing MENU: the saved menu is rebuilt, users and orders are kept
MENU = {  # (counter, section): [(name, price, emoji, veg)]
 ("kf", "Breakfast"): [("Idli (2 pcs)",30,"🍘",1),("Medu Vada",35,"🍩",1),("Masala Dosa",60,"🥞",1),("Plain Dosa",40,"🥞",1),("Ghee Pongal",50,"🍚",1),("Poori Masala",50,"🥘",1),("Upma",30,"🍲",1),
   ("Rava Dosa",55,"🥞",1),("Onion Uttapam",55,"🥞",1),("Podi Idli",40,"🍘",1),("Sambar Vada",40,"🍩",1),("Kesari Bath",30,"🍮",1),("Egg Dosa",60,"🍳",0)],
 ("kf", "Lunch"): [("Chicken Biryani",130,"🍛",0),("Veg Biryani",100,"🍚",1),("Chicken Mandi",160,"🍗",0),("Curd Rice",45,"🥣",1),("South Indian Meals",90,"🍛",1),
   ("Mutton Biryani",170,"🍛",0),("Egg Biryani",110,"🍛",0),("Lemon Rice",50,"🍋",1),("Sambar Rice",60,"🍲",1),("Chicken Curry Meals",130,"🍗",0),("Paneer Butter Masala",110,"🧈",1),("Veg Pulao",80,"🍚",1),("Chapati Kurma",70,"🫓",1)],
 ("kf", "Fast Food"): [("Veg Fried Rice",80,"🍚",1),("Chicken Fried Rice",100,"🍚",0),("Egg Fried Rice",90,"🍳",0),("Schezwan Fried Rice",95,"🌶️",1),("Veg Noodles",80,"🍜",1),("Chicken Noodles",100,"🍜",0),
   ("Gobi Manchurian",80,"🥦",1),("Chilli Chicken",110,"🌶️",0),("Chilli Paneer",100,"🧀",1),("Veg Manchow Soup",50,"🥣",1)],
 ("brew", "Tea and Coffee"): [("Tea",12,"🍵",1),("Masala Chai",15,"🍵",1),("Filter Coffee",20,"☕",1),("Cold Coffee",45,"🧋",1),("Lemon Tea",15,"🍋",1),
   ("Green Tea",20,"🍃",1),("Ginger Tea",15,"🫖",1),("Hot Chocolate",50,"🍫",1),("Cappuccino",50,"☕",1),("Iced Tea",35,"🧊",1),("Fresh Lime Soda",30,"🥤",1)],
 ("brew", "Snacks"): [("Veg Sandwich",40,"🥪",1),("Grilled Cheese Sandwich",55,"🧀",1),("Samosa",15,"🥟",1),("Veg Puff",20,"🥐",1),("Bread Omelette",35,"🍳",0),("Maggi",40,"🍜",1),
   ("Pav Bhaji",70,"🍛",1),("Aloo Tikki",30,"🥔",1),("Bread Pakoda",20,"🍞",1),("Egg Puff",25,"🥚",0),("Corn Chaat",40,"🌽",1),("Club Sandwich",70,"🥪",0)],
 ("brew", "Desserts"): [("Gulab Jamun",35,"🍡",1),("Chocolate Brownie",60,"🍫",1),("Rasmalai",50,"🍮",1),("Vanilla Ice Cream",35,"🍨",1),("Kulfi",40,"🍧",1),
   ("Chocolate Sundae",70,"🍨",1),("Gajar Halwa",50,"🥕",1),("Fruit Salad with Ice Cream",70,"🍓",1),("Payasam",40,"🥛",1),("Rasgulla",35,"⚪",1)],
 ("brew", "Pastries"): [("Chocolate Pastry",45,"🍰",1),("Black Forest Pastry",50,"🍰",1),("Pineapple Pastry",45,"🍍",1),("Red Velvet Pastry",60,"🍰",1),("Butterscotch Pastry",50,"🍰",1),
   ("Blueberry Cheesecake",80,"🫐",1),("Chocolate Donut",40,"🍩",1),("Cream Roll",25,"🥐",1),("Croissant",55,"🥐",1),("Muffin",40,"🧁",1)],
 ("roll", "Rolls"): [("Chicken Roll",70,"🌯",0),("Egg Roll",50,"🌯",0),("Paneer Roll",60,"🌯",1),("Veg Roll",45,"🌯",1),
   ("Chicken Tikka Roll",90,"🌯",0),("Mutton Seekh Roll",110,"🌯",0),("Double Egg Chicken Roll",90,"🌯",0),("Schezwan Veg Roll",55,"🌯",1),("Cheese Corn Roll",60,"🌯",1)],
 ("roll", "Burgers and Fries"): [("Zinger Burger",90,"🍔",0),("Veg Burger",60,"🍔",1),("French Fries",50,"🍟",1),("Peri Peri Fries",65,"🍟",1),("Cheese Fries",75,"🧀",1),("Cheese Balls",70,"🧀",1),
   ("Chicken Burger",80,"🍔",0),("Cheese Burger",70,"🍔",1),("Aloo Tikki Burger",50,"🍔",1),("Chicken Nuggets",80,"🍗",0),("Chicken Popcorn",90,"🍗",0),("Onion Rings",60,"🧅",1)],
}
SEED = [(ck, sec, n, p, e, bool(v)) for (ck, sec), lst in MENU.items() for (n, p, e, v) in lst]
HOME_CATS = [("Breakfast","kf","Breakfast"),("Lunch","kf","Lunch"),("Fast Food","kf","Fast Food"),("Tea and Coffee","brew","Tea and Coffee"),("Snacks","brew","Snacks"),
             ("Desserts","brew","Desserts"),("Pastries","brew","Pastries"),("Rolls","roll","Rolls"),("Burgers and Fries","roll","Burgers and Fries")]

# ---- Phase 1 storage: our own structures ----
users, menu, orders, bookings, notices = LinkedList(), LinkedList(), LinkedList(), LinkedList(), LinkedList()
parties = LinkedList()                                      # birthday party plans: pre-booked cakes, treats and tables at a discount
preorders = LinkedList()                                    # meal plans: a chosen meal for many days at a discounted price
offers, reviews = LinkedList(), LinkedList()                 # admin offers (discount / combo / BOGO / popular) and customer reviews
carts = {}                                                   # user id -> {"floor","counter","items": LinkedList}
queues = {f"{f}-{k}": Queue() for f in FLOORS for k in COUNTERS}   # 6 queues: one per counter per floor
undo_stacks = {}                                             # user id -> Stack of cart lines they removed (LIFO: Undo brings back the latest removal)
history = Stack()                                            # admin activity log, newest on top
count = {"user": 0, "item": 0, "order": 0, "book": 0, "notice": 0, "offer": 0, "review": 0, "plan": 0, "party": 0}
bsts = {}                                                    # Phase 2: one BST of food items per floor, keyed by name

def nid(k): count[k] = count.get(k, 0) + 1; return count[k]

def save():                                                  # everything goes to data.json
    data = {"menu_version": MENU_VERSION, "users": list(users.traverse()), "menu": list(menu.traverse()), "orders": list(orders.traverse()),
            "bookings": list(bookings.traverse()), "notices": list(notices.traverse())[-300:], "offers": list(offers.traverse()), "reviews": list(reviews.traverse()), "preorders": list(preorders.traverse()), "parties": list(parties.traverse()), "count": count, "history": list(history.items())[::-1],
            "carts": {str(u): {"floor": c["floor"], "counter": c["counter"], "items": list(c["items"].traverse())} for u, c in carts.items()}}
    with open(DB, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)

def seed_menu():
    count["item"] = 0
    for f in FLOORS:                                         # every floor counter owns its own copy of the menu
        for ck, sec, n, p, e, v in SEED:
            if pure(f) and not v: continue                   # veg-only floors skip the non-veg dishes
            menu.insert({"id": nid("item"), "floor": f, "counter": ck, "section": sec, "name": n, "price": p, "emoji": e, "veg": v, "avail": True})

def load():
    if not os.path.exists(DB): return False
    with open(DB, encoding="utf-8") as f: d = json.load(f)
    if d["menu"] and "counter" not in d["menu"][0]:
        print("Old data.json from an earlier version found. Delete it and restart."); return False
    stale = d.get("menu_version") != MENU_VERSION            # menu changed in the code: rebuild it, keep users and orders
    for rec in d["users"]: users.insert(rec)
    for rec in d["orders"]: orders.insert(rec)
    for rec in d["bookings"]:
        if "unit" in rec: bookings.insert(rec)               # bookings from the old table/slot design are dropped
    for rec in d.get("notices", []): notices.insert(rec)
    for rec in d.get("reviews", []): reviews.insert(rec)
    for rec in d.get("preorders", []): preorders.insert(rec)
    for rec in d.get("parties", []): parties.insert(rec)
    count.update(d["count"])
    for k in ("notice", "book", "item", "offer", "review", "plan", "party"): count.setdefault(k, 0)
    if not stale:
        for rec in d.get("offers", []): offers.insert(rec)
        for rec in d["menu"]: menu.insert(rec)
        for k, c in d.get("carts", {}).items():
            ll = LinkedList()
            for it in c["items"]: ll.insert(it)
            carts[int(k)] = {"floor": c["floor"], "counter": c["counter"], "items": ll}
    for o in orders.traverse():                              # old orders from earlier versions get the newer fields
        o.setdefault("ts", time.time() - 40 * 86400); o.setdefault("discounts", []); o.setdefault("subtotal", o["total"]); o.setdefault("method", ""); o.setdefault("pay_status", "Paid")
        o.setdefault("cname", (users.search("id", o["uid"]) or {}).get("name", "Guest"))
    for o in orders.traverse():                              # rebuild queues from saved pending orders
        if o["status"] == "Pending": queues[f"{o['floor']}-{o['counter']}"].enqueue(o)
    for h in d["history"]: history.push(h)
    if stale: seed_menu(); save()
    return True

def log(msg): history.push(f"{datetime.now():%d %b %H:%M} - {msg}"); save()

def rebuild_bst():
    for f in FLOORS:
        t = BST()
        for it in menu.traverse():
            if it["floor"] == f: t.insert(it["name"].lower(), it)
        bsts[f] = t

if not load():
    seed_menu(); save()
rebuild_bst()

def fmenu(floor): return [i for i in menu.traverse() if i["floor"] == floor]     # menu items of one floor

# ---- Phase 2: canteen map as a graph (one per floor, because the counter names differ) ----
def build_canteen(f):
    n1, n2, n3 = (cname(f, k) for k in COUNTERS)
    if n2 in (n1, n3): n2 = n2                                # names must be unique graph nodes
    edges = [("Entrance","Staircase"),("Entrance",n1),(n1,n2),(n2,n3),(n1,"Dining Area"),(n2,"Dining Area"),(n3,"Dining Area"),
             ("Dining Area","Washroom"),("Dining Area","Exit"),(n3,"Exit")]
    pos = {"Entrance":(70,200),"Staircase":(70,70),n1:(230,120),n2:(390,70),n3:(550,120),"Dining Area":(390,240),"Washroom":(200,320),"Exit":(630,250)}
    icons = {"Entrance": "🚪", "Staircase": "🪜", n1: COUNTERS["kf"]["emoji"], n2: COUNTERS["brew"]["emoji"], n3: COUNTERS["roll"]["emoji"], "Dining Area": "🍽️", "Washroom": "🚻", "Exit": "🏁"}
    g = Graph()
    for a, b in edges: g.add_edge(a, b)
    return g, edges, pos, icons, n3
CANTEENS = {f: build_canteen(f) for f in FLOORS}

# ---------------- email, notices ----------------
def send_mail(to, subject, body, attach=None):
    def job():
        u, p = os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD")
        if not (u and p): print(f"\n--- EMAIL to {to} ---\n{subject}\n{body}\n" + (f"[attachment: {attach[0]}]\n" if attach else "")); return
        try:
            m = EmailMessage(); m["From"], m["To"], m["Subject"] = u, to, subject; m.set_content(body)
            if attach: m.add_attachment(attach[1], maintype="application", subtype="pdf", filename=attach[0])
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s: s.login(u, p); s.send_message(m)
        except Exception as e: print("Email failed:", e)
    threading.Thread(target=job).start()

def notify(to, title, text, kind="info", oid=None):
    """to = 'u<userid>' | 'admin' | 'v<floor>-<key>'. The browser polls /api/notices and shows a pop-up."""
    notices.insert({"id": nid("notice"), "to": to, "title": title, "text": text, "kind": kind, "oid": oid, "t": f"{datetime.now():%H:%M}"})
    save()

def me(): return users.search("id", session.get("uid")) if session.get("uid") else None
def vendor():
    v = session.get("vendor")
    if not v: return None
    f, k = v.split("-"); f = int(f)
    return {"floor": f, "key": k, "name": cname(f, k), "c": COUNTERS[k], "target": f"v{f}-{k}"}
def safe(url, default): return url if url.startswith("/") and not url.startswith("//") else default

def active_offers(floor, counter, kind=None):
    return [o for o in offers.traverse() if o["active"] and o["floor"] == floor and o["counter"] == counter and (not kind or o["type"] == kind)]

def apply_offers(lines, floor, counter):
    """Works out the discounts for a cart. Every possible saving is a candidate; the candidates are ranked with merge sort
    (biggest saving first) and applied greedily, so one dish is never discounted twice."""
    by = {l["iid"]: l for l in lines}; cands = []
    for o in active_offers(floor, counter):
        if o["type"] == "discount":
            for iid in o["items"]:
                l = by.get(iid)
                if l: cands.append({"amount": round(l["sub"] * o["pct"] / 100), "items": [iid], "label": f"{o['pct']}% off {l['name']}", "oid": o["id"]})
        elif o["type"] == "bogo":
            for iid in o["items"]:
                l = by.get(iid)
                if l and l["qty"] >= 2: cands.append({"amount": (l["qty"] // 2) * l["price"], "items": [iid], "label": f"Buy 1 Get 1 free: {l['name']}", "oid": o["id"]})
        elif o["type"] == "combo" and o["items"] and all(i in by for i in o["items"]):
            n = min(by[i]["qty"] for i in o["items"]); per = sum(by[i]["price"] for i in o["items"]) - o["price"]
            if per > 0: cands.append({"amount": n * per, "items": list(o["items"]), "label": f"Combo: {o['title']} x{n}", "oid": o["id"]})
    ranked, _ = merge_sort(cands, lambda c: c["amount"], True)
    used, out = set(), []
    for c in ranked:
        if c["amount"] > 0 and not used.intersection(c["items"]): out.append(c); used.update(c["items"])
    return out

def make_bill(items, floor=None, counter=None):              # a stack evaluates the bill expression: subtotal minus offers
    lines, infix, post = [], [], []
    for l in items.traverse():
        it = menu.search("id", l["iid"])
        if not it: continue
        lines.append({"iid": it["id"], "name": it["name"], "emoji": it["emoji"], "price": it["price"], "qty": l["qty"], "sub": it["price"] * l["qty"]})
        infix.append(f"({it['price']}*{l['qty']})")
        post += [str(it["price"]), str(l["qty"]), "*"] + (["+"] if post else [])
    disc = apply_offers(lines, floor, counter) if lines and floor else []
    expr = "+".join(infix)
    for d in disc: expr += f"-({d['amount']})"; post += [str(d["amount"]), "-"]
    total = int(eval_postfix(" ".join(post))) if lines and balanced(expr) else 0
    return lines, expr, total, disc

def qr_svg(amount, oid_hint="order"):                       # UPI deep-link QR, drawn as inline SVG (needs: pip install segno)
    try:
        import segno
        from markupsafe import Markup
        link = f"upi://pay?pa={UPI_MERCHANT['vpa']}&pn={quote(UPI_MERCHANT['name'])}&am={amount}.00&cu=INR&tn={quote('CafeFlow ' + oid_hint)}"
        return Markup(segno.make(link, error="m").svg_inline(scale=5, border=1, dark="#1b1f3b", omitsize=True))
    except Exception: return None

def paylogo(m):                                              # drop a real logo at static/img/pay/<gpay|phonepe|paytm|upi|cod>.png (or .svg) to replace the built-in badge
    for ext in ("svg", "png", "webp", "jpg", "jpeg"):
        if os.path.exists(os.path.join(app.static_folder, "img", "pay", f"{m}.{ext}")): return f"/static/img/pay/{m}.{ext}"
    return None
app.jinja_env.globals.update(paylogo=paylogo, cname=cname, PAY_LABELS=PAY_LABELS, GST_PERCENT=GST_PERCENT)

@app.context_processor
def inject():
    u = me(); c = carts.get(u["id"]) if u else None
    lines, expr, total, _d = make_bill(c["items"], c["floor"], c["counter"]) if c else ([], "", 0, [])
    fl = session.get("floor", 1); vv = vendor()
    return {"PURE_VEG": pure(vv["floor"] if vv else fl), "user": u, "cart_n": sum(l["qty"] for l in lines), "cart_total": total, "COUNTERS": counters_for(fl), "vendor": vendor(), "is_admin": bool(session.get("admin")),
            "floors": FLOORS, "floor": fl, "floorpic": photo(f"canteen-floor-{fl}") or photo("canteen-floor"),
            "floorpics": {f: photo(f"canteen-floor-{f}") or photo("canteen-floor") for f in FLOORS}}

POSTERS = [("🍕","Pizza","#ff9a76","#ffd166"),("🍩","Donuts","#ff9ecb","#ffd6e8"),("🧋","Boba","#c3a6ff","#ffd1f5"),("🍔","Burgers","#ffb347","#ffe29a"),
 ("🍨","Ice Cream","#7fd8ff","#d6f1ff"),("☕","Coffee","#d9a66b","#ffe7c2"),("🍛","Biryani","#ffcf56","#ffb36b"),("🍰","Cake","#ff8fa3","#ffd0d8"),
 ("🥞","Dosa","#9be28f","#e9ffc9"),("🍵","Chai","#8fdcb4","#d8ffe9"),("🍫","Brownie","#c98b6b","#ffd9bf"),("🥭","Mango","#ffd23f","#fff2a8")]

# ---------------- food photos (static/img/<item-name>.jpg) ----------------
def slug(text): return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def norm(text): return re.sub(r"[^a-z0-9]", "", text.lower())

def photo(name):                                    # URL of the photo if a matching file exists, else None (templates fall back to emoji)
    wanted = {norm(name), norm(re.sub(r"\(.*?\)", "", name))}
    for folder in ("images", "img"):
        path = os.path.join(app.static_folder, folder)
        if not os.path.isdir(path): continue
        for fn in os.listdir(path):
            base, ext = os.path.splitext(fn)
            if ext.lower() in (".jpg", ".jpeg", ".png", ".webp", ".avif") and norm(base) in wanted: return f"/static/{folder}/{quote(fn)}"
    return None
app.jinja_env.globals["photo"] = photo

def counter_photo(floor, key): return photo(f"counter-{floor}-{key}") or photo(f"counter-{key}")
app.jinja_env.globals["counter_photo"] = counter_photo


# ---------------- offers shown to customers ----------------
_bs = {"t": 0, "n": -1, "d": {}}
def bestsellers(floor, key):                                 # top 3 dishes by units sold at one counter (cached for a few seconds)
    if time.time() - _bs["t"] > 15 or _bs["n"] != count["order"]:
        d = {}
        for o in orders.traverse():
            if o["status"] == "Rejected": continue
            c = d.setdefault((o["floor"], o["counter"]), Counter())
            for l in o["lines"]: c[l["name"]] += l["qty"]
        _bs.update(t=time.time(), n=count["order"], d={k: c.most_common(8) for k, c in d.items()})
    return _bs["d"].get((floor, key), [])

def item_tags(it):                                           # badges and sale price for one dish card
    fl, ck, tags, price = it["floor"], it["counter"], [], it["price"]
    top = [n for n, q in bestsellers(fl, ck)[:3] if q >= 5]
    pops = {i for o in active_offers(fl, ck, "popular") for i in o["items"]}
    best = it["name"] in top or it["id"] in pops
    for o in active_offers(fl, ck):
        if it["id"] not in o["items"]: continue
        if o["type"] == "discount": tags.append((f"{o['pct']}% OFF", "disc")); price = min(price, round(it["price"] * (100 - o["pct"]) / 100))
        elif o["type"] == "bogo": tags.append(("BUY 1 GET 1", "bogo"))
        elif o["type"] == "combo": tags.append(("IN COMBO", "combo"))
    return {"best": best, "tags": tags, "price": price}
app.jinja_env.globals["item_tags"] = item_tags

def offer_view(o):                                           # everything a template needs to draw an offer card / ad
    its = [menu.search("id", i) for i in o["items"]]; its = [i for i in its if i]
    base = sum(i["price"] for i in its)
    heads = {"discount": f"{o.get('pct', 0)}% OFF", "bogo": "BUY 1 GET 1 FREE", "combo": f"COMBO Rs {o.get('price', 0)}", "popular": "MOST ORDERED"}
    names = " + ".join(i["name"] for i in its) if o["type"] == "combo" else ", ".join(i["name"] for i in its)
    sub = {"discount": f"{o.get('pct', 0)}% off on {names}", "bogo": f"Buy one, get one free on {names}", "combo": f"{names} together for Rs {o.get('price', 0)} (save Rs {max(0, base - o.get('price', 0))})",
           "popular": f"Crowd favourites: {names}"}[o["type"]]
    return {"o": o, "head": heads[o["type"]], "sub": sub, "items": [{"id": i["id"], "name": i["name"], "price": i["price"], "pic": photo(i["name"]), "emoji": i["emoji"]} for i in its],
            "counter": cname(o["floor"], o["counter"]), "key": o["counter"], "save": max(0, base - o.get("price", 0)) if o["type"] == "combo" else 0}
app.jinja_env.globals["offer_view"] = offer_view
app.jinja_env.globals["has_review"] = lambda oid: reviews.search("oid", oid) is not None

@app.route("/add_offer/<int:oid>", methods=["POST"])
def add_offer(oid):                                          # one tap adds everything an offer needs to the cart
    u = me(); o = offers.search("id", oid)
    if not u or not o or not o["active"]: return redirect("/home")
    c = carts.get(u["id"]); back = safe(request.form.get("back", "/home"), "/home")
    if c and (c["counter"] != o["counter"] or c["floor"] != o["floor"]):
        flash(f"Your cart has items from {cname(c['floor'], c['counter'])} (Floor {c['floor']}). Place that order or clear the cart first."); return redirect(back)
    if not c: c = carts[u["id"]] = {"floor": o["floor"], "counter": o["counter"], "items": LinkedList()}
    q = 2 if o["type"] == "bogo" else 1
    for iid in o["items"]:
        it = menu.search("id", iid)
        if not it or not it.get("avail", True): continue
        line = c["items"].search("iid", iid)
        if line: line["qty"] = min(line["qty"] + q, 20)
        else: c["items"].insert({"iid": iid, "qty": q})
    save(); flash(f"Offer added to your cart: {o['title']}")
    return redirect("/cart")

@app.route("/order/<int:oid>/review", methods=["POST"])
def review(oid):                                             # one review per order; goes to the counter AND the admin
    o = mine_or_404(oid); u = me()
    wants_json = request.headers.get("X-Requested-With") == "fetch"
    if o["status"] == "Rejected" or reviews.search("oid", oid):
        return (jsonify({"ok": False, "msg": "This order cannot be reviewed (again)."}) if wants_json else redirect(f"/order/{oid}"))
    try: rating = max(1, min(5, int(request.form.get("rating", 5))))
    except ValueError: rating = 5
    text = request.form.get("text", "").strip()[:300]
    tags = [t for t in request.form.getlist("tags") if t in ("Tasty", "Fast", "Hot", "Value", "Clean")]
    reviews.insert({"id": nid("review"), "oid": oid, "uid": u["id"], "cname": u["name"], "floor": o["floor"], "counter": o["counter"], "rating": rating,
                    "text": text, "tags": tags, "ts": time.time(), "time": f"{datetime.now():%d %b %H:%M}"})
    cn, snippet = cname(o["floor"], o["counter"]), (f': "{text[:80]}"' if text else "")
    notify(f"v{o['floor']}-{o['counter']}", f"New {rating}-star review", f"{u['name']} reviewed order #{oid}{snippet}", "review", oid)      # to the counter
    notify("admin", f"{rating}-star review for {cn} (F{o['floor']})", f"{u['name']} on order #{oid}{snippet}", "review", oid)                 # to the admin
    log(f"{u['name']} gave {rating} star(s) to {cn}, Floor {o['floor']} (order #{oid})")
    if wants_json: return jsonify({"ok": True, "rating": rating})
    flash("Thanks for your review!"); return redirect(f"/order/{oid}")

def wall_reviews(floor=None, counter=None, limit=24, min_stars=1):      # newest first (merge sort, Phase 3), only reviews with something to show
    rs = [r for r in reviews.traverse() if (floor is None or r["floor"] == floor) and (counter is None or r["counter"] == counter) and r["rating"] >= min_stars and (r.get("text") or r["rating"] >= 4)]
    rs, _ = merge_sort(rs, lambda r: r.get("ts", 0), True)
    return [{**r, "cn": cname(r["floor"], r["counter"])} for r in rs[:limit]]

@app.route("/reviews")
def reviews_page():
    u = me()
    if not u: return redirect("/")
    fl, ck = session.get("floor", 1), request.args.get("c", "")
    rs = wall_reviews(fl, ck if ck in COUNTERS else None, 40)
    todo = [o for o in reversed(list(orders.traverse())) if o["uid"] == u["id"] and o["status"] != "Rejected" and not o.get("demo") and not reviews.search("oid", o["id"])][:8]
    mine = [r for r in reviews.traverse() if r["uid"] == u["id"]][::-1]
    allr = [r for r in reviews.traverse() if r["floor"] == fl]
    return render_template("reviews.html", rs=rs, ck=ck, todo=[{**o, "cn": cname(o["floor"], o["counter"]), "dish": ", ".join(l["name"] for l in o["lines"][:2])} for o in todo],
                           mine=[{**r, "cn": cname(r["floor"], r["counter"])} for r in mine], avg=avg_rating(allr), total=len(allr))

@app.route("/stories")
def stories():                                               # Instagram-style stories, built from live data: best sellers, offers and fresh reviews
    if not me(): return redirect("/")
    fl, rings = session.get("floor", 1), []
    for k, c in counters_for(fl).items():
        slides = []
        for name, qty in bestsellers(fl, k)[:3]:
            it = next((i for i in fmenu(fl) if i["name"] == name), None)
            if it: slides.append({"kind": "dish", "tag": f"Bestseller · {qty} sold", "title": it["name"], "sub": f"Rs {it['price']}", "pic": photo(it["name"]), "emoji": it["emoji"], "iid": it["id"]})
        if len(slides) < 2:
            slides += [{"kind": "dish", "tag": "On the menu", "title": i["name"], "sub": f"Rs {i['price']}", "pic": photo(i["name"]), "emoji": i["emoji"], "iid": i["id"]} for i in [x for x in fmenu(fl) if x["counter"] == k][:3 - len(slides)]]
        for o in active_offers(fl, k, None)[:2]:
            ov = offer_view(o); slides.append({"kind": "offer", "tag": "Offer", "title": ov["head"], "sub": ov["sub"], "pic": ov["items"][0]["pic"] if ov["items"] else None, "emoji": "🏷️", "iid": None})
        for r in wall_reviews(fl, k, 2, 4): slides.append({"kind": "review", "tag": f"{'★' * r['rating']} review", "title": f"“{r['text'] or 'Loved it!'}”", "sub": f"{r['cname']} · {c['name']}", "pic": None, "emoji": "💬", "iid": None})
        pic = next((s["pic"] for s in slides if s["pic"]), None)
        rings.append({"key": k, "name": c["name"], "emoji": c["emoji"], "c1": c["c1"], "c2": c["c2"], "pic": pic, "slides": slides})
    top = wall_reviews(fl, None, 6, 5)
    if top: rings.insert(0, {"key": "love", "name": "Loved by you", "emoji": "💛", "c1": "#ffb703", "c2": "#ff6b35", "pic": None,
                             "slides": [{"kind": "review", "tag": "★★★★★ review", "title": f"“{r['text'] or 'Loved it!'}”", "sub": f"{r['cname']} · {r['cn']}", "pic": None, "emoji": "💬", "iid": None} for r in top]})
    return render_template("stories.html", rings=[r for r in rings if r["slides"]])

@app.route("/vendor/reviews")
def vendor_reviews():
    v = vguard(); rs = [r for r in reviews.traverse() if r["floor"] == v["floor"] and r["counter"] == v["key"]]
    dist = Counter(r["rating"] for r in rs)
    return render_template("v_reviews.html", v=v, page="reviews", wall=wall_reviews(v["floor"], v["key"], 24), avg=avg_rating(rs), total=len(rs), dist=[dist[i] for i in (5, 4, 3, 2, 1)],
                           rs=[{**r, "cn": v["name"]} for r in merge_sort(rs, lambda r: r.get("ts", 0), True)[0][:60]])

# ---------------- Phase 3 helpers ----------------
def sort_key(field): return (lambda i: i["name"].lower()) if field == "name" else (lambda i: i[field])
SORTS = {"price_asc": ("price", False), "price_desc": ("price", True), "name": ("name", False)}

def hhmm(m): return f"{m // 60:02d}:{m % 60:02d}"
def pretty_time(m): h = m // 60; return f"{(h % 12) or 12}:{m % 60:02d} {'AM' if h < 12 else 'PM'}"
app.jinja_env.globals.update(hhmm=hhmm, pretty_time=pretty_time)

# ---------------- login / register ----------------
@app.route("/")
def index():
    if session.get("admin"): return redirect("/admin")
    if vendor(): return redirect("/vendor")
    if me(): return redirect("/home")
    return render_template("login.html", posters=POSTERS)

@app.route("/register", methods=["POST"])
def register():
    f = request.form; name, email = f["name"].strip(), f["email"].strip().lower()
    if name.lower() == ADMIN_NAME or name.lower() in VENDOR_LOGINS: flash("That name is reserved. Choose another.")
    elif f["password"] != f["confirm"]: flash("Passwords do not match.")
    elif users.search("lname", name.lower()): flash("That name is taken. Choose another.")
    elif users.search("email", email): flash("This Gmail is already registered.")
    else:
        users.insert({"id": nid("user"), "name": name, "lname": name.lower(), "email": email, "pw": generate_password_hash(f["password"])})
        log(f"New user registered: {name}")
        send_mail(email, "Welcome to CafeFlow", f"Hi {name},\n\nYour account was created successfully. Come have a bite!\n\nCafeFlow")
        flash("Account created! Check your Gmail, then log in.")
    return redirect("/")

@app.route("/login", methods=["POST"])
def login():
    name, pw = request.form["name"].strip(), request.form["password"]
    if name.lower() == ADMIN_NAME and pw == ADMIN_PASS:
        session.clear(); session.permanent = bool(request.form.get("remember")); session["admin"] = True; session["seen"] = count["notice"]; return redirect("/admin")
    v = VENDOR_LOGINS.get(name.lower())
    if v and check_password_hash(VENDOR_HASH[name.lower()], pw):             # a counter logs in with its own name and password
        session.clear(); session.permanent = bool(request.form.get("remember")); session["vendor"] = f"{v[0]}-{v[1]}"; session["seen"] = count["notice"]; return redirect("/vendor")
    u = users.search("lname", name.lower())
    if u and check_password_hash(u["pw"], pw):
        session.clear(); session.permanent = bool(request.form.get("remember")); session["uid"] = u["id"]; session["seen"] = count["notice"]; return redirect("/home")
    flash("Wrong name or password."); return redirect("/")

@app.route("/logout")
def logout(): session.clear(); return redirect("/")

@app.route("/api/notices")
def api_notices():                                           # polled by every page: new pop-ups for whoever is logged in
    if session.get("admin"): target = "admin"
    elif vendor(): target = vendor()["target"]
    elif me(): target = f"u{me()['id']}"
    else: return jsonify([])
    seen = session.get("seen", 0)
    out = [n for n in notices.traverse() if n["id"] > seen and n["to"] == target]
    session["seen"] = count["notice"]
    return jsonify(out)

# ---------------- customer pages ----------------
@app.route("/home")
def home():
    if not me(): return redirect("/")
    fl = session.get("floor", 1)
    items = fmenu(fl)
    cats = []
    for label, ck, sec in HOME_CATS:
        its = [i for i in items if i["counter"] == ck and i["section"] == sec]
        cats.append({"label": label, "ck": ck, "sec": sec, "n": len(its), "emoji": its[0]["emoji"] if its else "🍽️",
                     "pic": next((photo(i["name"]) for i in its if photo(i["name"])), None)})
    with_pic = [i for i in items if photo(i["name"])]
    popular = (with_pic + [i for i in items if i not in with_pic])[:28]
    hero = [{"name": i["name"], "url": photo(i["name"])} for i in with_pic[::max(1, len(with_pic) // 4)][:4]]
    counts = {k: sum(1 for i in items if i["counter"] == k) for k in COUNTERS}
    return render_template("home.html", wall=wall_reviews(fl, None, 20), cats=cats, belt1=popular[0::2], belt2=popular[1::2], hero_pics=hero, counts=counts,
                           n_items=len(items), dish_names=[i["name"] for i in items],
                           ads=[offer_view(o) for o in offers.traverse() if o["active"] and o["floor"] == fl and o.get("ad", True)])

@app.route("/menu")
def old_menu(): return redirect("/home")

@app.route("/floor/<int:n>")
def set_floor(n):
    if n in FLOORS: session["floor"] = n
    return redirect(safe(request.args.get("next", "/home"), "/home"))

@app.route("/counter/<key>")
def counter(key):
    if not me(): return redirect("/")
    if key not in COUNTERS: abort(404)
    fl = session.get("floor", 1)
    sec = request.args.get("sec", "")
    items = [i for i in fmenu(fl) if i["counter"] == key and (not sec or i["section"] == sec)]
    sort = request.args.get("sort", "")
    if sort in SORTS:                                        # Phase 3: merge sort inside the real menu page
        field, rev = SORTS[sort]; items, _ = merge_sort(items, sort_key(field), rev)
    return render_template("counter.html", key=key, c=counters_for(fl)[key], sec=sec, sort=sort, items=items, back=request.full_path.rstrip("?"),
                           deals=[offer_view(o) for o in active_offers(fl, key) if o["type"] != "popular"], hot=[n for n, q in bestsellers(fl, key)[:3] if q >= 5])

@app.route("/search")
def search():                                                # Phase 2: BST search
    if not me(): return redirect("/")
    q, note, items = request.args.get("q", "").strip(), "", []
    bst = bsts[session.get("floor", 1)]
    if q:
        hit, path = bst.search(q.lower())
        if hit: items, note = [hit], f"Found with BST search in {len(path)} step(s): " + " > ".join(path)
        else:
            items = [i for i in bst.inorder() if q.lower() in i["name"].lower()]
            note = "No exact match. Showing similar items (A to Z)." if items else "Nothing found."
    return render_template("search.html", q=q, note=note, items=items, show_counter=True, back=request.full_path.rstrip("?"))

@app.route("/add", methods=["POST"])
def add():
    u = me()
    if not u: return redirect("/")
    back = safe(request.form["back"], "/home")
    it = menu.search("id", int(request.form["iid"])); qty = max(1, min(int(request.form["qty"]), 20))
    if not it: return redirect(back)
    if not it.get("avail", True): flash(f"{it['name']} is sold out right now."); return redirect(back)
    fl = it["floor"]
    c = carts.get(u["id"])
    if c and (c["counter"] != it["counter"] or c["floor"] != fl):
        flash(f"Your cart has items from {cname(c['floor'], c['counter'])} (Floor {c['floor']}). Place that order or clear the cart first.")
        return redirect(back)
    if not c: c = carts[u["id"]] = {"floor": fl, "counter": it["counter"], "items": LinkedList()}
    line = c["items"].search("iid", it["id"])
    if line: line["qty"] = min(line["qty"] + qty, 20)
    else: c["items"].insert({"iid": it["id"], "qty": qty})
    save(); flash(f"Added {qty} x {it['name']} to your cart.")
    return redirect(back)

@app.route("/cart")
def cart():
    u = me()
    if not u: return redirect("/")
    c = carts.get(u["id"])
    lines, expr, total, disc = make_bill(c["items"], c["floor"], c["counter"]) if c else ([], "", 0, [])
    st = undo_stacks.get(u["id"]); un = [menu.search("id", e["line"]["iid"])["name"] for e in st.items() if menu.search("id", e["line"]["iid"])] if st else []
    return render_template("cart.html", undo=un, lines=lines, expr=expr, total=total, disc=disc, subtotal=sum(l["sub"] for l in lines), c=c, qr=qr_svg(total) if lines else None, upi_vpa=UPI_MERCHANT["vpa"], cn=cname(c["floor"], c["counter"]) if c else "")

@app.route("/cart/remove/<int:iid>")
def remove(iid):
    u = me(); c = carts.get(u["id"]) if u else None
    if c:
        line = c["items"].search("iid", iid)
        if line:
            undo_stacks.setdefault(u["id"], Stack()).push({"floor": c["floor"], "counter": c["counter"], "line": dict(line)})    # stack: remember what was removed
            c["items"].delete("iid", iid)
        if c["items"].head is None: del carts[u["id"]]
        save()
    return redirect("/cart")

@app.route("/cart/undo")
def cart_undo():                                             # STACK pop: the most recently removed dish comes back (insert_front keeps its place near the top)
    u = me()
    if not u: return redirect("/")
    st = undo_stacks.get(u["id"]); top = st.peek() if st else None
    if not top: flash("Nothing to undo."); return redirect("/cart")
    c = carts.get(u["id"])
    if c and (c["floor"], c["counter"]) != (top["floor"], top["counter"]): flash("Your cart is now from another counter, so that dish cannot be restored."); return redirect("/cart")
    st.pop()
    if not c: c = carts[u["id"]] = {"floor": top["floor"], "counter": top["counter"], "items": LinkedList()}
    back = c["items"].search("iid", top["line"]["iid"])
    if back: back["qty"] += top["line"]["qty"]
    else: c["items"].insert_front(top["line"])
    save(); flash("Brought back: " + str(menu.search("id", top["line"]["iid"])["name"])); return redirect("/cart")

@app.route("/cart/clear")
def clear():
    u = me()
    if u and u["id"] in carts: del carts[u["id"]]; save()
    return redirect("/cart")

# ---------------- payment, order tracking, bill ----------------
@app.route("/pay", methods=["POST"])
def pay():
    u = me()
    if not u: return redirect("/")
    c = carts.get(u["id"])
    lines, expr, total, disc = make_bill(c["items"], c["floor"], c["counter"]) if c else ([], "", 0, [])
    if not lines: return redirect("/cart")
    method, upi = request.form.get("method", ""), request.form.get("upi", "").strip()
    if method not in PAY_LABELS: flash("Choose a payment method."); return redirect("/cart")
    cn = cname(c["floor"], c["counter"]); upi = ""
    o = {"id": nid("order"), "uid": u["id"], "cname": u["name"], "floor": c["floor"], "counter": c["counter"], "lines": lines, "total": total, "discounts": disc, "subtotal": sum(l["sub"] for l in lines),
         "status": "Pending", "time": f"{datetime.now():%d %b %H:%M}", "ts": time.time(), "pay": PAY_LABELS[method], "method": method,
         "pay_status": "Pay on delivery" if method == "cod" else "Paid", "txn": "" if method == "cod" else f"CF{random.randint(10**9, 10**10 - 1)}",
         "upi": upi if method != "cod" else "", "eta": None, "eta_end": None, "reason": ""}
    orders.insert(o); queues[f"{o['floor']}-{o['counter']}"].enqueue(o); del carts[u["id"]]
    log(f"Order #{o['id']} placed by {u['name']} at {cn}, Floor {o['floor']} (Rs {total}, {o['pay']})")
    notify(f"v{o['floor']}-{o['counter']}", f"New order #{o['id']}", f"{u['name']} ordered {sum(l['qty'] for l in lines)} item(s), Rs {total} ({o['pay']})", "order", o["id"])
    send_mail(u["email"], f"CafeFlow bill: order #{o['id']} at {cn}",
              f"Hi {u['name']},\n\n" + ("Payment successful. " if method != "cod" else "Order placed, please pay cash when you collect. ") +
              f"Your order #{o['id']} (Rs {total}) is sent to {cn}, Floor {o['floor']}. Your bill is attached.\nWe will email you again when the dish is ready.\n\nCafeFlow",
              attach=(f"CafeFlow-bill-{o['id']}.pdf", bill_pdf(o)) if pdfcanvas else None)
    return redirect(f"/order/{o['id']}?new=1")

def barcode_bars(text):                                      # Code 128 bars as (x, width) in modules, shared by the PDF and the HTML bill
    try:
        from reportlab.graphics.barcode.code128 import Code128
        b = Code128(text, barWidth=1); b.validate(); b.encode(); b.decompose()
    except Exception: return [], 0
    x, bars = 0, []
    for ch in b.decomposed:
        w = ord(ch.lower()) - 96
        if ch.isupper(): bars.append((x, w))
        x += w
    return bars, x

def receipt_data(o):                                         # everything a bill shows, in one dict
    total, cn = o["total"], cname(o["floor"], o["counter"])
    when = datetime.fromtimestamp(o.get("ts") or time.time())
    upi = o.get("upi", ""); masked = (upi[:2] + "****@" + upi.split("@", 1)[1]) if "@" in upi else ""
    gst = round(total - total / (1 + GST_PERCENT / 100), 2) if GST_PERCENT and total else 0
    code = f"CF{o['id']:06d}"; bars, bw = barcode_bars(code)
    return {"biz": BUSINESS["name"], "addr": [a for a in (BUSINESS.get("line1"), f"Floor {o['floor']} - {cn}", BUSINESS.get("phone")) if a],
            "date": f"{when:%d/%m/%Y}", "time": f"{when:%I:%M:%S %p}", "customer": o.get("cname", "Guest"), "order": o["id"], "counter": cn, "floor": o["floor"],
            "lines": o["lines"], "subtotal": o.get("subtotal", total), "discounts": o.get("discounts", []), "gst_pct": GST_PERCENT, "gst": gst, "total": total,
            "method": o["pay"], "mkey": o.get("method", ""), "upi": masked, "txn": o.get("txn", ""), "status": o.get("pay_status", "Paid"),
            "code": code, "bars": bars, "bw": bw}

def bill_pdf(o):                                             # 80 mm till-roll receipt, laid out like the sample bill
    r = receipt_data(o); W, M = 226.8, 15; CW = W - 2 * M
    FN, FB, SZ = "Courier", "Courier-Bold", 8.6
    ops = []                                                 # (kind, left, right, font, size, height)
    def cols(size): return int(CW / (0.6 * size))
    def ctext(t, f=FN, sz=SZ):
        for ln in (textwrap.wrap(t, cols(sz)) or [""]): ops.append(("c", ln, "", f, sz, sz + 4))
    def lr(a, b="", f=FN, sz=SZ):
        lines = textwrap.wrap(a, max(8, cols(sz) - len(b) - 1)) or [""]
        for i, ln in enumerate(lines): ops.append(("lr", ln, b if i == 0 else "", f, sz, sz + 4))
    def rule(): ops.append(("rule", "", "", FN, SZ, 12))
    ops.append(("icon", "", "", FN, SZ, 46))
    ctext(r["biz"], FB, 12.5)
    for a in r["addr"]: ctext(a, FN, 8)
    rule(); lr("DATE: " + r["date"], "TIME: " + r["time"]); rule()
    lr("CUSTOMER: " + r["customer"].upper()); lr("COUNTER: " + r["counter"].upper()); lr(f"FLOOR: {r['floor']}"); lr(f"ORDER NO: #{r['order']}"); rule()
    for l in r["lines"]: lr(f"{l['qty']} x {l['name'].upper()} @ Rs {l['price']}", f"Rs {l['sub']}")
    rule(); lr("SUBTOTAL", f"Rs {r['subtotal']}")
    for d in r["discounts"]: lr(d["label"].upper(), f"- Rs {d['amount']}")
    if r["gst_pct"]: lr(f"INCL. GST ({r['gst_pct']}%)", f"Rs {r['gst']:.2f}")
    rule(); lr("TOTAL", f"Rs {r['total']}", FB, 11.5); rule()
    lr("PAYMENT: " + r["method"].upper())
    if r["upi"]: lr("UPI ID: " + r["upi"])
    if r["txn"]: lr("TXN: " + r["txn"])
    lr("STATUS: " + r["status"].upper()); rule()
    ctext("THANK YOU FOR VISITING!", FB); ctext("WE HOPE TO SEE YOU AGAIN", FB)
    ctext("Collect your order when you get the ready alert.", FN, 7.4)
    if r["bars"]: ops.append(("bars", "", "", FN, SZ, 52)); ops.append(("c", r["code"], "", FN, 7, 12))
    ops.append(("sp", "", "", FN, SZ, 8))
    H = M * 2 + sum(op[5] for op in ops)
    buf = io.BytesIO(); c = pdfcanvas.Canvas(buf, pagesize=(W, H)); c.setTitle(f"CafeFlow bill #{o['id']}"); y = H - M
    for kind, a, b, f, sz, h in ops:
        if kind == "c": c.setFont(f, sz); c.drawCentredString(W / 2, y - sz, a)
        elif kind == "lr":
            c.setFont(f, sz); c.drawString(M, y - sz, a)
            if b: c.drawRightString(W - M, y - sz, b)
        elif kind == "rule": c.setLineWidth(.8); c.setDash(2, 2); c.line(M, y - 6, W - M, y - 6); c.setDash()
        elif kind == "icon":
            cx, s = W / 2, 34; x0, y0 = cx - s / 2, y - s - 4
            c.setLineWidth(1.5); c.roundRect(x0, y0, s, s, 7, stroke=1, fill=0)
            c.rect(cx - 8, y0 + 8, 13, 12, stroke=1, fill=0); c.arc(cx + 3, y0 + 10, cx + 11, y0 + 18, -90, 180)
            c.setLineWidth(1.1); c.line(cx - 4, y0 + 23, cx - 4, y0 + 27); c.line(cx + 1, y0 + 23, cx + 1, y0 + 28)
        elif kind == "bars":
            k = (CW * .82) / r["bw"]; bx = (W - r["bw"] * k) / 2; c.setFillColorRGB(0, 0, 0)
            for x, w in r["bars"]: c.rect(bx + x * k, y - 46, w * k, 42, stroke=0, fill=1)
        y -= h
    c.showPage(); c.save(); return buf.getvalue()

def mine_or_404(oid):
    u = me(); o = orders.search("id", oid)
    if not u or not o or o["uid"] != u["id"]: abort(404)
    return o

def queue_ahead(o):                                          # QUEUE position: how many orders are in front of this one at its counter (None once it left the queue)
    return queues[f"{o['floor']}-{o['counter']}"].position("id", o["id"]) if o["status"] == "Pending" else None

def order_state(o):
    left = max(0, int(o["eta_end"] - time.time())) if o.get("eta_end") and o["status"] == "Accepted" else 0
    return {"id": o["id"], "status": o["status"], "ahead": queue_ahead(o), "eta": o.get("eta"), "left": left, "reason": o.get("reason", ""), "counter": cname(o["floor"], o["counter"]), "floor": o["floor"]}

@app.route("/order/<int:oid>")
def order_page(oid):
    o = mine_or_404(oid)
    return render_template("order.html", o=o, rd=receipt_data(o), cn=cname(o["floor"], o["counter"]), new=bool(request.args.get("new")), state=order_state(o), rev=reviews.search("oid", oid))

@app.route("/api/order/<int:oid>")
def api_order(oid): return jsonify(order_state(mine_or_404(oid)))

def bill_order_or_404(oid):                                  # the customer, the admin, or the counter that cooked it may open a bill
    o = orders.search("id", oid); u = me(); v = vendor()
    if not o: abort(404)
    if (u and o["uid"] == u["id"]) or session.get("admin") or (v and v["floor"] == o["floor"] and v["key"] == o["counter"]): return o
    abort(404)

@app.route("/bill/<int:oid>")
def bill(oid):
    o = bill_order_or_404(oid)
    if not pdfcanvas: abort(501)
    return Response(bill_pdf(o), mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename=CafeFlow-bill-{oid}.pdf"})

@app.route("/bill/<int:oid>/view")
def bill_view(oid):
    o = bill_order_or_404(oid)
    return render_template("receipt.html", o=o, rd=receipt_data(o), can_pdf=bool(pdfcanvas))

@app.route("/orders")
def my_orders():
    if not me(): return redirect("/")
    return render_template("orders.html", orders=[o for o in orders.traverse() if o["uid"] == me()["id"]][::-1])

# ---------------- pre-order meal plans: pick a meal once, get it every chosen day at a discount ----------------
PLANS = [("1d", "1 day", 1, 8), ("1w", "1 week", 7, 10), ("2w", "2 weeks", 14, 12), ("3w", "3 weeks", 21, 13), ("4w", "4 weeks", 28, 15), ("5w", "5 weeks", 35, 16),
         ("6w", "6 weeks", 42, 16), ("2m", "2 months", 60, 18), ("3m", "3 months", 90, 20), ("6m", "6 months", 180, 22), ("1y", "1 year", 365, 25)]   # key, label, calendar days, discount %
PLAN_BY = {k: {"key": k, "label": l, "days": d, "pct": p} for k, l, d, p in PLANS}
PRE_LEAD = 60                                                # the order reaches the counter this many minutes before the pickup time
PRE_MAX_START = 60                                           # a plan can start at most this many days ahead

def plan_dates(start, plan, weekdays, skip):                 # every calendar day of the plan that is a chosen weekday and not skipped
    out, d0 = [], date.fromisoformat(start)
    for i in range(plan["days"]):
        d = d0 + timedelta(days=i)
        if d.weekday() in weekdays and d.isoformat() not in skip: out.append(d.isoformat())
    return out

def pre_quote(f):                                            # authoritative price + dates for a plan request (used by the live calendar and by checkout)
    try:
        fl, key, plan = int(f["floor"]), f["counter"], PLAN_BY[f["plan"]]; start = f["start"]
        items = {int(k): int(v) for k, v in dict(f.get("items", {})).items() if int(v) > 0}
        weekdays = {int(x) for x in f.get("weekdays", [0, 1, 2, 3, 4])}; skip = set(f.get("skip", []))
        d0 = date.fromisoformat(start)
    except (KeyError, ValueError, TypeError): return {"ok": False, "error": "Please choose a counter, dishes, a plan and a start date."}
    lines = []
    for iid, q in items.items():
        it = menu.search("id", iid)
        if not it or it["floor"] != fl or it["counter"] != key or not it.get("avail", True): return {"ok": False, "error": "One of the dishes is not available."}
        lines.append({"iid": iid, "name": it["name"], "emoji": it["emoji"], "price": it["price"], "qty": min(q, 10), "sub": it["price"] * min(q, 10), "pic": photo(it["name"])})
    if not lines: return {"ok": False, "error": "Choose at least one dish."}
    if d0 <= date.today(): return {"ok": False, "error": "Pre-orders start from tomorrow."}
    if d0 > date.today() + timedelta(days=PRE_MAX_START): return {"ok": False, "error": f"Start within {PRE_MAX_START} days."}
    dates = plan_dates(start, plan, weekdays, skip)
    if not dates: return {"ok": False, "error": "No meal days selected. Pick at least one weekday."}
    regular = sum(l["sub"] for l in lines); per_day = max(1, round(regular * (100 - plan["pct"]) / 100))
    return {"ok": True, "lines": lines, "regular": regular, "per_day": per_day, "pct": plan["pct"], "days": dates, "n": len(dates), "total": per_day * len(dates),
            "full": regular * len(dates), "saved": (regular - per_day) * len(dates), "plan": plan, "floor": fl, "counter": key, "cname": cname(fl, key)}

def pre_release_time(p, d):                                  # when the order of day d should reach the counter
    h, m = divmod(p["pickup"], 60); return datetime.fromisoformat(d) + timedelta(hours=h, minutes=m - PRE_LEAD)

def release_due():
    release_parties()                                           # turn every plan day that is due into a normal order in the counter's queue
    now, made = datetime.now(), 0
    for p in preorders.traverse():
        if p["status"] != "active": continue
        for d in p["days"]:
            if d in p["released"] or pre_release_time(p, d) > now: continue
            u = users.search("id", p["uid"]); p["released"].append(d)
            lines = [{k: l[k] for k in ("iid", "name", "emoji", "price", "qty", "sub")} for l in p["lines"]]; regular = sum(l["sub"] for l in lines)
            o = {"id": nid("order"), "uid": p["uid"], "cname": u["name"] if u else "Guest", "floor": p["floor"], "counter": p["counter"], "lines": lines, "total": p["per_day"],
                 "discounts": [{"label": f"Pre-order plan {p['plan']['label']} ({p['pct']}% off)", "amount": regular - p["per_day"], "items": [l["iid"] for l in lines], "oid": f"plan{p['id']}"}] if regular > p["per_day"] else [],
                 "subtotal": regular, "status": "Pending", "time": f"{datetime.now():%d %b %H:%M}", "ts": time.time(), "pay": "Pre-order plan (" + PAY_LABELS[p["method"]] + ")", "method": p["method"],
                 "pay_status": "Pay on delivery" if p["method"] == "cod" else "Paid", "txn": p.get("txn", ""), "upi": "", "eta": None, "eta_end": None, "reason": "", "pre": p["id"], "pickup": pretty_time(p["pickup"])}
            orders.insert(o); queues[f"{o['floor']}-{o['counter']}"].enqueue(o); made += 1
            cn = cname(p["floor"], p["counter"])
            notify(f"v{p['floor']}-{p['counter']}", f"Pre-order #{o['id']} for {pretty_time(p['pickup'])}", f"{o['cname']}: {sum(l['qty'] for l in lines)} item(s), pickup {pretty_time(p['pickup'])}. Prepare it on time.", "order", o["id"])
            notify(f"u{p['uid']}", f"Today's pre-order is with {cn}", f"Pickup at {pretty_time(p['pickup'])}. We will alert you when it is ready.", "accepted", o["id"])
            if u: send_mail(u["email"], f"Your pre-ordered meal is with {cn}", f"Hi {u['name']},\n\nYour pre-order (plan #{p['id']}) for today has reached {cn}, Floor {p['floor']}. Pickup time: {pretty_time(p['pickup'])}.\n\nCafeFlow")
        if len(p["released"]) >= len(p["days"]): p["status"] = "completed"
    if made: save()
    return made

_last_release = [0.0]
@app.before_request
def _pre_tick():                                             # also checked on every request, at most once every 20 seconds
    if time.time() - _last_release[0] > 20: _last_release[0] = time.time(); release_due()

def _pre_loop():
    while True: time.sleep(30); release_due()

def pre_view(p):                                             # extra fields a template needs for one plan
    nxt = next((d for d in p["days"] if d not in p["released"]), None)
    left = [d for d in p["days"] if d not in p["released"]]
    return {"p": p, "next": nxt, "left": len(left), "done": len(p["released"]), "remaining_value": len(left) * p["per_day"], "cname": cname(p["floor"], p["counter"]),
            "span": f"{date.fromisoformat(p['days'][0]):%d %b} to {date.fromisoformat(p['days'][-1]):%d %b %Y}"}

@app.route("/preorder")
def preorder():
    u = me()
    if not u: return redirect("/")
    fl = session.get("floor", 1); menus = {}
    for k in COUNTERS:
        menus[k] = [{"id": i["id"], "name": i["name"], "price": i["price"], "emoji": i["emoji"], "pic": photo(i["name"]), "section": i["section"]} for i in fmenu(fl) if i["counter"] == k and i.get("avail", True)]
    mine = [pre_view(p) for p in preorders.traverse() if p["uid"] == u["id"]][::-1]
    return render_template("preorder.html", menus=menus, plans=[PLAN_BY[k] for k, *_ in PLANS], mine=mine, tomorrow=(date.today() + timedelta(days=1)).isoformat(),
                           maxd=(date.today() + timedelta(days=PRE_MAX_START)).isoformat(), starts=list(range(DAY_START, DAY_END, STEP)), upi_vpa=UPI_MERCHANT["vpa"])

@app.route("/api/preorder/quote", methods=["POST"])
def api_pre_quote():
    if not me(): return jsonify({"ok": False, "error": "Please log in."})
    q = pre_quote(request.get_json(silent=True) or {})
    if q.get("ok"): q["plan"] = q["plan"]["label"]; q["qr"] = str(qr_svg(q["total"], "preorder") or "")
    return jsonify(q)

def plan_receipt(p):                                         # a plan bill: every meal day, the plan discount and the total paid up front
    n = len(p["days"]); lines = [{**l, "qty": l["qty"] * n, "sub": l["price"] * l["qty"] * n} for l in p["lines"]]
    ts = time.mktime(datetime.strptime(f"{datetime.now().year} {p['created']}", "%Y %d %b %H:%M").timetuple())
    o = {"id": p["id"], "floor": p["floor"], "counter": p["counter"], "cname": p["cname"], "lines": lines, "total": p["total"], "subtotal": p["regular"] * n, "ts": ts,
         "discounts": [{"label": f"Pre-order {p['plan']['label']} ({p['pct']}% off)", "amount": p["saved"]}] if p["saved"] else [],
         "pay": "UPI" if p["method"] == "upi" else "Cash on pickup", "method": p["method"], "txn": p.get("txn", ""), "pay_status": "Paid" if p["method"] == "upi" else "Pay at pickup"}
    rd = receipt_data(o); rd["code"] = f"PL{p['id']:06d}"; rd["bars"], rd["bw"] = barcode_bars(rd["code"]); rd["order"] = f"PLAN-{p['id']}"
    rd["addr"] = rd["addr"] + [f"{n} meal day(s): {p['days'][0]} to {p['days'][-1]}", f"Pickup {pretty_time(p['pickup'])} daily"]
    return o, rd

def plan_or_404(pid):
    p = preorders.search("id", pid); u = me(); v = vendor()
    if p and ((u and p["uid"] == u["id"]) or session.get("admin") or (v and v["floor"] == p["floor"] and v["key"] == p["counter"])): return p
    abort(404)

@app.route("/preorder/<int:pid>/bill")
def plan_bill_view(pid):
    o, rd = plan_receipt(plan_or_404(pid))
    return render_template("receipt.html", o=o, rd=rd, can_pdf=bool(pdfcanvas), pdf_url=f"/preorder/{pid}/bill.pdf")

@app.route("/preorder/<int:pid>/bill.pdf")
def plan_bill_pdf(pid):
    if not pdfcanvas: abort(501)
    o, rd = plan_receipt(plan_or_404(pid))
    global receipt_data
    keep = receipt_data; receipt_data = lambda _o: rd
    try: pdf = bill_pdf(o)
    finally: receipt_data = keep
    return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename=CafeFlow-plan-{pid}.pdf"})

@app.route("/admin/preorders")
def admin_preorders():
    aguard(); names = Names({u["id"]: u["name"] for u in users.traverse()})
    plans = [pre_view(p) for p in preorders.traverse()][::-1]
    act = [m for m in plans if m["p"]["status"] == "active"]
    kpi = {"plans": len(plans), "active": len(act), "booked": sum(m["p"]["total"] for m in plans if m["p"]["status"] != "cancelled"), "meals": sum(m["left"] for m in act)}
    return render_template("a_pre.html", plans=plans, kpi=kpi, names=names, page="pre")

@app.route("/preorder/create", methods=["POST"])
def preorder_create():
    u = me()
    if not u: return jsonify({"ok": False, "error": "Please log in."})
    f = request.get_json(silent=True) or {}; q = pre_quote(f); method = f.get("method")
    if not q.get("ok"): return jsonify(q)
    if method not in ("upi", "cod"): return jsonify({"ok": False, "error": "Choose how you will pay."})
    try: pickup = int(f.get("pickup"))
    except (TypeError, ValueError): pickup = 0
    if pickup not in range(DAY_START, DAY_END, STEP): return jsonify({"ok": False, "error": "Choose a pickup time."})
    p = {"id": nid("plan"), "uid": u["id"], "cname": u["name"], "floor": q["floor"], "counter": q["counter"], "lines": q["lines"], "plan": q["plan"], "pct": q["pct"], "days": q["days"], "released": [],
         "per_day": q["per_day"], "regular": q["regular"], "total": q["total"], "saved": q["saved"], "pickup": pickup, "method": method, "status": "active",
         "txn": f"PRE{random.randint(10**8, 10**9 - 1)}" if method == "upi" else "", "created": f"{datetime.now():%d %b %H:%M}"}
    preorders.insert(p); cn = cname(p["floor"], p["counter"])
    log(f"Pre-order plan #{p['id']} by {u['name']} at {cn}: {len(p['days'])} day(s), Rs {p['total']}")
    notify(f"v{p['floor']}-{p['counter']}", f"New pre-order plan #{p['id']}", f"{u['name']}: {len(p['days'])} meal day(s) from {p['days'][0]}, pickup {pretty_time(pickup)}, Rs {p['per_day']}/day", "booking")
    send_mail(u["email"], f"CafeFlow pre-order plan #{p['id']} confirmed", f"Hi {u['name']},\n\nYour {p['plan']['label']} meal plan at {cn} (Floor {p['floor']}) is confirmed.\nMeal days: {len(p['days'])} ({p['days'][0]} to {p['days'][-1]})\nPickup: {pretty_time(pickup)} each day\nPer day: Rs {p['per_day']} instead of Rs {p['regular']}\nTotal: Rs {p['total']} ({'paid by UPI' if method == 'upi' else 'pay cash at pickup'}). You save Rs {p['saved']}.\n\nCafeFlow")
    release_due(); save()
    return jsonify({"ok": True, "id": p["id"]})

@app.route("/preorder/<int:pid>/cancel", methods=["POST"])
def preorder_cancel(pid):
    u = me(); p = preorders.search("id", pid)
    if u and p and p["uid"] == u["id"] and p["status"] == "active":
        left = len([d for d in p["days"] if d not in p["released"]]); p["status"] = "cancelled"
        p["refund"] = left * p["per_day"] if p["method"] == "upi" else 0
        log(f"{u['name']} cancelled pre-order plan #{pid}"); notify(f"v{p['floor']}-{p['counter']}", f"Pre-order plan #{pid} cancelled", f"{u['name']} cancelled; {left} meal day(s) removed.", "info")
        save(); flash(f"Plan cancelled. {left} day(s) removed" + (f", Rs {p['refund']} will be refunded to your UPI." if p["refund"] else "."))
    return redirect("/preorder")

# ---------------- seat booking ----------------
def overlaps(b, fl, unit, d, start, dur): return b["floor"] == fl and b["unit"] == unit and b["date"] == d and start < b["start"] + b["dur"] and b["start"] < start + dur
def start_options(): return list(range(DAY_START, DAY_END, STEP))

@app.route("/reserve", methods=["GET", "POST"])
def reserve():
    u = me()
    if not u: return redirect("/")
    today = date.today()
    days = [(today + timedelta(d)) for d in range(7)]
    if request.method == "POST":
        f = request.form
        try: fl, unit, d, start, dur, guests = int(f["floor"]), f["unit"], f["date"], int(f["start"]), int(f["dur"]), int(f["guests"])
        except (KeyError, ValueError): return redirect("/reserve")
        un = UNIT_BY_ID.get(unit); back = f"/reserve?date={d}&start={start}&dur={dur}"
        if not un or fl not in FLOORS or d not in [x.isoformat() for x in days] or start not in start_options() or dur not in DURATIONS or not 1 <= guests <= un["seats"]:
            flash("Please check the booking details."); return redirect("/reserve")
        if datetime.fromisoformat(d) + timedelta(minutes=start) < datetime.now(): flash("That time has already passed. Pick a later time."); return redirect(back)
        if start + dur > DAY_END + 60: flash("The canteen closes at 9 pm. Pick a shorter stay."); return redirect(back)
        if any(overlaps(b, fl, unit, d, start, dur) for b in bookings.traverse()): flash(f"{unit} was just taken for that time. Pick another.")
        elif any(b["uid"] == u["id"] and b["date"] == d and start < b["start"] + b["dur"] and b["start"] < start + dur for b in bookings.traverse()): flash("You already have a seat booked in that time.")
        else:
            b = {"id": nid("book"), "uid": u["id"], "floor": fl, "unit": unit, "date": d, "start": start, "dur": dur, "guests": guests}
            bookings.insert(b)
            when = f"{datetime.fromisoformat(d):%a %d %b}, {pretty_time(start)} to {pretty_time(start + dur)}"
            log(f"{u['name']} reserved {unit}, Floor {fl}, {when}")
            notify("admin", f"New seat booking: {unit}, Floor {fl}", f"{u['name']} booked {unit} for {guests} guest(s) on {when}", "booking")
            send_mail(u["email"], "CafeFlow seat reserved", f"Hi {u['name']},\n\nYour seat {unit} ({un['kind']}, {guests} guest(s)) on Floor {fl} is reserved for {when}.\nPlease arrive on time; the seat is released 15 minutes after the start.\n\nCafeFlow")
            flash(f"{unit} on Floor {fl} reserved for {when}.")
        return redirect(back)
    d = request.args.get("date", today.isoformat()); d = d if d in [x.isoformat() for x in days] else today.isoformat()
    try: start, dur = int(request.args.get("start", 0)), int(request.args.get("dur", 60))
    except ValueError: start, dur = 0, 60
    now = datetime.now()
    if start not in start_options():                         # default: next half hour inside opening hours
        start = next((s for s in start_options() if datetime.fromisoformat(d) + timedelta(minutes=s) > now), DAY_START)
    dur = dur if dur in DURATIONS else 60
    fl = session.get("floor", 1)
    state = [None] * len(UNITS)                              # fixed ARRAY: index = unit number, value = who holds it in the chosen window
    for b in bookings.traverse():
        for i, un in enumerate(UNITS):
            if overlaps(b, fl, un["id"], d, start, dur): state[i] = b["uid"]
    seats = [{**un, "state": ("mine" if state[i] == u["id"] else "booked" if state[i] else "free")} for i, un in enumerate(UNITS)]
    mine = [b for b in bookings.traverse() if b["uid"] == u["id"]]
    mine, _ = merge_sort(mine, lambda b: (b["date"], b["start"]))
    past = lambda b: datetime.fromisoformat(b["date"]) + timedelta(minutes=b["start"]) < now
    return render_template("reserve.html", seats=seats, d=d, start=start, dur=dur, days=days, starts=start_options(), durs=DURATIONS, mine=mine, past=past,
                           n_free=sum(1 for s in seats if s["state"] == "free"), plan=photo("floorplan"))

@app.route("/reserve/cancel/<int:bid>")
def cancel(bid):
    u = me(); b = bookings.search("id", bid)
    if u and b and b["uid"] == u["id"]:
        bookings.delete("id", bid); log(f"{u['name']} cancelled {b['unit']}, Floor {b['floor']}, {b['date']} {hhmm(b['start'])}")
        notify("admin", f"Booking cancelled: {b['unit']}, Floor {b['floor']}", f"{u['name']} cancelled {b['date']} {pretty_time(b['start'])}", "booking"); flash("Booking cancelled.")
    return redirect("/reserve")
# ---------------- Phase 3 page: search and sort lab ----------------
@app.route("/linear")
def linear_lab():                                            # Phase 1 lab: animated linked list, stack and queue + the LIVE structures of this student
    u = me()
    if not u: return redirect("/")
    c = carts.get(u["id"]); cart_nodes = []
    if c:
        for l in c["items"].traverse():
            it = menu.search("id", l["iid"])
            if it: cart_nodes.append(f"{it['name']} x{l['qty']}")
    st = undo_stacks.get(u["id"]); undo = [menu.search("id", e["line"]["iid"])["name"] for e in st.items() if menu.search("id", e["line"]["iid"])] if st else []
    qs = []
    for k, q in queues.items():                              # every counter queue that currently holds this student's order
        row = [(o["id"], o["uid"] == u["id"]) for o in q.items()]
        if any(m for _, m in row): f, ck = k.split("-"); qs.append({"counter": cname(int(f), ck), "floor": int(f), "orders": [{"id": i, "mine": m} for i, m in row]})
    names = [i["name"] for i in fmenu(session.get("floor", 1))][:14]
    return render_template("linear.html", live={"cart": cart_nodes, "undo": undo, "queues": qs}, names=names, page="/linear")

@app.route("/algo")
def algo():
    if not me(): return redirect("/")
    ck = request.args.get("c", "kf")
    pool = [i for i in fmenu(session.get("floor", 1)) if ck == "all" or i["counter"] == ck]
    tag = lambda i: i["id"]
    ilog, mlog, llog, blog = [], [], [], []
    _, c_ins = insertion_sort(pool, sort_key("price"), log=ilog, tag=tag)
    _, c_mrg = merge_sort(pool, sort_key("price"), log=mlog, tag=tag)
    by_name, _ = merge_sort(pool, sort_key("name"))          # binary search needs the A to Z sorted array
    q = request.args.get("q", "").strip()
    if not q and pool: q = pool[(len(pool) * 2) // 3]["name"]
    li, lc = linear_search(pool, lambda i: i["name"].lower(), q.lower(), log=llog)
    bi, bc, _ = binary_search(by_name, lambda i: i["name"].lower(), q.lower(), log=blog)
    brief = lambda i: {"id": i["id"], "name": i["name"], "price": i["price"], "emoji": i["emoji"]}
    data = {"bars": [brief(i) for i in pool], "ins": ilog, "mrg": mlog,
            "lin": {"cells": [brief(i) for i in pool], "log": llog, "found": li}, "bin": {"cells": [brief(i) for i in by_name], "log": blog, "found": bi}}
    return render_template("algo.html", ck=ck, q=q, n=len(pool), data=data, c_ins=c_ins, c_mrg=c_mrg, lc=lc, bc=bc, li=li, bi=bi, names=[i["name"] for i in by_name])

# ---------------- birthday party planner: pre-book cakes, pastries, fries, chips and tables at a discount ----------------
PARTY_TIERS = [(4, 10), (10, 15), (20, 20)]                  # (guests from, % off): bigger parties save more
PARTY_EARLY = (3, 5)                                         # book 3+ days ahead: 5% extra
PARTY_MAX_PCT, PARTY_LEAD, PARTY_STAY = 25, 120, 120         # cap on the discount, minutes before the party the counters get the order, minutes of seating
PARTY_MIN_G, PARTY_MAX_G, PARTY_MAX_DAYS = 4, 30, 60
PARTY_SECTIONS = {("brew", "Pastries"), ("brew", "Desserts"), ("brew", "Snacks"), ("brew", "Tea and Coffee"), ("roll", "Burgers and Fries"), ("roll", "Rolls")}
PARTY_EXTRAS = [  # iid, counter, name, price, emoji, veg   (party specials, not on the daily menu)
    (9001, "brew", "Birthday Cake 500 g", 450, "🎂", 1), (9002, "brew", "Birthday Cake 1 kg", 800, "🎂", 1), (9003, "brew", "Cupcake Box (6)", 240, "🧁", 1),
    (9004, "brew", "Masala Chips Party Bowl", 90, "🥔", 1), (9005, "roll", "Fries Party Platter (serves 4)", 180, "🍟", 1)]
EXTRA_BY_ID = {e[0]: e for e in PARTY_EXTRAS}

def party_pct(guests, date_s):
    pct = max((p for g, p in PARTY_TIERS if guests >= g), default=0)
    early = (datetime.fromisoformat(date_s).date() - date.today()).days >= PARTY_EARLY[0]
    return min(PARTY_MAX_PCT, pct + (PARTY_EARLY[1] if early else 0)), early

def party_menu(fl):                                          # what can go on a party order on this floor
    out = {k: [] for k in ("brew", "roll")}
    for e in PARTY_EXTRAS: out[e[1]].append({"id": e[0], "name": e[2], "price": e[3], "emoji": e[4], "pic": None, "section": "Party specials", "special": True})
    for i in fmenu(fl):
        if (i["counter"], i["section"]) in PARTY_SECTIONS and i.get("avail", True):
            out[i["counter"]].append({"id": i["id"], "name": i["name"], "price": i["price"], "emoji": i["emoji"], "pic": photo(i["name"]), "section": i["section"], "special": False})
    return out

def party_when(p): return datetime.fromisoformat(p["date"]) + timedelta(minutes=p["time"])

def party_quote(f, fl):
    try:
        guests, d, tm = int(f["guests"]), str(f["date"]), int(f["time"]); star = str(f.get("star", "")).strip()[:30]; msg = str(f.get("msg", "")).strip()[:40]
        want = {int(k): max(0, min(int(v), 60)) for k, v in (f.get("items") or {}).items()}
        when = datetime.fromisoformat(d) + timedelta(minutes=tm)
    except (KeyError, ValueError, TypeError): return {"ok": False, "error": "Please fill in the guests, date and time."}
    if not star: return {"ok": False, "error": "Whose birthday is it? Add the birthday star's name."}
    if not PARTY_MIN_G <= guests <= PARTY_MAX_G: return {"ok": False, "error": f"Parties are for {PARTY_MIN_G} to {PARTY_MAX_G} guests."}
    if tm not in start_options() or tm + PARTY_STAY > DAY_END + 60: return {"ok": False, "error": "Choose a party time between 8 am and 7 pm."}
    day = datetime.fromisoformat(d).date()
    if day < date.today() + timedelta(days=1): return {"ok": False, "error": "Parties must be pre-booked at least one day ahead."}
    if day > date.today() + timedelta(days=PARTY_MAX_DAYS): return {"ok": False, "error": f"Book within {PARTY_MAX_DAYS} days."}
    pm, lines = party_menu(fl), []
    for k, its in pm.items():
        for it in its:
            q = want.get(it["id"], 0)
            if q: lines.append({"iid": it["id"], "name": it["name"], "emoji": it["emoji"], "price": it["price"], "qty": q, "sub": it["price"] * q, "counter": k})
    if not lines: return {"ok": False, "error": "Pick at least one treat for the party."}
    pct, early = party_pct(guests, d); by = {}
    for l in lines: by.setdefault(l["counter"], {"sub": 0})["sub"] += l["sub"]
    for k, c in by.items(): c["total"] = max(1, round(c["sub"] * (100 - pct) / 100))
    regular, total = sum(c["sub"] for c in by.values()), sum(c["total"] for c in by.values())
    sizes = [6] * (guests // 6) + ([guests % 6] if guests % 6 else [])
    plan, waste, nodes = seat_groups(sizes, free_units(fl, d, tm, PARTY_STAY))        # Phase 4 backtracking finds the tables
    if not plan: return {"ok": False, "error": "Not enough free tables at that time for your group. Try another time or a smaller group."}
    perks = ["🕯️ Birthday candles (free)", "✍️ Message on the cake (free)"] + (["🎈 Balloons and a Happy Birthday banner at your tables (free)"] if guests >= 10 else []) + (["🎉 Party poppers for everyone (free)"] if guests >= 20 else [])
    nxt = next(((g, p) for g, p in PARTY_TIERS if guests < g), None)
    return {"ok": True, "floor": fl, "star": star, "msg": msg, "guests": guests, "date": d, "time": tm, "lines": lines, "pct": pct, "early": early, "regular": regular, "total": total, "saved": regular - total, "by": by,
            "seats": plan, "waste": waste, "perks": perks, "next_tier": {"guests": nxt[0], "pct": nxt[1], "more": nxt[0] - guests} if nxt else None, "when": f"{when:%a %d %b}, {pretty_time(tm)}"}

@app.route("/api/party/quote", methods=["POST"])
def api_party_quote():
    if not me(): return jsonify({"ok": False, "error": "Please log in."})
    q = party_quote(request.get_json(silent=True) or {}, session.get("floor", 1))
    if q.get("ok"): q["qr"] = str(qr_svg(q["total"], "party") or "")
    return jsonify(q)

def party_perk_lines(p):                                     # zero-price lines so the counter sees what to prepare
    z = lambda name, emoji: {"iid": 0, "name": name, "emoji": emoji, "price": 0, "qty": 1, "sub": 0}
    out = [z("Birthday candles", "🕯️")]
    if p.get("msg"): out.append(z(f'Cake message: "{p["msg"]}"', "✍️"))
    if p["guests"] >= 10: out.append(z("Balloons + Happy Birthday banner for tables", "🎈"))
    if p["guests"] >= 20: out.append(z("Party poppers", "🎉"))
    return out

@app.route("/party/create", methods=["POST"])
def party_create():
    u = me()
    if not u: return jsonify({"ok": False, "error": "Please log in."})
    f = request.get_json(silent=True) or {}; fl = session.get("floor", 1); q = party_quote(f, fl); method = f.get("method")
    if not q.get("ok"): return jsonify(q)
    if method not in ("upi", "cod"): return jsonify({"ok": False, "error": "Choose how you will pay."})
    p = {"id": nid("party"), "uid": u["id"], "cname": u["name"], "floor": fl, "star": q["star"], "msg": q["msg"], "date": q["date"], "time": q["time"], "guests": q["guests"], "lines": q["lines"], "pct": q["pct"],
         "regular": q["regular"], "total": q["total"], "saved": q["saved"], "by": q["by"], "seats": q["seats"], "method": method, "txn": f"PTY{random.randint(10**8, 10**9 - 1)}" if method == "upi" else "",
         "status": "confirmed", "created": f"{datetime.now():%d %b %H:%M}", "ts": time.time()}
    parties.insert(p)
    for g, size, uid, seats in p["seats"]: bookings.insert({"id": nid("book"), "uid": u["id"], "floor": fl, "unit": uid, "date": p["date"], "start": p["time"], "dur": PARTY_STAY, "guests": size, "party": p["id"]})
    log(f"Birthday party #{p['id']} for {p['star']} by {u['name']}: {p['guests']} guests, {q['when']}, Rs {p['total']} ({p['pct']}% off)")
    for k in p["by"]: notify(f"v{fl}-{k}", f"Birthday party #{p['id']} booked", f"{p['star']}'s party, {q['when']}, {p['guests']} guests. Order reaches you {PARTY_LEAD // 60} h before.", "booking")
    notify("admin", f"New birthday party #{p['id']} (Floor {fl})", f"{u['name']} booked {p['star']}'s party for {p['guests']} guests, {q['when']}, Rs {p['total']}", "booking")
    send_mail(u["email"], f"CafeFlow: {p['star']}'s birthday party is booked!", f"Hi {u['name']},\n\n{p['star']}'s birthday party is booked at CafeFlow, Floor {fl}.\nWhen: {q['when']}\nGuests: {p['guests']}\nTables: {', '.join(x[2] for x in p['seats'])}\nTotal: Rs {p['total']} (you save Rs {p['saved']}, {p['pct']}% party discount) - {'paid by UPI' if method == 'upi' else 'pay cash when you collect'}.\n\nCafeFlow")
    save(); return jsonify({"ok": True, "id": p["id"]})

def release_parties():                                       # PARTY_LEAD minutes before the party, each counter gets its normal order
    made = 0
    for p in parties.traverse():
        if p["status"] != "confirmed" or party_when(p) - timedelta(minutes=PARTY_LEAD) > datetime.now(): continue
        u = users.search("id", p["uid"]); p["status"] = "sent"; first = "brew" if "brew" in p["by"] else sorted(p["by"])[0]
        for k, c in p["by"].items():
            lines = [{x: l[x] for x in ("iid", "name", "emoji", "price", "qty", "sub")} for l in p["lines"] if l["counter"] == k] + (party_perk_lines(p) if k == first else [])
            o = {"id": nid("order"), "uid": p["uid"], "cname": u["name"] if u else "Guest", "floor": p["floor"], "counter": k, "lines": lines, "total": c["total"],
                 "discounts": [{"label": f"Birthday party {p['pct']}% off", "amount": c["sub"] - c["total"], "items": [], "oid": f"party{p['id']}"}] if c["sub"] > c["total"] else [], "subtotal": c["sub"],
                 "status": "Pending", "time": f"{datetime.now():%d %b %H:%M}", "ts": time.time(), "pay": "Birthday party (" + PAY_LABELS[p["method"]] + ")", "method": p["method"],
                 "pay_status": "Pay on delivery" if p["method"] == "cod" else "Paid", "txn": p.get("txn", ""), "upi": "", "eta": None, "eta_end": None, "reason": "", "party": p["id"], "pickup": pretty_time(p["time"])}
            orders.insert(o); queues[f"{o['floor']}-{k}"].enqueue(o); made += 1
            notify(f"v{p['floor']}-{k}", f"🎂 Party order #{o['id']} for {pretty_time(p['time'])}", f"{p['star']}'s party, {p['guests']} guests. Prepare on time.", "order", o["id"])
        notify(f"u{p['uid']}", f"🎂 {p['star']}'s party order is with the counters", f"Pickup at {pretty_time(p['time'])}. We will alert you when each part is ready.", "accepted")
    if made: save()
    return made

def party_view(p):
    return {"p": p, "when": f"{party_when(p):%a %d %b}, {pretty_time(p['time'])}", "days": (party_when(p).date() - date.today()).days, "tables": ", ".join(x[2] for x in p["seats"]),
            "counters": ", ".join(cname(p["floor"], k) for k in p["by"]), "orders": [o for o in orders.traverse() if o.get("party") == p["id"]]}

@app.route("/party")
def party_page():
    u = me()
    if not u: return redirect("/")
    fl = session.get("floor", 1); tomorrow = date.today() + timedelta(days=1)
    mine = [party_view(p) for p in parties.traverse() if p["uid"] == u["id"]][::-1]
    return render_template("party.html", menus=party_menu(fl), tiers=PARTY_TIERS, early=PARTY_EARLY, maxpct=PARTY_MAX_PCT, gmin=PARTY_MIN_G, gmax=PARTY_MAX_G, lead=PARTY_LEAD, mine=mine, tomorrow=tomorrow.isoformat(),
                           maxd=(date.today() + timedelta(days=PARTY_MAX_DAYS)).isoformat(), starts=[s for s in start_options() if s + PARTY_STAY <= DAY_END + 60], upi_vpa=UPI_MERCHANT["vpa"], ok=request.args.get("ok"), star0=u["name"].split()[0])

def party_or_404(pid):
    p = parties.search("id", pid); u = me(); v = vendor()
    if p and ((u and p["uid"] == u["id"]) or session.get("admin") or (v and v["floor"] == p["floor"] and v["key"] in p["by"])): return p
    abort(404)

@app.route("/party/<int:pid>/cancel", methods=["POST"])
def party_cancel(pid):
    p = party_or_404(pid); u = me()
    if not u or p["uid"] != u["id"] or p["status"] != "confirmed": flash("This party can no longer be cancelled."); return redirect("/party")
    p["status"] = "cancelled"; p["refund"] = p["total"] if p["method"] == "upi" else 0
    for b in [b for b in bookings.traverse() if b.get("party") == pid]: bookings.delete("id", b["id"])
    log(f"{u['name']} cancelled birthday party #{pid}")
    for k in p["by"]: notify(f"v{p['floor']}-{k}", f"Party #{pid} cancelled", f"{p['star']}'s party on {p['date']} was cancelled.", "info")
    notify("admin", f"Party #{pid} cancelled", f"{u['name']} cancelled {p['star']}'s party" + (f" (refund Rs {p['refund']})" if p["refund"] else ""), "info")
    save(); flash("Party cancelled, tables released." + (f" Rs {p['refund']} will be refunded." if p["refund"] else "")); return redirect("/party")

def party_receipt(p):
    lines = [{x: l[x] for x in ("iid", "name", "emoji", "price", "qty", "sub")} for l in p["lines"]] + party_perk_lines(p)
    o = {"id": p["id"], "floor": p["floor"], "counter": sorted(p["by"])[0], "cname": p["cname"], "lines": lines, "total": p["total"], "subtotal": p["regular"], "ts": p.get("ts", time.time()),
         "discounts": [{"label": f"Birthday party ({p['pct']}% off)", "amount": p["saved"]}] if p["saved"] else [], "pay": "UPI" if p["method"] == "upi" else "Cash on pickup", "method": p["method"],
         "txn": p.get("txn", ""), "pay_status": "Paid" if p["method"] == "upi" else "Pay at pickup"}
    rd = receipt_data(o); rd["code"] = f"PT{p['id']:06d}"; rd["bars"], rd["bw"] = barcode_bars(rd["code"]); rd["order"] = f"PARTY-{p['id']}"; rd["counter"] = "Party order"
    rd["addr"] = [a for a in rd["addr"][:-0 or None] if not a.startswith("Floor")] + [f"Floor {p['floor']} - birthday party", f"{p['star']}'s party, {p['guests']} guests", f"{party_when(p):%d %b %Y}, {pretty_time(p['time'])}", "Tables: " + ", ".join(x[2] for x in p["seats"])]
    return o, rd

@app.route("/party/<int:pid>/bill")
def party_bill_view(pid):
    o, rd = party_receipt(party_or_404(pid))
    return render_template("receipt.html", o=o, rd=rd, can_pdf=bool(pdfcanvas), pdf_url=f"/party/{pid}/bill.pdf")

@app.route("/party/<int:pid>/bill.pdf")
def party_bill_pdf(pid):
    if not pdfcanvas: abort(501)
    o, rd = party_receipt(party_or_404(pid))
    global receipt_data
    keep = receipt_data; receipt_data = lambda _o: rd
    try: pdf = bill_pdf(o)
    finally: receipt_data = keep
    return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename=CafeFlow-party-{pid}.pdf"})

@app.route("/admin/parties")
def admin_parties():
    aguard(); names = Names({u["id"]: u["name"] for u in users.traverse()}); ps = [party_view(p) for p in parties.traverse()][::-1]; live = [m["p"] for m in ps if m["p"]["status"] in ("confirmed", "sent")]
    kpi = {"n": len(ps), "up": sum(1 for m in ps if m["p"]["status"] == "confirmed"), "guests": sum(p["guests"] for p in live), "value": sum(p["total"] for p in live), "saved": sum(p["saved"] for p in live)}
    return render_template("a_parties.html", ps=ps, kpi=kpi, names=names, page="parties", tiers=PARTY_TIERS, early=PARTY_EARLY, maxpct=PARTY_MAX_PCT)

@app.route("/vendor/parties")
def vendor_parties():
    v = vguard(); ps = []
    for p in parties.traverse():
        if p["floor"] == v["floor"] and v["key"] in p["by"] and p["status"] in ("confirmed", "sent"):
            m = party_view(p); m["mine"] = [l for l in p["lines"] if l["counter"] == v["key"]]; m["amount"] = p["by"][v["key"]]["total"]; ps.append(m)
    ps, _ = merge_sort(ps, lambda m: (m["p"]["date"], m["p"]["time"]))
    return render_template("v_parties.html", v=v, ps=ps, page="parties", lead=PARTY_LEAD)

# ---------------- built-in chatbot (free, no outside service) ----------------
def staff_stats(floor=None, key=None):                       # numbers the counter / admin assistant talks about
    ok = [o for o in orders.traverse() if not o.get("demo") and o["status"] != "Rejected" and (floor is None or (o["floor"] == floor and o["counter"] == key))]
    live = [o for o in orders.traverse() if not o.get("demo") and (floor is None or (o["floor"] == floor and o["counter"] == key))]
    td = [o for o in ok if datetime.fromtimestamp(o.get("ts", 0)).date() == date.today()]
    rs = [r for r in reviews.traverse() if floor is None or (r["floor"] == floor and r["counter"] == key)]
    last, _ = merge_sort([r for r in rs if r.get("text")], lambda r: r.get("ts", 0), True)
    sold = Counter()
    for o in ok:
        for l in o["lines"]: sold[l["name"]] += l["qty"]
    return {"pending": sum(o["status"] == "Pending" for o in live), "preparing": sum(o["status"] == "Accepted" for o in live), "ready": sum(o["status"] == "Ready" for o in live),
            "today_n": len(td), "today_rev": sum(o["total"] for o in td), "total_n": len(ok), "total_rev": sum(o["total"] for o in ok), "top": sold.most_common(6),
            "rating": avg_rating(rs), "nreviews": len(rs), "latest": last[0]["text"][:80] if last else ""}

@app.route("/api/chat", methods=["POST"])
def api_chat():
    u = me(); v = vendor(); text = str((request.get_json(silent=True) or {}).get("text", ""))
    if not u and not v and not session.get("admin"): return jsonify({"text": "Please log in to chat.", "items": [], "links": [], "chips": []}), 401
    if v:                                                    # counter assistant
        ctx = staff_stats(v["floor"], v["key"])
        ctx["soldout"] = [i["name"] for i in fmenu(v["floor"]) if i["counter"] == v["key"] and not i.get("avail", True)]
        ctx["parties"] = [{"star": p["star"], "when": f"{party_when(p):%d %b}, {pretty_time(p['time'])}", "guests": p["guests"]} for p in parties.traverse() if p["floor"] == v["floor"] and v["key"] in p["by"] and p["status"] == "confirmed"]
        return jsonify(staff_reply(text, "vendor", ctx))
    if not u:                                                # admin assistant
        ctx = staff_stats(); ctx["users_n"] = sum(1 for _ in users.traverse()); ctx["by_counter"], rows = {}, []
        for f in FLOORS:
            for k in COUNTERS:
                st = staff_stats(f, k); row = {"label": counter_label(f, k), "rev": st["total_rev"], "orders": st["total_n"], "pending": st["pending"], "rating": st["rating"], "reviews": st["nreviews"]}
                rows.append(row); ctx["by_counter"][cname(f, k).lower()] = row if cname(f, k).lower() not in ctx["by_counter"] else ctx["by_counter"][cname(f, k).lower()]
        ctx["counters"], _ = merge_sort(rows, lambda r: r["rev"], True)
        ctx["parties_n"] = sum(1 for p in parties.traverse() if p["status"] != "cancelled"); ctx["parties_up"] = sum(1 for p in parties.traverse() if p["status"] == "confirmed")
        return jsonify(staff_reply(text, "admin", ctx))
    fl = session.get("floor", 1)                             # student assistant
    items = [i for i in fmenu(fl) if i.get("avail", True)]
    sold = Counter()
    for k in COUNTERS:
        for name, qty in bestsellers(fl, k): sold[name] += qty
    best = sold.most_common(8)
    offs = []
    for o in offers.traverse():
        if o["active"] and o["floor"] == fl: ov = offer_view(o); offs.append(f"{ov['head']} at {ov['counter']}: {ov['sub']}")
    mine = [o for o in reversed(list(orders.traverse())) if o["uid"] == u["id"] and not o.get("demo")]
    ctx = {"ahead": {o["id"]: queue_ahead(o) for o in mine if o["status"] == "Pending"}, "items": items, "cname": lambda k: cname(fl, k), "orders": mine, "offers": offs, "sold": sold, "best": best, "floor": fl, "pure_veg": pure(fl)}
    return jsonify(bot_reply(text, ctx))

@app.route("/api/chat/add", methods=["POST"])
def api_chat_add():                                          # "Add" button inside the chat; same one-counter rule as the cart page
    u = me()
    if not u: return jsonify({"ok": False, "msg": "Please log in."}), 401
    try: iid = int((request.get_json(silent=True) or {}).get("iid"))
    except (TypeError, ValueError): return jsonify({"ok": False, "msg": "Unknown dish."})
    it = menu.search("id", iid)
    if not it: return jsonify({"ok": False, "msg": "Unknown dish."})
    if not it.get("avail", True): return jsonify({"ok": False, "msg": f"{it['name']} is sold out right now."})
    c = carts.get(u["id"])
    if c and (c["counter"] != it["counter"] or c["floor"] != it["floor"]): return jsonify({"ok": False, "msg": f"Your cart has items from {cname(c['floor'], c['counter'])}. Place that order or clear the cart first."})
    if not c: c = carts[u["id"]] = {"floor": it["floor"], "counter": it["counter"], "items": LinkedList()}
    line = c["items"].search("iid", it["id"])
    if line: line["qty"] = min(line["qty"] + 1, 20)
    else: c["items"].insert({"iid": it["id"], "qty": 1})
    save(); return jsonify({"ok": True, "msg": f"Added {it['name']} to your cart."})

# ---------------- Phase 4 pages: greedy, dynamic programming, backtracking ----------------
def popularity(floor, key):                                  # units sold per dish at one counter (used as the "value" of a dish)
    c = Counter()
    for o in orders.traverse():
        if o["floor"] == floor and o["counter"] == key and o["status"] != "Rejected":
            for l in o["lines"]: c[l["name"]] += l["qty"]
    return c

def free_units(fl, d, start, dur):                           # seating units nobody holds in that window
    return [(un["id"], un["seats"]) for un in UNITS if not any(overlaps(b, fl, un["id"], d, start, dur) for b in bookings.traverse())]

@app.route("/api/change")
def api_change():                                            # GREEDY: notes and coins to hand back
    try: total, paid = int(request.args.get("total", 0)), int(request.args.get("paid", 0))
    except ValueError: return jsonify({"error": "numbers only"}), 400
    if paid < total: return jsonify({"change": 0, "notes": [], "pieces": 0, "short": total - paid})
    notes, pieces = make_change(paid - total)
    return jsonify({"change": paid - total, "notes": notes, "pieces": pieces})

@app.route("/solve")
def solve():
    u = me()
    if not u: return redirect("/")
    fl, a = session.get("floor", 1), request.args
    # --- GREEDY: change maker ---
    try: bill, paid = int(a.get("bill", 137)), int(a.get("paid", 500))
    except ValueError: bill, paid = 137, 500
    notes, pieces = make_change(max(0, paid - bill))
    # --- DYNAMIC PROGRAMMING: budget meal planner ---
    ck = a.get("c", "kf") if a.get("c", "kf") in COUNTERS else "kf"
    try: budget = max(10, min(int(a.get("budget", 150)), 400))
    except ValueError: budget = 150
    pop = popularity(fl, ck)
    pool = [{**i, "value": 10 + 3 * pop.get(i["name"], 0) + (6 if len(i["name"]) % 3 == 0 else 0)} for i in fmenu(fl) if i["counter"] == ck and i.get("avail", True) and i["price"] <= budget]
    chosen, value, table = budget_knapsack(pool, budget)
    spent = sum(c["price"] for c in chosen)
    step = max(10, budget // 10)
    cols = list(range(0, budget + 1, step))
    show = pool[:8]                                          # first 8 dishes only, so the table fits on screen
    # --- BACKTRACKING: group seating ---
    today = date.today().isoformat()
    sizes = [int(x) for x in re.findall(r"\d+", a.get("groups", "4,3,6")) if 0 < int(x) <= 6][:5]
    d, start, dur = a.get("date", today), int(a.get("start", 0) or 0), int(a.get("dur", 60) or 60)
    if start not in start_options(): start = next((s for s in start_options() if datetime.fromisoformat(d) + timedelta(minutes=s) > datetime.now()), DAY_START)
    if dur not in DURATIONS: dur = 60
    free = free_units(fl, d, start, dur)
    plan, waste, nodes = seat_groups(sizes, free) if sizes else (None, 0, 0)
    return render_template("solve.html", bill=bill, paid=paid, notes=notes, pieces=pieces, ck=ck, budget=budget, pool_n=len(pool), chosen=chosen, value=value, spent=spent,
                           cols=cols, show=show, table=table, step=step, groups=", ".join(map(str, sizes)), d=d, start=start, dur=dur, starts=start_options(), durs=DURATIONS,
                           days=[(date.today() + timedelta(x)).isoformat() for x in range(7)], plan=plan, waste=waste, nodes=nodes, n_free=len(free), pretty_time=pretty_time)

@app.route("/solve/cart", methods=["POST"])
def solve_cart():                                            # put the planned meal into the real cart
    u = me()
    if not u: return redirect("/")
    ids = [int(x) for x in request.form.getlist("iid") if x.isdigit()]
    c = carts.get(u["id"]); n = 0
    for iid in ids:
        it = menu.search("id", iid)
        if not it or not it.get("avail", True): continue
        if c and (c["counter"] != it["counter"] or c["floor"] != it["floor"]): flash("Your cart has items from another counter. Place that order or clear the cart first."); return redirect("/cart")
        if not c: c = carts[u["id"]] = {"floor": it["floor"], "counter": it["counter"], "items": LinkedList()}
        if not c["items"].search("iid", iid): c["items"].insert({"iid": iid, "qty": 1}); n += 1
    save(); flash(f"{n} dish(es) from your budget plan added to the cart."); return redirect("/cart")

@app.route("/solve/seats", methods=["POST"])
def solve_seats():                                           # book the backtracking plan
    u = me()
    if not u: return redirect("/")
    f = request.form
    try: fl, d, start, dur = int(f["floor"]), f["date"], int(f["start"]), int(f["dur"]); sizes = [int(x) for x in f["groups"].split(",")]
    except (KeyError, ValueError): return redirect("/solve")
    back = f"/solve?groups={f['groups']}&date={d}&start={start}&dur={dur}"
    if fl not in FLOORS or start not in start_options() or dur not in DURATIONS or datetime.fromisoformat(d) + timedelta(minutes=start) < datetime.now() or start + dur > DAY_END + 60:
        flash("Please check the date and time."); return redirect(back)
    plan, waste, _ = seat_groups(sizes, free_units(fl, d, start, dur))      # re-solve on the server so nobody can book a taken seat
    if not plan: flash("No free seats can hold all those groups at that time."); return redirect(back)
    if any(b["uid"] == u["id"] and b["date"] == d and start < b["start"] + b["dur"] and b["start"] < start + dur for b in bookings.traverse()): flash("You already have a seat booked in that time."); return redirect(back)
    for g, size, uid, seats in plan: bookings.insert({"id": nid("book"), "uid": u["id"], "floor": fl, "unit": uid, "date": d, "start": start, "dur": dur, "guests": size})
    when = f"{datetime.fromisoformat(d):%a %d %b}, {pretty_time(start)} to {pretty_time(start + dur)}"
    log(f"{u['name']} group-booked {', '.join(p[2] for p in plan)} on Floor {fl}, {when}")
    notify("admin", "Group seat booking", f"{u['name']} booked {len(plan)} unit(s) on Floor {fl} for {when}", "booking"); save()
    flash(f"Booked {', '.join(p[2] for p in plan)} on Floor {fl} for {when}."); return redirect("/reserve")

PHASES = [
 (1, "Linear data structures", "CLO1", [("Linked list stores users, menu, carts, orders, bookings (insert, delete, search, traverse)", "ds.py / every page", "/home"),
   ("Stack: admin activity log and bill expression (balanced brackets + postfix)", "ds.py", "/cart"), ("Queue: one pending-order queue per counter; students see how many orders are ahead of them", "ds.py / vendor", "/linear#queue"), ("Animated Linear lab: linked list, stack and queue step by step", "templates/linear.html", "/linear"), ("Cart Undo = stack of removed dishes", "app.py cart_undo", "/cart")]),
 (2, "Trees and graphs", "CLO2", [("Binary search tree: dish search with the search path shown", "ds.py", "/search?q=tea"), ("In, pre and post order traversals", "ds.py", "/tree"),
   ("Graph: adjacency list and matrix of the canteen", "ds.py", "/map"), ("BFS (queue) and DFS (stack) routes", "ds.py", "/map")]),
 (3, "Searching and sorting", "CLO2", [("Linear and binary search, with comparison counts", "ds.py", "/algo"), ("Insertion sort and merge sort race", "ds.py", "/algo"),
   ("Sorting inside the workflow: menu sort, order reports, counter ranking", "app.py", "/counter/kf?sort=price")]),
 (4, "Greedy, DP and backtracking", "CLO3", [("Greedy: fewest notes and coins as change for cash orders", "algos.py", "/solve#greedy"), ("Dynamic programming: 0/1 knapsack budget meal planner, adds to cart", "algos.py", "/solve#dp"),
   ("Backtracking: seat several groups with least wasted seats, books the seats", "algos.py", "/solve#bt"), ("Counter end and admin end: queue, BST, graph, sorts, change, rush-hour DP, stove backtracking, combo DP, group seating", "app.py lab_data", "/admin/lab"), ("Backtracking inside the birthday party planner: finds tables for the whole group", "app.py party_quote", "/party"), ("Final testing: python tests.py checks every phase", "tests.py", "/phases")])]

@app.route("/phases")
def phases():
    if not me() and not guard(): return redirect("/")
    return render_template("phases.html", phases=PHASES)

# ---------------- Phase 2 pages ----------------
def tree_layout(root):                                       # x = inorder position, y = depth
    pos, i = {}, [0]
    def place(n, d):
        if n:
            place(n.left, d + 1); pos[n.key] = (50 + i[0] * 56, 46 + d * 86, d); i[0] += 1; place(n.right, d + 1)
    place(root, 0)
    nodes, edges = [], []
    def collect(n):
        if n:
            x, y, d = pos[n.key]
            nodes.append({"key": n.key, "label": n.data["name"], "emoji": n.data["emoji"], "x": x, "y": y, "d": d})
            for ch in (n.left, n.right):
                if ch: cx, cy, cd = pos[ch.key]; edges.append({"x1": x, "y1": y, "x2": cx, "y2": cy, "d": cd}); collect(ch)
    collect(root)
    xs, ys = [p[0] for p in pos.values()] + [100], [p[1] for p in pos.values()] + [50]
    return nodes, edges, max(xs) + 50, max(ys) + 62, (max(p[2] for p in pos.values()) + 1) if pos else 0

@app.route("/tree")
def tree():
    if not me(): return redirect("/")
    ck, shape, q = request.args.get("counter", "kf"), request.args.get("shape", "balanced"), request.args.get("q", "").strip().lower()
    items = [i for i in fmenu(session.get("floor", 1)) if ck == "all" or i["counter"] == ck]
    t = BST()
    if shape == "plain":                                     # insert in menu order: the tree can lean to one side
        for i in items: t.insert(i["name"].lower(), i)
    else:                                                    # insert the middle first so the tree stays short
        def build(a):
            if a: m = len(a) // 2; t.insert(a[m]["name"].lower(), a[m]); build(a[:m]); build(a[m + 1:])
        build(merge_sort(items, sort_key("name"))[0])
    found, path = t.search(q) if q else (None, [])
    nodes, edges, w, h, height = tree_layout(t.root)
    keys = lambda L: [i["name"].lower() for i in L]
    data = {"order": {"in": keys(t.inorder()), "pre": keys(t.preorder()), "post": keys(t.postorder())}, "path": path, "found": bool(found), "target": (q if found else ""),
            "names": {n["key"]: n["label"] for n in nodes}}
    return render_template("tree.html", ck=ck, shape=shape, q=q, found=found, path=path, nodes=nodes, edges=edges, w=w, h=h, height=height, n=len(nodes), data=data)

@app.route("/map")
def canteen_map():
    if not me(): return redirect("/")
    canteen, EDGES, POS, ICONS, N3 = CANTEENS[session.get("floor", 1)]
    start, goal = request.args.get("start", "Entrance"), request.args.get("goal", N3)
    if start not in canteen.adj or goal not in canteen.adj: start, goal = "Entrance", N3
    bsteps, bpath = canteen.bfs_trace(start, goal)
    dsteps, dpath = canteen.dfs_trace(start, goal)
    names, matrix = canteen.matrix()
    data = {"pos": POS, "edges": EDGES, "icons": ICONS, "start": start, "goal": goal,
            "bfs": {"steps": bsteps, "path": bpath}, "dfs": {"steps": dsteps, "path": dpath}}
    return render_template("map.html", places=names, matrix=matrix, adj=canteen.adj, start=start, goal=goal, data=data,
                           bpath=bpath or [], dpath=dpath or [], bn=len(bsteps), dn=len(dsteps))

# ---------------- admin: the main authority (sees both floors, every counter, every customer) ----------------
def guard(): return session.get("admin")
def aguard():
    if not guard(): abort(redirect("/"))

class Names(dict):
    def __missing__(self, k): return "Sample customer"

EARNED = ("Accepted", "Ready", "Collected")
def all_orders(): return list(orders.traverse())              # oldest first, so already sorted by order id
def in_window(lst, days): cut = time.time() - days * 86400 if days else 0; return [o for o in lst if o.get("ts", 0) >= cut]
def days_arg(default="30"): d = request.args.get("days", default); return int(d) if d in ("7", "30", "90") else 0
def avg_rating(rs): return round(sum(r["rating"] for r in rs) / len(rs), 1) if rs else 0
def counter_label(f, k): return f"{cname(f, k)} (F{f})"

def counter_table(lst):                                       # one row per floor-counter, ranked with merge sort (Phase 3)
    rows = []
    for f in FLOORS:
        for k in COUNTERS:
            mine = [o for o in lst if o["floor"] == f and o["counter"] == k]; ok = [o for o in mine if o["status"] in EARNED]; dec = [o for o in mine if o["status"] != "Pending"]
            rs = [r for r in reviews.traverse() if r["floor"] == f and r["counter"] == k]; preps = [o["eta"] for o in ok if o.get("eta")]
            rows.append({"floor": f, "key": k, "name": cname(f, k), "rev": sum(o["total"] for o in ok), "orders": len(ok), "aov": round(sum(o["total"] for o in ok) / len(ok)) if ok else 0,
                         "accept": round(100 * len([o for o in dec if o["status"] != "Rejected"]) / len(dec)) if dec else 0, "prep": round(sum(preps) / len(preps)) if preps else 0,
                         "rating": avg_rating(rs), "reviews": len(rs), "waiting": len(list(queues[f"{f}-{k}"].items())),
                         "saved": sum(d["amount"] for o in ok for d in o.get("discounts", []))})
    rows, _ = merge_sort(rows, lambda r: r["rev"], True); return rows

@app.route("/admin")
def admin():
    aguard(); days = days_arg(); lst = in_window(all_orders(), days); A = analytics(lst, days)
    table = counter_table(lst); ok = [o for o in lst if o["status"] in EARNED]
    per_floor = {f: {"rev": sum(o["total"] for o in ok if o["floor"] == f), "orders": sum(1 for o in ok if o["floor"] == f)} for f in FLOORS}
    rs = [r for r in reviews.traverse() if r.get("ts", 0) >= (time.time() - days * 86400 if days else 0)]
    buyers = Counter(o.get("cname") or o["uid"] for o in ok); real_users = list(users.traverse())
    extra = {"users": len(real_users), "bookings": len(list(bookings.traverse())), "rating": avg_rating(rs), "reviews": len(rs), "saved": sum(d["amount"] for o in ok for d in o.get("discounts", [])),
             "repeat_pct": round(100 * sum(1 for c in buyers.values() if c > 1) / len(buyers)) if buyers else 0, "offers": sum(1 for o in offers.traverse() if o["active"]),
             "waiting": sum(r["waiting"] for r in table)}
    return render_template("a_home.html", A=A, days=days, table=table, per_floor=per_floor, X=extra, has_demo=any(o.get("demo") for o in all_orders()), page="home",
                           by_counter={"labels": [counter_label(r["floor"], r["key"]) for r in table], "vals": [r["rev"] for r in table]},
                           by_floor={"labels": [f"Floor {f}" for f in FLOORS], "vals": [per_floor[f]["rev"] for f in FLOORS]})

@app.route("/admin/orders")
def admin_orders():
    aguard(); names = Names({u["id"]: u["name"] for u in users.traverse()}); allo = all_orders()
    fl, ck, st = request.args.get("floor", ""), request.args.get("counter", ""), request.args.get("status", "")
    rows = [o for o in allo if (not fl or str(o["floor"]) == fl) and (not ck or o["counter"] == ck) and (not st or o["status"] == st)]
    sort, report, rep_comps = request.args.get("sort", ""), rows[::-1], None
    if sort == "amount": report, rep_comps = merge_sort(rows, lambda o: o["total"], True)             # Phase 3: merge sort
    find, found = request.args.get("find", "").strip(), None
    if find.isdigit():                                       # Phase 3: binary search by order id, linear search for comparison
        li, lc = linear_search(allo, lambda o: o["id"], int(find)); bi, bc, bpath = binary_search(allo, lambda o: o["id"], int(find))
        found = {"id": int(find), "order": allo[bi] if bi >= 0 else None, "lc": lc, "bc": bc, "path": bpath, "n": len(allo)}
    waiting = [o for q in queues.values() for o in q.items()]
    prio, prio_comps = insertion_sort(waiting, lambda o: sum(l["qty"] for l in o["lines"]))           # Phase 3: insertion sort on the live list
    return render_template("a_orders.html", report=report[:150], total_rows=len(rows), sort=sort, rep_comps=rep_comps, find=find, found=found, prio=prio, prio_comps=prio_comps, names=names,
                           fl=fl, ck=ck, st=st, page="orders", qs={k: len(list(q.items())) for k, q in queues.items()})

@app.route("/admin/users")
def admin_users():
    aguard(); q = request.args.get("q", "").strip().lower(); allo = all_orders()
    stats = {}
    for o in allo:
        if o["status"] not in EARNED or not o["uid"]: continue
        s = stats.setdefault(o["uid"], {"orders": 0, "spend": 0, "last": "", "fav": Counter()}); s["orders"] += 1; s["spend"] += o["total"]; s["last"] = o["time"]; s["fav"][counter_label(o["floor"], o["counter"])] += 1
    rows = []
    for u in users.traverse():
        s = stats.get(u["id"]); rows.append({"id": u["id"], "name": u["name"], "email": u["email"], "orders": s["orders"] if s else 0, "spend": s["spend"] if s else 0,
                                           "last": s["last"] if s else "-", "fav": s["fav"].most_common(1)[0][0] if s else "-",
                                           "bookings": sum(1 for b in bookings.traverse() if b["uid"] == u["id"]), "reviews": sum(1 for r in reviews.traverse() if r["uid"] == u["id"])})
    by_name, _ = merge_sort(rows, lambda r: r["name"].lower())
    hit = None
    if q:                                                    # Phase 3: binary search on the A-Z sorted users (linear search for comparison)
        bi, bc, bpath = binary_search(by_name, lambda r: r["name"].lower(), q); li, lc = linear_search(by_name, lambda r: r["name"].lower(), q)
        hit = {"row": by_name[bi] if bi >= 0 else None, "bc": bc, "lc": lc, "path": bpath}
    sort = request.args.get("sort", "")
    shown = merge_sort(rows, lambda r: r["spend"], True)[0] if sort == "spend" else by_name
    return render_template("a_users.html", rows=shown, q=q, hit=hit, sort=sort, page="users")

@app.route("/admin/payments")
def admin_payments():
    aguard(); days = days_arg("0"); f = request.args
    rows = [o for o in in_window(all_orders(), days)[::-1] if (not f.get("method") or o.get("method") == f["method"]) and (not f.get("status") or o.get("pay_status", "Paid") == f["status"])
            and (not f.get("floor") or str(o["floor"]) == f["floor"]) and (not f.get("counter") or o["counter"] == f["counter"])]
    if f.get("csv"):
        out = io.StringIO(); w = csv.writer(out); w.writerow(["Order", "Date", "Floor", "Counter", "Customer", "Method", "Txn id", "Amount", "Discount", "Payment status", "Order status"])
        for o in rows: w.writerow([o["id"], o["time"], o["floor"], cname(o["floor"], o["counter"]), o.get("cname", ""), o["pay"], o.get("txn", ""), o["total"], sum(d["amount"] for d in o.get("discounts", [])), o.get("pay_status", "Paid"), o["status"]])
        return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=cafeflow-payments.csv"})
    allr = in_window(all_orders(), days); sm = lambda fn: sum(o["total"] for o in allr if fn(o))
    summary = {"online": sm(lambda o: o.get("pay_status") == "Paid"), "cash": sm(lambda o: o.get("pay_status") == "Cash collected"), "due": sm(lambda o: o.get("pay_status") == "Pay on delivery" and o["status"] != "Rejected"),
               "refund": sm(lambda o: o.get("pay_status") == "Refund initiated"), "disc": sum(d["amount"] for o in allr if o["status"] in EARNED for d in o.get("discounts", []))}
    A = analytics(allr, days)
    return render_template("a_pay.html", rows=rows[:200], n=len(rows), summary=summary, A=A, days=days, f=f, page="pay", statuses=["Paid", "Pay on delivery", "Cash collected", "Refund initiated"])

@app.route("/admin/behaviour")
def admin_behaviour():
    aguard(); days = days_arg("90"); lst = in_window(all_orders(), days); ok = [o for o in lst if o["status"] in EARNED]
    cust = {}
    for o in ok:
        c = cust.setdefault(o.get("cname") or f"user{o['uid']}", {"name": o.get("cname") or f"user{o['uid']}", "orders": 0, "spend": 0, "items": 0, "last": "", "fav": Counter(), "dish": Counter()})
        c["orders"] += 1; c["spend"] += o["total"]; c["items"] += sum(l["qty"] for l in o["lines"]); c["last"] = o["time"]; c["fav"][counter_label(o["floor"], o["counter"])] += 1
        for l in o["lines"]: c["dish"][l["name"]] += l["qty"]
    rows = [{**c, "fav": c["fav"].most_common(1)[0][0], "dish": c["dish"].most_common(1)[0][0], "aov": round(c["spend"] / c["orders"])} for c in cust.values()]
    top, _ = merge_sort(rows, lambda r: r["spend"], True)
    seg = {"New (1 order)": sum(1 for r in rows if r["orders"] == 1), "Regular (2-4)": sum(1 for r in rows if 2 <= r["orders"] <= 4), "Loyal (5+)": sum(1 for r in rows if r["orders"] >= 5)}
    dow = Counter(); heat = [[0] * 15 for _ in range(7)]
    for o in ok:
        t = datetime.fromtimestamp(o["ts"]); dow[t.weekday()] += 1
        if 7 <= t.hour < 22: heat[t.weekday()][t.hour - 7] += 1
    hmax = max([max(r) for r in heat] + [1])
    basket = Counter(min(sum(l["qty"] for l in o["lines"]), 6) for o in ok)
    pref_c = Counter(); pref_p = Counter()
    for o in ok: pref_c[counter_label(o["floor"], o["counter"])] += o["total"]; pref_p[o["pay"]] += 1
    bk = list(bookings.traverse()); bhour = Counter(b["start"] // 60 for b in bk); btype = Counter("Sofa" if b["unit"].startswith("S") else "Table" for b in bk)
    rs = [r for r in reviews.traverse()]; tags = Counter(t for r in rs for t in r.get("tags", []))
    return render_template("a_behaviour.html", days=days, top=top[:10], seg=seg, n_cust=len(rows), repeat=round(100 * sum(1 for r in rows if r["orders"] > 1) / len(rows)) if rows else 0,
        avg_spend=round(sum(r["spend"] for r in rows) / len(rows)) if rows else 0, avg_items=round(sum(o_["items"] for o_ in rows) / max(1, sum(o_["orders"] for o_ in rows)), 1) if rows else 0,
        dow={"labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "vals": [dow[i] for i in range(7)]}, heat=heat, hmax=hmax, hours=[f"{h % 12 or 12}{'a' if h < 12 else 'p'}" for h in range(7, 22)],
        basket={"labels": [str(k) if k < 6 else "6+" for k in range(1, 7)], "vals": [basket[k] for k in range(1, 7)]}, pref_c={"labels": list(pref_c), "vals": list(pref_c.values())},
        pref_p={"labels": list(pref_p), "vals": list(pref_p.values())}, bk_hour={"labels": [f"{h % 12 or 12}{'a' if h < 12 else 'p'}" for h in range(8, 21)], "vals": [bhour[h] for h in range(8, 21)]},
        bk_type={"labels": list(btype), "vals": list(btype.values())}, tags={"labels": [t for t, _ in tags.most_common(6)], "vals": [c for _, c in tags.most_common(6)]}, page="behaviour")

@app.route("/admin/reviews")
def admin_reviews():
    aguard(); f = request.args; sort = f.get("sort", "new")
    rs = [r for r in reviews.traverse() if (not f.get("counter") or f"{r['floor']}-{r['counter']}" == f["counter"]) and (not f.get("stars") or str(r["rating"]) == f["stars"])]
    rs, comps = merge_sort(rs, (lambda r: (r["rating"], r["ts"])) if sort == "high" else (lambda r: (-r["rating"], -r["ts"])) if sort == "low" else (lambda r: r["ts"]), sort != "low")
    allr = list(reviews.traverse()); dist = Counter(r["rating"] for r in allr)
    per = []
    for fl in FLOORS:
        for k in COUNTERS:
            mine = [r for r in allr if r["floor"] == fl and r["counter"] == k]; per.append({"label": counter_label(fl, k), "avg": avg_rating(mine), "n": len(mine), "key": f"{fl}-{k}"})
    return render_template("a_reviews.html", wall=wall_reviews(None, None, 24), rs=rs[:60], n=len(rs), sort=sort, comps=comps, f=f, avg=avg_rating(allr), total=len(allr), dist=[dist[i] for i in (5, 4, 3, 2, 1)], per=per, page="reviews")

BASKET_ITEMS = lambda: {k: sorted({i["name"] for i in menu.traverse() if i["counter"] == k}) for k in COUNTERS}

@app.route("/admin/basket")
def admin_basket():
    aguard(); f = request.args
    fl, ck = f.get("floor", "0"), f.get("counter", "all")
    try: sup, conf = float(f.get("sup", 5)), float(f.get("conf", 30))
    except ValueError: sup, conf = 5.0, 30.0
    tx = [set(l["name"] for l in o["lines"]) for o in all_orders() if o["status"] in EARNED and (fl == "0" or str(o["floor"]) == fl) and (ck == "all" or o["counter"] == ck)]
    R = apriori(tx, sup / 100, conf / 100)
    where = {}                                               # dish name -> counter key, so a rule can become an offer in one click
    for i in menu.traverse(): where.setdefault(i["name"], i["counter"])
    rules = [{**r, "key": where.get(r["ante"][0]), "label": " + ".join(r["ante"]) + "  →  " + " + ".join(r["cons"])} for r in R["rules"][:40]]
    multi = sorted([(k, c) for k, c in R["freq"].items() if len(k) >= 2], key=lambda kc: -kc[1])[:15]
    singles = sorted([k[0] for k in R["freq"] if len(k) == 1], key=str.lower)
    dish, lookup = f.get("dish", "").strip(), None
    if dish:                                                 # Phase 3: binary search in the sorted frequent dishes
        bi, bc, bpath = binary_search(singles, lambda s: s.lower(), dish.lower())
        lookup = {"name": singles[bi] if bi >= 0 else None, "bc": bc, "path": bpath, "n": len(singles), "rules": [r for r in R["rules"] if bi >= 0 and singles[bi] in r["ante"]][:6]}
    return render_template("a_basket.html", R=R, rules=rules, multi=multi, f=f, fl=fl, ck=ck, sup=sup, conf=conf, dish=dish, lookup=lookup, ntx=len(tx), singles=singles,
        avg_size=round(sum(len(t) for t in tx) / len(tx), 2) if tx else 0, steps=R["steps"], page="basket",
        pairs={"labels": [" + ".join(k) for k, c in multi[:8]], "vals": [c for k, c in multi[:8]]})

# ---- offers: the admin picks dishes and chooses discount / combo / buy-one-get-one / most bought ----
def offer_sales():                                           # how often each offer was used and how much it saved
    use = {}
    for o in orders.traverse():
        if o["status"] not in EARNED: continue
        for d in o.get("discounts", []): u = use.setdefault(d["oid"], {"n": 0, "saved": 0}); u["n"] += 1; u["saved"] += d["amount"]
    return use

@app.route("/admin/offers")
def admin_offers():
    aguard(); allo = all_orders(); top = {}
    for k in COUNTERS:
        c = Counter()
        for o in allo:
            if o["counter"] == k and o["status"] in EARNED:
                for l in o["lines"]: c[l["name"]] += l["qty"]
        top[k] = [n for n, _ in c.most_common(5)]
    menus = {k: [{"name": n, "price": next(i["price"] for i in menu.traverse() if i["counter"] == k and i["name"] == n), "pic": photo(n)} for n in BASKET_ITEMS()[k]] for k in COUNTERS}
    use = offer_sales()
    ls = [{"o": o, "view": offer_view(o), "use": use.get(o["id"], {"n": 0, "saved": 0}), "cname": cname(o["floor"], o["counter"])} for o in offers.traverse()][::-1]
    pre = {"type": request.args.get("type", "discount"), "counter": request.args.get("counter", "kf"), "names": [n for n in request.args.get("names", "").split("|") if n], "price": request.args.get("price", "")}
    return render_template("a_offers.html", ls=ls, menus=menus, top=top, pre=pre, kinds=OFFER_KINDS_UI, page="offers", names_by=counters_names())

OFFER_KINDS_UI = [("discount", "Discount", "% off chosen dishes"), ("combo", "Combo offer", "Dishes together at one price"), ("bogo", "Buy 1 Get 1", "Buy one, get one free"), ("popular", "Most bought", "Highlight crowd favourites")]
def counters_names(): return {k: [cname(f, k) + f" (F{f})" for f in FLOORS] for k in COUNTERS}

@app.route("/admin/offers/add", methods=["POST"])
def admin_offer_add():
    aguard(); f = request.form; typ, ck, scope = f.get("type"), f.get("counter"), f.get("scope", "both")
    names = f.getlist("names"); floors_ = FLOORS if scope == "both" else [int(scope)] if scope in ("1", "2") else []
    pct, price = int(f.get("pct") or 0), int(f.get("price") or 0)
    if typ not in [k for k, _, _ in OFFER_KINDS_UI] or ck not in COUNTERS or not floors_ or not names: flash("Pick an offer type, a counter and at least one dish."); return redirect("/admin/offers")
    if typ == "discount" and not 1 <= pct <= 90: flash("Discount must be between 1 and 90 percent."); return redirect("/admin/offers")
    if typ == "combo" and (len(names) < 2 or price < 1): flash("A combo needs at least two dishes and a combo price."); return redirect("/admin/offers")
    made = 0
    for fl in floors_:
        ids = [i["id"] for n in names for i in menu.traverse() if i["floor"] == fl and i["counter"] == ck and i["name"] == n][:12]
        if not ids: continue
        title = f.get("title", "").strip() or {"discount": f"{pct}% off", "combo": "Combo deal", "bogo": "Buy 1 Get 1", "popular": "Crowd favourites"}[typ]
        offers.insert({"id": nid("offer"), "type": typ, "title": title, "items": ids, "pct": pct, "price": price, "floor": fl, "counter": ck, "active": True, "ad": True, "created": f"{datetime.now():%d %b %H:%M}"}); made += 1
    log(f"Admin created {typ} offer '{f.get('title', '')}' on {made} floor(s)"); save(); flash(f"Offer is live on {made} floor(s). Students now see it as an ad and on the counter page."); return redirect("/admin/offers")

@app.route("/admin/offers/<int:oid>/<action>", methods=["POST"])
def admin_offer_action(oid, action):
    aguard(); o = offers.search("id", oid)
    if o and action == "toggle": o["active"] = not o["active"]; save()
    elif o and action == "delete": offers.delete("id", oid); log(f"Admin removed offer '{o['title']}'"); save()
    return redirect("/admin/offers")

@app.route("/admin/authority")
def admin_authority():
    aguard(); bk, _ = merge_sort(list(bookings.traverse()), lambda b: (b["date"], b["start"]))
    names = Names({u["id"]: u["name"] for u in users.traverse()})
    return render_template("a_auth.html", bookings=bk, names=names, items=list(menu.traverse()), vendors=VENDOR_LOGINS, log=list(history.items())[:60], page="auth",
                           counts={"users": len(list(users.traverse())), "menu": len(list(menu.traverse())), "orders": len(all_orders()), "offers": len(list(offers.traverse())), "reviews": len(list(reviews.traverse())), "notices": len(list(notices.traverse()))})

@app.route("/admin/menu/add", methods=["POST"])
def add_item():
    if guard():
        f = request.form; fl, ck, sec = f["place"].split("|")
        menu.insert({"id": nid("item"), "floor": int(fl), "counter": ck, "section": sec, "name": f["name"].strip(), "price": int(f["price"]), "emoji": "🍽️", "veg": pure(int(fl)) or f.get("veg", "1") == "1", "avail": True})
        rebuild_bst(); log(f"Menu item added: {f['name']}")
    return redirect("/admin/authority")

@app.route("/admin/menu/delete/<int:iid>")
def del_item(iid):
    if guard() and menu.delete("id", iid): rebuild_bst(); log(f"Menu item #{iid} removed")
    return redirect("/admin/authority")

@app.route("/admin/booking/cancel/<int:bid>")
def admin_cancel(bid):
    if guard() and bookings.delete("id", bid): log(f"Admin cancelled booking #{bid}")
    return redirect("/admin/authority")

@app.route("/admin/demo/<action>", methods=["POST"])
def admin_demo(action):
    aguard()
    if action == "clear": clear_demo(); save(); flash("Sample data removed from every counter.")
    else:
        for f in FLOORS:
            for k in COUNTERS: gen_demo(f, k)
        save(); flash("Sample sales and reviews for 30 days loaded into all six counters.")
    return redirect(safe(request.form.get("back", "/admin"), "/admin"))

# ---------------- counter (vendor) site ----------------
def vguard():
    v = vendor()
    if not v: abort(redirect("/"))
    return v

def my_orders_of(v, include_demo=True): return [o for o in orders.traverse() if o["floor"] == v["floor"] and o["counter"] == v["key"] and (include_demo or not o.get("demo"))]
def customer_email(o): u = users.search("id", o["uid"]); return u["email"] if u else None

@app.route("/vendor")
def vendor_orders():
    v = vguard(); mine = my_orders_of(v)
    q = queues[f"{v['floor']}-{v['key']}"]
    pending = list(q.items())
    cooking = [o for o in mine if o["status"] == "Accepted"]
    done = [o for o in mine if o["status"] in ("Ready", "Collected", "Rejected")][::-1][:30]
    return render_template("v_orders.html", v=v, pending=pending, cooking=cooking, done=done, now=time.time(), page="orders")

@app.route("/vendor/order/<int:oid>/<action>", methods=["POST"])
def vendor_action(oid, action):
    v = vguard(); o = orders.search("id", oid)
    if not o or o["floor"] != v["floor"] or o["counter"] != v["key"]: abort(404)
    q = queues[f"{v['floor']}-{v['key']}"]; cn = v["name"]; email = customer_email(o); f = request.form
    if action in ("accept", "decline") and o["status"] == "Pending":
        front = q.peek()
        if not front or front["id"] != oid: flash("Orders are served first come, first served. Handle the oldest order first."); return redirect("/vendor")
        q.dequeue()
        if action == "accept":
            mins = max(1, min(int(f.get("minutes") or 10), 120))
            o.update(status="Accepted", eta=mins, eta_end=time.time() + mins * 60, accepted_ts=time.time())
            notify(f"u{o['uid']}", f"Order #{oid} accepted", f"{cn} is cooking your order. Ready in about {mins} min.", "accepted", oid)
            if email: send_mail(email, f"CafeFlow order #{oid} accepted", f"{cn} accepted your order #{oid}. It will be ready in about {mins} minutes.")
        else:
            reason = f.get("reason", "").strip() or "The counter cannot prepare this order right now."
            o.update(status="Rejected", reason=reason)
            if o.get("method") != "cod" and o.get("pay_status") == "Paid": o["pay_status"] = "Refund initiated"
            notify(f"u{o['uid']}", f"Order #{oid} declined", f"{cn}: {reason}" + (" Your money will be refunded." if o["pay_status"] == "Refund initiated" else ""), "rejected", oid)
            if email: send_mail(email, f"CafeFlow order #{oid} declined", f"Sorry, {cn} declined your order #{oid}: {reason}" + (" Your payment will be refunded." if o["pay_status"] == "Refund initiated" else ""))
        log(f"Order #{oid} {o['status'].lower()} by {cn}")
    elif action == "ready" and o["status"] == "Accepted":
        o.update(status="Ready", ready_ts=time.time())
        notify(f"u{o['uid']}", f"Order #{oid} is ready!", f"Your dish is ready. Please collect it from {cn}, Floor {o['floor']}.", "ready", oid)
        if email: send_mail(email, f"Your CafeFlow order #{oid} is ready", f"Your dish is ready! Please collect order #{oid} from {cn}, Floor {o['floor']}.")
        log(f"Order #{oid} ready at {cn}")
    elif action == "collected" and o["status"] == "Ready":
        o["status"] = "Collected"
        if o.get("pay_status") == "Pay on delivery": o["pay_status"] = "Cash collected"
        log(f"Order #{oid} collected")
    save(); return redirect("/vendor")

@app.route("/vendor/menu", methods=["GET", "POST"])
def vendor_menu():
    v = vguard()
    if request.method == "POST":
        f = request.form; name = f["name"].strip(); sec = f["section"]
        if name and sec in v["c"]["sections"] and f["price"].isdigit() and int(f["price"]) > 0:
            menu.insert({"id": nid("item"), "floor": v["floor"], "counter": v["key"], "section": sec, "name": name, "price": int(f["price"]), "emoji": "🍽️", "veg": pure(v["floor"]) or f.get("veg", "1") == "1", "avail": True})
            img = request.files.get("photo")
            if img and img.filename and os.path.splitext(img.filename)[1].lower() in (".jpg", ".jpeg", ".png", ".webp"):
                img.save(os.path.join(app.static_folder, "img", slug(name) + os.path.splitext(img.filename)[1].lower()))
            rebuild_bst(); log(f"{v['name']} added menu item: {name}"); flash(f"{name} added to your menu.")
        else: flash("Enter a name, a section and a price.")
        return redirect("/vendor/menu")
    items = [i for i in fmenu(v["floor"]) if i["counter"] == v["key"]]
    return render_template("v_menu.html", v=v, items=items, page="menu")

@app.route("/vendor/menu/<int:iid>/<action>", methods=["POST"])
def vendor_menu_action(iid, action):
    v = vguard(); it = menu.search("id", iid)
    if it and it["floor"] == v["floor"] and it["counter"] == v["key"]:
        if action == "remove": menu.delete("id", iid); rebuild_bst(); log(f"{v['name']} removed {it['name']}"); flash(f"{it['name']} removed.")
        elif action == "toggle": it["avail"] = not it.get("avail", True); save(); flash(f"{it['name']} marked {'available' if it['avail'] else 'sold out'}.")
        elif action == "price" and request.form.get("price", "").isdigit() and int(request.form["price"]) > 0: it["price"] = int(request.form["price"]); save(); flash(f"{it['name']} now costs Rs {it['price']}.")
    return redirect("/vendor/menu")

def analytics(lst, days):
    now = datetime.now()
    cut = time.time() - days * 86400 if days else 0
    inw = [o for o in lst if o.get("ts", 0) >= cut]
    earned = lambda L: [o for o in L if o["status"] in ("Accepted", "Ready", "Collected")]
    ok = earned(inw); rev = sum(o["total"] for o in ok)
    prev = earned([o for o in lst if cut - days * 86400 <= o.get("ts", 0) < cut]) if days else []
    prev_rev = sum(o["total"] for o in prev)
    decided = [o for o in inw if o["status"] != "Pending"]
    span = days or min(90, max(7, int((time.time() - min([o.get("ts", time.time()) for o in lst] or [time.time()])) / 86400) + 1))
    labels = [(now - timedelta(days=span - 1 - i)).date() for i in range(span)]
    by_day = Counter(); orders_by_day = Counter()
    for o in ok: d = datetime.fromtimestamp(o["ts"]).date(); by_day[d] += o["total"]; orders_by_day[d] += 1
    hours = Counter(datetime.fromtimestamp(o["ts"]).hour for o in ok)
    dishes, rev_dish, sections = Counter(), Counter(), Counter()
    for o in ok:
        for l in o["lines"]:
            dishes[l["name"]] += l["qty"]; rev_dish[l["name"]] += l["sub"]
            it = menu.search("id", l["iid"]); sections[it["section"] if it else "Other"] += l["sub"]
    methods = Counter(); status = Counter(o["status"] for o in inw)
    for o in ok: methods[o["pay"]] += o["total"]
    custs = Counter(o.get("cname") or o["uid"] for o in ok)
    top = dishes.most_common(8); peak = max(hours, key=hours.get) if hours else None
    preps = [o["eta"] for o in ok if o.get("eta")]
    return {"kpi": {"rev": rev, "orders": len(ok), "aov": round(rev / len(ok)) if ok else 0, "delta": round((rev - prev_rev) * 100 / prev_rev) if prev_rev else None,
                    "accept": round(100 * len([o for o in decided if o["status"] != "Rejected"]) / len(decided)) if decided else 0, "prep": round(sum(preps) / len(preps)) if preps else 0,
                    "repeat": sum(1 for c in custs.values() if c > 1), "customers": len(custs), "peak": f"{peak % 12 or 12} {'AM' if peak < 12 else 'PM'}" if peak is not None else "-",
                    "pending": len([o for o in lst if o["status"] == "Pending"])},
            "daily": {"labels": [f"{d:%d %b}" for d in labels], "rev": [by_day[d] for d in labels], "orders": [orders_by_day[d] for d in labels]},
            "hourly": {"labels": [f"{h % 12 or 12}{'a' if h < 12 else 'p'}" for h in range(7, 22)], "vals": [hours[h] for h in range(7, 22)]},
            "top": {"labels": [d for d, _ in top], "qty": [q for _, q in top], "rev": [rev_dish[d] for d, _ in top]},
            "sections": {"labels": list(sections), "vals": list(sections.values())},
            "methods": {"labels": list(methods), "vals": list(methods.values())},
            "status": {"labels": list(status), "vals": list(status.values())}}

@app.route("/vendor/preorders")
def vendor_preorders():                                      # what is pre-booked, so the counter can prepare in advance
    v = vguard(); plans = [p for p in preorders.traverse() if p["floor"] == v["floor"] and p["counter"] == v["key"] and p["status"] == "active"]
    days = []
    for i in range(14):
        d = (date.today() + timedelta(days=i)).isoformat(); rows, dishes = [], Counter()
        for p in plans:
            if d in p["days"]:
                rows.append({"cname": p["cname"], "pickup": p["pickup"], "items": ", ".join(f"{l['qty']} x {l['name']}" for l in p["lines"]), "done": d in p["released"], "method": p["method"], "per_day": p["per_day"]})
                for l in p["lines"]: dishes[l["name"]] += l["qty"]
        if rows: days.append({"date": d, "label": f"{date.fromisoformat(d):%a %d %b}", "rows": sorted(rows, key=lambda r: r["pickup"]), "dishes": dishes.most_common(), "n": len(rows), "today": i == 0})
    return render_template("v_pre.html", v=v, days=days, plans=plans, page="pre", revenue=sum(p["total"] for p in plans), lead=PRE_LEAD)

# ---------------- algorithm labs: all four phases at the counter end and the admin end ----------------
def prep_min(o): return 1 + 2 * sum(l["qty"] for l in o["lines"])            # cooking minutes: 1 + 2 per item

def lab_data(role, fl, ck):
    a = request.args; L = {"role": role, "fl": fl, "ck": ck}
    pool_o = [o for o in orders.traverse() if o["floor"] == fl and (ck == "all" or o["counter"] == ck) and o["status"] != "Rejected"] if role == "vendor" else [o for o in orders.traverse() if o["status"] != "Rejected"]
    # PHASE 1: queue + stack + linked list
    L["queues"] = [(f, k, cname(f, k), queues[f"{f}-{k}"].size() if hasattr(queues[f"{f}-{k}"], "size") else len(list(queues[f"{f}-{k}"].items()))) for f in FLOORS for k in COUNTERS if (role == "admin" or (f == fl and k == ck))]
    L["front"] = [(o["id"], o["cname"], len(o["lines"])) for o in list(queues[f"{fl}-{ck}"].items())[:6]] if role == "vendor" else []
    L["stack"] = list(history.items())[:6] if role == "admin" else []
    L["list_n"] = len(pool_o)
    # PHASE 2: BST of the menu + graph route
    items = [i for i in fmenu(fl) if ck == "all" or i["counter"] == ck]
    t = BST()
    def build(arr):
        if arr: m = len(arr) // 2; t.insert(arr[m]["name"].lower(), arr[m]); build(arr[:m]); build(arr[m + 1:])
    build(merge_sort(items, sort_key("name"))[0])
    q = a.get("q", "").strip().lower(); found, path = t.search(q) if q else (None, [])
    nm = lambda L_: [i["name"] for i in L_]
    L.update(q=q, found=found, path=path, n_menu=len(items), tin=nm(t.inorder()), tpre=nm(t.preorder()), tpost=nm(t.postorder()))
    canteen = CANTEENS[fl][0]; goals = [n for n in canteen.adj if n != "Entrance"]
    goal = a.get("goal") if a.get("goal") in canteen.adj else (cname(fl, ck) if role == "vendor" else goals[2])
    bs, bp = canteen.bfs_trace("Entrance", goal); ds_, dp = canteen.dfs_trace("Entrance", goal)
    L.update(goals=goals, goal=goal, bfs=len(bs), bpath=bp or [], dfs=len(ds_), dpath=dp or [])
    # PHASE 3: sorting and searching on real orders
    srt, c_m = merge_sort(pool_o, lambda o: o["total"], True); _, c_i = insertion_sort(pool_o, lambda o: o["total"], True)
    byid = sorted(pool_o, key=lambda o: o["id"]); fid = int(a["oid"]) if a.get("oid", "").isdigit() else (byid[len(byid) * 2 // 3]["id"] if byid else 0)
    li, lc = linear_search(byid, lambda o: o["id"], fid); bi, bc, bpth = binary_search(byid, lambda o: o["id"], fid)
    L.update(top=srt[:5], c_m=c_m, c_i=c_i, n_o=len(pool_o), fid=fid, lc=lc, bc=bc, bhit=(byid[bi] if bi >= 0 else None), bpth=bpth)
    # PHASE 4a GREEDY: change
    try: bill, paid = int(a.get("bill", 137)), int(a.get("paid", 500))
    except ValueError: bill, paid = 137, 500
    L["bill"], L["paid"] = bill, paid; L["notes"], L["pieces"] = make_change(max(0, paid - bill))
    if role == "vendor":
        live = [o for o in orders.traverse() if o["floor"] == fl and o["counter"] == ck and o["status"] in ("Pending", "Accepted")]
        L["live"] = [(o["id"], o["cname"], prep_min(o), o["total"]) for o in live]
        try: cap = max(5, min(int(a.get("mins", 20)), 120))
        except ValueError: cap = 20
        try: stoves = max(1, min(int(a.get("stoves", 2)), 4))
        except ValueError: stoves = 2
        pend = [{"id": o["id"], "name": f"#{o['id']} {o['cname']}", "price": prep_min(o), "value": o["total"]} for o in live if o["status"] == "Pending"]
        ch, val, _ = budget_knapsack(pend, cap)                               # DP: minutes are the "budget", rupees are the "value"
        L.update(cap=cap, dp_pick=ch, dp_val=val, dp_min=sum(c["price"] for c in ch), stoves=stoves)
        plan, span, nodes = balance_stations([x[2] for x in L["live"]][:9], stoves) if live else (None, 0, 0)
        L.update(bt=plan, span=span, nodes=nodes, bt_ids=[x[0] for x in L["live"]][:9])
    else:
        try: budget = max(30, min(int(a.get("budget", 150)), 400))
        except ValueError: budget = 150
        ck2 = a.get("c", "kf") if a.get("c", "kf") in COUNTERS else "kf"; pop = popularity(fl, ck2)
        pool = [{**i, "value": 10 + 3 * pop.get(i["name"], 0)} for i in fmenu(fl) if i["counter"] == ck2 and i.get("avail", True) and i["price"] <= budget]
        ch, val, _ = budget_knapsack(pool, budget)
        L.update(budget=budget, ck2=ck2, dp_pick=ch, dp_val=val, dp_cost=sum(c["price"] for c in ch))
        today = date.today().isoformat()
        sizes = [int(x) for x in re.findall(r"\d+", a.get("groups", "4,3,6")) if 0 < int(x) <= 6][:5]
        st = next((s for s in start_options() if datetime.fromisoformat(today) + timedelta(minutes=s) > datetime.now()), DAY_START)
        free = free_units(fl, today, st, 60); plan, waste, nodes = seat_groups(sizes, free) if sizes else (None, 0, 0)
        L.update(groups=", ".join(map(str, sizes)), seat_plan=plan, waste=waste, nodes=nodes, n_free=len(free), st=pretty_time(st))
    return L

@app.route("/vendor/lab")
def vendor_lab():
    v = vguard(); return render_template("v_lab.html", v=v, L=lab_data("vendor", v["floor"], v["key"]), page="lab", cname=cname)

@app.route("/admin/lab")
def admin_lab():
    aguard(); fl = request.args.get("floor", "1"); fl = int(fl) if fl.isdigit() and int(fl) in FLOORS else 1
    ck = request.args.get("counter", "all"); ck = ck if ck in COUNTERS else "all"
    return render_template("a_lab.html", L=lab_data("admin", fl, ck), page="lab", cname=cname)

@app.route("/vendor/dashboard")
def vendor_dashboard():
    v = vguard(); days = request.args.get("days", "7"); days = int(days) if days in ("7", "30", "90") else 0
    return render_template("v_dash.html", v=v, days=days, A=analytics(my_orders_of(v), days), has_demo=any(o.get("demo") for o in my_orders_of(v)), has_any=bool(my_orders_of(v)), page="dash")

@app.route("/vendor/payments")
def vendor_payments():
    v = vguard(); method, status = request.args.get("method", ""), request.args.get("status", "")
    rows = [o for o in my_orders_of(v)[::-1] if o["status"] != "Pending" or o.get("method")]
    if method: rows = [o for o in rows if o.get("method", "") == method]
    if status: rows = [o for o in rows if o.get("pay_status", "Paid") == status]
    if request.args.get("csv"):
        out = io.StringIO(); w = csv.writer(out); w.writerow(["Order", "Date", "Customer", "Method", "UPI ID", "Txn id", "Amount", "Payment status", "Order status"])
        for o in rows: w.writerow([o["id"], o["time"], o.get("cname", "Guest"), o["pay"], o.get("upi", ""), o.get("txn", ""), o["total"], o.get("pay_status", "Paid"), o["status"]])
        return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={slug(v['name'])}-payments.csv"})
    allr = my_orders_of(v); sm = lambda f: sum(o["total"] for o in allr if f(o))
    summary = {"online": sm(lambda o: o.get("pay_status") == "Paid"), "cash": sm(lambda o: o.get("pay_status") == "Cash collected"),
               "due": sm(lambda o: o.get("pay_status") == "Pay on delivery" and o["status"] != "Rejected"), "refund": sm(lambda o: o.get("pay_status") == "Refund initiated")}
    return render_template("v_pay.html", v=v, rows=rows, summary=summary, method=method, status=status, page="pay",
                           statuses=["Paid", "Pay on delivery", "Cash collected", "Refund initiated"])

AFFINITY = {   # dishes that sample customers like to buy together (so Apriori has real patterns to find)
 "kf": [("Idli (2 pcs)", "Medu Vada", "Ghee Pongal"), ("Veg Fried Rice", "Gobi Manchurian", "Veg Manchow Soup"), ("Veg Biryani", "Curd Rice"), ("Masala Dosa", "Kesari Bath"), ("Poori Masala", "Ghee Pongal")],
 "brew": [("Tea", "Samosa"), ("Filter Coffee", "Veg Puff"), ("Cold Coffee", "Veg Sandwich"), ("Chocolate Brownie", "Vanilla Ice Cream"), ("Pav Bhaji", "Fresh Lime Soda"), ("Masala Chai", "Bread Pakoda")],
 "roll": [("Veg Burger", "French Fries"), ("Paneer Roll", "Peri Peri Fries"), ("Cheese Corn Roll", "Cheese Fries"), ("Schezwan Veg Roll", "Cheese Balls"), ("Aloo Tikki Burger", "Onion Rings")]}
FAKE = ["Aarav", "Diya", "Rohan", "Meera", "Karthik", "Ananya", "Vikram", "Sneha", "Arjun", "Pooja", "Ishaan", "Kavya", "Nikhil", "Riya", "Siddharth", "Tanvi"]
REVIEW_TEXT = {5: ["Super tasty and hot!", "Loved it, quick service", "Best on campus"], 4: ["Good food, slight wait", "Nice taste", "Value for money"], 3: ["Okay, could be hotter", "Average"], 2: ["Too slow today"], 1: ["Cold food"]}

def gen_demo(floor, key, days=30):
    rnd = random.Random(floor * 31 + sum(map(ord, key)) + len(list(orders.traverse())))
    items = [i for i in fmenu(floor) if i["counter"] == key]; by_name = {i["name"]: i for i in items}
    groups = [[by_name[n] for n in g if n in by_name] for g in AFFINITY[key]]; groups = [g for g in groups if len(g) >= 2]
    methods = [("gpay", 4), ("phonepe", 3), ("paytm", 2), ("upi", 1), ("cod", 2)]
    for back in range(days - 1, -1, -1):
        day = datetime.now() - timedelta(days=back)
        for _ in range(rnd.randint(6, 18) + (4 if day.weekday() < 5 else -3)):
            hr = rnd.choices([8, 9, 10, 12, 13, 14, 16, 17, 18], [5, 6, 3, 8, 9, 4, 5, 6, 2])[0]
            t = day.replace(hour=hr, minute=rnd.randint(0, 59), second=0, microsecond=0)
            if t > datetime.now(): continue
            if groups and rnd.random() < .6: chosen = rnd.choice(groups)[:]; rnd.shuffle(chosen); chosen = chosen[:rnd.randint(2, len(chosen))]
            else: chosen = rnd.sample(items, rnd.randint(1, 2))
            lines = []
            for it in chosen:
                qty = rnd.choice([1, 1, 1, 2]); lines.append({"iid": it["id"], "name": it["name"], "emoji": it["emoji"], "price": it["price"], "qty": qty, "sub": it["price"] * qty})
            m = rnd.choices([m for m, _ in methods], [w for _, w in methods])[0]; rejected = rnd.random() < .05
            status = "Rejected" if rejected else rnd.choices(["Collected", "Ready"], [9, 1])[0]
            pay_status = ("Refund initiated" if rejected else "Paid") if m != "cod" else ("Pay on delivery" if rejected else "Cash collected")
            who = rnd.choice(FAKE) if rnd.random() < .7 else rnd.choice(FAKE[:6])
            o = {"id": nid("order"), "uid": 0, "cname": who, "floor": floor, "counter": key, "lines": lines, "total": sum(l["sub"] for l in lines), "discounts": [], "subtotal": sum(l["sub"] for l in lines),
                 "status": status, "time": f"{t:%d %b %H:%M}", "ts": t.timestamp(), "pay": PAY_LABELS[m], "method": m, "pay_status": pay_status,
                 "txn": "" if m == "cod" else f"CF{rnd.randint(10**9, 10**10 - 1)}", "upi": "", "eta": None if rejected else rnd.choice([5, 8, 10, 12, 15]), "eta_end": None,
                 "reason": "Out of stock" if rejected else "", "demo": True}
            orders.insert(o)
            if not rejected and rnd.random() < .35:
                rt = rnd.choices([5, 4, 3, 2, 1], [8, 6, 3, 1, 1])[0]
                reviews.insert({"id": nid("review"), "oid": o["id"], "uid": 0, "cname": who, "floor": floor, "counter": key, "rating": rt, "text": rnd.choice(REVIEW_TEXT[rt]),
                                "tags": rnd.sample(["Tasty", "Fast", "Hot", "Value", "Clean"], rnd.randint(0, 2)), "ts": t.timestamp() + 1800, "time": f"{t:%d %b %H:%M}", "demo": True})

def clear_demo(floor=None, key=None):
    for o in [o for o in orders.traverse() if o.get("demo") and (floor is None or (o["floor"] == floor and o["counter"] == key))]: orders.delete("id", o["id"])
    for r in [r for r in reviews.traverse() if r.get("demo") and (floor is None or (r["floor"] == floor and r["counter"] == key))]: reviews.delete("id", r["id"])

@app.route("/vendor/demo/<action>", methods=["POST"])
def vendor_demo(action):                                     # sample sales so the charts have something to show
    v = vguard()
    if action == "clear": clear_demo(v["floor"], v["key"]); save(); flash("Sample data removed."); return redirect("/vendor/dashboard")
    gen_demo(v["floor"], v["key"]); save(); flash("Sample sales for the last 30 days loaded. Remove them any time from this page."); return redirect("/vendor/dashboard")

if os.environ.get("RENDER"):                                         # hosted on Render (gunicorn): start the background timer that sends pre-orders and parties on time
    threading.Thread(target=_pre_loop, daemon=True).start()

if __name__ == "__main__":
    threading.Thread(target=_pre_loop, daemon=True).start()          # sends each pre-order day to its counter on time
    app.run(debug=True, use_reloader=False)
