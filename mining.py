"""Market-basket analysis: the Apriori algorithm written from scratch (uses our own merge sort from Phase 3)."""
from ds import merge_sort

def _subsets_of_size(items, k):                    # all k-sized subsets of a tuple (no itertools)
    out = []
    def rec(start, cur):
        if len(cur) == k: out.append(tuple(cur)); return
        for i in range(start, len(items)): cur.append(items[i]); rec(i + 1, cur); cur.pop()
    rec(0, []); return out

def apriori(transactions, min_sup, min_conf, max_k=3):
    """transactions: list of sets of dish names. min_sup / min_conf are fractions (0.05 = 5%).
    Returns frequent itemsets, association rules (sorted by lift with merge sort) and a step log."""
    n = len(transactions); steps = []
    if n == 0: return {"n": 0, "freq": {}, "rules": [], "steps": [], "comps": 0, "sup": {}}
    need = max(1, -(-min_sup * n // 1))            # minimum count, rounded up
    need = int(need)
    count = {}
    for t in transactions:
        for it in t: count[(it,)] = count.get((it,), 0) + 1
    L = {k: v for k, v in count.items() if v >= need}
    freq = dict(L); steps.append({"k": 1, "cand": len(count), "pruned": len(count) - len(L), "kept": len(L)})
    k = 2
    while L and k <= max_k:
        prev = sorted(L); cands = []
        for i in range(len(prev)):                  # join step: merge itemsets that share the first k-2 items
            for j in range(i + 1, len(prev)):
                a, b = prev[i], prev[j]
                if a[:k - 2] == b[:k - 2]: cands.append(tuple(sorted(set(a) | set(b))))
        ok = []
        for c in cands:                             # prune step: every (k-1)-subset must itself be frequent
            if all(s in L for s in _subsets_of_size(c, k - 1)): ok.append(c)
        cnt = {c: 0 for c in ok}
        for t in transactions:                      # one scan of the data per level
            for c in ok:
                if all(x in t for x in c): cnt[c] += 1
        L = {c: v for c, v in cnt.items() if v >= need}
        steps.append({"k": k, "cand": len(cands), "pruned": len(cands) - len(L), "kept": len(L)})
        freq.update(L); k += 1
    rules = []
    for iset, c in freq.items():
        if len(iset) < 2: continue
        for r in range(1, len(iset)):
            for ante in _subsets_of_size(iset, r):
                cons = tuple(x for x in iset if x not in ante)
                conf = c / freq[ante]
                if conf >= min_conf:
                    lift = conf / (freq[cons] / n)
                    rules.append({"ante": ante, "cons": cons, "sup": c / n, "count": c, "conf": conf, "lift": lift})
    rules, comps = merge_sort(rules, lambda r: (r["lift"], r["conf"]), True)
    return {"n": n, "freq": freq, "rules": rules, "steps": steps, "comps": comps, "need": need}
