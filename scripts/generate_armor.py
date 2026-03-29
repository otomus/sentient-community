#!/usr/bin/env python3
"""
Generate armor.json files for all mcp_tools and mcps.

Reads each tool.json / meta.json, determines the appropriate MCPArmor
security profile based on category and capabilities, and writes an
armor.json alongside the source manifest.

Reference: https://otomus.github.io/mcparmor/docs/manifest
"""

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_TOOLS_DIR = REPO_ROOT / "mcp_tools"
MCPS_DIR = REPO_ROOT / "mcps"

# ---------------------------------------------------------------------------
# Profile classification for mcp_tools (by tool name or category)
# ---------------------------------------------------------------------------

# Tools that do pure computation — no I/O at all
STRICT_TOOLS = {
    "base64", "hash", "math_eval", "regex", "uuid_generate", "json_tool",
    "table_format", "diff_compute", "password", "prompt_template",
    "explain_quantum_computing", "geography_nerve",
}

# Tools that need temp filesystem for media processing
SANDBOXED_TOOLS = {
    "barcode", "chart_create", "csv", "docx", "gif_create",
    "image_convert", "image_crop", "image_resize", "pdf", "pptx",
    "qr_code", "xlsx", "video_trim", "video_extract_frames",
    "diagram_create", "audio_convert", "markdown_convert",
    "compare_databases",
}

# Browser automation tools
BROWSER_TOOLS = {
    "browser_click", "browser_close", "browser_execute_js", "browser_fill",
    "browser_open", "browser_screenshot", "browser_text",
    "screen_capture", "screen_ocr",
}

# Tools that need to spawn child processes
SPAWN_TOOLS = {
    "docker_build", "docker_exec", "docker_logs", "docker_ps",
    "docker_pull", "docker_run", "docker_stop",
    "process_kill", "process_list", "process_run",
}

# System tools that access the local filesystem or OS
SYSTEM_TOOLS = {
    "file_read", "file_write", "file_append", "file_copy", "file_delete",
    "file_exists", "file_grep", "file_info", "file_move", "file_search",
    "file_watch", "dir_create", "dir_delete", "dir_list",
    "code_analyze", "code_deps", "code_format", "code_lint",
    "coverage_report", "test_discover", "test_run",
    "pkg_info", "pkg_install", "pkg_list", "pkg_search", "pkg_update",
    "git_add", "git_branch_create", "git_branch_delete", "git_branch_list",
    "git_checkout", "git_clone", "git_commit", "git_diff", "git_log",
    "git_merge", "git_pull", "git_push", "git_rebase", "git_stash",
    "git_status", "git_tag",
    "log", "note", "cron_create", "cron_delete", "cron_list",
    "lock_set", "metric_record", "queue", "reminder",
    "clipboard", "calendar",
    "keyboard_press", "keyboard_type", "mouse_click", "mouse_move",
    "mouse_scroll", "window",
}

# Network tools — call external APIs or services
NETWORK_TOOLS = {
    "http_get", "http_post", "http_put", "http_delete",
    "web_search", "web_scrape", "weather", "stock", "crypto_price",
    "currency", "news_fetch", "rss_fetch", "translate_text",
    "url_shorten", "whois_lookup", "dns_lookup", "cert_check",
    "email", "sms_send", "social", "webhook",
    "embedding", "llm_call", "llm_tokenize",
    "image_generate", "image_to_text",
    "audio_synthesize", "audio_transcribe", "music_identify",
    "youtube_info", "youtube_search", "youtube_transcript",
    "gif_search", "notification_send", "alert_send",
    "vuln_scan", "port_scan", "video_download", "video_get_info",
}

# IoT / hardware tools — need network for device communication
IOT_TOOLS = {
    "actuator", "device", "light", "sensor", "speaker", "thermostat",
    "sleep_tracker_read", "camera_capture", "image_capture",
    "audio_record",
}

# ---------------------------------------------------------------------------
# Profile classification for mcps (by category)
# ---------------------------------------------------------------------------

MCP_CATEGORY_PROFILES = {
    "automation": "network",
    "ai": "network",
    "cloud": "network",
    "coding": "system",
    "communication": "network",
    "creative": "sandboxed",
    "database": "network",
    "developer": "network",
    "devops": "system",
    "finance": "network",
    "knowledge": "network",
    "language": "network",
    "media": "network",
    "music": "network",
    "news": "network",
    "productivity": "network",
    "search": "network",
    "security": "network",
    "smart_home": "network",
    "social": "network",
    "travel": "network",
    "utilities": "network",
    "utility": "sandboxed",
    "voice": "sandboxed",
    "weather": "network",
    "iot": "network",
}

# MCPs that specifically need spawn (run subprocesses)
MCP_SPAWN_NAMES = {"shell", "npm_manage", "terraform", "test_runner", "eslint"}

# MCPs that need filesystem access
MCP_SYSTEM_NAMES = {
    "filesystem", "git", "code_search", "lsp", "eslint",
    "npm_manage", "test_runner", "shell", "terraform",
}

# Browser-based MCPs
MCP_BROWSER_NAMES = {"playwright", "peekaboo"}


def classify_tool(name: str, category: str | None) -> str:
    """Determine the MCPArmor profile for an mcp_tool."""
    if name in STRICT_TOOLS:
        return "strict"
    if name in SANDBOXED_TOOLS:
        return "sandboxed"
    if name in BROWSER_TOOLS:
        return "browser"
    if name in SPAWN_TOOLS:
        return "system"
    if name in SYSTEM_TOOLS:
        return "system"
    if name in NETWORK_TOOLS:
        return "network"
    if name in IOT_TOOLS:
        return "network"
    # Fallback: use category
    cat = (category or "").lower()
    if cat in ("browser",):
        return "browser"
    if cat in ("filesystem", "system", "git", "coding"):
        return "system"
    if cat in ("data", "crypto", "security"):
        return "strict"
    if cat in ("media",):
        return "sandboxed"
    # Default: network (most tools call external APIs)
    return "network"


def classify_mcp(name: str, category: str | None) -> str:
    """Determine the MCPArmor profile for an MCP server."""
    if name in MCP_BROWSER_NAMES:
        return "browser"
    if name in MCP_SYSTEM_NAMES:
        return "system"
    cat = (category or "").lower()
    return MCP_CATEGORY_PROFILES.get(cat, "sandboxed")


def needs_spawn(name: str, is_mcp: bool) -> bool:
    """Check if a tool or MCP needs to spawn child processes."""
    if is_mcp:
        return name in MCP_SPAWN_NAMES
    return name in SPAWN_TOOLS


def build_armor_for_tool(name: str, meta: dict) -> dict:
    """Build an armor.json dict for an mcp_tool."""
    category = meta.get("category")
    profile = classify_tool(name, category)
    spawn = needs_spawn(name, is_mcp=False)

    armor = {
        "version": "1.0",
        "profile": profile,
    }

    if profile == "network":
        armor["network"] = {
            "allow": ["*:443"],
            "deny_local": True,
            "deny_metadata": True,
        }
    elif profile == "browser":
        armor["network"] = {
            "allow": ["*:443", "*:80"],
            "deny_local": False,
            "deny_metadata": True,
        }
    elif profile == "system":
        armor["filesystem"] = {
            "read": ["**/*"],
            "write": ["/tmp/mcparmor/*"],
        }

    if profile == "sandboxed":
        armor["filesystem"] = {
            "read": ["/tmp/mcparmor/*"],
            "write": ["/tmp/mcparmor/*"],
        }

    armor["spawn"] = spawn

    # Secret scanning on for anything with network access
    if profile in ("network", "browser", "system"):
        armor["output"] = {
            "scan_secrets": True,
        }

    return armor


def build_armor_for_mcp(name: str, meta: dict) -> dict:
    """Build an armor.json dict for an MCP server."""
    category = meta.get("category")
    profile = classify_mcp(name, category)
    spawn = needs_spawn(name, is_mcp=True)
    auth_type = meta.get("auth_type", "none")

    armor = {
        "version": "1.0",
        "profile": profile,
    }

    if profile == "network":
        armor["network"] = {
            "allow": ["*:443"],
            "deny_local": True,
            "deny_metadata": True,
        }
    elif profile == "browser":
        armor["network"] = {
            "allow": ["*:443", "*:80"],
            "deny_local": False,
            "deny_metadata": True,
        }
    elif profile == "system":
        armor["filesystem"] = {
            "read": ["**/*"],
            "write": ["/tmp/mcparmor/*"],
        }
        armor["network"] = {
            "allow": ["*:443"],
            "deny_local": True,
            "deny_metadata": True,
        }

    if profile == "sandboxed":
        armor["filesystem"] = {
            "read": ["/tmp/mcparmor/*"],
            "write": ["/tmp/mcparmor/*"],
        }

    armor["spawn"] = spawn

    # Allow env vars for authenticated MCPs
    if auth_type and auth_type != "none":
        env_var = f"{name.upper()}_API_KEY"
        armor["env"] = {"allow": [env_var]}

    armor["output"] = {
        "scan_secrets": True,
    }

    return armor


def write_armor(directory: Path, armor: dict) -> None:
    """Write armor.json to the given directory."""
    path = directory / "armor.json"
    with open(path, "w") as f:
        json.dump(armor, f, indent=2)
        f.write("\n")


def generate_tool_armors() -> int:
    """Generate armor.json for all mcp_tools. Returns count."""
    count = 0
    for tool_dir in sorted(MCP_TOOLS_DIR.iterdir()):
        if not tool_dir.is_dir():
            continue
        manifest = tool_dir / "tool.json"
        if manifest.exists():
            with open(manifest) as f:
                meta = json.load(f)
        else:
            meta = {}
        name = meta.get("name", tool_dir.name)
        armor = build_armor_for_tool(name, meta)
        write_armor(tool_dir, armor)
        count += 1
    return count


def generate_mcp_armors() -> int:
    """Generate armor.json for all mcps. Returns count."""
    count = 0
    for mcp_dir in sorted(MCPS_DIR.iterdir()):
        manifest = mcp_dir / "meta.json"
        if not manifest.exists():
            continue
        with open(manifest) as f:
            meta = json.load(f)
        name = meta.get("name", mcp_dir.name)
        armor = build_armor_for_mcp(name, meta)
        write_armor(mcp_dir, armor)
        count += 1
    return count


def main() -> None:
    """Generate all armor.json files."""
    tools_count = generate_tool_armors()
    mcps_count = generate_mcp_armors()
    print(f"Generated {tools_count} armor.json files in mcp_tools/")
    print(f"Generated {mcps_count} armor.json files in mcps/")
    print(f"Total: {tools_count + mcps_count}")


if __name__ == "__main__":
    main()
