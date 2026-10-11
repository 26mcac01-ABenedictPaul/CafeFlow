# ☕ CafeFlow: Smart Canteen Management

A full-stack canteen ordering and management web app built with **Flask**, where every feature is powered by **data structures and algorithms written from scratch** (no built-in sort, search or queue libraries for the core logic). Students order food, pre-book tables and plan birthday parties; counters run their kitchens; the admin watches the whole canteen.

> Course project covering all four phases: linear structures, trees and graphs, searching and sorting, and greedy / dynamic programming / backtracking.

## ✨ Features
**For students**
- Browse two floors (veg-only and mixed), search dishes, add to cart, pay with UPI QR or cash, get a till-roll bill (HTML and PDF)
- 🔔 Live order tracking with pop-up alerts when an order is accepted, ready or collected
- 🪑 Book a table or sofa on a floor map with time slots; 📅 pre-order meals for coming days
- 🎂 **Plan a Birthday Party**: pre-book tables, cakes, pastries, fries and chips with tiered discounts (up to 25%)
- ⭐ Cute review pop-up after every order, an animated review wall, and Instagram-style **Stories** of bestsellers and offers
- 🔐 "Remember me" login, password autofill, show/hide password

**For counters (vendors)**: order queue, menu and stock control, sales charts, payments, reviews and party prep lists.
**For the admin**: overview, customers, payments, behaviour analytics, reviews, basket analysis (Apriori), offers and ads, authority controls, birthday party report.

## 🧠 Data structures and algorithms (by phase)
| Phase | Topic | Where it is used |
|---|---|---|
| 1 | Linked list, stack, queue | Linked lists store users, menu, carts, orders and bookings. A queue per counter holds pending orders. A stack keeps the admin activity log and checks bill expressions. |
| 2 | Binary tree, BST, graph | BST dish search with in/pre/post-order animation (and where a searched dish falls in each order). Canteen graph with adjacency list and matrix, BFS and DFS routes. |
| 3 | Searching and sorting | Linear and binary search, insertion sort and merge sort race with comparison counts; sorting used inside menus, reports and rankings. |
| 4 | Greedy, DP, backtracking | Greedy change-maker for cash orders, 0/1 knapsack budget meal planner, backtracking seat allocator for groups and birthday parties. |

Also: Apriori association rules for "bought together" analysis. The app has a live checklist at `/phases` and an interactive lab at `/algo`, `/tree`, `/map` and `/solve`.

## 🛠 Tech stack
Python 3, Flask, Jinja2, vanilla JavaScript, SVG animations, ReportLab (PDF bills), Segno (UPI QR codes), JSON file storage (`data.json`).

## ▶️ Run locally
    pip install -r requirements.txt
    python app.py          # open http://127.0.0.1:5000
    python tests.py        # runs the automated tests for every phase

## 🔑 Demo logins
- Admin: `admin` / `admin123`
- Counters, Floor 1: `campusfeast` / `feast123`, `zamorin1` / `zamorin123`, `slurrpp` / `slurrpp123`
- Counters, Floor 2: `annaprada` / `anna123`, `zamorin2` / `zamorin456`, `delhibite` / `delhi123`
- Students: register on the login page.

These are demo credentials for a class project. Change them in `VENDOR_LOGINS` and `ADMIN_PASS` (top of `app.py`) before any real use.

## ☁️ Deploy on Render
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --workers 1 --threads 4 --timeout 120`
- Keep a single worker: data lives in memory and is saved to `data.json`. On Render's free plan the file system resets on redeploy.

## 📁 Project structure
    app.py        Flask routes and app logic
    ds.py         Linked list, stack, queue, BST, graph, searches and sorts
    algos.py      Greedy, dynamic programming, backtracking
    mining.py     Apriori basket analysis
    templates/    Jinja pages (student, counter and admin)
    static/       CSS, JS and images
    tests.py      Automated tests for every phase and main pages
    data.json     Seed data (menu, users, orders)

## Settings (top of app.py)
| Setting | Default | Meaning |
|---|---|---|
| `PURE_VEG_FLOORS` | `{1: True, 2: False}` | Floor 1 is veg-only, Floor 2 has veg and non-veg. Change it, restart, and the menu is rebuilt; users and orders are kept. |
| `GST_PERCENT` | `5` | GST line on the bill. It is already inside the menu prices, so totals never change. `0` hides the line. |
| `BUSINESS` | CAFEFLOW CANTEEN / Campus Canteen | Name, address line and phone printed at the top of every bill. |
| `VENDOR_LOGINS` | see above | Counter usernames and passwords. |

## Payments
Scan & pay with UPI (a QR for the exact amount, works with Google Pay, PhonePe, Paytm or any UPI app; no UPI ID typed) or Cash on Delivery. Confirmation is simulated. Put your real UPI ID in `UPI_MERCHANT` at the top of app.py to make the QR real. Refunds are flagged when a counter declines a paid order.
Put your real logos in `static/img/pay/` as `gpay.png`, `phonepe.png`, `paytm.png`, `upi.png`, `cod.png` (svg, webp, jpg also work). See the README.txt in that folder.

## Bill
Till-roll receipt (header, date and time, customer, counter, items, subtotal, offers, GST, total, payment method, masked UPI ID, transaction id, thank-you note, barcode).
- On the order page after paying, and at `/bill/<order id>/view` (print or save as PDF from the browser)
- PDF download at `/bill/<order id>`, also attached to the confirmation email
- The customer, the admin, and the counter that cooked the order can open a bill. Admin and counter payment tables link each order number to its bill.

## Email
Set `GMAIL_USER` and `GMAIL_APP_PASSWORD` environment variables to send real emails; otherwise they print in the terminal.

## What came from where
- Base: the final build (admin suite, per-counter vendor sites, seat plan booking, offers, reviews, payments)
- From the backup: the full menu with non-veg dishes (switchable with `PURE_VEG`), and the Phase 1 console program in `legacy/cafeflow_phase1_console.py`
- New: receipt-style bill (PDF and on-screen), payment logo slots, bill access for admin and counters, veg or non-veg choice when adding dishes

## Phase coverage (course plan)
| Phase | Topic | Where in CafeFlow | File |
|---|---|---|---|
| 1 | Linear structures | Linked list stores users, menu, carts, orders, bookings; queue per counter; stack for the activity log and bill expressions | `ds.py` |
| 2 | Trees and graphs | BST dish search, in/pre/post order, canteen graph (adjacency list + matrix), BFS and DFS | `ds.py`, `/tree`, `/map` |
| 3 | Search and sort | Linear and binary search, insertion and merge sort race, sorting inside menu, reports and rankings | `ds.py`, `/algo` |
| 4 | Greedy, DP, backtracking | Greedy change maker (cart, cash orders), DP knapsack budget meal planner (adds to cart), backtracking group seating (books seats) | `algos.py`, `/solve` |

Open `/phases` in the app for a live checklist. Run `python tests.py` to test every phase and the main pages.

## Pre-order (new)
Header tab **Pre-order**: pick a counter, dishes, plan length (1 day … 1 year), start date and pickup time on the calendar. Longer plan = bigger discount (1 day 8% … 1 year 25%; e.g. idli+vada 65 -> 60). Each meal day is released into the counter's normal queue 60 min before pickup, so food is ready and there is no queue. Vendors see demand under **Pre-orders** in the sidebar; plans can be cancelled for a refund of the remaining days.

Bills and admin: every plan gets a bill (Pre-order tab -> Bill, HTML/PDF, shown to the customer, admin and that counter), and the admin has a **Pre-orders** page listing every plan (customer, counter, meal, duration, days served/left, payment, status). Each day's meal also appears as a normal order, with its own bill, in Orders once released.

## Algorithm lab (counter end and admin end)
All four phases also run on the staff sides. Counter: sidebar **Algorithm lab** (queue, menu BST + traversals, BFS/DFS route, merge/insertion sort and binary/linear search on its orders, greedy change, DP rush-hour planner, backtracking stove balancing). Admin: **Algorithm lab** (all queues + activity stack, BST, graph, sorts/searches, greedy change, DP combo designer, backtracking group seating).

## Reviews, stories, remember me (new)
- **Review pop-up:** after an order is placed and the bill shows, a "Thanks for ordering" dialog asks for a 1-5 star rating (the mascot face changes with the stars), quick tags and a comment. Skip with "Maybe later"; the tracking pop-up opens next. Customers can also rate any past order from the header tab **Add reviews**.
- **Shared instantly:** every review goes to the counter (pop-up + `/vendor/reviews`, sidebar **Reviews**) and to the admin (pop-up + `/admin/reviews`). One review per order.
- **Animated display:** a drifting review wall (hover to pause) on Home, Add reviews, the counter reviews page and the admin reviews page; cards fade in as you scroll.
- **Header tabs:** Home, Book a table, Pre-order, Add reviews, Stories (then My orders and the algorithm pages).
- **Stories:** `/stories`, tap-through story circles per counter built from best sellers, offers and fresh 5-star reviews, with an Add to cart button on dish slides.
- **Login:** "Remember me" keeps you signed in for 30 days and remembers your name; browser/password-manager autofill is enabled; Show/Hide password toggle.

## Plan a Birthday Party (new)
Always the first ad in **Offers for you** on the student home page, and a header tab **Plan a party** (`/party`).
- Pick the birthday star, an optional cake message, date (pre-book at least 1 day ahead, up to 60), party time and 4 to 30 guests.
- Add cakes (500 g / 1 kg), cupcakes, pastries, desserts, fries platters, chips, snacks and drinks from Brew and Roll, or tap a quick pack (Cake + candles, Pastry for everyone, Fries & chips, A drink each).
- **Discount:** 4+ guests 10%, 10+ guests 15%, 20+ guests 20%, plus 5% extra when booked 3+ days ahead (max 25%). The live summary shows the price, savings and how many more guests unlock the next tier. Edit `PARTY_TIERS`, `PARTY_EARLY`, `PARTY_MAX_PCT` in app.py.
- **Free perks:** candles and cake message always; balloons and a banner at 10+ guests; party poppers at 20+.
- **Tables:** the Phase 4 backtracking seat planner finds free tables for the whole group and holds them for 2 hours.
- **Pay:** UPI QR or cash on collection. Confirmation notifies the admin and each counter involved, emails the customer, and creates a party bill (HTML and PDF).
- **Fulfilment:** 2 hours before the party the order is split into a normal order for each counter (with the candles and the cake message as lines). Customers can copy an invite text, view the bill or cancel (tables are released, UPI is flagged for refund).
- **Admin:** sidebar **Birthday parties** (all parties, value, discounts, tables). **Counter:** sidebar **Birthday parties** (upcoming items to prepare).
