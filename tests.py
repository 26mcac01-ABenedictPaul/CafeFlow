"""Final testing for CafeFlow: run  python tests.py  (covers every phase)."""
import unittest, os, tempfile, shutil
from ds import LinkedList, Stack, Queue, BST, Graph, balanced, eval_postfix, linear_search, binary_search, insertion_sort, merge_sort
from algos import make_change, budget_knapsack, seat_groups

class Phase1(unittest.TestCase):
    def test_linked_list(self):
        l = LinkedList()
        for i in (1, 2, 3): l.insert({"id": i})
        self.assertEqual([r["id"] for r in l.traverse()], [1, 2, 3])
        self.assertTrue(l.delete("id", 2)); self.assertFalse(l.delete("id", 9))
        self.assertIsNone(l.search("id", 2)); self.assertEqual(l.search("id", 3), {"id": 3})
    def test_stack_queue(self):
        s, q = Stack(), Queue()
        for i in (1, 2, 3): s.push(i); q.enqueue(i)
        self.assertEqual((s.pop(), q.dequeue()), (3, 1)); self.assertEqual(s.peek(), 2); self.assertEqual(q.peek(), 2)
    def test_expressions(self):
        self.assertTrue(balanced("(60*2)+(40*1)")); self.assertFalse(balanced("((1)"))
        self.assertEqual(eval_postfix("60 2 * 40 1 * +"), 160)

class Phase2(unittest.TestCase):
    def setUp(self):
        self.t = BST()
        for k in (5, 3, 8, 1, 4, 9): self.t.insert(k, k)
    def test_traversals(self):
        self.assertEqual(self.t.inorder(), [1, 3, 4, 5, 8, 9]); self.assertEqual(self.t.preorder(), [5, 3, 1, 4, 8, 9]); self.assertEqual(self.t.postorder(), [1, 4, 3, 9, 8, 5])
    def test_bst_search(self):
        self.assertEqual(self.t.search(4)[0], 4); self.assertIsNone(self.t.search(7)[0])
    def test_graph(self):
        g = Graph()
        for a, b in [("A", "B"), ("B", "C"), ("A", "D"), ("D", "C"), ("C", "E")]: g.add_edge(a, b)
        self.assertEqual(len(g.bfs("A", "E")[1]), 4)                       # BFS = shortest route
        _, path = g.dfs_trace("A", "E"); self.assertEqual((path[0], path[-1]), ("A", "E"))
        names, m = g.matrix(); self.assertEqual(m[names.index("A")][names.index("B")], 1)

class Phase3(unittest.TestCase):
    data = [{"n": x} for x in (9, 4, 7, 1, 8, 2, 2, 6)]
    def test_sorts(self):
        want = sorted(d["n"] for d in self.data); k = lambda d: d["n"]
        self.assertEqual([d["n"] for d in insertion_sort(self.data, k)[0]], want)
        self.assertEqual([d["n"] for d in merge_sort(self.data, k)[0]], want)
        self.assertEqual([d["n"] for d in merge_sort(self.data, k, True)[0]], want[::-1])
    def test_search(self):
        s, _ = merge_sort(self.data, lambda d: d["n"]); k = lambda d: d["n"]
        self.assertEqual(linear_search(self.data, k, 7)[0], 2); self.assertEqual(s[binary_search(s, k, 7)[0]]["n"], 7)
        self.assertEqual(binary_search(s, k, 5)[0], -1)
    def test_merge_beats_insertion_on_big_input(self):
        big = list(range(300, 0, -1)); k = lambda x: x
        self.assertLess(merge_sort(big, k)[1], insertion_sort(big, k)[1])

class Phase4(unittest.TestCase):
    def test_greedy_change(self):
        notes, pieces = make_change(363); self.assertEqual(notes, [(200, 1), (100, 1), (50, 1), (10, 1), (2, 1), (1, 1)])
        self.assertEqual(sum(d * n for d, n in notes), 363); self.assertEqual(make_change(0), ([], 0))
    def test_knapsack(self):
        items = [{"price": 30, "value": 10}, {"price": 40, "value": 40}, {"price": 50, "value": 45}, {"price": 70, "value": 60}]
        chosen, value, _ = budget_knapsack(items, 100)
        self.assertEqual(value, 85); self.assertLessEqual(sum(c["price"] for c in chosen), 100)    # 40+50 = Rs 90, score 85
        best = max(sum(items[i]["value"] for i in range(4) if m >> i & 1) for m in range(16) if sum(items[i]["price"] for i in range(4) if m >> i & 1) <= 100)
        self.assertEqual(value, best)
    def test_seat_groups(self):
        plan, waste, _ = seat_groups([4, 3, 6], [("S1", 4), ("S2", 4), ("T1", 6), ("T2", 6)])
        self.assertEqual(waste, 1); self.assertEqual(len({p[2] for p in plan}), 3)
        self.assertIsNone(seat_groups([6, 6, 6], [("T1", 6), ("T2", 6)])[0])
        self.assertIsNone(seat_groups([5], [("S1", 4)])[0])

class Website(unittest.TestCase):                                 # real pages, using a throw-away copy of the data
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(); shutil.copy("data.json", os.path.join(cls.tmp, "data.json")); cls.cwd = os.getcwd(); os.chdir(cls.tmp)
        import sys; sys.path.insert(0, cls.cwd)
        import app; cls.app = app; cls.c = app.app.test_client()
    @classmethod
    def tearDownClass(cls): os.chdir(cls.cwd); shutil.rmtree(cls.tmp, ignore_errors=True)
    def test_pages(self):
        c = self.c; c.post("/register", data={"name": "Tester", "email": "t@test.com", "password": "pass1234", "confirm": "pass1234"})
        c.post("/login", data={"name": "Tester", "password": "pass1234"})
        for url in ["/home", "/tree", "/algo", "/map", "/solve", "/solve?c=brew&budget=200", "/solve?groups=6,6,6,6,6", "/phases", "/party", "/reviews", "/stories", "/reserve", "/api/change?total=137&paid=500"]:
            self.assertEqual(c.get(url).status_code, 200, url)
        self.assertEqual(c.get("/api/change?total=137&paid=500").get_json()["change"], 363)
        r = c.get("/solve?c=kf&budget=150").get_data(as_text=True); self.assertIn("Best meal for Rs 150", r)
        ids = self.app.menu.search("counter", "kf")["id"]
        c.post("/solve/cart", data={"iid": [ids]}); self.assertIn("Your cart", c.get("/cart").get_data(as_text=True))
        # review flow: place an order, review it, check counter + admin got it
        it = self.app.menu.search("counter", "kf"); c.post("/add", data={"iid": it["id"], "qty": 1, "back": "/cart"})
        r = c.post("/pay", data={"method": "cod"}); oid = int(r.headers["Location"].split("/order/")[1].split("?")[0])
        page = c.get(f"/order/{oid}?new=1").get_data(as_text=True); self.assertIn("rvd", page)
        j = c.post(f"/order/{oid}/review", data={"rating": 5, "text": "Great dosa!", "tags": ["Tasty"]}, headers={"X-Requested-With": "fetch"}).get_json(); self.assertTrue(j["ok"])
        self.assertFalse(c.post(f"/order/{oid}/review", data={"rating": 1}, headers={"X-Requested-With": "fetch"}).get_json()["ok"])   # one review per order
        tos = [n["to"] for n in self.app.notices.traverse() if n["kind"] == "review"]; self.assertIn("admin", tos); self.assertIn("v1-kf", tos)
        self.assertIn("Great dosa!", c.get("/reviews").get_data(as_text=True)); self.assertIn("Great dosa!", c.get("/home").get_data(as_text=True))
        # birthday party: quote, discount tiers, seats, booking, release to counters, bill, cancel
        from datetime import date, timedelta
        d = (date.today() + timedelta(days=4)).isoformat(); body = {"star": "Riya", "msg": "Happy Birthday Riya!", "date": d, "time": 960, "guests": 12, "items": {"9001": 1, "9005": 3}}
        q = c.post("/api/party/quote", json=body).get_json(); self.assertTrue(q["ok"], q); self.assertEqual(q["pct"], 20)            # 15% for 10+ guests, +5% early bird
        self.assertEqual(q["regular"], 450 + 3 * 180); self.assertLess(q["total"], q["regular"]); self.assertEqual(sum(s[1] for s in q["seats"]), 12)
        self.assertFalse(c.post("/api/party/quote", json={**body, "date": date.today().isoformat()}).get_json()["ok"])              # must pre-book a day ahead
        self.assertFalse(c.post("/api/party/quote", json={**body, "guests": 2}).get_json()["ok"]); self.assertFalse(c.post("/api/party/quote", json={**body, "items": {}}).get_json()["ok"])
        j = c.post("/party/create", json={**body, "method": "cod"}).get_json(); self.assertTrue(j["ok"]); pid = j["id"]
        self.assertEqual(sum(1 for b in self.app.bookings.traverse() if b.get("party") == pid), len(q["seats"]))
        to = [n["to"] for n in self.app.notices.traverse() if "Birthday party" in n["title"] or "birthday party" in n["title"]]; self.assertIn("admin", to); self.assertIn("v1-brew", to); self.assertIn("v1-roll", to)
        self.assertIn("Riya", c.get("/party").get_data(as_text=True)); self.assertEqual(c.get(f"/party/{pid}/bill").status_code, 200); self.assertEqual(c.get(f"/party/{pid}/bill.pdf").status_code, 200)
        p = self.app.parties.search("id", pid); p["date"], p["time"] = date.today().isoformat(), 0; self.app.release_parties()                 # time travel: the party is due
        po = [o for o in self.app.orders.traverse() if o.get("party") == pid]; self.assertEqual(sorted(o["counter"] for o in po), ["brew", "roll"])
        self.assertTrue(any("Cake message" in l["name"] for o in po for l in o["lines"])); self.assertEqual(sum(o["total"] for o in po), p["total"])
        j2 = c.post("/party/create", json={**body, "date": (date.today() + timedelta(days=9)).isoformat(), "method": "upi"}).get_json(); self.assertTrue(j2["ok"])
        c.post(f"/party/{j2['id']}/cancel"); self.assertEqual(self.app.parties.search("id", j2["id"])["status"], "cancelled"); self.assertEqual(sum(1 for b in self.app.bookings.traverse() if b.get("party") == j2["id"]), 0)
        # remember me: cookie lasts 30 days
        c2 = self.app.app.test_client(); r = c2.post("/login", data={"name": "Tester", "password": "pass1234", "remember": "1"}); self.assertIn("Expires", r.headers["Set-Cookie"])
        r = self.app.app.test_client().post("/login", data={"name": "Tester", "password": "pass1234"}); self.assertNotIn("Expires", r.headers["Set-Cookie"])
        # counter + admin pages
        v = self.app.app.test_client(); v.post("/login", data={"name": "campusfeast", "password": "feast123"}); self.assertIn("Great dosa!", v.get("/vendor/reviews").get_data(as_text=True))
        a = self.app.app.test_client(); a.post("/login", data={"name": "admin", "password": "admin123"}); self.assertIn("Great dosa!", a.get("/admin/reviews").get_data(as_text=True)); self.assertIn("Riya", a.get("/admin/parties").get_data(as_text=True)); self.assertEqual(a.get("/admin/offers").status_code, 200)
        self.assertEqual(v.get("/vendor/parties").status_code, 200)
        self.assertEqual(c.post("/solve/seats", data={"floor": 1, "groups": "4,3", "date": "2000-01-01", "start": 480, "dur": 60}).status_code, 302)  # past time: refused politely

class LabPages(unittest.TestCase):
    def test_counter_and_admin_labs(self):
        import app as A
        from algos import balance_stations
        plan, span, _ = balance_stations([5, 3, 7, 2, 4], 2); assert span == 11
        for who, url in (("admin", "/admin/lab"), ("1-kf", "/vendor/lab")):
            c = A.app.test_client()
            with c.session_transaction() as s:
                if who == "admin": s["admin"] = True
                else: s["vendor"] = who
            r = c.get(url); assert r.status_code == 200 and b"Phase 4" in r.data
        assert A.app.test_client().get("/vendor/lab").status_code == 302

if __name__ == "__main__": unittest.main(verbosity=1)
