ToDo: the solution needs to be updated because we will do it differently

## Fix: Remove `actor_customer_id` from Tool Parameters

The core vulnerability is architectural: the LLM can independently specify `actor_customer_id`, allowing it to impersonate any customer. The LLM is not inherently trustworthy.

### Goal

The `actor_customer_id` should come from **system context**, not from tool parameters the LLM controls. The actor should be baked into the tool wrapper, not exposed to the model.

<details>
<summary>Hint 1</summary>

## Step 1: Create Wrapped Tool Functions in `tools.py`

Create internal tools that accept `actor_customer_id` from the caller, and public tool stubs that DO NOT expose it to the LLM:

```python
# Keep the existing tool functions but mark them as internal
def _get_customer_profile_impl(
    actor_customer_id: str,
    customer_id: str,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Internal implementation of get_customer_profile."""
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

# Create a PUBLIC tool that the LLM sees (no actor_customer_id parameter)
@tool
def get_customer_profile(customer_id: str, *, db_path: str | None = None) -> dict[str, Any]:
    """Fetch a customer profile (your own profile only).

    Args:
        customer_id: The customer ID to fetch (must be your own).
    """
    # Get the actor from the system context (set at agent init time)
    actor_customer_id = os.environ.get("ACTOR_CUSTOMER_ID", "cust_001")
    return _get_customer_profile_impl(actor_customer_id, customer_id, db_path=db_path)
```
</details>


## Step 2: Apply Same Pattern to All Sensitive Tools

Do the same for `list_orders`, `refund_order`, `apply_discount`, and `send_email`:

<details>
<summary>Hint 2</summary>

```python
def _list_orders_impl(actor_customer_id: str, customer_id: str | None = None, *, db_path: str | None = None) -> dict[str, Any]:
    """Internal implementation."""
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


@tool
def list_orders(customer_id: str | None = None, *, db_path: str | None = None) -> dict[str, Any]:
    """List your orders."""
    actor_customer_id = os.environ.get("ACTOR_CUSTOMER_ID", "cust_001")
    return _list_orders_impl(actor_customer_id, customer_id, db_path=db_path)
```

</details>

Repeat for `refund_order`, `apply_discount`, and `send_email`.

---

## Step 3: Update `app.py` Command Mode

For command-line mode, pass `ACTOR_CUSTOMER_ID` via environment:

<details>
<summary>Hint 3</summary>

```python
def _command_mode() -> None:
    # Already set: ACTOR_CUSTOMER_ID from environment
    print(f"Logged in as: {ACTOR_CUSTOMER_ID}")

    # Tools are now called without specifying actor_customer_id
    # They fetch it from os.environ internally
    if raw.startswith("profile "):
        cid = raw.removeprefix("profile ").strip()
        _print_result(ecomm_tools.get_customer_profile(cid, db_path=DB_PATH))
```
</details>

## Step 4: Validate the fix

Run:

```bash
pytest tests/test_guardrails.py::test_pii_scoping_blocks_other_customer
```

---

## Teaching Points

1. **Never expose security context to the model**: `actor_customer_id` is security context, not a user input parameter.

2. **Principle of least privilege for parameters**: The LLM should only see the parameters it *needs* to control. Identity is not one of them.

3. **Environment-based identity**: System context (like actor identity) belongs in environment variables or injected at initialization time, not in tool signatures.

4. **Defense in depth**: Even if an LLM prompt is injected, it cannot change who it is acting as—the identity is baked into the tool layer, not exposed for manipulation.

5. **Comparison**: This is like operating systems restricting system calls; user code cannot change its own uid/gid—it's enforced at the kernel level.
