# AI Security Workshop: Insecure Strands E‑Commerce Agent

This repo contains an **intentionally insecure** Strands-based e-commerce assistant for running hands-on workshops about:

- prompt injection
- tool authorization
- approvals / risk thresholds
- PII scoping
- outbound exfiltration controls
- auditability

The app is **supposed to start insecure**. The accompanying tests encode the **desired secure behavior**, so the initial version is expected to fail tests until you add guardrails.

## Setup

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11 or higher | |
| `uv` | latest | Fast Python package manager |
| Git | any recent version | |
| AWS CLI | v2 | For configuring your IAM credentials |
| A code editor | — | VS Code recommended |

### 1. Python 3.11+

Check your current version:

```bash
python3 --version
```

If the version shown is below 3.11, install a newer one.

- **macOS** (via Homebrew): `brew install python@3.11`
- **Windows / Linux / macOS alternatives**: download from [python.org/downloads](https://www.python.org/downloads/)

You can also use [pyenv](https://github.com/pyenv/pyenv) to manage multiple Python versions. The repository includes a `.python-version` file that pins the project to Python 3.11.

### 2. `uv` — Python package manager

`uv` is the package manager used by this project. It is significantly faster than `pip` and handles virtual environments automatically.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify: `uv --version` — documentation: [docs.astral.sh/uv](https://docs.astral.sh/uv/)

### 3. AWS CLI v2

The workshop agent calls Amazon Bedrock, so you need the AWS CLI to configure your credentials.

Install instructions by platform: [docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

Verify: `aws --version` — expected output: `aws-cli/2.x.x ...`

### 4. Configure your AWS IAM credentials

You will be given an IAM user with access to the Bedrock model used in this workshop. You will receive:

- **Access Key ID**
- **Secret Access Key**

Configure a named profile for this workshop so it does not interfere with any existing AWS credentials you have:

```bash
aws configure --profile ai-workshop
```

You will be prompted for four values:

```
AWS Access Key ID [None]: <your Access Key ID>
AWS Secret Access Key [None]: <your Secret Access Key>
Default region name [None]: eu-central-1
Default output format [None]: json
```

> **Region is important.** The model used in this workshop is hosted in the AWS EU region. Enter `eu-central-1` exactly.

Verify the profile was saved correctly:

```bash
aws sts get-caller-identity --profile ai-workshop
```

You should see a JSON response with your account and user ARN. If you see an error, double-check the keys and region.

You also need to export the region as an environment variable so the Bedrock client picks it up at runtime:

```bash
export AWS_REGION=eu-central-1
```

Add this to your shell profile (e.g. `~/.zshrc` or `~/.bashrc`) so you don't have to repeat it each session.

### 5. Clone and install

```bash
git clone <repository-url>
cd ai-security-workshop
uv sync
```

`uv sync` creates a virtual environment (`.venv/`) and installs all dependencies from the lock file.

### 6. Verify the setup

Activate the virtual environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

Then run the test suite:

```bash
AWS_PROFILE=ai-workshop pytest -q
```

You should see output like:

```
FAILED tests/test_guardrails.py::test_pii_scoping_blocks_other_customer
FAILED tests/test_guardrails.py::test_refund_blocks_other_customers_order
...
5 failed in 0.XXs
```

**Failing tests are expected at this point.** The tests encode the secure behavior you will implement during the workshop. If the tests run (even if they fail), your environment is set up correctly.

### 7. Start the web interface

```bash
AWS_PROFILE=ai-workshop python server.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser. You should see a chat interface and be able to send messages to the agent.

If port 5000 is already in use:

```bash
AWS_PROFILE=ai-workshop PORT=8080 python server.py
```

Then open [http://localhost:8080](http://localhost:8080) instead.

> **macOS note:** port 5000 is used by AirPlay Receiver by default. Disable it in System Settings → General → AirDrop & Handoff, or use a different port.

## Quick reference

| Task | Command |
|---|---|
| Install dependencies | `uv sync` |
| Activate virtualenv (macOS/Linux) | `source .venv/bin/activate` |
| Set AWS region | `export AWS_REGION=eu-central-1` |
| Start web UI | `AWS_PROFILE=ai-workshop python server.py` |
| Start CLI (LLM mode) | `AWS_PROFILE=ai-workshop python app.py` |
| Start CLI (no LLM) | `ENABLE_LLM=0 python app.py` |
| Run tests | `AWS_PROFILE=ai-workshop pytest -q` |
| Reset database | `python reset_db.py` |

## Troubleshooting

**`uv: command not found`**
Restart your terminal after installing `uv`, or add `~/.local/bin` (macOS/Linux) to your `PATH`.

**`aws sts get-caller-identity` returns an auth error**
Re-run `aws configure --profile ai-workshop` and check for typos. Keys are case-sensitive.

**`python server.py` falls back to command mode or raises a Bedrock error**
Make sure `AWS_PROFILE=ai-workshop` is set. You can test Bedrock connectivity independently:
```bash
aws bedrock list-foundation-models --region eu-central-1 --profile ai-workshop
```

**Tests error instead of fail**
There is a difference between a test *failing* (assertion not met — expected) and a test *erroring* (exception raised — unexpected). If tests error, check that `uv sync` completed without errors and that your virtualenv is activated.

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