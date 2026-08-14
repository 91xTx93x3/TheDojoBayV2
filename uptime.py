"""Persistent rolling availability history for Dojo nodes."""
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class UptimeHistory:
    """Record health-check samples and annotate results with 30-day uptime."""

    def __init__(self, history_file: Path, window_days: int = 30):
        self.history_file = history_file
        self.window = timedelta(days=window_days)
        self._lock = threading.Lock()

    def record(
        self,
        results: Dict[str, Any],
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Persist this check and add rolling uptime fields to each node."""
        checked_at = now or datetime.now(timezone.utc)
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=timezone.utc)
        checked_at = checked_at.astimezone(timezone.utc)
        cutoff = checked_at - self.window

        with self._lock:
            history = self._load()
            nodes = history.setdefault("nodes", {})
            current_keys = set()

            for network in ("mainnet", "testnet"):
                for entry in results.get(network, []):
                    key = self._node_key(network, entry)
                    current_keys.add(key)
                    node = nodes.setdefault(key, {
                        "network": network,
                        "name": entry.get("name", ""),
                        "first_checked": checked_at.isoformat(),
                        "samples": [],
                    })
                    node["name"] = entry.get("name", node.get("name", ""))
                    node["samples"] = [
                        sample for sample in node.get("samples", [])
                        if self._parse_timestamp(sample[0]) >= cutoff
                    ]

                    if entry.get("status") in {"Active", "Inactive"}:
                        node["samples"].append([
                            checked_at.isoformat(),
                            entry["status"] == "Active",
                        ])
                    self._annotate(entry, node)

            history["nodes"] = {
                key: node for key, node in nodes.items()
                if key in current_keys or any(
                    self._parse_timestamp(sample[0]) >= cutoff
                    for sample in node.get("samples", [])
                )
            }
            self._save(history)

        return results

    @staticmethod
    def _node_key(network: str, entry: Dict[str, Any]) -> str:
        url = entry.get("pairing", {}).get("url") or entry.get("url")
        identifier = url or entry.get("name", "")
        return f"{network}:{identifier}"

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _annotate(entry: Dict[str, Any], node: Dict[str, Any]) -> None:
        samples = node.get("samples", [])
        if not samples:
            return
        active = sum(bool(sample[1]) for sample in samples)
        entry["uptime_30d"] = round(active * 100 / len(samples), 1)
        entry["uptime_checks"] = len(samples)
        entry["uptime_since"] = node["first_checked"]

    def _load(self) -> Dict[str, Any]:
        if not self.history_file.exists():
            return {"version": 1, "nodes": {}}
        with self.history_file.open() as source:
            payload = json.load(source)
        if payload.get("version") != 1 or not isinstance(payload.get("nodes"), dict):
            raise ValueError("Unsupported uptime history format")
        return payload

    def _save(self, history: Dict[str, Any]) -> None:
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.history_file.with_suffix(self.history_file.suffix + ".tmp")
        with temporary.open("w") as destination:
            json.dump(history, destination, separators=(",", ":"))
        os.replace(temporary, self.history_file)
