"""
CafeFlow -- Simple Campus Canteen Ordering System (Phase 1, Python)
=====================================================================
Linear Data Structures Implementation (CLO1)

Flow:
  Register / Login (user)  ->  Browse menu  ->  Place order (pay)
  ->  Order is PENDING  ->  Admin accepts/rejects  ->  user sees status.

Data structures used:
  - Node + LinkedList (generic, reused for Users, MenuItems, Orders)
      -> demonstrates insert / delete / search / traverse
  - Stack (linked-list based)
      -> operation history log
      -> stack-based postfix expression evaluation (used for real bill math)
  - Queue (linked-list based)
      -> pending-orders line: admin reviews orders in the order they
         were placed (FIFO), fair and simple

No canteens, counters, floors, or roles -- just one simple canteen.
Emails are SIMULATED (printed, not actually sent) since real sending
needs the user's own email credentials configured separately.
"""

import time


# =====================================================================
# SIMULATED EMAIL
# =====================================================================
def send_email(to_email, subject, message):
    """Prints what WOULD be emailed. Not a real send -- see module docstring."""
    print("\n  [Simulated Email]")
    print(f"    To: {to_email}")
    print(f"    Subject: {subject}")
    print(f"    Message: {message}")
    print("    (This is a simulated email for demo purposes.)")


# =====================================================================
# RECORDS -- the project's input data
# =====================================================================
class User:
    def __init__(self, user_id, name, email, password):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.password = password

    def __str__(self):
        return f"User[{self.user_id}] {self.name} <{self.email}>"


class MenuItem:
    def __init__(self, item_code, name, price, category):
        self.item_code = item_code
        self.name = name
        self.price = price
        self.category = category

    def __str__(self):
        return f"{self.item_code}. {self.name} - Rs.{self.price}"


class Order:
    _counter = 1000

    def __init__(self, user_id, items, amount):
        Order._counter += 1
        self.order_id = Order._counter
        self.user_id = user_id
        self.items = items          # dict: item_code -> quantity
        self.amount = amount
        self.status = "PENDING"     # PENDING / CONFIRMED / REJECTED
        self.order_time = time.strftime("%H:%M:%S")
        self.decision_time = None

    def __str__(self):
        return (f"Order #{self.order_id} | user {self.user_id} | "
                f"Rs.{self.amount} | {self.status} | placed {self.order_time}")


# =====================================================================
# GENERIC NODE + LINKED LIST
# Python's duck typing lets ONE LinkedList class serve Users, MenuItems,
# AND Orders -- no need for three separate typed classes.
# =====================================================================
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None


class LinkedList:
    def __init__(self):
        self.head = None
        self.size = 0

    def insert(self, data):
        node = Node(data)
        if self.head is None:
            self.head = node
        else:
            current = self.head
            while current.next:
                current = current.next
            current.next = node
        self.size += 1

    def delete(self, match_fn):
        """match_fn(data) -> True for the node to remove."""
        current = self.head
        prev = None
        while current:
            if match_fn(current.data):
                if prev is None:
                    self.head = current.next
                else:
                    prev.next = current.next
                self.size -= 1
                return True
            prev = current
            current = current.next
        return False

    def search(self, match_fn):
        current = self.head
        while current:
            if match_fn(current.data):
                return current.data
            current = current.next
        return None

    def traverse(self):
        result = []
        current = self.head
        while current:
            result.append(current.data)
            current = current.next
        return result


# =====================================================================
# STACK (linked-list based, LIFO)
# =====================================================================
class Stack:
    def __init__(self):
        self.top = None
        self.size = 0

    def push(self, data):
        node = Node(data)
        node.next = self.top
        self.top = node
        self.size += 1

    def pop(self):
        if self.top is None:
            return None
        node = self.top
        self.top = node.next
        self.size -= 1
        return node.data

    def peek(self):
        return self.top.data if self.top else None

    def is_empty(self):
        return self.top is None

    def display(self):
        print(f"\n--- Operation history (most recent first), size={self.size} ---")
        if self.is_empty():
            print("  (empty)")
            return
        current = self.top
        while current:
            print("  ", current.data)
            current = current.next


# =====================================================================
# QUEUE (linked-list based, FIFO)
# =====================================================================
class Queue:
    def __init__(self):
        self.front = None
        self.rear = None
        self.size = 0

    def enqueue(self, data):
        node = Node(data)
        if self.rear is None:
            self.front = self.rear = node
        else:
            self.rear.next = node
            self.rear = node
        self.size += 1

    def dequeue(self):
        if self.front is None:
            return None
        node = self.front
        self.front = node.next
        if self.front is None:
            self.rear = None
        self.size -= 1
        return node.data

    def peek(self):
        return self.front.data if self.front else None

    def is_empty(self):
        return self.front is None

    def display(self):
        print(f"\n--- Pending orders queue (front -> rear), size={self.size} ---")
        if self.is_empty():
            print("  (no pending orders)")
            return
        current = self.front
        position = 1
        while current:
            print(f"  {position}. {current.data}")
            current = current.next
            position += 1


# =====================================================================
# STACK-BASED EXPRESSION HANDLING
# Used for REAL bill calculation, not just as an isolated demo:
# selected items are turned into a postfix expression and evaluated
# with a stack, e.g. cart [(70,2), (30,1)] -> "70 2 * 30 1 * +" -> 170
# =====================================================================
def is_balanced(expression):
    stack = Stack()
    for ch in expression:
        if ch == '(':
            stack.push(ch)
        elif ch == ')':
            if stack.is_empty():
                return False
            stack.pop()
    return stack.is_empty()


def evaluate_postfix(expression):
    stack = Stack()
    for token in expression.split():
        if token in ('+', '-', '*', '/'):
            b = stack.pop()
            a = stack.pop()
            if token == '+':
                stack.push(a + b)
            elif token == '-':
                stack.push(a - b)
            elif token == '*':
                stack.push(a * b)
            else:
                stack.push(a / b)
        else:
            stack.push(float(token))
    return stack.pop()


def build_bill_postfix(cart):
    """cart: list of (price, quantity) tuples -> postfix expression string."""
    if not cart:
        return "0"
    price0, qty0 = cart[0]
    tokens = [str(price0), str(qty0), '*']
    for price, qty in cart[1:]:
        tokens += [str(price), str(qty), '*', '+']
    return " ".join(tokens)


# =====================================================================
# THE SYSTEM -- wires records + structures together
# =====================================================================
ADMIN_ID = "admin"
ADMIN_PASSWORD = "admin123"


class CafeFlowSystem:
    def __init__(self):
        self.users = LinkedList()
        self.menu = LinkedList()
        self.orders = LinkedList()
        self.pending_queue = Queue()
        self.history = Stack()

        self.next_user_id = 1
        self.next_item_code = 1
        self.current_user = None   # session state: who is logged in

        self._seed_menu()

    def _seed_menu(self):
        starter_items = [
            ("Veg Thali", 70, "Main Food"),
            ("Paneer Butter Masala", 80, "Main Food"),
            ("Veg Fried Rice", 60, "Main Food"),
            ("Chicken Fried Rice", 80, "Main Food"),
            ("Masala Chai", 15, "Beverages & Snacks"),
            ("Cold Coffee", 30, "Beverages & Snacks"),
            ("Samosa (2 pc)", 20, "Beverages & Snacks"),
            ("Veg Burger", 45, "Fast Food"),
            ("French Fries", 50, "Fast Food"),
            ("Veg Roll", 40, "Fast Food"),
            ("Chocolate Pastry", 40, "Bakery"),
            ("Donut", 30, "Bakery"),
        ]
        for name, price, category in starter_items:
            self.menu.insert(MenuItem(self.next_item_code, name, price, category))
            self.next_item_code += 1

    # ----------------- USER: register / login -----------------
    def register(self):
        name = input("  Name: ").strip()
        email = input("  Gmail: ").strip()

        if self.users.search(lambda u: u.email == email):
            print("  An account with this email already exists. Please log in instead.")
            return

        password = input("  Password: ").strip()
        confirm = input("  Confirm Password: ").strip()
        if password != confirm:
            print("  Passwords do not match. Registration cancelled.")
            return

        user = User(self.next_user_id, name, email, password)
        self.users.insert(user)
        self.history.push(f"INSERT (register) -> {name} <{email}> id={self.next_user_id}")
        self.next_user_id += 1

        send_email(email, "Registration Successful",
                   f"Welcome to CafeFlow, {name}! Your account has been created.")
        print("  Registration successful! You can now log in.")

    def login(self):
        email = input("  Gmail: ").strip()
        password = input("  Password: ").strip()
        user = self.users.search(lambda u: u.email == email and u.password == password)
        if user:
            self.current_user = user
            print(f"  Welcome back, {user.name}!")
            return True
        print("  Invalid email or password.")
        return False

    # ----------------- USER: menu / order / status -----------------
    def show_menu(self):
        items = self.menu.traverse()
        grouped = {}
        for item in items:
            grouped.setdefault(item.category, []).append(item)

        print("\n===== CafeFlow Menu =====")
        for category, cat_items in grouped.items():
            print(f"-- {category} --")
            for item in cat_items:
                print(f"  {item}")

    def find_item(self, code):
        return self.menu.search(lambda m: m.item_code == code)

    def place_order(self):
        self.show_menu()
        print("\n  Enter items as itemCodexQuantity, comma-separated (e.g. 2x1,5x3)")
        raw = input("  Your order: ").strip()

        cart_items = {}       # item_code -> quantity
        cart_for_bill = []    # list of (price, quantity)

        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            if "x" not in part:
                print(f"  Skipping invalid entry: '{part}' (expected format like 2x1)")
                continue
            code_str, qty_str = part.split("x", 1)
            try:
                code = int(code_str.strip())
                qty = int(qty_str.strip())
            except ValueError:
                print(f"  Could not parse numbers in: '{part}'")
                continue

            item = self.find_item(code)
            if item is None:
                print(f"  Item code {code} not found -- skipping.")
                continue
            if qty <= 0:
                print(f"  Quantity must be positive -- skipping '{part}'.")
                continue

            cart_items[code] = cart_items.get(code, 0) + qty
            cart_for_bill.append((item.price, qty))

        if not cart_items:
            print("  No valid items selected. Order cancelled.")
            return

        postfix_expr = build_bill_postfix(cart_for_bill)
        amount = evaluate_postfix(postfix_expr)

        print("\n  --- Your Bill ---")
        for code, qty in cart_items.items():
            item = self.find_item(code)
            print(f"  {item.name} x{qty} = Rs.{item.price * qty}")
        print(f"  Total: Rs.{amount}")
        print(f"  (Total computed via stack-based postfix evaluation: \"{postfix_expr}\")")

        proceed = input("\n  Proceed to payment? (yes/no): ").strip().lower()
        if proceed != "yes":
            print("  Order cancelled.")
            return

        print("  Processing payment...")
        print(f"  Payment of Rs.{amount} successful (simulated).")

        order = Order(self.current_user.user_id, cart_items, amount)
        self.orders.insert(order)
        self.pending_queue.enqueue(order)
        self.history.push(f"INSERT (order) -> Order #{order.order_id} by {self.current_user.name}")

        print(f"\n  Order placed! Order ID: {order.order_id}")
        print("  Your order is PENDING admin approval.")

    def my_orders(self):
        mine = [o for o in self.orders.traverse() if o.user_id == self.current_user.user_id]
        if not mine:
            print("  You have no orders yet.")
            return

        for o in mine:
            print(f"\n  Order #{o.order_id} -- Status: {o.status}")
            print(f"    Placed at: {o.order_time}")
            for code, qty in o.items.items():
                item = self.find_item(code)
                name = item.name if item else f"item {code}"
                print(f"      {name} x{qty}")
            print(f"    Total: Rs.{o.amount}")
            if o.status == "CONFIRMED":
                print(f"    Confirmed at: {o.decision_time}")
            elif o.status == "REJECTED":
                print(f"    Rejected at: {o.decision_time}")
            else:
                print("    Waiting for admin confirmation...")

    # ----------------- ADMIN actions -----------------
    def admin_view_users(self):
        users = self.users.traverse()
        print(f"\n--- Registered users ({len(users)}) ---")
        if not users:
            print("  (none)")
        for u in users:
            print("  ", u)

    def admin_add_menu_item(self):
        name = input("  Item name: ").strip()
        try:
            price = float(input("  Price: ").strip())
        except ValueError:
            print("  Invalid price.")
            return
        category = input("  Category: ").strip()

        item = MenuItem(self.next_item_code, name, price, category)
        self.menu.insert(item)
        self.history.push(f"INSERT (admin added menu item) -> {name}")
        print(f"  Added: {item}")
        self.next_item_code += 1

    def admin_process_next_order(self):
        if self.pending_queue.is_empty():
            print("  No pending orders.")
            return

        order = self.pending_queue.peek()
        print(f"\n  Next pending order: {order}")
        for code, qty in order.items.items():
            item = self.find_item(code)
            name = item.name if item else f"item {code}"
            print(f"    {name} x{qty}")

        user = self.users.search(lambda u: u.user_id == order.user_id)
        decision = input("  Accept or Reject this order? (a/r): ").strip().lower()
        self.pending_queue.dequeue()
        order.decision_time = time.strftime("%H:%M:%S")

        if decision == "a":
            order.status = "CONFIRMED"
            self.history.push(f"CONFIRMED (admin) -> Order #{order.order_id}")
            if user:
                send_email(user.email, "Order Confirmed",
                           f"Your order #{order.order_id} has been confirmed! Total: Rs.{order.amount}")
            print("  Order confirmed.")
        else:
            order.status = "REJECTED"
            self.history.push(f"REJECTED (admin) -> Order #{order.order_id}")
            if user:
                send_email(user.email, "Order Rejected",
                           f"Sorry, your order #{order.order_id} was rejected.")
            print("  Order rejected.")

    def admin_view_all_orders(self):
        all_orders = self.orders.traverse()
        print(f"\n--- All orders ({len(all_orders)}) ---")
        if not all_orders:
            print("  (none)")
        for o in all_orders:
            print("  ", o)


# =====================================================================
# CONSOLE INTERFACE
# =====================================================================
def print_welcome():
    print("=" * 45)
    print("     WELCOME TO CAFEFLOW CANTEEN")
    print("   Order ahead. Skip the line. Eat sooner.")
    print("=" * 45)


def admin_login(system):
    admin_id = input("  Admin ID: ").strip()
    password = input("  Admin Password: ").strip()
    if admin_id == ADMIN_ID and password == ADMIN_PASSWORD:
        print("  Admin login successful.")
        admin_menu(system)
    else:
        print("  Invalid admin credentials.")


def admin_menu(system):
    while True:
        print("\n----- Admin Menu -----")
        print("1. View all registered users")
        print("2. Add a new menu item")
        print("3. View pending orders")
        print("4. Accept/Reject next pending order")
        print("5. View all orders")
        print("6. View operation history")
        print("0. Logout")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            system.admin_view_users()
        elif choice == "2":
            system.admin_add_menu_item()
        elif choice == "3":
            system.pending_queue.display()
        elif choice == "4":
            system.admin_process_next_order()
        elif choice == "5":
            system.admin_view_all_orders()
        elif choice == "6":
            system.history.display()
        elif choice == "0":
            print("  Logged out.")
            break
        else:
            print("  Invalid option, try again.")


def user_menu(system):
    while True:
        print(f"\n----- User Menu (logged in as {system.current_user.name}) -----")
        print("1. View menu")
        print("2. Place an order")
        print("3. My orders")
        print("0. Logout")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            system.show_menu()
        elif choice == "2":
            system.place_order()
        elif choice == "3":
            system.my_orders()
        elif choice == "0":
            system.current_user = None
            print("  Logged out.")
            break
        else:
            print("  Invalid option, try again.")


def main():
    system = CafeFlowSystem()
    print_welcome()

    while True:
        print("\n===== CafeFlow -- Main Menu =====")
        print("1. Register")
        print("2. Login")
        print("3. Admin Login")
        print("0. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            system.register()
        elif choice == "2":
            if system.login():
                user_menu(system)
        elif choice == "3":
            admin_login(system)
        elif choice == "0":
            print("Exiting. Goodbye!")
            break
        else:
            print("Invalid option, try again.")


if __name__ == "__main__":
    main()
