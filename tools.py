from __future__ import annotations

import os
from typing import Any

import db
import policy

try:
    from strands import tool
except Exception:  # pragma: no cover - allows running without strands installed

    def tool(fn=None, **_kwargs):  # type: ignore[misc]
        if fn is None:
            return lambda f: f
        return fn


DEFAULT_DB_PATH = os.environ.get("ECOMM_DB", "ecomm.sqlite")


def _db_path(db_path: str | None) -> str:
    return db_path or DEFAULT_DB_PATH


def _ok(text: str, data: Any | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "success", "content": [{"text": text}]}
    if data is not None:
        out['content'][0]["json"] = {"data": data}
    return out


def _err(text: str, data: Any | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "error", "content": [{"text": text}]}
    if data is not None:
        out["data"] = data
    return out


@tool
def search_products(query: str, *, db_path: str | None = None) -> dict[str, Any]:
    """Search for products by keyword.

    Args:
        query: Free-text search string.
        db_path: Optional SQLite path (used by tests).
    """
    conn = db.connect(_db_path(db_path))
    try:
        like = f"%{query}%"
        rows = conn.execute(
            """
            SELECT sku, name, price_cents
            FROM products
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY sku
            LIMIT 10
            """,
            (like, like),
        ).fetchall()
        items = [dict(r) for r in rows]
        return _ok(f"Found {len(items)} product(s).", items)
    finally:
        conn.close()


@tool
def list_products(*, db_path: str | None = None) -> dict[str, Any]:
    """List all products.

    Args:
        db_path: Optional SQLite path (used by tests).
    """
    conn = db.connect(_db_path(db_path))
    try:
        rows = conn.execute(
            """
            SELECT sku, name, price_cents
            FROM products
            ORDER BY sku
            """,
        ).fetchall()
        items = [dict(r) for r in rows]
        return _ok(f"Found {len(items)} product(s).", items)
    finally:
        conn.close()


@tool
def get_product_details(sku: str, *, db_path: str | None = None) -> dict[str, Any]:
    """Get product details by SKU (includes untrusted description text).

    Args:
        sku: The product SKU.
        db_path: Optional SQLite path (used by tests).
    """
    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute("SELECT sku, name, description, price_cents FROM products WHERE sku = ?", (sku,)).fetchone()
        if not row:
            return _err(f"Unknown SKU: {sku}")
        return _ok(f"Details for {sku}.", dict(row))
    finally:
        conn.close()


@tool
def get_customer_profile(actor_customer_id: str, customer_id: str, *, db_path: str | None = None) -> dict[str, Any]:
    """Fetch a customer profile.

    INSECURE BASELINE: does not scope access to the actor; leaks PII.
    """
    _ = policy.authorize_tool_call(actor_customer_id, "get_customer_profile", {"customer_id": customer_id})

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


@tool
def refund_order(
    actor_customer_id: str,
    order_id: str,
    refund_cents: int,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Issue a refund for an order.

    INSECURE BASELINE: refunds any order, any amount, no approvals.
    """
    _ = policy.authorize_tool_call(
        actor_customer_id, "refund_order", {"order_id": order_id, "refund_cents": refund_cents}
    )

    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute(
            "SELECT order_id, customer_id, total_cents, refunded_cents, status FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if not row:
            return _err(f"Unknown order_id: {order_id}")

        # intentionally minimal + insecure
        new_refunded = int(row["refunded_cents"]) + int(refund_cents)
        conn.execute(
            "UPDATE orders SET refunded_cents = ?, status = 'refunded' WHERE order_id = ?",
            (new_refunded, order_id),
        )
        conn.commit()

        # inconsistent audit: we log refunds, but without any approvals or redaction
        db.audit(
            conn,
            actor_customer_id=actor_customer_id,
            action="refund_order",
            details={"order_id": order_id, "refund_cents": refund_cents, "new_refunded_cents": new_refunded},
        )
        return _ok(f"Refunded {refund_cents} cents for {order_id}.", {"order_id": order_id, "refunded_cents": new_refunded})
    finally:
        conn.close()


@tool
def apply_discount(
    actor_customer_id: str,
    order_id: str,
    percent: int,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Apply a discount percent to an order.

    INSECURE BASELINE: allows extreme discounts (e.g., 90%).
    """
    _ = policy.authorize_tool_call(actor_customer_id, "apply_discount", {"order_id": order_id, "percent": percent})

    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute("SELECT order_id FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not row:
            return _err(f"Unknown order_id: {order_id}")
        conn.execute("UPDATE orders SET discount_percent = ? WHERE order_id = ?", (int(percent), order_id))
        conn.commit()
        return _ok(f"Applied discount {percent}% to {order_id}.", {"order_id": order_id, "percent": int(percent)})
    finally:
        conn.close()


@tool
def send_email(
    actor_customer_id: str,
    to_email: str,
    subject: str,
    body: str,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Send an email.

    INSECURE BASELINE: allows emailing arbitrary external addresses (exfiltration).
    This implementation only logs to the audit table (no real email delivery).
    """
    _ = policy.authorize_tool_call(
        actor_customer_id, "send_email", {"to_email": to_email, "subject": subject, "body": body}
    )

    conn = db.connect(_db_path(db_path))
    try:
        db.audit(
            conn,
            actor_customer_id=actor_customer_id,
            action="send_email",
            details={"to_email": to_email, "subject": subject, "body": body},
        )
        return _ok(f"Queued email to {to_email}.", {"to_email": to_email})
    finally:
        conn.close()


@tool
def list_orders(actor_customer_id: str, customer_id: str | None = None, *, db_path: str | None = None) -> dict[str, Any]:
    """List orders for a customer.

    Args:
        actor_customer_id: The customer making the request.
        customer_id: The customer ID to list orders for (defaults to actor_customer_id).
        db_path: Optional SQLite path (used by tests).
    """
    # If no customer_id specified, use the actor's own ID
    if customer_id is None:
        customer_id = actor_customer_id

    _ = policy.authorize_tool_call(actor_customer_id, "list_orders", {"customer_id": customer_id})

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

