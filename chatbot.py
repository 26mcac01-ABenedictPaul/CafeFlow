"""CafeFlow assistant: a free, rule-based chatbot that lives inside the app (no outside service).
It answers from live canteen data and reuses the project's own algorithms:
  BST (ds.py)            exact dish look-up
  linear scan            fuzzy dish look-up
  merge sort (ds.py)     cheapest / under-budget lists
  knapsack DP (algos.py) "plan my meal for Rs 150"
  greedy (algos.py)      "change for 500, bill 137"
It also TEACHES the 4 DSA phases: ask "explain BST", "explain phase 2", "what is backtracking".
"""
import re
from ds import BST, merge_sort
from algos import make_change, budget_knapsack

STOP = set("""a an the is are am i me my we you your do does did can could would will to of for at in on with and or any some have has had get got give show tell
please pls want need like order price prices cost costs much how what whats which where when who it its this that there here today now item items food menu available avail rs rupees
veg non nonveg vegetarian cheap cheapest under below less than upto budget buy eat serve serving sell selling much many""".split())

CHIPS = ["What's popular?", "Cheapest dishes", "Plan my meal for Rs 150", "Where is my order?", "Plan a birthday party", "Today's offers", "Explain stack", "Explain queue", "Explain linked list"]


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


# ======================================================================== DSA teacher: explains every concept of the 4 phases
# Each topic: (text, student page link, follow-up chips). Staff get a link to their own algorithm lab instead.
def _t(*lines): return "\n".join(lines)

DSA_TOPICS = {
 "overview": (_t("CafeFlow uses all four DSA phases for real:",
                 "• Phase 1, Linear structures: linked list, stack, queue, expression handling",
                 "• Phase 2, Trees and graphs: binary tree, BST, traversals, graph, BFS and DFS",
                 "• Phase 3, Searching and sorting: linear and binary search, insertion and merge sort",
                 "• Phase 4, Problem solving: greedy, dynamic programming, backtracking",
                 "Pick a phase, or ask about one idea, for example \"explain BST\"."),
              ("All 4 phases in the project", "/phases"), ["Explain phase 1", "Explain phase 2", "Explain phase 3", "Explain phase 4"]),
 "phase1": (_t("Phase 1: Linear data structures (CLO1)",
               "• Linked list: stores users, menu items, carts, orders and bookings",
               "• Stack: cart Undo, the admin activity log, and the bracket check + postfix for the bill",
               "• Queue: one pending-order queue per counter, with 'orders ahead of you' on your order page",
               "Which one should I explain?"),
            ("See Phase 1 in the project", "/phases"), ["Explain linked list", "Explain stack", "Explain queue", "Explain postfix"]),
 "phase2": (_t("Phase 2: Trees and graphs (CLO2)",
               "• Binary tree with in, pre and post order traversals",
               "• Binary search tree: dish search that shows its search path",
               "• Graph of the canteen as an adjacency list and a matrix",
               "• BFS and DFS to find a walking route",
               "Which one should I explain?"),
            ("See Phase 2 in the project", "/phases"), ["Explain binary tree", "Explain BST", "Explain graph", "Explain BFS and DFS"]),
 "phase3": (_t("Phase 3: Searching and sorting (CLO2)",
               "• Linear search and binary search, with comparison counts",
               "• Insertion sort and merge sort",
               "• Used inside the workflow: menu sorting, order reports, counter ranking, and this chat's cheapest-dishes list",
               "Which one should I explain?"),
            ("See Phase 3 in the project", "/phases"), ["Explain binary search", "Explain merge sort", "Linear vs binary search", "Insertion vs merge sort"]),
 "phase4": (_t("Phase 4: Basic algorithmic problem solving (CLO3)",
               "• Greedy: fewest notes and coins as change",
               "• Dynamic programming: the best meal for your budget (knapsack)",
               "• Backtracking: seat several groups with the fewest wasted seats",
               "• Bonus: Apriori market basket in the admin Basket analysis",
               "Which one should I explain?"),
            ("See Phase 4 in the project", "/phases"), ["Explain greedy", "Explain dynamic programming", "Explain backtracking", "Explain apriori"]),

 "linked_list": (_t("Linked list (Phase 1)",
                    "A chain of nodes. Each node = data + a pointer (next) to the following node. The first node is the head, the last one points to None.",
                    "• Insert at the end: walk to the last node, then last.next = new node (O(n))",
                    "• Insert at the front: new.next = head, head = new (O(1)), the Undo in your cart uses this",
                    "• Delete: find the node, then make the one before it skip over it (prev.next = cur.next)",
                    "• Search / traverse: follow the pointers one by one (O(n)). Reverse: flip every pointer with prev, cur, nxt.",
                    "Tiny trace, cart = Samosa → Tea: add Maggi ⇒ walk Samosa, Tea (last) ⇒ Tea.next = Maggi ⇒ Samosa → Tea → Maggi → None. Remove Tea ⇒ Samosa.next = Maggi.",
                    "In CafeFlow: users, menu, orders, bookings, parties, reviews and every student's cart are linked lists (ds.py). Open the Linear lab to watch the pointers move."),
                 ("Watch the linked list animation", "/linear#ll"), ["Explain stack", "Explain queue", "How does undo work?"]),
 "stack": (_t("Stack (Phase 1)",
              "Last in, first out (LIFO), like a pile of plates. push puts a node on top, pop removes the top, peek just looks at it. All O(1).",
              "Tiny trace: push Tea, push Samosa, push Maggi ⇒ top is Maggi. pop ⇒ Maggi leaves first, then Samosa, then Tea.",
              "Where CafeFlow uses it:",
              "• Cart Undo: every dish you remove is pushed on your undo stack; Undo pops the latest one back into the cart",
              "• Bill: a stack checks the brackets of (60*2)+(40*1) and then evaluates the postfix form to get the total",
              "• Admin activity log: newest action on top",
              "• DFS on the canteen map keeps its path on a stack"),
           ("Watch the stack animation", "/linear#stack"), ["Explain queue", "Explain postfix", "How does undo work?"]),
 "queue": (_t("Queue (Phase 1)",
              "First in, first out (FIFO), like the line at a counter. enqueue adds at the rear, dequeue removes from the front, peek looks at the front. All O(1) with a front and a rear pointer.",
              "Tiny trace: orders #101, #102, #103 arrive ⇒ front #101, rear #103. The counter accepts #101 (dequeue) ⇒ front is now #102.",
              "Where CafeFlow uses it:",
              "• Every counter has its own queue of pending orders. A counter can only accept or decline the order at the FRONT",
              "• Your order page and my bot tell you how many orders are ahead of you (queue position)",
              "• Pre-orders and party orders join the same queue when they are released",
              "• BFS on the canteen map uses a queue to explore level by level"),
           ("Watch the queue animation", "/linear#queue"), ["Explain stack", "Explain linked list", "How many orders are ahead of me?"]),
 "undo": (_t("Cart Undo: a stack in action",
             "When you press Remove in the cart, the dish is pushed on your personal undo stack and deleted from the cart's linked list.",
             "Undo last removal pops the top of the stack and puts that dish back at the front of the linked list. Remove 3 dishes, press Undo 3 times: they come back in reverse order (LIFO)."),
          ("Open my cart", "/cart"), ["Explain stack", "Explain linked list"]),
 "expression": (_t("Expression handling (Phase 1)",
                   "A stack checks the bill expression, for example (60*2)+(40*1).",
                   "• Balanced brackets: push on '(' and pop on ')'. If nothing is left on the stack at the end, the brackets match.",
                   "• Postfix: for \"60 2 * 40 1 * +\" push the numbers; at an operator pop two numbers, calculate and push the result. The last value, 160, is the answer.",
                   "In CafeFlow: used for the bill on the cart page."),
                ("See the bill on the cart", "/cart"), ["Explain stack", "Explain queue"]),

 "tree": (_t("Binary tree (Phase 2)",
             "Every node has at most two children, a left and a right. There are three ways to visit all nodes:",
             "• Inorder: left, root, right (on a BST this gives A to Z order)",
             "• Preorder: root, left, right",
             "• Postorder: left, right, root",
             "In CafeFlow: the Menu tree page draws the dishes as a tree and shows all three traversals.",
             "Speed: a traversal visits every node once, O(n)."),
          ("Open the menu tree", "/tree"), ["Explain BST", "Explain graph"]),
 "bst": (_t("Binary search tree, BST (Phase 2)",
            "A binary tree with one rule: smaller keys go to the left, larger keys go to the right. Every step of a search throws away half of the remaining tree.",
            "In CafeFlow: dishes are stored by name in one BST per floor. A dish search shows the path of dishes it compared, and this chat uses the same BST to find an exact dish name.",
            "Speed: O(log n) when the tree is balanced, O(n) if it leans to one side. The Menu tree page can build both shapes so you can compare."),
         ("Try a BST search", "/search?q=tea"), ["Explain binary tree", "Explain graph"]),
 "graph": (_t("Graph, BFS and DFS (Phase 2)",
              "A graph is nodes joined by edges. In CafeFlow the nodes are places (Entrance, Staircase, the three counters, Dining Area, Washroom, Exit) and the edges are the walking paths.",
              "• Adjacency list: each place lists its neighbours",
              "• Adjacency matrix: a table of 1s and 0s showing which places connect",
              "• BFS uses a queue and explores level by level, so it finds the route with the fewest steps",
              "• DFS uses a stack and goes as deep as it can first, so it finds a route but not always the shortest",
              "Speed: O(V + E), visiting each place and path once."),
           ("Open the canteen map", "/map"), ["Explain binary tree", "Explain BST"]),

 "linear": (_t("Linear search (Phase 3)",
               "Check the items one by one from the start until you find the target. It works on unsorted data.",
               "Speed: O(n). A menu of n dishes can need n checks.",
               "In CafeFlow: the Search & sort page counts the comparisons it makes."),
            ("Open Search & sort", "/algo"), ["Explain binary search", "Linear vs binary search"]),
 "binary": (_t("Binary search (Phase 3)",
               "The list must be sorted first (CafeFlow sorts dish names A to Z with merge sort). Look at the middle item: if it is the target you are done; if the target is smaller keep the left half, otherwise the right half. Repeat.",
               "Speed: O(log n). Around 80 dishes need at most about 7 comparisons instead of 80.",
               "In CafeFlow: the Search & sort page shows linear and binary search side by side with their comparison counts."),
            ("Open Search & sort", "/algo"), ["Explain linear search", "Explain merge sort"]),
 "insertion": (_t("Insertion sort (Phase 3)",
                  "Take each item in turn and slide it left into its place among the items already sorted, like arranging playing cards in your hand.",
                  "Speed: O(n²) in the worst case, but quick for small or nearly sorted lists.",
                  "In CafeFlow: the counter page orders its waiting orders with insertion sort, and the Search & sort page races it against merge sort."),
               ("Open Search & sort", "/algo"), ["Explain merge sort", "Insertion vs merge sort"]),
 "merge": (_t("Merge sort (Phase 3)",
              "Divide and conquer: split the list in half again and again until each part has one item, then merge the parts back together in order.",
              "Speed: O(n log n) every time, so it beats insertion sort on big lists.",
              "In CafeFlow: menu sorting by price or name, newest reviews, counter ranking and order reports use merge sort, and so does this chat's cheapest-dishes list."),
           ("Open Search & sort", "/algo"), ["Explain insertion sort", "Insertion vs merge sort"]),
 "compare": (_t("Searching and sorting compared (Phase 3)",
                "• Linear search is O(n); binary search is O(log n) but needs sorted data",
                "• Insertion sort is O(n²); merge sort is O(n log n)",
                "On a small list the difference is tiny. On a big list binary search and merge sort win clearly. The Search & sort page shows the real comparison counts for each."),
             ("Open Search & sort", "/algo"), ["Explain binary search", "Explain merge sort"]),

 "greedy": (_t("Greedy method (Phase 4)",
               "At every step take the best choice available right now and never undo it. For change, always hand over the largest note or coin that still fits: 500, 200, 100, 50, 20, 10, 5, 2, 1.",
               "Example: change of Rs 363 = 200 + 100 + 50 + 10 + 2 + 1, which is 6 pieces.",
               "Greedy is correct for Indian notes and coins. For odd coin sets it can fail, which is where dynamic programming helps.",
               "In CafeFlow: cash orders show the fewest notes and coins to give back. Try \"change for 500, bill 137\"."),
            ("Open the change maker", "/solve#greedy"), ["Explain dynamic programming", "Explain backtracking"]),
 "dp": (_t("Dynamic programming (Phase 4)",
           "Solve small sub-problems once, store the answers in a table, and build the big answer from them. CafeFlow uses the 0/1 knapsack: each dish can be picked once, your budget is the bag size, and a dish's value is its popularity.",
           "The table best[i][b] holds the best value using the first i dishes with b rupees. The last cell is the answer, and tracing back through the table shows which dishes were picked.",
           "In CafeFlow: the Meal planner. Try \"plan my meal for Rs 150\".",
           "Speed: O(dishes x budget)."),
        ("Open the meal planner", "/solve#dp"), ["Explain greedy", "Explain backtracking"]),
 "backtracking": (_t("Backtracking (Phase 4)",
                     "Try a choice, go deeper, and if it leads nowhere (or is already worse than the best answer found) undo it and try the next choice.",
                     "In CafeFlow: group seating. Each group needs its own table or sofa big enough for it, and we want the fewest wasted seats. The biggest groups are placed first so bad branches fail early. The birthday party planner uses it to find tables too.",
                     "Speed: it can blow up for many groups, but pruning keeps it fast for a handful."),
                  ("Open group seating", "/solve#bt"), ["Explain greedy", "Explain dynamic programming"]),
 "apriori": (_t("Apriori, market basket analysis (bonus)",
                "Finds dishes that are often bought together. Support is how often a combination appears across all orders; confidence is how often the second dish comes with the first. Combinations below the minimum are dropped, and only the survivors are grown into bigger sets.",
                "In CafeFlow: the admin Basket analysis page."),
             None, ["Explain greedy", "Explain dynamic programming"]),
}

# keywords that always mean "teach me this" (matched as whole words or phrases, in this order: most specific first)
DSA_STRONG = [
 ("bst", ["bst", "binary search tree"]),
 ("graph", ["bfs", "dfs", "adjacency", "breadth first", "depth first"]),
 ("tree", ["binary tree", "inorder", "preorder", "postorder", "in order traversal", "pre order traversal", "post order traversal", "traversal", "traversals"]),
 ("undo", ["undo", "how does undo work"]),
 ("linked_list", ["linked list", "linked lists", "linkedlist", "singly linked", "head node", "next pointer"]),
 ("stack", ["stack", "stacks", "lifo", "push", "pop", "peek", "stack overflow", "underflow"]),
 ("queue", ["fifo", "enqueue", "dequeue", "front and rear"]),
 ("expression", ["postfix", "infix", "balanced brackets", "parentheses"]),
 ("greedy", ["greedy", "coin change", "making change", "make change"]),
 ("dp", ["dynamic programming", "dynamic", "knapsack", "memoization", "dp"]),
 ("backtracking", ["backtracking", "backtrack"]),
 ("apriori", ["apriori", "market basket", "basket analysis"]),
]
# words that only mean "teach me" when the user also asks to explain (they are everyday words too)
DSA_WEAK = [
 ("graph", ["graph", "graphs", "map"]), ("tree", ["tree", "trees"]), ("queue", ["queue", "queues"]),
 ("expression", ["expression", "expressions", "brackets"]), ("linked_list", ["node", "nodes"]),
]
EXPLAIN = ("explain", "how does", "how do", "how is", "how are", "what is a", "what is an", "what are", "what s a", "what s an", "define", "meaning of", "tell me about", "teach", "concept", "concepts", "working of", "how it works", "used in", "learn", "why do", "why does", "why is")


def dsa_reply(t, nums, role="student"):
    """Return a teaching answer if the question is about a DSA concept of the project, else None."""
    if has(t, "change", "balance") and len(nums) >= 2 and not has(t, "greedy", "explain"): return None    # that is a real change calculation, not a lesson
    asked = has(t, *EXPLAIN); key = None
    # both of a pair mentioned, or a general word -> the comparison page
    if (has(t, "linear") and has(t, "binary")) or (has(t, "insertion") and has(t, "merge")): key = "compare"
    elif has(t, "complexity", "big o", "time complexity") or (has(t, "compare", "comparison", "faster", "fastest", "better") and has(t, "sort", "sorting", "sorts", "search", "searching")): key = "compare"
    elif has(t, "phase", "phases") and nums and nums[0] in (1, 2, 3, 4): key = f"phase{nums[0]}"
    elif has(t, "phases", "dsa", "data structure", "data structures", "algorithm", "algorithms", "concepts", "clo", "clos") and (asked or has(t, "dsa", "phases", "data structures", "algorithms")): key = "overview"
    if not key:
        for k, ws in DSA_STRONG:
            if has(t, *ws): key = k; break
    if not key:
        for k, ws in (("binary", ["binary search"]), ("linear", ["linear search"]), ("insertion", ["insertion sort"]), ("merge", ["merge sort", "mergesort"])):
            if has(t, *ws): key = k; break
    if not key and asked:
        for k, ws in DSA_WEAK:
            if has(t, *ws): key = k; break
        if not key and has(t, "sorting", "sort", "sorts", "searching", "search"): key = "compare"
    if not key: return None
    text, link, chips = DSA_TOPICS[key]; out = {"text": text, "items": [], "links": [], "chips": list(chips)}
    if role == "student":
        if link: out["links"].append({"label": link[0], "url": link[1]})
    elif role == "admin":
        out["links"].append({"label": "Basket analysis", "url": "/admin/basket"} if key == "apriori" else {"label": "Algorithm lab", "url": "/admin/lab"})
    else: out["links"].append({"label": "Algorithm lab", "url": "/vendor/lab"})
    return out


def reply(text, ctx):
    """ctx: items (dishes of this floor, available only), cname (fn counter key -> name), orders (this student's, newest first), offers (list of text lines),
    sold (dict dish name -> units sold), best (list of (name, qty)), floor, pure_veg"""
    t = text.strip()[:200]; items, cn = ctx["items"], ctx["cname"]
    out = {"text": "", "items": [], "links": [], "chips": []}
    nums = [int(n) for n in re.findall(r"\d+", t)]
    card = lambda lst: [item_card(i, cn(i["counter"])) for i in lst]

    if not t: out["text"] = "Type a question, for example: price of samosa."; out["chips"] = CHIPS; return out

    # ---- explain a DSA concept of the project (Phases 1 to 4)
    lesson = dsa_reply(t, nums)
    if lesson: return lesson

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

    # ---- queue position (a real QUEUE lookup)
    if has(t, "ahead of me", "my position", "my turn", "in the queue", "in queue", "in line", "queue position", "how long will", "how many orders"):
        pend = [o for o in ctx["orders"] if o["status"] == "Pending"]
        if not pend: out["text"] = "None of your orders is waiting in a queue right now. Once you place one, I can tell you how many orders are ahead of you."; out["chips"] = ["Explain queue"]; return out
        o = pend[0]; a = ctx.get("ahead", {}).get(o["id"])
        out["text"] = (f"Order #{o['id']} is at the FRONT of the {cn(o['counter'])} queue. The counter will see it next." if a == 0 else f"{a} order(s) are ahead of your order #{o['id']} at {cn(o['counter'])}. The counter serves the queue first come, first served.") + " (I looked at the counter's queue with the position() method.)"
        out["links"] = [{"label": "Open order #%d" % o["id"], "url": f"/order/{o['id']}"}, {"label": "Watch the queue animation", "url": "/linear#queue"}]; return out

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
        out["text"] = "Hi! I'm the CafeFlow assistant ☕ Ask me about dishes and prices, offers, your order, tables, pre-orders or birthday parties. I can also explain the DSA concepts behind CafeFlow 📚"; out["chips"] = CHIPS; return out
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


# ======================================================================== staff assistants (counter and admin)
STAFF_CHIPS = {"vendor": ["Pending orders", "Today's sales", "Top dishes", "Sold out items", "My rating", "Upcoming parties", "Explain the DSA concepts"],
               "admin": ["Today's sales", "Total revenue", "Top counter", "Pending orders", "How are reviews?", "Upcoming parties", "Explain the DSA concepts"]}


def staff_reply(text, role, ctx):
    """role 'vendor' (one counter) or 'admin' (whole canteen). ctx holds numbers worked out by the website (see api_chat)."""
    t = text.strip()[:200]; out = {"text": "", "items": [], "links": [], "chips": []}; money = lambda n: f"Rs {int(n):,}"
    link = lambda label, url: out["links"].append({"label": label, "url": url})
    home = "/vendor/dashboard" if role == "vendor" else "/admin"
    if not t: out["text"] = "Ask me about orders, sales, top dishes or reviews."; out["chips"] = STAFF_CHIPS[role]; return out
    lesson = dsa_reply(t, [int(n) for n in re.findall(r"\d+", t)], role)           # explain a DSA concept of the project
    if lesson: return lesson

    if role == "admin":                                      # a counter named in the question: show that counter
        for name, c in ctx["by_counter"].items():
            if name in t.lower():
                out["text"] = f"{c['label']}: {c['orders']} orders, {money(c['rev'])} revenue, {c['pending']} waiting now, rating {c['rating'] or 'n/a'} ({c['reviews']} reviews)."; return out

    if has(t, "hi", "hello", "hey", "hii", "help", "start", "who are you"):
        out["text"] = "Hi! I'm the CafeFlow assistant 🤖 I can also explain the DSA concepts behind this project. " + ("I can tell you about this counter's orders, sales, sold-out dishes, reviews and parties." if role == "vendor" else "I can summarise orders, revenue, counters, customers, reviews and parties for the whole canteen.")
        out["chips"] = STAFF_CHIPS[role]; return out
    if has(t, "thanks", "thank you", "thx", "bye"): out["text"] = "Anytime! 😊"; return out

    if has(t, "pending", "waiting", "queue", "new order", "new orders", "to accept", "orders now", "live", "active"):
        if role == "vendor":
            out["text"] = f"{ctx['pending']} order(s) waiting to be accepted, {ctx['preparing']} being prepared, {ctx['ready']} ready for pickup."; link("Open orders", "/vendor/orders")
        else:
            out["text"] = f"{ctx['pending']} order(s) are waiting at counters right now, {ctx['preparing']} being prepared and {ctx['ready']} ready."; link("All orders", "/admin/orders")
        return out
    if has(t, "today", "sales", "sale", "earn", "earnings", "income", "turnover") and not has(t, "total"):
        out["text"] = f"Today: {ctx['today_n']} order(s) and {money(ctx['today_rev'])}." + (f" Overall: {ctx['total_n']} orders, {money(ctx['total_rev'])}." if ctx.get("total_n") else ""); link("Dashboard", home); return out
    if has(t, "revenue", "total", "money", "profit", "income", "overall", "all time"):
        out["text"] = f"Total revenue so far: {money(ctx['total_rev'])} from {ctx['total_n']} orders (rejected orders are not counted)."; link("Dashboard", home); return out
    if role == "admin" and has(t, "counter", "counters", "rank", "ranking", "leaderboard", "which counter", "best counter"):
        c = ctx["counters"]; out["text"] = ("Counters by revenue:\n" + "\n".join(f"{i + 1}. {x['label']}: {money(x['rev'])} ({x['orders']} orders)" for i, x in enumerate(c[:6]))) if c else "No counter sales yet."; link("Behaviour & ranking", "/admin/behaviour"); return out
    if has(t, "top", "best", "popular", "bestseller", "bestsellers", "selling", "favourite", "dishes", "dish"):
        out["text"] = ("Top dishes: " + ", ".join(f"{n} ({q})" for n, q in ctx["top"][:6])) if ctx["top"] else "No sales yet, so there are no top dishes. Sample data can be loaded from the dashboard."; return out
    if role == "admin" and has(t, "user", "users", "customer", "customers", "students", "registered", "signups"):
        out["text"] = f"{ctx['users_n']} student account(s) registered."; link("Customers", "/admin/users"); return out
    if role == "vendor" and has(t, "sold out", "stock", "unavailable", "out of stock", "soldout", "availability", "available"):
        out["text"] = ("Marked sold out right now: " + ", ".join(ctx["soldout"])) if ctx["soldout"] else "Everything on your menu is available."; link("Manage menu", "/vendor/menu"); return out
    if has(t, "review", "reviews", "rating", "ratings", "feedback", "stars"):
        out["text"] = (f"Average rating {ctx['rating']} ★ from {ctx['nreviews']} review(s)." + (f' Latest: "{ctx["latest"]}"' if ctx.get("latest") else "")) if ctx["nreviews"] else "No reviews yet."; link("Reviews", "/vendor/reviews" if role == "vendor" else "/admin/reviews"); return out
    if has(t, "party", "parties", "birthday", "celebration"):
        if role == "vendor":
            out["text"] = ("Upcoming parties for your counter:\n" + "\n".join(f"• {p['star']}: {p['when']}, {p['guests']} guests" for p in ctx["parties"][:5])) if ctx["parties"] else "No birthday parties booked for your counter yet."; link("Birthday parties", "/vendor/parties")
        else:
            out["text"] = f"{ctx['parties_up']} upcoming birthday part{'y' if ctx['parties_up'] == 1 else 'ies'} ({ctx['parties_n']} booked in total)."; link("Birthday parties", "/admin/parties")
        return out
    if has(t, "offer", "offers", "discount", "ad", "ads", "promotion"):
        out["text"] = ("You can add discounts, buy-one-get-one and combos from Offers. They appear as ads on the student home page." if role == "admin" else "Offers are created by the admin and appear as ads for your dishes."); link("Offers", "/admin/offers") if role == "admin" else None; return out
    if has(t, "how", "accept", "reject", "ready", "collect", "mark", "price", "menu", "add dish", "change"):
        if role == "vendor":
            out["text"] = "Orders: open Orders, tap Accept (set prep time), then Mark ready, then Collected. Reject needs a reason. Menu: use Manage menu to change prices, mark a dish sold out or add a new dish."; link("Orders", "/vendor/orders"); link("Manage menu", "/vendor/menu")
        else:
            out["text"] = "Use the left menu: Orders, Customers, Payments, Behaviour, Reviews, Basket analysis, Offers, Authority and Birthday parties. Algorithm demos are in the Lab."; link("Admin home", "/admin")
        return out
    if has(t, "pay", "payment", "payments", "upi", "cash"):
        out["text"] = "Payments (UPI and cash) are listed with transaction IDs on the Payments page."; link("Payments", "/vendor/payments" if role == "vendor" else "/admin/payments"); return out
    out["text"] = "I did not catch that 🤔 Try \"pending orders\", \"today's sales\", \"top dishes\" or \"how are reviews?\"."; out["chips"] = STAFF_CHIPS[role]; return out
