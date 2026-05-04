You’re right. Here is a **Module 1 fix section** you can use.

## 🛠️ Fix: Enforce Customer Ownership in the Tools

The vulnerability is not in the model. The tools accept both:

```python
actor_customer_id
customer_id
```

…but they do not enforce that they match.

### Goal

A customer may only access their own:

* profile
* orders

Accessing another customer’s data must fail closed.

---

## Step 1: Fix `get_customer_profile`

In `tools.py`, update `get_customer_profile` before the database query:

```python
@tool
def get_customer_profile(actor_customer_id: str, customer_id: str, *, db_path: str | None = None) -> dict[str, Any]:
    """Fetch a customer profile."""

    if actor_customer_id != customer_id:
        return _err(f"Not authorized to access profile for customer_id: {customer_id}")

    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute(
            "SELECT customer_id, full_name, email, shipping_address FROM customers WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        if not row:
            return _err(f"Unknown customer_id: {customer_id}")
        return _ok(f"Profile for {customer_id}.", dict(row))
    finally:
        conn.close()
```

---

## Step 2: Fix `list_orders`

Also in `tools.py`:

```python
@tool
def list_orders(actor_customer_id: str, customer_id: str | None = None, *, db_path: str | None = None) -> dict[str, Any]:
    """List orders for a customer."""

    if customer_id is None:
        customer_id = actor_customer_id

    if actor_customer_id != customer_id:
        return _err(f"Not authorized to list orders for customer_id: {customer_id}")

    conn = db.connect(_db_path(db_path))
    try:
        rows = conn.execute(
            """
            SELECT order_id, sku, qty, total_cents, discount_percent, refunded_cents, status, created_at
            FROM orders
            WHERE customer_id = ?
            ORDER BY created_at DESC
            """,
            (customer_id,),
        ).fetchall()

        orders = [dict(r) for r in rows]
        if not orders:
            return _ok(f"No orders found for customer {customer_id}.", [])

        return _ok(f"Found {len(orders)} order(s) for customer {customer_id}.", orders)
    finally:
        conn.close()
```

---

## Step 3: Validate the fix

Run:

```bash
pytest tests/test_guardrails.py::test_pii_scoping_blocks_other_customer
```

I’d also add a dedicated test for orders, because Module 1 includes both profile and order access:

```python
def test_order_scoping_blocks_other_customer(tmp_path: Path) -> None:
    db_path = _init_tmp_db(tmp_path)

    res = tools.list_orders("cust_001", "cust_002", db_path=db_path)

    assert res["status"] == "error"
    assert "not authorized" in res["content"][0]["text"].lower()
```

---

## Teaching point

> The model should behave politely, but the tool must behave securely.
> Authorization belongs in deterministic code, close to the data access.

