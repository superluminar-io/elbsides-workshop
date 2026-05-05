## Fix: Restrict Email Access — Customers Should Not Send Emails at All

The central vulnerability is asking the wrong question: *why should a customer be able to send emails at all?* An e-commerce site is not an email provider. The `send_email` tool should not be available to regular customers.

### Goal

Customers may not send emails. This tool is restricted to internal staff or disabled entirely in the customer assistant.

---

## Step 1: Update `allowed_email_recipient` in `policy.py`

The policy function should reject email sending for customer actors:

```python
def allowed_email_recipient(actor_customer_id: str, to_email: str) -> Decision:
    """Check whether the actor is allowed to send email.

    FIXED: Customers are not allowed to send emails. This is an internal-only function.
    """
    return Decision(
        allowed=False,
        reason="Customers are not authorized to send emails. Contact support if you need assistance."
    )
```

---

## Step 2: Update `send_email` in `tools.py`

In `tools.py`, check the policy before allowing any email action:

```python
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

    FIXED: Customers cannot send emails. This is a restricted tool.
    """
    # Check policy: customers are not allowed to send emails
    decision = policy.allowed_email_recipient(actor_customer_id, to_email)
    if not decision.allowed:
        return _err(decision.reason)

    conn = db.connect(_db_path(db_path))
    try:
        # Only reached if policy approves
        db.audit(
            conn,
            actor_customer_id=actor_customer_id,
            action="send_email",
            details={"to_email": to_email, "subject": subject},
        )
        return _ok(f"Queued email to {to_email}.", {"to_email": to_email})
    finally:
        conn.close()
```

---

## Step 3: Alternatively, Remove the Tool Entirely

For a customer-facing assistant, you could simply not register the `send_email` tool at all in `app.py`:

```python
# In app.py, when building the agent:
agent.register_tool(search_products)
agent.register_tool(list_products)
agent.register_tool(get_product_details)
agent.register_tool(get_customer_profile)
agent.register_tool(list_orders)
agent.register_tool(refund_order)
agent.register_tool(apply_discount)
# agent.register_tool(send_email)  # NOT available to customers
```

---

## Step 4: Validate the fix

Run:

```bash
pytest tests/test_guardrails.py::test_email_to_other_customer_blocked
```

---

## Teaching Points

1. **Not every capability should be exposed**: Just because a tool exists doesn't mean the AI should have access to it.

2. **Principle of least privilege**: Customers need to browse, refund, and discount. They do not need to send emails.

3. **Policy as a safety net**: Even if a tool is accidentally registered, the policy layer can reject it.

4. **Role-based access control**: In a mature system, different actors (customers, support staff, admins) would have different tool access. This is a simple example of that principle.
