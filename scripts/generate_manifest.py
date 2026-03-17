#!/usr/bin/env python3
"""Generate manifest.json by walking the repo tree.

Reads all bundle.json, meta.json, and connector meta.json files
and builds a unified manifest for discovery and search.
"""

import json
import os
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_SIZE_CLASS = "unknown"


def _load_json(path: str) -> dict | None:
    """Load and return parsed JSON from *path*, or None on any error."""
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _sorted_subdirs(parent: str) -> list[str]:
    """Return sorted directory names directly under *parent*."""
    if not os.path.isdir(parent):
        return []
    return [
        name for name in sorted(os.listdir(parent))
        if os.path.isdir(os.path.join(parent, name))
    ]


def _extract_model_scores(bundle: dict) -> dict:
    """Extract per-model scores from a nerve bundle's model_adapters map."""
    model_scores = {}
    for model, adapter in bundle.get("model_adapters", {}).items():
        if "score" in adapter:
            model_scores[model] = adapter["score"]
    return model_scores


def _build_nerve_entry(bundle: dict) -> dict:
    """Build a single nerve manifest entry from a parsed bundle."""
    return {
        "description": bundle.get("description", ""),
        "role": bundle.get("role", "tool"),
        "tags": bundle.get("tags", []),
        "authors": bundle.get("authors", []),
        "version": bundle.get("version", "1.0"),
        "tools": [t["name"] for t in bundle.get("tools", [])],
        "model_scores": _extract_model_scores(bundle),
    }


def collect_nerves() -> dict:
    """Walk nerves/ and extract bundle info."""
    nerves = {}
    nerves_dir = os.path.join(REPO_ROOT, "nerves")

    for name in sorted(os.listdir(nerves_dir)) if os.path.isdir(nerves_dir) else []:
        bundle = _load_json(os.path.join(nerves_dir, name, "bundle.json"))
        if bundle is None:
            continue
        nerves[name] = _build_nerve_entry(bundle)

    return nerves


def _read_qualification_score(adapter_dir: str) -> float | None:
    """Return the overall_score from qualification.json, or None if unavailable."""
    qual = _load_json(os.path.join(adapter_dir, "qualification.json"))
    if qual is None:
        return None
    return qual.get("overall_score")


def _build_adapter_entry(meta: dict, role: str, size_class: str,
                         model_name: str | None, score: float | None) -> dict:
    """Build a single adapter manifest entry from parsed metadata."""
    return {
        "role": role,
        "model": meta.get("model", model_name or size_class),
        "size_class": meta.get("size_class", size_class),
        "provider": meta.get("provider", ""),
        "score": score,
        "contributor": meta.get("contributor", {}).get("github", ""),
        "has_lora": meta.get("has_lora", False),
    }


def _collect_adapter_entry(adapters: dict, adapter_dir: str, role: str,
                           size_class: str, model_name: str | None) -> None:
    """Read a single adapter directory and add it to the adapters dict.

    Reads meta.json for adapter metadata and optionally qualification.json
    for the adapter's evaluation score.
    """
    meta = _load_json(os.path.join(adapter_dir, "meta.json"))
    if meta is None:
        return

    score = _read_qualification_score(adapter_dir)

    key = f"{role}/{size_class}/{model_name}" if model_name else f"{role}/{size_class}"
    adapters[key] = _build_adapter_entry(meta, role, size_class, model_name, score)


def _collect_size_class_adapters(adapters: dict, role: str, role_dir: str) -> None:
    """Collect all adapters for a given role across its size classes."""
    for size_class in _sorted_subdirs(role_dir):
        size_dir = os.path.join(role_dir, size_class)

        # Size-class default adapter
        _collect_adapter_entry(adapters, size_dir, role, size_class, model_name=None)

        # Model-specific adapters within this size class
        for model_name in _sorted_subdirs(size_dir):
            model_dir = os.path.join(size_dir, model_name)
            _collect_adapter_entry(adapters, model_dir, role, size_class, model_name)


def collect_adapters() -> dict:
    """Walk adapters/{role}/{size_class}/[{model_name}/] and extract adapter info.

    Structure:
        adapters/{role}/{size_class}/              -- size-class default adapter
        adapters/{role}/{size_class}/{model_name}/ -- model-specific adapter

    Fallback order at runtime:
        1. exact model -> 2. size_class default -> 3. tinylm (ultimate fallback)
    """
    adapters = {}
    adapters_root = os.path.join(REPO_ROOT, "adapters")

    for role in _sorted_subdirs(adapters_root):
        role_dir = os.path.join(adapters_root, role)
        _collect_size_class_adapters(adapters, role, role_dir)

    return adapters


def collect_tools() -> dict:
    """Walk mcp_tools/ and extract tool metadata."""
    tools = {}
    tools_dir = os.path.join(REPO_ROOT, "mcp_tools")

    for name in sorted(os.listdir(tools_dir)) if os.path.isdir(tools_dir) else []:
        meta = _load_json(os.path.join(tools_dir, name, "meta.json"))
        if meta is None:
            continue

        tools[name] = {
            "name": meta.get("name", name),
            "version": meta.get("version", ""),
            "description": meta.get("description", ""),
            "implementations": meta.get("implementations", {}),
            "author": meta.get("author", {}).get("github", ""),
            "category": meta.get("category", ""),
            "tags": meta.get("tags", []),
            "parameters": meta.get("parameters", []),
            "requires_api_key": meta.get("requires_api_key", False),
        }

    return tools


def collect_mcps() -> dict:
    """Walk mcps/ and extract external MCP server metadata."""
    mcps = {}
    mcps_dir = os.path.join(REPO_ROOT, "mcps")

    for name in sorted(os.listdir(mcps_dir)) if os.path.isdir(mcps_dir) else []:
        meta = _load_json(os.path.join(mcps_dir, name, "meta.json"))
        if meta is None:
            continue

        mcps[name] = {
            "name": meta.get("name", name),
            "version": meta.get("version", ""),
            "description": meta.get("description", ""),
            "source": meta.get("source", ""),
            "package": meta.get("package", ""),
            "command": meta.get("command", []),
            "auth_type": meta.get("auth_type", "none"),
            "tools": meta.get("tools", []),
            "capabilities": meta.get("capabilities", []),
            "category": meta.get("category", ""),
        }
        if meta.get("auth_env"):
            mcps[name]["auth_env"] = meta["auth_env"]
        if meta.get("auth_provider"):
            mcps[name]["auth_provider"] = meta["auth_provider"]

    return mcps


def collect_connectors() -> dict:
    """Walk connectors/ and extract connector info."""
    connectors = {}
    connectors_dir = os.path.join(REPO_ROOT, "connectors")

    for name in sorted(os.listdir(connectors_dir)) if os.path.isdir(connectors_dir) else []:
        meta = _load_json(os.path.join(connectors_dir, name, "meta.json"))
        if meta is None:
            continue

        connectors[name] = {
            "name": meta.get("name", name),
            "version": meta.get("version", ""),
            "description": meta.get("description", ""),
            "language": meta.get("language", ""),
            "platforms": meta.get("platforms", []),
            "author": meta.get("author", {}).get("github", ""),
            "capabilities": meta.get("capabilities", {}),
            "config_fields": meta.get("config_fields", []),
        }

    return connectors


def build_leaderboard(adapters: dict) -> dict:
    """Build leaderboard of top adapters grouped by size_class.

    Returns a dict mapping each size_class to a list of adapter entries
    sorted by score in descending order.
    """
    by_class: dict[str, list] = {}
    for _name, info in adapters.items():
        if info.get("score") is None:
            continue
        sc = info.get("size_class", DEFAULT_SIZE_CLASS)
        by_class.setdefault(sc, []).append({
            "model": info["model"],
            "score": info["score"],
            "contributor": info.get("contributor", ""),
        })

    for sc in by_class:
        by_class[sc].sort(key=lambda x: x["score"], reverse=True)

    return by_class


def main():
    """Collect all community components and write manifest.json."""
    nerves = collect_nerves()
    adapters = collect_adapters()
    connectors = collect_connectors()
    tools = collect_tools()
    mcps = collect_mcps()

    manifest = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nerves": nerves,
        "adapters": adapters,
        "connectors": connectors,
        "tools": tools,
        "mcps": mcps,
        "stats": {
            "total_nerves": len(nerves),
            "total_adapters": len(adapters),
            "total_connectors": len(connectors),
            "total_tools": len(tools),
            "total_mcps": len(mcps),
        },
        "leaderboard": build_leaderboard(adapters),
    }

    manifest_path = os.path.join(REPO_ROOT, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Generated manifest.json: {len(nerves)} nerves, {len(adapters)} adapters, "
          f"{len(connectors)} connectors, {len(tools)} tools, {len(mcps)} mcps")


if __name__ == "__main__":
    main()
