from __future__ import annotations

import json
import os
from typing import Any

from flask import Flask, render_template, request, jsonify

import db
from prompts import SYSTEM_PROMPT
import tools as ecomm_tools

app = Flask(__name__, template_folder="templates")

ACTOR_CUSTOMER_ID = os.environ.get("ACTOR_CUSTOMER_ID", "cust_001")
DB_PATH = os.environ.get("ECOMM_DB", "ecomm.sqlite")
MODEL_ID = "eu.amazon.nova-2-lite-v1:0"
PORT = int(os.environ.get("PORT", 5000))

# Global agent instance
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        try:
            from strands import Agent  # type: ignore[import-not-found]

            model = os.environ.get("STRANDS_MODEL") or MODEL_ID
            _agent = Agent(
                model=model,
                system_prompt=SYSTEM_PROMPT,
                callback_handler=None,
                tools=[
                    ecomm_tools.search_products,
                    ecomm_tools.get_product_details,
                    ecomm_tools.get_customer_profile,
                    ecomm_tools.list_orders,
                    ecomm_tools.refund_order,
                    ecomm_tools.apply_discount,
                    ecomm_tools.send_email,
                ],
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize agent: {e}")
    return _agent


@app.route("/")
def index():
    """Serve the chat interface."""
    return render_template("index.html", actor_customer_id=ACTOR_CUSTOMER_ID)


@app.route("/api/chat", methods=["POST"])
def chat():
    """Handle chat messages and return agent responses."""
    try:
        data = request.get_json()
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"error": "Empty message"}), 400

        agent = _get_agent()
        result = agent(message, invocation_state={"actor_customer_id": ACTOR_CUSTOMER_ID, "db_path": DB_PATH})

        # Extract response from agent result (AgentResult object)
        try:
            # AgentResult is an object, not a dict
            if hasattr(result, "message"):
                msg = result.message
            else:
                msg = result

            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", []) or []
            text = ""
            json_data = None

            if isinstance(content, list) and content:
                if isinstance(content[0], dict):
                    text = content[0].get("text", "")
                    json_data = content[0].get("json", None)

            return jsonify({"response": text, "data": json_data})
        except Exception as e:
            return jsonify({"response": f"Error processing response: {e}", "data": None})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "actor_customer_id": ACTOR_CUSTOMER_ID})


def main():
    """Run the web server."""
    db.initialize(DB_PATH)
    print(f"Starting chat server...")
    print(f"Logged in as: {ACTOR_CUSTOMER_ID}")
    print(f"Open http://localhost:{PORT} in your browser")
    app.run(debug=False, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
