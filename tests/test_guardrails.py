from __future__ import annotations

from pathlib import Path

import db
import tools


def _init_tmp_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "test.sqlite")
    db.initialize(db_path)
    return db_path

def test_refund_blocks_other_customers_order(tmp_path: Path) -> None:
    """cust_001 must not be able to refund an order that belongs to cust_002."""
    db_path = _init_tmp_db(tmp_path)

    res = tools.refund_order("cust_001", "order_002", 100, db_path=db_path)

    assert res["status"] == "error"
    assert "not authorized" in res["content"][0]["text"].lower()


def test_refund_exceeds_order_total_blocked(tmp_path: Path) -> None:
    """A refund larger than the order total must be rejected."""
    db_path = _init_tmp_db(tmp_path)
    # order_001 total is 2500 cents; requesting far more
    res = tools.refund_order("cust_001", "order_001", 999_999, db_path=db_path)

    assert res["status"] == "error"


def test_discount_exceeds_maximum_blocked(tmp_path: Path) -> None:
    """A discount above the allowed maximum must be rejected."""
    db_path = _init_tmp_db(tmp_path)

    res = tools.apply_discount("cust_001", "order_001", 90, db_path=db_path)

    assert res["status"] == "error"
    assert any(word in res["content"][0]["text"].lower() for word in ["exceed", "maximum", "limit", "cap"])


def test_discount_ownership_enforced(tmp_path: Path) -> None:
    """cust_001 must not be able to apply a discount to cust_002's order."""
    db_path = _init_tmp_db(tmp_path)

    res = tools.apply_discount("cust_001", "order_002", 10, db_path=db_path)

    assert res["status"] == "error"
    assert "not authorized" in res["content"][0]["text"].lower()


def test_external_email_blocked(tmp_path: Path) -> None:
    """Customers must not be able to send email to arbitrary external addresses."""
    db_path = _init_tmp_db(tmp_path)

    res = tools.send_email("cust_001", "attacker@gmail.com", "hi", "steal data", db_path=db_path)

    assert res["status"] == "error"
    assert "not authorized" in res["content"][0]["text"].lower()


def test_pii_scoping_blocks_other_customer(tmp_path: Path) -> None:
    """cust_001 must not be able to read cust_002's profile."""
    db_path = _init_tmp_db(tmp_path)

    res = tools.get_customer_profile("cust_001", "cust_002", db_path=db_path)

    assert res["status"] == "error"
    assert "access" in res["content"][0]["text"].lower()
