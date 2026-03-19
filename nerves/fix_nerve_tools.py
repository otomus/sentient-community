#!/usr/bin/env python3
"""
Fix all nerve bundle.json tool references.

Three categories of fixes:
1. Map sub-operation tool names to actual mcp_tools/ directory names
2. Replace phantom MCP references with correct implementations paths
3. Fix semantic mismatches (wrong tools for the nerve's purpose)
"""

import json
from pathlib import Path

NERVES_DIR = Path(__file__).parent
MCP_TOOLS_DIR = NERVES_DIR.parent / "mcp_tools"
MCPS_DIR = NERVES_DIR.parent / "mcps"

# Actual mcp_tools directories
MCP_TOOL_DIRS = set(p.name for p in MCP_TOOLS_DIR.iterdir() if p.is_dir())

# Actual MCP servers
MCP_SERVERS = set(p.name for p in MCPS_DIR.iterdir() if p.is_dir())

# ── Sub-operation → parent directory mapping ─────────────────────────────
# When a tool name is a sub-operation of a parent tool in mcp_tools/

SUB_OP_TO_PARENT: dict[str, str] = {
    "pdf_read": "pdf",
    "pdf_create": "pdf",
    "json_format": "json_tool",
    "json_parse": "json_tool",
    "json_query": "json_tool",
    "csv_read": "csv",
    "csv_write": "csv",
    "text_to_speech": "audio_synthesize",
    "voice_recognition": "audio_transcribe",
    "take_photo": "camera_capture",
    "stock_quote": "stock",
    "stock_history": "stock",
    "docx_read": "docx",
    "xlsx_read": "xlsx",
    "markdown_to_html": "markdown_convert",
    "markdown_to_pdf": "markdown_convert",
    "base64_encode": "base64",
    "base64_decode": "base64",
    "embedding_create": "embedding",
    "embedding_search": "embedding",
    "email_send": "email",
    "git_stash_pop": "git_stash",
    "regex_match": "regex",
    "regex_replace": "regex",
    "note_create": "note",
    "capture_screen": "screen_capture",
    "generate_image": "image_generate",
    "log_read": "log",
    "social_search": "social",
    "social_post": "social",
    "get_sleep_data": "sleep_tracker_read",
    "fetch": "http_get",
    "fetch_content": "web_scrape",
    "search": "web_search",
    "sleep_tracker_read": "sleep_tracker_read",
    "get_current_time": "get_current_time",  # MCP-only (chrono)
    "convert_timezone": "convert_timezone",  # MCP-only (chrono)
}

# ── Tool → MCP server mapping (tools that have external MCP backing) ────

TOOL_TO_MCP: dict[str, str] = {
    "web_search": "duckduckgo",
    "search": "duckduckgo",
    "crypto_price": "coincap",
    "music_identify": "shazam",
    "rss_fetch": "rss_reader",
    "youtube_transcript": "youtube_transcript",
    "youtube_info": "youtube",
    "youtube_search": "youtube",
    "weather": "weather",
    "translate_text": "deepl",
    "image_generate": "image_gen",
    "generate_image": "image_gen",
    "get_current_time": "chrono",
    "convert_timezone": "chrono",
}

# ── Semantic fixes: nerves where tools need to be replaced entirely ──────

NERVE_TOOL_OVERRIDES: dict[str, list[dict]] = {
    "ci_check_nerve": [
        {"name": "http_get", "description": "Call CI/CD API endpoints"},
        {"name": "json_tool", "description": "Parse CI pipeline responses"},
        {"name": "alert_send", "description": "Send status notifications"},
    ],
    "crypto_price_nerve": [
        {"name": "crypto_price", "description": "Get cryptocurrency price"},
    ],
    "music_identify_nerve": [
        {"name": "music_identify", "description": "Identify a song via audio fingerprint"},
    ],
    "rss_monitor_nerve": [
        {"name": "rss_fetch", "description": "Fetch and parse RSS/Atom feeds"},
    ],
    "youtube_transcript_nerve": [
        {"name": "youtube_transcript", "description": "Download video transcript/captions"},
    ],
    "draft_email_nerve": [
        {"name": "llm_call", "description": "Generate polished email draft via AI"},
        {"name": "file_write", "description": "Save the draft to a file"},
    ],
    "video_transcribe_nerve": [
        {"name": "video_download", "description": "Download video file"},
        {"name": "audio_transcribe", "description": "Transcribe audio to text"},
    ],
}

# ── Description fixes ────────────────────────────────────────────────────

DESCRIPTION_FIXES: dict[str, str] = {
    "draft_email_nerve": "Compose a polished email draft using AI and save it to a file",
}


def resolve_tool_dir(tool_name: str) -> str | None:
    """Find the mcp_tools directory for a tool name."""
    if tool_name in MCP_TOOL_DIRS:
        return tool_name
    if tool_name in SUB_OP_TO_PARENT:
        parent = SUB_OP_TO_PARENT[tool_name]
        if parent in MCP_TOOL_DIRS:
            return parent
    return None


def canonical_tool_name(tool_name: str) -> str:
    """Return the canonical (parent) name for a tool, collapsing sub-ops."""
    if tool_name in MCP_TOOL_DIRS:
        return tool_name
    if tool_name in SUB_OP_TO_PARENT:
        return SUB_OP_TO_PARENT[tool_name]
    return tool_name


def build_tool_entry(tool_name: str) -> dict:
    """Build a correct tool entry with proper implementations/mcp references.

    Uses the canonical (parent) tool name when the input is a sub-operation.
    """
    canon = canonical_tool_name(tool_name)
    entry: dict = {"name": canon}

    tool_dir = resolve_tool_dir(canon)
    mcp_server = TOOL_TO_MCP.get(canon) or TOOL_TO_MCP.get(tool_name)

    if mcp_server and mcp_server in MCP_SERVERS:
        entry["mcp"] = mcp_server

    if tool_dir:
        entry["implementations"] = {
            "python": f"mcp_tools/{tool_dir}/tool.py"
        }
    else:
        entry["implementations"] = {}

    return entry


def fix_nerve(nerve_dir: Path) -> dict:
    """Fix a single nerve's bundle.json. Returns summary of changes."""
    bundle_path = nerve_dir / "bundle.json"
    if not bundle_path.exists():
        return {"name": nerve_dir.name, "skipped": True}

    bundle = json.loads(bundle_path.read_text())
    name = bundle.get("name", nerve_dir.name)
    changes = []

    # Fix description if needed
    if name in DESCRIPTION_FIXES:
        old_desc = bundle.get("description", "")
        new_desc = DESCRIPTION_FIXES[name]
        if old_desc != new_desc:
            bundle["description"] = new_desc
            changes.append(f"description: '{old_desc}' → '{new_desc}'")

    # Fix tools
    if name in NERVE_TOOL_OVERRIDES:
        # Complete tool replacement for semantic mismatches
        old_tools = [t["name"] for t in bundle.get("tools", [])]
        new_tools = []
        for override in NERVE_TOOL_OVERRIDES[name]:
            entry = build_tool_entry(override["name"])
            new_tools.append(entry)
        bundle["tools"] = new_tools
        new_tool_names = [t["name"] for t in new_tools]
        changes.append(f"tools: {old_tools} → {new_tool_names} (semantic fix)")
    else:
        # Fix individual tool references
        new_tools = []
        seen_canons = set()  # Deduplicate sub-ops that map to same parent
        for tool in bundle.get("tools", []):
            tool_name = tool["name"]
            canon = canonical_tool_name(tool_name)
            old_mcp = tool.get("mcp", "")
            old_impl = tool.get("implementations", {})

            # Check if this canonical tool was already added
            if canon in seen_canons:
                changes.append(f"  {tool_name}: merged into {canon}")
                continue
            seen_canons.add(canon)

            # Check if tool name is a sub-op that should be renamed
            name_needs_rename = canon != tool_name

            # Check if MCP reference is phantom (doesn't exist)
            mcp_is_phantom = old_mcp and old_mcp not in MCP_SERVERS

            # Check if implementations path is invalid
            impl_path = (
                old_impl.get("python", "") if isinstance(old_impl, dict)
                else ""
            )
            impl_is_invalid = False
            if impl_path:
                dir_name = (
                    impl_path.split("/")[1] if "/" in impl_path else ""
                )
                impl_is_invalid = dir_name and dir_name not in MCP_TOOL_DIRS

            # Check if tool has no references at all
            has_no_refs = not old_impl and not old_mcp

            needs_fix = (
                name_needs_rename or mcp_is_phantom
                or impl_is_invalid or has_no_refs
            )

            if needs_fix:
                fixed = build_tool_entry(tool_name)
                fix_details = []
                if name_needs_rename:
                    fix_details.append(f"renamed '{tool_name}' → '{canon}'")
                if mcp_is_phantom:
                    if "mcp" in fixed:
                        fix_details.append(
                            f"mcp: '{old_mcp}' → '{fixed['mcp']}'"
                        )
                    else:
                        fix_details.append(
                            f"removed phantom mcp '{old_mcp}'"
                        )
                tool_dir = resolve_tool_dir(canon)
                if tool_dir and not impl_path:
                    fix_details.append(
                        f"impl → mcp_tools/{tool_dir}/tool.py"
                    )

                new_tools.append(fixed)
                if fix_details:
                    changes.append(
                        f"  {tool_name}: {', '.join(fix_details)}"
                    )
            else:
                new_tools.append(tool)

        bundle["tools"] = new_tools

    if changes:
        bundle_path.write_text(json.dumps(bundle, indent=2) + "\n")

    return {"name": name, "changes": changes}


def main() -> None:
    """Fix all nerve bundle.json tool references."""
    nerve_dirs = sorted(
        d for d in NERVES_DIR.iterdir()
        if d.is_dir() and (d / "bundle.json").exists()
    )

    print(f"Auditing {len(nerve_dirs)} nerves\n")

    fixed_count = 0
    for nerve_dir in nerve_dirs:
        result = fix_nerve(nerve_dir)
        if result.get("skipped"):
            continue
        if result["changes"]:
            fixed_count += 1
            print(f"{result['name']}:")
            for c in result["changes"]:
                print(f"  {c}")
            print()

    print(f"Fixed {fixed_count} nerves")


if __name__ == "__main__":
    main()
