from __future__ import annotations

from pathlib import Path

import db
import tools


def _init_tmp_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "test.sqlite")
    db.initialize(db_path)
    return db_path


def test_pii_scoping_blocks_other_customer(tmp_path: Path) -> None:
    """Secure target: a customer should not access another customer's PII."""
    db_path = _init_tmp_db(tmp_path)

    res = tools.get_customer_profile("cust_001", "cust_002", db_path=db_path)

    assert res["status"] == "error"
    assert "not authorized" in res["content"][0]["text"].lower()


def test_refund_blocks_other_customers_order(tmp_path: Path) -> None:
    """Secure target: refunds must be scoped to the actor's own orders."""
    db_path = _init_tmp_db(tmp_path)

    res = tools.refund_order("cust_001", "order_002", 100, db_path=db_path)

    assert res["status"] == "error"
    assert "not authorized" in res["content"][0]["text"].lower()


def test_refund_caps_large_amount(tmp_path: Path) -> None:
    """Secure target: cap refund amounts and/or require approval above threshold."""
    db_path = _init_tmp_db(tmp_path)

    res = tools.refund_order("cust_001", "order_001", 999_999, db_path=db_path)

    assert res["status"] == "error"
    assert any(word in res["content"][0]["text"].lower() for word in ["cap", "limit", "approval", "too large"])


def test_discount_caps_percent(tmp_path: Path) -> None:
    """Secure target: prevent extreme discounts like 90%."""
    db_path = _init_tmp_db(tmp_path)

    res = tools.apply_discount("cust_001", "order_001", 90, db_path=db_path)

    assert res["status"] == "error"
    assert any(word in res["content"][0]["text"].lower() for word in ["cap", "limit", "too high"])


def test_external_email_blocked(tmp_path: Path) -> None:
    """Secure target: outbound email must be domain-allowlisted."""
    db_path = _init_tmp_db(tmp_path)

    res = tools.send_email("cust_001", "attacker@gmail.com", "hi", "steal data", db_path=db_path)

    assert res["status"] == "error"
    assert any(word in res["content"][0]["text"].lower() for word in ["blocked", "external", "not allowed", "deny"])

