"""Standalone external API for Dojobay.

This file does not modify app.py and can run independently.
"""

from flask import Flask, jsonify, request
import json
import os
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "dojos_data.json"
VALID_NETWORKS = {"mainnet", "testnet"}
DEFAULT_API_TOKEN = "FREESAMOURAI"

app = Flask(__name__)


def require_api_token():
    """Validate Authorization: Bearer <token> against env var token."""
    expected_token = os.getenv("DOJOBAY_API_TOKEN", DEFAULT_API_TOKEN).strip()

    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header.startswith("Bearer "):
        return (
            jsonify(
                {
                    "error": "Unauthorized",
                    "hint": "Use header: Authorization: Bearer <token>",
                }
            ),
            401,
        )

    received_token = auth_header.replace("Bearer ", "", 1).strip()
    if received_token != expected_token:
        return jsonify({"error": "Unauthorized", "hint": "Invalid token"}), 401

    return None


def load_dojos_data():
    """Load Dojo data from disk."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("mainnet", []), data.get("testnet", [])


def pick_electrum_server(dojo):
    """Extract electrum server-like URL from known fields."""
    return (
        dojo.get("electrum_server")
        or dojo.get("explorer", {}).get("url")
        or dojo.get("pairing", {}).get("url")
    )


def normalize_dojo(dojo, network):
    """Return the public API shape requested by user."""
    return {
        "user": dojo.get("user") or dojo.get("paynym") or "unknown",
        "name": dojo.get("name", "unknown"),
        "network": network,
        "electrum_server": pick_electrum_server(dojo),
    }


def parse_network_filter():
    """Validate optional ?network=mainnet|testnet filter."""
    network = request.args.get("network", "").strip().lower()
    if network and network not in VALID_NETWORKS:
        return None, jsonify(
            {
                "error": "Invalid network value",
                "allowed": sorted(list(VALID_NETWORKS)),
                "example": "/api/dojos?network=mainnet",
            }
        ), 400
    return network, None, None


@app.route("/api/dojos", methods=["GET"])
def api_dojos():
    """Public endpoint with user, name, network and electrum_server."""
    try:
        auth_error = require_api_token()
        if auth_error is not None:
            return auth_error

        network_filter, err_body, err_code = parse_network_filter()
        if err_body is not None:
            return err_body, err_code

        mainnet, testnet = load_dojos_data()

        dojos = []
        if not network_filter or network_filter == "mainnet":
            dojos.extend(normalize_dojo(d, "mainnet") for d in mainnet)
        if not network_filter or network_filter == "testnet":
            dojos.extend(normalize_dojo(d, "testnet") for d in testnet)

        examples = [
            {
                "user": "91xTx93x3",
                "name": "TantoE",
                "network": "mainnet",
                "electrum_server": "3xmxfolrxdyaqbfwohdxsntem4agugpbozb2u5re2vrwhpgkl6c5ufqd.onion:50001",
            },
            {
                "user": "example_user_2",
                "name": "Example Testnet Dojo",
                "network": "testnet",
                "electrum_server": "electrum://example-testnet.onion:60001",
            },
            {
                "user": "example_user_3",
                "name": "Example Node 3",
                "network": "mainnet",
                "electrum_server": "electrum://example-node-3.onion:50001",
            },
        ]

        return jsonify(
            {
                "count": len(dojos),
                "filter": network_filter or "all",
                "dojos": dojos,
                "examples": examples,
            }
        )
    except FileNotFoundError:
        return jsonify({"error": "dojos_data.json not found"}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "dojos_data.json has invalid JSON"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Basic health endpoint for API checks."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
