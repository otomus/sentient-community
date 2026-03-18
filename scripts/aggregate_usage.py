#!/usr/bin/env python3
"""Aggregate usage reports from all server instances into a community-wide summary.

Reads individual instance reports from reports/usage_*.json and produces
reports/community_usage.json with combined stats across all instances.

Run manually or via CI:
    python scripts/aggregate_usage.py
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent / "reports"
OUTPUT_FILE = REPORTS_DIR / "community_usage.json"


def aggregate() -> dict:
    """Read all instance reports and merge into a single community summary.

    Returns:
        Dict with 'nerves', 'tools', 'mcps' keys — each a list sorted by
        total calls descending. Also includes 'instances' count and
        'instance_ids' list.
    """
    instance_files = sorted(REPORTS_DIR.glob("usage_*.json"))
    if not instance_files:
        return {"nerves": [], "tools": [], "mcps": [], "instances": 0, "instance_ids": []}

    buckets = {"nerves": defaultdict(lambda: {"total": 0, "successes": 0, "failures": 0}),
               "tools": defaultdict(lambda: {"total": 0, "successes": 0, "failures": 0}),
               "mcps": defaultdict(lambda: {"total": 0, "successes": 0, "failures": 0})}
    instance_ids = []

    for path in instance_files:
        try:
            report = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        instance_id = report.get("instance_id", path.stem.removeprefix("usage_"))
        instance_ids.append(instance_id)

        for category in ("nerves", "tools", "mcps"):
            for entry in report.get(category, []):
                name = entry["name"]
                buckets[category][name]["total"] += entry.get("total", 0)
                buckets[category][name]["successes"] += entry.get("successes", 0)
                buckets[category][name]["failures"] += entry.get("failures", 0)

    result = {"instances": len(instance_ids), "instance_ids": instance_ids}

    for category in ("nerves", "tools", "mcps"):
        entries = []
        for name, stats in buckets[category].items():
            total = stats["total"]
            failures = stats["failures"]
            entries.append({
                "name": name,
                "total": total,
                "successes": stats["successes"],
                "failures": failures,
                "error_rate": round(failures / total, 4) if total else 0,
            })
        entries.sort(key=lambda e: e["total"], reverse=True)
        result[category] = entries

    return result


def main():
    """Aggregate and write the community usage summary."""
    summary = aggregate()
    OUTPUT_FILE.write_text(json.dumps(summary, indent=2) + "\n")

    print(f"Aggregated {summary['instances']} instance(s):")
    print(f"  Nerves: {len(summary['nerves'])}")
    print(f"  Tools:  {len(summary['tools'])}")
    print(f"  MCPs:   {len(summary['mcps'])}")
    print(f"Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
