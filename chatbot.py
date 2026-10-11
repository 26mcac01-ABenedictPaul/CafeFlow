"""CafeFlow assistant: a free, rule-based chatbot that lives inside the app (no outside service).
It answers from live canteen data and reuses the project's own algorithms:
  BST (ds.py)            exact dish look-up
  linear scan            fuzzy dish look-up
  merge sort (ds.py)     cheapest / under-budget lists
  knapsack DP (algos.py) "plan my meal for Rs 150"
  greedy (algos.py)      "change for 500, bill 137"
"""
import re
from ds import BST, merge_sort
from algos import make_change, budget_knapsack

STOP = set("""a an the is are am i me my we you your do does did can could would will to of for at in on with and or any some have has had get got give show tell
please pls want need like order price prices cost costs much how what whats which where when who it its this that there here today now item items food menu available avail rs rupees
veg non nonveg vegetarian cheap cheapest under below less than upto budget buy eat serve serving sell selling much many""".split())

CHIPS = ["What's popular?", "Cheapest dishes", "Plan my meal for Rs 150", "Where is my order?", "Plan a birthday party", "Today's offers"]


def words(t): return re.findall(r"[a-z0-9']+", t.lower())


def has(text, *keys):                                        # whole-word or phrase match
    pad = " " + " ".join(words(text)) + " "
    return any(" " + k + " " in pad for k in keys)


def item_card(it, counter_name):
    return {"id": it["id"], "name": it["name"], "price": it["price"], "emoji": it["emoji"], "counter": counter_name, "veg": bool(it.get("veg", True))}


def find_dishes(text, items):
    """Exact name first (binary search tree), then fuzzy: score = how many meaningful words of the question appear in the dish name."""
    tree = BST()
    for it in items: tree.insert(it["name"].lower(), it)
    phrase = " ".join(w for w in words(text) if w not in STOP)
    hit, _ = tree.search(phrase)
    if hit: return [hit]
    toks = [w for w in words(text) if w not in STOP and len(w) >= 3]
    if not toks: return []
    scored = []
    for it in items:
        nm = words(it["name"]); s = sum(1 for t in toks if any(t == n or (len(t) >= 4 and (t in n or n in t)) for n in nm))
        if s: scored.append((s, it))
    if not scored: return []
    top = max(s for s, _ in scored)
    return [it for s, it in scored if s == top][:6]


def reply(text, ctx):
    """ctx: items (dishes of this floor, available only), cname (fn counter key -> name), orders (this student's, newest first), offers (list of text lines),
    sold (dict dish name -> units sold), best (list of (name, qty)), floor, pure_veg"""
    t = text.strip()[:200]; items, cn = ctx["items"], ctx["cname"]
    out = {"text": "", "items": [], "links": [], "chips": []}
    nums = [int(n) for n in re.findall(r"\d+", t)]
    card = lambda lst: [item_card(i, cn(i["counter"])) for i in lst]

    if not t: out["text"] = "Type a question, for example: price of samosa."; out["chips"] = CHIPS; return out

    # ---- greedy: change maker
    if has(t, "change", "balance") and len(nums) >= 2:
        paid, bill = max(nums[:2]), min(nums[:2]); notes, pieces = make_change(paid - bill)
        out["text"] = f"For a bill of Rs {bill} paid with Rs {paid}, the change is Rs {paid - bill}: " + (", ".join(f"{n} x Rs {d}" for d, n in notes) if notes else "no change needed") + f" ({pieces} piece(s), worked out with the greedy method)."
        return out

    # ---- dynamic programming: budget meal
    if (has(t, "plan", "meal", "combo", "suggest", "recommend", "budget", "afford") or has(t, "i have", "i got")) and nums and 20 <= max(nums) <= 1000 and not has(t, "party", "birthday"):
        b = min(max(nums), 400); best = None
        for k in sorted({i["counter"] for i in items}):
            pool = [{**i, "value": 10 + 3 * ctx["sold"].get(i["name"], 0)} for i in items if i["counter"] == k and i["price"] <= b]
            if not pool: continue
            ch, val, _ = budget_knapsack(pool, b)
            if ch and (best is None or val > best[1]): best = (ch, val, k)
        if best:
            ch, val, k = best; sp = sum(c["price"] for c in ch)
            out["text"] = f"Best meal for Rs {b} at {cn(k)}: {len(ch)} dish(es) for Rs {sp}, picked with dynamic programming (most popular value for your money)."; out["items"] = card(ch)
        else: out["text"] = f"Nothing fits Rs {b} right now. Try a bit more."
        out["links"] = [{"label": "Open the full meal planner", "url": "/solve#dp"}]; return out

    # ---- my order
    if has(t, "my order", "order status", "track", "where is my", "is my order", "ready yet", "status"):
        if not ctx["orders"]: out["text"] = "You have no orders yet. Pick something tasty and I will help you track it."; out["links"] = [{"label": "Browse the menu", "url": "/home"}]; return out
        o = ctx["orders"][0]; msg = {"Pending": "is waiting for the counter to accept it", "Accepted": "is being prepared", "Ready": "is READY, please collect it now", "Collected": "was collected", "Rejected": "was rejected by the counter"}.get(o["status"], o["status"])
        out["text"] = f"Order #{o['id']} from {cn(o['counter'])} {msg}." + (f" Preparation is about {o['eta']} min." if o.get("eta") and o["status"] == "Accepted" else "") + (f" Reason: {o['reason']}" if o.get("reason") else "")
        out["links"] = [{"label": "Open order #%d" % o["id"], "url": f"/order/{o['id']}"}, {"label": "All my orders", "url": "/orders"}]; return out

    # ---- features and how-tos
    if has(t, "party", "birthday", "bday", "celebrate", "celebration", "cake"):
        out["text"] = "Plan a birthday party: pre-book tables, cakes, pastries, fries and chips at least a day ahead. 10% off for 4+ guests, 15% for 10+, 20% for 20+, and 5% extra if you book 3+ days early."; out["links"] = [{"label": "Plan a party", "url": "/party"}]; return out
    if has(t, "table", "seat", "seats", "sofa", "reserve", "reservation", "booking", "book"):
        out["text"] = "Book a table from the floor map: choose date, time and how long you will stay, then tap a free seat. For a group, use the party planner or the group seating tool."; out["links"] = [{"label": "Book a table", "url": "/reserve"}, {"label": "Group seating", "url": "/solve#bt"}]; return out
    if has(t, "preorder", "pre-order", "pre order", "advance", "schedule", "tomorrow", "next week"):
        out["text"] = "Pre-order lets you pick meals for coming days. Each day is sent to the counter an hour before pickup, so your food is fresh."; out["links"] = [{"label": "Pre-order meals", "url": "/preorder"}]; return out
    if has(t, "review", "rating", "rate", "feedback", "complain", "complaint"):
        out["text"] = "After any order you can give 1 to 5 stars and a comment. It goes straight to the counter and the admin."; out["links"] = [{"label": "Add a review", "url": "/reviews"}]; return out
    if has(t, "story", "stories"): out["text"] = "Stories show each counter's bestsellers, offers and fresh reviews."; out["links"] = [{"label": "Watch stories", "url": "/stories"}]; return out
    if has(t, "pay", "payment", "upi", "gpay", "phonepe", "paytm", "cash", "cod", "qr", "bill", "receipt"):
        out["text"] = "You can pay with a UPI QR (Google Pay, PhonePe, Paytm or any UPI app) or choose Cash on Delivery. After paying you get a bill you can print or save as PDF."; out["links"] = [{"label": "My cart", "url": "/cart"}]; return out
    if has(t, "open", "close", "closing", "timing", "timings", "hours", "time"):
        out["text"] = "The canteen is open from 8:00 AM to 8:00 PM. Table slots run through the day."; return out
    if has(t, "offer", "offers", "deal", "deals", "discount", "discounts", "coupon", "save"):
        out["text"] = ("Today's offers:\n" + "\n".join("• " + x for x in ctx["offers"][:5])) if ctx["offers"] else "No special offers right now, but birthday parties get up to 25% off."; out["links"] = [{"label": "Plan a party", "url": "/party"}]; return out
    if has(t, "cart", "checkout", "basket"): out["text"] = "Your cart has everything you added. Review it, pick a payment method and place the order."; out["links"] = [{"label": "Open cart", "url": "/cart"}]; return out
    if has(t, "floor", "floors", "counter", "counters", "map", "route", "way", "directions"):
        out["text"] = "Floor 1 is pure veg; Floor 2 has veg and non-veg. Use the canteen map for the shortest walking route between counters."; out["links"] = [{"label": "Canteen map", "url": "/map"}]; return out
    if has(t, "hi", "hello", "hey", "hii", "hola", "namaste", "good morning", "good evening", "good afternoon", "help", "start", "who are you"):
        out["text"] = "Hi! I'm the CafeFlow assistant ☕ Ask me about dishes and prices, offers, your order, tables, pre-orders or birthday parties."; out["chips"] = CHIPS; return out
    if has(t, "thanks", "thank you", "thx", "ty", "bye", "ok thanks"): out["text"] = "Happy to help! Enjoy your meal 😊"; return out

    # ---- a particular dish
    dishes = find_dishes(t, items)
    if dishes:
        if len(dishes) == 1:
            d = dishes[0]; out["text"] = f"{d['emoji']} {d['name']} is Rs {d['price']} at {cn(d['counter'])} ({'veg' if d.get('veg', True) else 'non-veg'})."
        else: out["text"] = f"I found {len(dishes)} dishes that match:"
        out["items"] = card(dishes); return out

    # ---- lists
    if has(t, "popular", "best", "bestseller", "bestsellers", "trending", "famous", "top", "recommend", "recommended", "favourite", "favorite"):
        names = [n for n, _ in ctx["best"][:6]]; lst = [i for n in names for i in items if i["name"] == n][:6]
        if lst: out["text"] = "Here are the crowd favourites right now:"; out["items"] = card(lst); return out
    if has(t, "nonveg", "non-veg", "non veg", "chicken", "mutton", "egg", "meat", "fish"):
        lst = [i for i in items if not i.get("veg", True)][:6]
        out["text"] = "Non-veg dishes available:" if lst else "This floor is pure veg. Switch to Floor 2 for non-veg dishes."; out["items"] = card(lst); return out
    if has(t, "veg", "vegetarian"):
        lst = [i for i in items if i.get("veg", True)]; lst, _ = merge_sort(lst, lambda i: -ctx["sold"].get(i["name"], 0)); out["text"] = ("All of Floor %d is pure veg. " % ctx["floor"] if ctx["pure_veg"] else "") + "Popular veg dishes:"; out["items"] = card(lst[:6]); return out
    cap = max(nums) if nums and has(t, "under", "below", "less", "upto", "within", "max") else None
    if cap or has(t, "cheap", "cheapest", "lowest", "low", "affordable", "budget", "snack", "snacks"):
        lst = [i for i in items if (cap is None or i["price"] <= cap)]; lst, _ = merge_sort(lst, lambda i: i["price"])    # merge sort, cheapest first
        out["text"] = (f"Dishes under Rs {cap}:" if cap else "The cheapest dishes right now:") if lst else "Nothing matches that budget."; out["items"] = card(lst[:6]); return out

    out["text"] = "I did not catch that 🤔 Try asking about a dish (\"price of samosa\"), \"cheapest dishes\", \"plan my meal for Rs 120\", \"where is my order\" or \"plan a birthday party\"."; out["chips"] = CHIPS; return out
