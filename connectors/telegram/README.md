# Telegram Connector

Bridges Telegram bot messages to the Sentient brain via Redis using [Telegraf](https://telegraf.js.org/).

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) on Telegram and get your bot token.

2. Install dependencies:
   ```bash
   cd connectors/telegram
   npm install
   ```

3. Create config:
   ```bash
   cp config-template.json config.json
   ```

4. Add your `bot_token` to `config.json`.

5. Start the connector:
   ```bash
   node connector.js
   ```

## Configuration

| Field | Required | Description |
|-------|----------|-------------|
| `bot_token` | Yes | Bot token from @BotFather |
| `bot_name` | No | Bot display name (default: "Sentient") |
| `bot_aliases` | No | Alternative names the bot responds to |
| `whitelisted_users` | No | Telegram user IDs allowed to interact (empty = all) |
| `whitelisted_groups` | No | Telegram group IDs to process (empty = all) |
| `monitor_groups` | No | Group IDs to observe read-only |

## Access Control

1. Monitor groups: messages collected but never responded to
2. Group whitelist: only listed groups are processed (if set)
3. User whitelist: only listed user IDs can trigger the bot (if set)
4. In groups, messages must address the bot by name, @mention, or /command

## Supported Message Types

**Incoming**: text, photo, video, audio, voice, sticker, animation, document, location, contact, poll

**Outgoing**: text, photo, animation/GIF, audio/voice, sticker, document, location, contact, poll, card

## Redis Channels

| Direction | Channel | Purpose |
|-----------|---------|---------|
| Publish | `brain:task` | Send user messages to brain |
| Publish | `telegram:monitor` | Forward monitor group messages |
| Subscribe | `brain:response` | Receive brain responses |
| Subscribe | `brain:audio` | Receive TTS audio |

## Requirements

- Node.js 18+
- Redis server running locally
- Telegram bot token from @BotFather
