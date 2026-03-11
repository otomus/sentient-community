# WhatsApp Connector

Bridges WhatsApp messages to the Sentient brain via Redis using [Baileys](https://github.com/WhiskeySockets/Baileys).

## Setup

1. Install dependencies:
   ```bash
   cd connectors/whatsapp
   npm install
   ```

2. Create config:
   ```bash
   cp config-template.json config.json
   ```

3. Edit `config.json` with your settings (see Configuration below).

4. Start the connector:
   ```bash
   node connector.js
   ```

5. On first run, scan the QR code displayed in terminal with WhatsApp (Linked Devices > Link a Device). Session persists in `auth_store/` for subsequent runs.

## Configuration

| Field | Required | Description |
|-------|----------|-------------|
| `bot_name` | No | Bot display name (default: "Sentient") |
| `bot_aliases` | No | Alternative names the bot responds to |
| `whitelisted_users` | No | Phone numbers allowed to interact (empty = all) |
| `whitelisted_groups` | No | Group IDs to process (empty = all) |
| `monitor_groups` | No | Group IDs to observe read-only |

## Access Control

1. Status broadcasts are always ignored
2. Monitor groups: messages collected but never responded to
3. Group whitelist: only listed groups are processed (if set)
4. User whitelist: only listed phone numbers can trigger the bot (if set)
5. In groups, messages must address the bot by name or alias

## Supported Message Types

**Incoming**: text, image, video, audio, sticker, document, location, contact, poll

**Outgoing**: text, image, GIF, audio/voice note, sticker, document, location, contact, poll, reaction, card

## Redis Channels

| Direction | Channel | Purpose |
|-----------|---------|---------|
| Publish | `brain:task` | Send user messages to brain |
| Publish | `whatsapp:monitor` | Forward monitor group messages |
| Subscribe | `brain:response` | Receive brain responses |
| Subscribe | `brain:audio` | Receive TTS audio |

## Requirements

- Node.js 18+
- Redis server running locally
- WhatsApp account for QR pairing
