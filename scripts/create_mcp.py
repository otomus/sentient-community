#!/usr/bin/env python3
"""Scaffold a new external MCP server entry.

Usage:
    python scripts/create_mcp.py <name> --package <npm-package>
    python scripts/create_mcp.py <name> --package <npm-package> --auth api_key --auth-env API_KEY_VAR
    python scripts/create_mcp.py <name> --package <npm-package> --auth oauth2 --auth-provider google

Examples:
    python scripts/create_mcp.py brave_search --package brave-search-mcp --category search
    python scripts/create_mcp.py linear --package linear-mcp --auth api_key --auth-env LINEAR_API_KEY
"""

import argparse
import json
import os
import sys
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_meta(mcp_dir: str, name: str, package: str, description: str,
                category: str, auth_type: str, auth_env: str, auth_provider: str,
                tools: list[str], capabilities: list[str], author: str) -> None:
    meta = {
        "name": name,
        "version": "1.0.0",
        "description": description,
        "source": "npm",
        "package": package,
        "command": ["npx", "-y", package],
        "auth_type": auth_type,
        "tools": tools,
        "capabilities": capabilities,
        "category": category,
    }
    if auth_env:
        meta["auth_env"] = auth_env
    if auth_provider:
        meta["auth_provider"] = auth_provider
    if author:
        meta["author"] = {"github": author}

    with open(os.path.join(mcp_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")


def create_readme(mcp_dir: str, name: str, package: str, description: str,
                  auth_type: str, auth_env: str, auth_provider: str,
                  tools: list[str], capabilities: list[str]) -> None:
    auth_section = "No authentication required."
    if auth_type == "api_key":
        auth_section = f"Requires an API key. Set the `{auth_env}` environment variable."
    elif auth_type == "oauth2":
        auth_section = f"Requires OAuth2 authentication with {auth_provider}."

    tools_section = "\n".join(f"- `{t}`" for t in tools) if tools else "- Tools not yet enumerated."
    caps_section = " ".join(f"`{c}`" for c in capabilities) if capabilities else "N/A"

    readme = f"""# {name}

{description}

## Installation

This MCP server is installed automatically by sentient-core. To use it manually:

```bash
npx -y {package}
```

## Authentication

{auth_section}

## Tools

{tools_section}

## Capabilities

{caps_section}
"""

    with open(os.path.join(mcp_dir, "README.md"), "w") as f:
        f.write(readme)


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new external MCP server entry")
    parser.add_argument("name", help="MCP server name (lowercase, underscores, e.g., brave_search)")
    parser.add_argument("--package", "-p", required=True, help="npm package name (e.g., brave-search-mcp)")
    parser.add_argument("--description", "-d", default="", help="Server description (auto-generated if empty)")
    parser.add_argument("--category", "-c", default="utilities", help="Category (e.g., search, knowledge, finance)")
    parser.add_argument("--auth", default="none", choices=["none", "api_key", "oauth2"], help="Authentication type")
    parser.add_argument("--auth-env", default="", help="Environment variable for API key (when --auth api_key)")
    parser.add_argument("--auth-provider", default="", help="OAuth2 provider (when --auth oauth2)")
    parser.add_argument("--tools", nargs="*", default=[], help="Tool names exposed by this server")
    parser.add_argument("--capabilities", nargs="*", default=[], help="Capability keywords for runtime matching")
    parser.add_argument("--author", "-a", default="", help="GitHub username of the contributor")
    args = parser.parse_args()

    name = args.name.lower().replace("-", "_").replace(" ", "_")

    # Validate name pattern
    import re
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        print(f"Error: name must match ^[a-z][a-z0-9_]*$ — got '{name}'")
        sys.exit(1)

    mcp_dir = os.path.join(REPO_ROOT, "mcps", name)

    if os.path.exists(mcp_dir):
        print(f"Error: mcps/{name}/ already exists")
        sys.exit(1)

    # Validate auth args
    if args.auth == "api_key" and not args.auth_env:
        print("Error: --auth-env is required when --auth is api_key")
        sys.exit(1)
    if args.auth == "oauth2" and not args.auth_provider:
        print("Error: --auth-provider is required when --auth is oauth2")
        sys.exit(1)

    description = args.description or f"{name.replace('_', ' ').title()} MCP server — {args.package}"
    capabilities = args.capabilities or [name.replace("_", " ")]

    os.makedirs(mcp_dir)
    print(f"Creating MCP server: {name}")

    create_meta(mcp_dir, name, args.package, description, args.category,
                args.auth, args.auth_env, args.auth_provider,
                args.tools, capabilities, args.author)

    create_readme(mcp_dir, name, args.package, description,
                  args.auth, args.auth_env, args.auth_provider,
                  args.tools, capabilities)

    print(f"""
MCP server scaffolded at: mcps/{name}/

Files created:
  meta.json  — Server metadata (edit to refine tools, capabilities, description)
  README.md  — Setup instructions

Next steps:
  1. Edit meta.json — add specific tools and capabilities for better runtime matching
  2. Verify the package works: npx -y {args.package}
  3. Submit a PR using the mcp PR template
""")


if __name__ == "__main__":
    main()
