"""PHASE 4 - Basic algorithmic problem solving, written from scratch.

  GREEDY        make_change      : fewest notes/coins to hand back as change (cash orders)
  DYNAMIC PROG. budget_knapsack  : best set of dishes for a budget (0/1 knapsack)
  BACKTRACKING  seat_groups      : seat several groups on tables/sofas with the least wasted seats

Each function returns the answer AND a small "stats"/trace so the website can show how the algorithm worked.
"""

DENOMS = [500, 200, 100, 50, 20, 10, 5, 2, 1]          # Indian notes and coins, largest first


# ---------------------------------------------------------------- GREEDY
def make_change(amount, denoms=DENOMS):
    """Greedy: always take the biggest note/coin that still fits. Optimal for this currency system.
    Returns (list of (denomination, count), total pieces)."""
    out, pieces = [], 0
    for d in sorted(denoms, reverse=True):              # largest first = the greedy choice
        if amount >= d:
            n = amount // d
            amount -= n * d
            out.append((d, n)); pieces += n
    return out, pieces


# ---------------------------------------------------------------- DYNAMIC PROGRAMMING
def budget_knapsack(items, budget, max_items=None):
    """0/1 knapsack. items: list of dicts with 'price' (int) and 'value' (int). Each dish may be picked once.
    best[i][b] = best total value using the first i dishes with b rupees. Returns (chosen items, total value, table).
    The table is returned so the page can show it (rows = dishes, columns = budget in steps)."""
    n = len(items)
    best = [[0] * (budget + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        p, v = items[i - 1]["price"], items[i - 1]["value"]
        for b in range(budget + 1):
            best[i][b] = best[i - 1][b]                                   # skip this dish
            if p <= b and best[i - 1][b - p] + v > best[i][b]:            # or take it
                best[i][b] = best[i - 1][b - p] + v
    chosen, b = [], budget                                                # walk back to find which dishes were taken
    for i in range(n, 0, -1):
        if best[i][b] != best[i - 1][b]:
            chosen.append(items[i - 1]); b -= items[i - 1]["price"]
    chosen.reverse()
    if max_items and len(chosen) > max_items:                             # keep it sensible: trim to the best-value dishes
        chosen = sorted(chosen, key=lambda x: -x["value"])[:max_items]
    return chosen, sum(c["value"] for c in chosen), best


# ---------------------------------------------------------------- BACKTRACKING
def seat_groups(groups, units):
    """Backtracking. groups: list of group sizes. units: list of (unit id, seats) that are free.
    Give every group its own unit big enough for it, so that total wasted seats is the smallest possible.
    Try a unit for group i, go deeper, and UNDO (backtrack) when stuck or when the waste is already worse than the best found.
    Returns (assignment list of (group no, size, unit id, seats) or None, wasted seats, nodes explored)."""
    order = sorted(range(len(groups)), key=lambda i: -groups[i])         # biggest groups first: fails early, prunes more
    used, current = set(), []
    best = {"plan": None, "waste": 10 ** 9}
    nodes = [0]

    def solve(k, waste):
        nodes[0] += 1
        if waste >= best["waste"]: return                                # prune: cannot beat the best plan
        if k == len(order):
            best["plan"], best["waste"] = list(current), waste; return
        g = order[k]
        for uid, seats in units:
            if uid in used or seats < groups[g]: continue
            used.add(uid); current.append((g + 1, groups[g], uid, seats))   # choose
            solve(k + 1, waste + seats - groups[g])                          # explore
            used.discard(uid); current.pop()                                 # un-choose (backtrack)

    solve(0, 0)
    if best["plan"] is None: return None, 0, nodes[0]
    return sorted(best["plan"]), best["waste"], nodes[0]


def balance_stations(times, k):
    """Backtracking (counter end). times: cooking minutes of each order. k: number of stoves/cooks.
    Try every order on every stove, undo (backtrack) when stuck, and prune when a stove is already longer than the best plan.
    Goal: the busiest stove finishes as early as possible. Returns (stoves = list of lists of (order no, minutes), longest load, nodes explored)."""
    order = sorted(range(len(times)), key=lambda i: -times[i])           # longest jobs first prune most
    loads, groups = [0] * k, [[] for _ in range(k)]
    best = {"plan": None, "span": 10 ** 9}; nodes = [0]

    def solve(j):
        nodes[0] += 1
        if max(loads) >= best["span"]: return                           # prune
        if j == len(order): best["plan"], best["span"] = [list(g) for g in groups], max(loads); return
        i, tried = order[j], set()
        for s in range(k):
            if loads[s] in tried: continue                               # two stoves with equal load are the same choice
            tried.add(loads[s]); loads[s] += times[i]; groups[s].append((i + 1, times[i]))       # choose
            solve(j + 1)
            loads[s] -= times[i]; groups[s].pop()                                                 # un-choose (backtrack)
    solve(0)
    return best["plan"], (best["span"] if best["plan"] else 0), nodes[0]
