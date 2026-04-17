# AI Security Workshop: Insecure Strands E‑Commerce Agent

This repo contains an **intentionally insecure** Strands-based e-commerce assistant for running hands-on workshops about:

- prompt injection
- tool authorization
- approvals / risk thresholds
- PII scoping
- outbound exfiltration controls
- auditability

The app is **supposed to start insecure**. The accompanying tests encode the **desired secure behavior**, so the initial version is expected to fail tests until you add guardrails.

## Quickstart

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you use `pyenv`, make sure Python **3.11+** is installed/active (this repo includes a `.python-version`).

### Run the app (LLM mode by default)

```bash
python app.py
```

By default, the CLI **tries to start in LLM mode** (natural-language chat) and falls back to command mode if Strands/model configuration isn’t available.
### Run the web chat interface

```bash
python server.py
```

Then open http://localhost:5000 in your browser. The web interface provides a chat UI for interacting with the agent.

If port 5000 is already in use, specify a different port:

```bash
PORT=8080 python server.py
```

Then open http://localhost:8080 in your browser.
### Force command mode (no LLM)

```bash
ENABLE_LLM=0 python app.py
```

### Run tests

```bash
pytest -q
```

OR

```bash
python -m pytest -q
```

### Reset the database

To reset the database to its initial state (deletes all changes and reinitializes seed data):

```bash
python reset_db.py
```

**Note:** tests are expected to fail at first. The workshop exercise is to implement guardrails (typically in `policy.py` and enforced by `tools.py`) so the tests pass.

## Repository tour

- `app.py`: CLI entrypoint (optionally uses a Strands `Agent`)
- `server.py`: Web server with Flask (serves chat UI on http://localhost:5000)
- `reset_db.py`: Script to reset the database to initial state
- `db.py`: SQLite schema + seed data (includes a malicious product description with prompt injection)
- `tools.py`: Strands tools (intentionally vulnerable)
- `policy.py`: policy abstraction (exists but initially permissive / unused)
- `prompts.py`: deliberately unsafe system prompt
- `templates/`: HTML templates for the web interface
- `tests/test_guardrails.py`: target secure behavior (fails initially)