#!/usr/bin/env python3
"""Scaffold a new Sentient connector.

Usage:
    python scripts/create_connector.py <name> --language <js|ts|py> --platform <platform>

Example:
    python scripts/create_connector.py discord --language javascript --platform discord
    python scripts/create_connector.py slack --language typescript --platform slack
"""

import argparse
import json
import os
import sys
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_meta(connector_dir: str, name: str, language: str, platform: str, author: str) -> None:
    meta = {
        "name": name,
        "version": "1.0.0",
        "description": f"{platform.capitalize()} connector for Sentient — bridges {platform} messages to the brain via Redis",
        "language": language,
        "platforms": [platform],
        "author": {"github": author},
        "capabilities": {
            "incoming": ["text"],
            "outgoing": ["text"],
        },
        "config_fields": [
            {"name": "bot_name", "required": False, "secret": False, "description": "Bot display name (default: Sentient)"},
            {"name": "bot_aliases", "required": False, "secret": False, "description": "Alternative names the bot responds to"},
            {"name": "whitelisted_users", "required": False, "secret": False, "description": "User IDs allowed to interact"},
            {"name": "whitelisted_groups", "required": False, "secret": False, "description": "Group IDs to process messages from"},
            {"name": "monitor_groups", "required": False, "secret": False, "description": "Group IDs to observe read-only"},
        ],
        "redis_channels": {
            "subscribe": ["brain:response", "brain:audio"],
            "publish": ["brain:task", f"{name}:monitor"],
        },
    }
    with open(os.path.join(connector_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")


def create_config_template(connector_dir: str) -> None:
    config = {
        "_instructions": "Copy this file to config.json and fill in your values. config.json is gitignored.",
        "bot_name": "Sentient",
        "bot_aliases": [],
        "whitelisted_users": [],
        "whitelisted_groups": [],
        "monitor_groups": [],
    }
    with open(os.path.join(connector_dir, "config-template.json"), "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def create_gitignore(connector_dir: str) -> None:
    with open(os.path.join(connector_dir, ".gitignore"), "w") as f:
        f.write("node_modules/\nconfig.json\npackage-lock.json\n")


def create_js_connector(connector_dir: str, name: str, platform: str) -> None:
    # package.json
    pkg = {
        "name": f"sentient-{name}",
        "private": True,
        "scripts": {"start": "node connector.js"},
        "dependencies": {"redis": "^4.6.0"},
    }
    with open(os.path.join(connector_dir, "package.json"), "w") as f:
        json.dump(pkg, f, indent=2)
        f.write("\n")

    # connector.js
    code = textwrap.dedent(f'''\
        /**
         * {platform.capitalize()} Connector — bridges {platform} messages to the Sentient brain via Redis.
         *
         * Uses the shared ConnectorBase for Redis, config, access control, and response dispatch.
         * You only need to implement platform-specific setup and send hooks.
         */

        const ConnectorBase = require("../lib/connector-base");
        const path = require("path");

        const connector = new ConnectorBase("{name}", __dirname);

        // --- Platform-specific: group detection ---
        connector.setGroupDetector((chatId) => {{
          // TODO: Return true if chatId represents a group chat
          // Example (Telegram): return chatId < 0;
          // Example (WhatsApp): return String(chatId).endsWith("@g.us");
          return false;
        }});

        // --- Platform-specific: send hooks ---
        connector.setSendHooks({{
          async sendText(chatId, text) {{
            // TODO: Send a text message to chatId
            console.log(`[{name.upper()}] Would send to ${{chatId}}: ${{text}}`);
          }},

          async sendImage(chatId, caption, imageBuffer, mime) {{
            // TODO: Send an image with optional caption
          }},

          async sendAudio(chatId, text, audioBuffer, mime) {{
            // TODO: Send audio/voice message
          }},

          async sendGif(chatId, caption, gifUrl) {{
            // TODO: Send GIF/animation
          }},

          async sendSticker(chatId, stickerBuffer, text) {{
            // TODO: Send sticker
          }},

          async sendDocument(chatId, {{ buffer, fileName, mime, caption }}) {{
            // TODO: Send document/file
          }},

          async sendLocation(chatId, location, text) {{
            // TODO: Send location (location.latitude, location.longitude)
          }},

          async sendContact(chatId, contacts, text) {{
            // TODO: Send contact(s)
          }},

          async sendPoll(chatId, poll, text) {{
            // TODO: Send poll (poll.name, poll.options, poll.selectable_count)
          }},

          async sendCard(chatId, card, text) {{
            // Render card as formatted text (most platforms don't have native cards)
            await connector._sendHooks.sendText(chatId, connector.formatCard(card, text));
          }},

          async sendTyping(chatId) {{
            // TODO: Show typing indicator
          }},

          async clearTyping(chatId) {{
            // TODO: Clear typing indicator
          }},
        }});

        // --- Platform-specific: message listener ---
        async function setupPlatform() {{
          // TODO: Initialize your platform SDK/library here
          // When a message arrives, normalize it and call connector.handleIncoming():
          //
          // await connector.handleIncoming({{
          //   chatId: "...",
          //   senderId: "...",
          //   senderName: "...",
          //   text: "message text",
          //   media: {{ type: "image", path: "/path/to/file", mime: "image/jpeg", size: 1234, buffer: Buffer }},
          //   location: {{ latitude: 0, longitude: 0, name: "", address: "" }},
          //   contacts: [{{ name: "...", phone: "...", vcard: "..." }}],
          //   poll: {{ name: "...", options: ["a", "b"], selectable_count: 1 }},
          //   msgKey: platformMessageKey,
          //   extra: {{ language_code: "en" }},
          // }});
        }}

        // --- Main ---
        async function main() {{
          await connector.start();
          await setupPlatform();
          console.log(`[{name.upper()}] Connector running.`);
        }}

        main().catch((err) => {{
          console.error(`[{name.upper()}] Fatal:`, err);
          process.exit(1);
        }});
    ''')
    with open(os.path.join(connector_dir, "connector.js"), "w") as f:
        f.write(code)


def create_ts_connector(connector_dir: str, name: str, platform: str) -> None:
    # package.json
    pkg = {
        "name": f"sentient-{name}",
        "private": True,
        "scripts": {"start": "npx tsx connector.ts"},
        "dependencies": {"redis": "^4.6.0"},
        "devDependencies": {"tsx": "^4.0.0", "typescript": "^5.0.0"},
    }
    with open(os.path.join(connector_dir, "package.json"), "w") as f:
        json.dump(pkg, f, indent=2)
        f.write("\n")

    # connector.ts (same structure as JS with type annotations)
    code = textwrap.dedent(f'''\
        /**
         * {platform.capitalize()} Connector — bridges {platform} messages to the Sentient brain via Redis.
         *
         * Uses the shared ConnectorBase for Redis, config, access control, and response dispatch.
         * You only need to implement platform-specific setup and send hooks.
         */

        const ConnectorBase = require("../lib/connector-base");

        const connector = new ConnectorBase("{name}", __dirname);

        // --- Platform-specific: group detection ---
        connector.setGroupDetector((chatId: string | number) => {{
          // TODO: Return true if chatId represents a group chat
          return false;
        }});

        // --- Platform-specific: send hooks ---
        connector.setSendHooks({{
          async sendText(chatId: string, text: string) {{
            // TODO: Send a text message to chatId
            console.log(`[{name.upper()}] Would send to ${{chatId}}: ${{text}}`);
          }},

          async sendImage(chatId: string, caption: string, imageBuffer: Buffer, mime: string) {{
            // TODO: Send an image with optional caption
          }},

          async sendAudio(chatId: string, text: string, audioBuffer: Buffer, mime: string) {{
            // TODO: Send audio/voice message
          }},

          // Add more send hooks as needed (sendGif, sendSticker, sendDocument, etc.)
        }});

        // --- Platform-specific: message listener ---
        async function setupPlatform() {{
          // TODO: Initialize your platform SDK and set up message handlers
          // Call connector.handleIncoming({{ chatId, senderId, senderName, text, ... }})
        }}

        async function main() {{
          await connector.start();
          await setupPlatform();
          console.log(`[{name.upper()}] Connector running.`);
        }}

        main().catch((err: Error) => {{
          console.error(`[{name.upper()}] Fatal:`, err);
          process.exit(1);
        }});
    ''')
    with open(os.path.join(connector_dir, "connector.ts"), "w") as f:
        f.write(code)


def create_py_connector(connector_dir: str, name: str, platform: str) -> None:
    code = textwrap.dedent(f'''\
        #!/usr/bin/env python3
        """
        {platform.capitalize()} Connector — bridges {platform} messages to the Sentient brain via Redis.

        This connector uses Redis pub/sub to communicate with the Sentient brain.
        Implement the platform-specific setup and message handling below.
        """

        import asyncio
        import json
        import os

        import redis.asyncio as redis

        CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

        # Load config
        config = {{
            "bot_name": "Sentient",
            "bot_aliases": [],
            "whitelisted_users": [],
            "whitelisted_groups": [],
            "monitor_groups": [],
        }}

        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                config.update(json.load(f))


        async def main():
            # Redis setup
            redis_pub = redis.Redis()
            redis_sub = redis.Redis()
            pubsub = redis_sub.pubsub()
            await pubsub.subscribe("brain:response", "brain:audio")

            print("[{name.upper()}] Redis connected")

            # TODO: Initialize your platform SDK here

            # TODO: Set up message listener
            # When a message arrives from the platform, publish to brain:
            #
            # await redis_pub.publish("brain:task", json.dumps({{
            #     "task": "user message text",
            #     "source": "{name}",
            #     "chat_id": "...",
            #     "connector_user_id": "...",
            #     "sender_name": "...",
            # }}))

            # Response handler
            async def handle_responses():
                async for msg in pubsub.listen():
                    if msg["type"] != "message":
                        continue
                    data = json.loads(msg["data"])
                    if data.get("source") != "{name}":
                        continue
                    chat_id = data.get("chat_id")
                    text = data.get("message") or data.get("text") or ""

                    # TODO: Send response back to the platform
                    print(f"[{name.upper()}] Would send to {{chat_id}}: {{text}}")

            await handle_responses()


        if __name__ == "__main__":
            print("[{name.upper()}] Sentient {platform.capitalize()} Connector starting...")
            asyncio.run(main())
    ''')
    with open(os.path.join(connector_dir, "connector.py"), "w") as f:
        f.write(code)

    # requirements.txt
    with open(os.path.join(connector_dir, "requirements.txt"), "w") as f:
        f.write("redis>=5.0.0\n")


def create_readme(connector_dir: str, name: str, platform: str, language: str) -> None:
    lang_setup = {
        "javascript": "```bash\nnpm install\nnode connector.js\n```",
        "typescript": "```bash\nnpm install\nnpx tsx connector.ts\n```",
        "python": "```bash\npip install -r requirements.txt\npython connector.py\n```",
    }

    readme = textwrap.dedent(f"""\
        # {platform.capitalize()} Connector

        Bridges {platform} messages to the Sentient brain via Redis.

        ## Setup

        1. Install dependencies and create config:
           ```bash
           cd connectors/{name}
           cp config-template.json config.json
           ```

        2. Edit `config.json` with your settings.

        3. Start the connector:
           {lang_setup.get(language, lang_setup["javascript"])}

        ## Configuration

        | Field | Required | Description |
        |-------|----------|-------------|
        | `bot_name` | No | Bot display name (default: "Sentient") |
        | `bot_aliases` | No | Alternative names the bot responds to |
        | `whitelisted_users` | No | User IDs allowed to interact (empty = all) |
        | `whitelisted_groups` | No | Group IDs to process (empty = all) |
        | `monitor_groups` | No | Group IDs to observe read-only |

        ## Requirements

        - Redis server running locally
    """)

    with open(os.path.join(connector_dir, "README.md"), "w") as f:
        f.write(readme)


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new Sentient connector")
    parser.add_argument("name", help="Connector name (lowercase, e.g., discord)")
    parser.add_argument("--language", "-l", required=True, choices=["javascript", "typescript", "python", "js", "ts", "py"],
                        help="Implementation language")
    parser.add_argument("--platform", "-p", help="Platform name (default: same as connector name)")
    parser.add_argument("--author", "-a", default="", help="GitHub username of the author")
    args = parser.parse_args()

    name = args.name.lower().replace("-", "_").replace(" ", "_")
    platform = (args.platform or name).lower()

    # Normalize language aliases
    lang_map = {"js": "javascript", "ts": "typescript", "py": "python"}
    language = lang_map.get(args.language, args.language)

    connector_dir = os.path.join(REPO_ROOT, "connectors", name)

    if os.path.exists(connector_dir):
        print(f"Error: connectors/{name}/ already exists")
        sys.exit(1)

    os.makedirs(connector_dir)
    print(f"Creating connector: {name} ({language}) for {platform}")

    create_meta(connector_dir, name, language, platform, args.author)
    create_config_template(connector_dir)
    create_gitignore(connector_dir)
    create_readme(connector_dir, name, platform, language)

    if language == "javascript":
        create_js_connector(connector_dir, name, platform)
    elif language == "typescript":
        create_ts_connector(connector_dir, name, platform)
    elif language == "python":
        create_py_connector(connector_dir, name, platform)

    print(f"""
Connector scaffolded at: connectors/{name}/

Files created:
  meta.json            — Connector metadata
  config-template.json — Config template (copy to config.json)
  connector.{{'js' if language == 'javascript' else 'ts' if language == 'typescript' else 'py'}}       — Implementation (fill in TODOs)
  README.md            — Setup instructions
  .gitignore           — Excludes config.json, node_modules

Next steps:
  1. Install your platform SDK (add to {'package.json' if language != 'python' else 'requirements.txt'})
  2. Implement the TODOs in connector.{{'js' if language == 'javascript' else 'ts' if language == 'typescript' else 'py'}}
  3. Test locally with Redis running
  4. Submit a PR using the connector PR template
""")


if __name__ == "__main__":
    main()
