"""PHASE 1 - Linear data structures, built from scratch (no Python list/dict tricks for storage logic)."""

class Node:                       # one box in a chain: holds data + pointer to next box
    def __init__(self, data):
        self.data, self.next = data, None

class LinkedList:                 # stores users, menu items, orders
    def __init__(self): self.head = None

    def insert(self, data):       # add at the end
        node = Node(data)
        if not self.head: self.head = node; return
        cur = self.head
        while cur.next: cur = cur.next
        cur.next = node

    def delete(self, key, value): # remove node whose record[key] == value
        prev, cur = None, self.head
        while cur:
            if cur.data[key] == value:
                if prev: prev.next = cur.next
                else: self.head = cur.next
                return True
            prev, cur = cur, cur.next
        return False

    def search(self, key, value): # linear search, returns record or None
        for rec in self.traverse():
            if rec[key] == value: return rec
        return None

    def traverse(self):           # walk head -> end
        cur = self.head
        while cur:
            yield cur.data
            cur = cur.next

class Stack:                      # LIFO - last in, first out (admin activity log)
    def __init__(self): self.top = None
    def push(self, data):
        node = Node(data); node.next = self.top; self.top = node
    def pop(self):
        if not self.top: return None
        data = self.top.data; self.top = self.top.next; return data
    def peek(self): return self.top.data if self.top else None
    def empty(self): return self.top is None
    def items(self):
        cur = self.top
        while cur: yield cur.data; cur = cur.next

class Queue:                      # FIFO - first in, first out (pending orders)
    def __init__(self): self.front = self.rear = None
    def enqueue(self, data):
        node = Node(data)
        if self.rear: self.rear.next = node
        else: self.front = node
        self.rear = node
    def dequeue(self):
        if not self.front: return None
        data = self.front.data; self.front = self.front.next
        if not self.front: self.rear = None
        return data
    def peek(self): return self.front.data if self.front else None
    def items(self):
        cur = self.front
        while cur: yield cur.data; cur = cur.next

# ---- Stack applied to expressions (used for the bill) ----
def balanced(expr):               # "(60*2)+(40*1)" -> True
    s = Stack()
    for ch in expr:
        if ch == "(": s.push(ch)
        elif ch == ")":
            if s.empty(): return False
            s.pop()
    return s.empty()

def eval_postfix(expr):           # "60 2 * 40 1 * +" -> 160
    s = Stack()
    for tok in expr.split():
        if tok in ("+", "-", "*"):
            b, a = s.pop(), s.pop()
            s.push(a + b if tok == "+" else a - b if tok == "-" else a * b)
        else: s.push(float(tok))
    return s.pop()

# ================= PHASE 2: trees and graphs =================
class TreeNode:
    def __init__(self, key, data):
        self.key, self.data, self.left, self.right = key, data, None, None

class BinaryTree:
    def __init__(self): self.root = None
    def inorder(self):   return self._in(self.root)
    def preorder(self):  return self._pre(self.root)
    def postorder(self): return self._post(self.root)
    def _in(self, n):   return self._in(n.left) + [n.data] + self._in(n.right) if n else []
    def _pre(self, n):  return [n.data] + self._pre(n.left) + self._pre(n.right) if n else []
    def _post(self, n): return self._post(n.left) + self._post(n.right) + [n.data] if n else []

class BST(BinaryTree):
    def insert(self, key, data):
        node = TreeNode(key, data)
        if not self.root: self.root = node; return
        cur = self.root
        while True:
            if key < cur.key:
                if cur.left: cur = cur.left
                else: cur.left = node; return
            else:
                if cur.right: cur = cur.right
                else: cur.right = node; return
    def search(self, key):
        cur, path = self.root, []
        while cur:
            path.append(cur.key)
            if key == cur.key: return cur.data, path
            cur = cur.left if key < cur.key else cur.right
        return None, path

class Graph:
    def __init__(self): self.adj = {}
    def add_edge(self, a, b):
        self.adj.setdefault(a, []).append(b)
        self.adj.setdefault(b, []).append(a)
    def matrix(self):
        names = list(self.adj)
        return names, [[1 if b in self.adj[a] else 0 for b in names] for a in names]
    def bfs(self, start, goal):
        q, seen, parent, order = Queue(), {start}, {start: None}, []
        q.enqueue(start)
        cur = q.dequeue()
        while cur:
            order.append(cur)
            if cur == goal: break
            for nb in self.adj[cur]:
                if nb not in seen: seen.add(nb); parent[nb] = cur; q.enqueue(nb)
            cur = q.dequeue()
        if cur != goal: return order, None
        path = []
        while cur: path.append(cur); cur = parent[cur]
        return order, path[::-1]

    # ---- replayable runs for the animated map ----
    def _route(self, parent, cur, goal):
        if cur != goal: return None
        path = []
        while cur: path.append(cur); cur = parent[cur]
        return path[::-1]

    def bfs_trace(self, start, goal):
        """BFS with our own Queue. Each step: the place visited, the places it added, and the queue after that."""
        q, seen, parent, steps = Queue(), {start}, {start: None}, []
        q.enqueue(start)
        cur = q.dequeue()
        while cur:
            added = []
            if cur != goal:
                for nb in self.adj[cur]:
                    if nb not in seen: seen.add(nb); parent[nb] = cur; q.enqueue(nb); added.append(nb)
            steps.append({"node": cur, "from": parent[cur], "added": added, "frontier": list(q.items())})
            if cur == goal: break
            cur = q.dequeue()
        return steps, self._route(parent, cur, goal)

    def dfs_trace(self, start, goal):
        """DFS with our own Stack: dive deep first, backtrack when stuck. Same step format as bfs_trace."""
        st, seen, parent, steps, cur = Stack(), set(), {}, [], None
        st.push((start, None))
        while not st.empty():
            cur, par = st.pop()
            if cur in seen: continue
            seen.add(cur); parent[cur] = par
            added = []
            if cur != goal:
                for nb in reversed(self.adj[cur]):
                    if nb not in seen: st.push((nb, cur)); added.append(nb)
            steps.append({"node": cur, "from": par, "added": added, "frontier": [n for n, _ in st.items()]})
            if cur == goal: break
        return steps, self._route(parent, cur, goal)

# ================= PHASE 3: searching and sorting =================
# Every function can also write a "log" of what it did; the website replays that log as an animation.
def linear_search(items, key, target, log=None):
    """Look at every item from the start. Returns (index or -1, comparisons)."""
    comps = 0
    for i, it in enumerate(items):
        comps += 1
        if log is not None: log.append(i)
        if key(it) == target: return i, comps
    return -1, comps

def binary_search(items, key, target, log=None):
    """items MUST be sorted by key. Halve the range each step. Returns (index or -1, comparisons, keys visited)."""
    lo, hi, comps, path = 0, len(items) - 1, 0, []
    while lo <= hi:
        mid = (lo + hi) // 2
        comps += 1; path.append(key(items[mid]))
        if log is not None: log.append([lo, mid, hi])
        if key(items[mid]) == target: return mid, comps, path
        if key(items[mid]) < target: lo = mid + 1
        else: hi = mid - 1
    return -1, comps, path

def insertion_sort(items, key, reverse=False, log=None, tag=None):
    """Pick each item and slide it back into place. Fast for small or nearly sorted lists. Returns (sorted list, comparisons)."""
    tag = tag or (lambda x: x)
    a, comps = list(items), 0
    for i in range(1, len(a)):
        cur, j = a[i], i - 1
        if log is not None: log.append(["pick", i, tag(cur)])
        while j >= 0:
            comps += 1
            if log is not None: log.append(["cmp", j])
            if (key(a[j]) < key(cur)) if reverse else (key(a[j]) > key(cur)):
                a[j + 1] = a[j]
                if log is not None: log.append(["set", j + 1, tag(a[j])])
                j -= 1
            else: break
        a[j + 1] = cur
        if log is not None: log.append(["set", j + 1, tag(cur)])
    return a, comps

def merge_sort(items, key, reverse=False, log=None, tag=None):
    """Split in halves, sort each half, merge them. Always O(n log n). Returns (sorted list, comparisons)."""
    tag, count = tag or (lambda x: x), [0]
    def merge(left, right, lo):
        out, i, j = [], 0, 0
        while i < len(left) and j < len(right):
            count[0] += 1
            if log is not None: log.append(["cmp", lo + i, lo + len(left) + j])
            take_left = key(left[i]) >= key(right[j]) if reverse else key(left[i]) <= key(right[j])
            if take_left: out.append(left[i]); i += 1
            else: out.append(right[j]); j += 1
        out += left[i:] + right[j:]
        if log is not None:
            for p, it in enumerate(out): log.append(["set", lo + p, tag(it)])
        return out
    def sort(a, lo):
        if len(a) <= 1: return a
        mid = len(a) // 2
        return merge(sort(a[:mid], lo), sort(a[mid:], lo + mid), lo)
    return sort(list(items), 0), count[0]