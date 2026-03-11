/**
 * Connector Base — shared integration wrapper for all Sentient connectors.
 *
 * Handles: Redis pub/sub, config loading, access control, brain task building,
 * response dispatch, active chat tracking, and TTS audio delivery.
 *
 * Platform connectors extend this by providing hooks for:
 *   - Platform setup/teardown
 *   - Message parsing (extracting text, media, sender info)
 *   - Sending messages (text, image, audio, etc.)
 *
 * Usage:
 *   const ConnectorBase = require("../lib/connector-base");
 *   const connector = new ConnectorBase("whatsapp", __dirname);
 *   connector.setSendHooks({ sendText, sendImage, ... });
 *   await connector.start();
 *   // When a message arrives from the platform:
 *   await connector.handleIncoming(normalizedMessage);
 */

const { createClient } = require("redis");
const path = require("path");
const fs = require("fs");

class ConnectorBase {
  constructor(name, connectorDir) {
    this.name = name;
    this.tag = `[${name.toUpperCase()}]`;
    this.connectorDir = connectorDir;

    // Config
    this.config = {
      bot_name: "Sentient",
      bot_aliases: [],
      whitelisted_users: [],
      whitelisted_groups: [],
      monitor_groups: [],
    };

    // Normalized sets (populated in loadConfig)
    this.whitelistedUsers = new Set();
    this.whitelistedGroups = new Set();
    this.monitorGroups = new Set();
    this.botNames = [];

    // State
    this.activeChatIds = new Map(); // chatId -> lastActivity timestamp
    this.pendingChats = new Map();
    this.RESPONSE_TIMEOUT_MS = 120_000;
    this.CHAT_IDLE_MS = 3_600_000; // 1 hour — remove inactive chats
    this._cleanupTimer = null;

    // Redis clients
    this.redisSub = null;
    this.redisPub = null;

    // Platform-specific state (for use by implementations)
    this.platformData = {};

    // Platform hooks (set by connector implementation)
    this._sendHooks = {};
    this._isGroupChat = () => false;
  }

  // --- Config ---

  loadConfig(extraDefaults = {}) {
    const configFile = path.join(this.connectorDir, "config.json");
    this.config = { ...this.config, ...extraDefaults };

    if (fs.existsSync(configFile)) {
      try {
        const loaded = JSON.parse(fs.readFileSync(configFile, "utf8"));
        this.config = { ...this.config, ...loaded };
        console.log(`${this.tag} Config loaded from config.json`);
      } catch (err) {
        console.warn(`${this.tag} Failed to parse config.json, using defaults:`, err.message);
      }
    }

    this.whitelistedUsers = new Set(this.config.whitelisted_users.map(String));
    this.whitelistedGroups = new Set(this.config.whitelisted_groups.map(String));
    this.monitorGroups = new Set(this.config.monitor_groups.map(String));
    this.botNames = [this.config.bot_name, ...this.config.bot_aliases]
      .map((n) => n.toLowerCase().trim())
      .filter(Boolean);

    console.log(`${this.tag} Bot name: ${this.config.bot_name} | Aliases: ${this.config.bot_aliases.join(", ") || "(none)"}`);
    if (this.whitelistedUsers.size) console.log(`${this.tag} Whitelisted users: ${[...this.whitelistedUsers].join(", ")}`);
    if (this.whitelistedGroups.size) console.log(`${this.tag} Whitelisted groups: ${[...this.whitelistedGroups].join(", ")}`);
    if (this.monitorGroups.size) console.log(`${this.tag} Monitor-only groups: ${[...this.monitorGroups].join(", ")}`);

    return this.config;
  }

  // --- Platform hooks ---

  /**
   * Set the function that determines if a chatId is a group chat.
   * @param {(chatId: any) => boolean} fn
   */
  setGroupDetector(fn) {
    this._isGroupChat = fn;
  }

  /**
   * Set send hooks for outgoing messages.
   * Each hook receives (chatId, text, data) and should return a promise.
   *
   * Required hooks: sendText
   * Optional hooks: sendImage, sendGif, sendAudio, sendSticker, sendDocument,
   *   sendLocation, sendContact, sendPoll, sendCard, sendReaction,
   *   sendTyping, clearTyping
   */
  setSendHooks(hooks) {
    this._sendHooks = hooks;
  }

  // --- Access control ---

  isGroupChat(chatId) {
    return this._isGroupChat(chatId);
  }

  isUserWhitelisted(userId) {
    if (this.whitelistedUsers.size === 0) return true;
    return this.whitelistedUsers.has(String(userId));
  }

  isGroupWhitelisted(chatId) {
    if (this.whitelistedGroups.size === 0) return true;
    return this.whitelistedGroups.has(String(chatId));
  }

  isMonitorGroup(chatId) {
    return this.monitorGroups.has(String(chatId));
  }

  /**
   * Check if text addresses the bot (name prefix match).
   * Override in platform connector to add platform-specific checks
   * (e.g., @mention, /command).
   */
  addressesBot(text) {
    const lower = text.toLowerCase().trim();
    for (const name of this.botNames) {
      if (lower.startsWith(name)) {
        const after = lower[name.length];
        if (!after || ",: .!?\n".includes(after)) return true;
      }
    }
    return false;
  }

  /**
   * Strip bot name/alias prefix from text.
   * Override in platform connector to also strip @mention, /command, etc.
   */
  stripBotPrefix(text) {
    const lower = text.toLowerCase().trim();
    for (const name of this.botNames) {
      if (lower.startsWith(name)) {
        const after = lower[name.length];
        if (!after || ",: .!?\n".includes(after)) {
          let stripped = text.trim().substring(name.length);
          stripped = stripped.replace(/^[,:\s.!?]+/, "").trim();
          return stripped || text;
        }
      }
    }
    return text;
  }

  // --- Redis ---

  async setupRedis() {
    this.redisSub = createClient();
    this.redisPub = createClient();
    this.redisSub.on("error", (err) => console.error(`[REDIS-SUB]`, err.message));
    this.redisPub.on("error", (err) => console.error(`[REDIS-PUB]`, err.message));
    await this.redisSub.connect();
    await this.redisPub.connect();
    console.log(`${this.tag} Redis connected`);
  }

  // --- Incoming message handling ---

  /**
   * Process an incoming message from the platform.
   * Call this from your platform's message handler.
   *
   * @param {object} msg - Normalized message object:
   *   - chatId: string|number — chat/group identifier
   *   - senderId: string — user identifier
   *   - senderName: string — display name
   *   - text: string — message text
   *   - media?: { type, path, mime, size, buffer } — downloaded media
   *   - location?: { latitude, longitude, name?, address? }
   *   - contacts?: [{ name, phone?, vcard? }]
   *   - poll?: { name, options[], selectable_count }
   *   - msgKey?: any — platform-specific message key (for reactions)
   *   - extra?: object — platform-specific extra fields (language_code, msg_id, etc.)
   */
  async handleIncoming(msg) {
    const chatId = String(msg.chatId);
    const isGroup = this.isGroupChat(msg.chatId);

    // 1. Monitor-only groups: collect but don't respond
    if (isGroup && this.isMonitorGroup(chatId)) {
      console.log(`${this.tag}-MONITOR] ${chatId}: ${msg.senderId}: ${(msg.text || "").substring(0, 80)}`);
      await this.redisPub.publish(`${this.name}:monitor`, JSON.stringify({
        group: chatId,
        sender: msg.senderId,
        text: msg.text || "",
        media_type: msg.media?.type || null,
        timestamp: Date.now(),
      }));
      return;
    }

    // 2. Group whitelist
    if (isGroup && !this.isGroupWhitelisted(chatId)) return;

    // 3. User whitelist
    if (!this.isUserWhitelisted(msg.senderId)) {
      console.log(`${this.tag} Ignoring non-whitelisted user ${msg.senderId}`);
      return;
    }

    const hasContent = (msg.text || "").trim() || msg.media || msg.location || msg.contacts || msg.poll;
    if (!hasContent) return;

    // 4. Bot addressing in groups
    if (isGroup && msg.text) {
      if (!this.addressesBot(msg.text)) return;
    }

    const taskText = isGroup ? this.stripBotPrefix(msg.text || "") : (msg.text || "");

    // 5. Build brain task
    const brainTask = {
      task: taskText,
      source: this.name,
      chat_id: chatId,
      connector_user_id: msg.senderId,
      sender_name: msg.senderName || "",
      ...(msg.extra || {}),
    };

    // Attach media
    if (msg.media) {
      brainTask.media = {
        type: msg.media.type,
        path: msg.media.path,
        mime: msg.media.mime || "",
        size: msg.media.size || 0,
      };
      if (msg.media.buffer) {
        if (msg.media.type === "image") {
          brainTask.media.image_b64 = msg.media.buffer.toString("base64");
        } else if (msg.media.type === "audio") {
          brainTask.media.audio_b64 = msg.media.buffer.toString("base64");
        } else if (msg.media.type === "sticker") {
          brainTask.media.sticker_b64 = msg.media.buffer.toString("base64");
        }
      }
      if (!taskText) brainTask.task = `[Received ${msg.media.type}]`;
      console.log(`${this.tag} ${msg.senderId}: ${msg.media.type} (${msg.media.size} bytes) ${taskText || ""}`);
    }

    // Attach location
    if (msg.location) {
      brainTask.location = msg.location;
      if (!taskText) brainTask.task = `[Shared location: ${msg.location.name || `${msg.location.latitude},${msg.location.longitude}`}]`;
      console.log(`${this.tag} ${msg.senderId}: location ${msg.location.latitude},${msg.location.longitude}`);
    }

    // Attach contacts
    if (msg.contacts) {
      brainTask.contacts = msg.contacts;
      if (!taskText) brainTask.task = `[Shared ${msg.contacts.length} contact(s)]`;
      console.log(`${this.tag} ${msg.senderId}: ${msg.contacts.length} contact(s)`);
    }

    // Attach poll
    if (msg.poll) {
      brainTask.poll = msg.poll;
      if (!taskText) brainTask.task = `[Created poll: ${msg.poll.name}]`;
      console.log(`${this.tag} ${msg.senderId}: poll "${msg.poll.name}"`);
    }

    if (!brainTask.task) {
      console.log(`${this.tag} ${msg.senderId}: empty message, skipping`);
      return;
    }

    if (!msg.media && !msg.location && !msg.contacts && !msg.poll) {
      console.log(`${this.tag} ${msg.senderId}: ${taskText}`);
    }

    // 6. Track active chat
    this.activeChatIds.set(chatId, Date.now());
    this.pendingChats.set(chatId, { timestamp: Date.now(), msgKey: msg.msgKey || null });

    // 7. Publish to brain
    await this.redisPub.publish("brain:task", JSON.stringify(brainTask));
  }

  // --- Outgoing response handling ---

  async setupResponseHandler() {
    await this.redisSub.subscribe("brain:response", async (message) => {
      try {
        const data = JSON.parse(message);
        if (data.source !== this.name) return;

        const chatId = data.chat_id;
        if (!chatId || !this.activeChatIds.has(chatId)) return;

        const responseText = data.message || data.text || "";
        const pending = this.pendingChats.get(chatId) || {};
        this.pendingChats.delete(chatId);
        const media = data.media || {};

        // Reaction
        if (data.reactions?.length > 0 && pending.msgKey && this._sendHooks.sendReaction) {
          try {
            await this._sendHooks.sendReaction(chatId, data.reactions[0], pending.msgKey);
            console.log(`${this.tag} Reacted ${data.reactions[0]}`);
          } catch (err) {
            console.warn(`${this.tag} Reaction failed: ${err.message}`);
          }
          if (!responseText && !media.gif_url && !media.image_b64 && !media.image_path && !media.audio_b64) return;
        }

        // Typing indicator
        if (this._sendHooks.sendTyping) {
          try { await this._sendHooks.sendTyping(chatId); } catch (_) {}
        }

        // GIF
        if (media.gif_url && this._sendHooks.sendGif) {
          try {
            await this._sendHooks.sendGif(chatId, responseText, media.gif_url);
            console.log(`${this.tag} GIF sent to ${chatId}`);
            return;
          } catch (err) {
            console.warn(`${this.tag} GIF failed, falling back: ${err.message}`);
          }
        }

        // Sticker
        if (media.sticker_b64 && this._sendHooks.sendSticker) {
          try {
            const buf = Buffer.from(media.sticker_b64, "base64");
            await this._sendHooks.sendSticker(chatId, buf, responseText);
            console.log(`${this.tag} Sticker sent to ${chatId}`);
            return;
          } catch (err) {
            console.warn(`${this.tag} Sticker failed: ${err.message}`);
          }
        }

        // Image
        if ((media.image_path || media.image_b64) && this._sendHooks.sendImage) {
          try {
            let buf;
            if (media.image_path) {
              try { buf = await fs.promises.readFile(media.image_path); } catch (_) {}
            }
            if (!buf && media.image_b64) {
              buf = Buffer.from(media.image_b64, "base64");
            }
            if (buf) {
              await this._sendHooks.sendImage(chatId, responseText, buf, media.image_mime || "image/png");
              console.log(`${this.tag} Image sent to ${chatId}`);
              return;
            }
          } catch (err) {
            console.warn(`${this.tag} Image failed, falling back: ${err.message}`);
          }
        }

        // Audio
        if (media.audio_b64 && this._sendHooks.sendAudio) {
          try {
            const buf = Buffer.from(media.audio_b64, "base64");
            await this._sendHooks.sendAudio(chatId, responseText, buf, media.audio_mime || "audio/mp4");
            console.log(`${this.tag} Audio sent to ${chatId}`);
            return;
          } catch (err) {
            console.warn(`${this.tag} Audio failed, falling back: ${err.message}`);
          }
        }

        // Document
        if (media.document_b64 && this._sendHooks.sendDocument) {
          try {
            const buf = Buffer.from(media.document_b64, "base64");
            await this._sendHooks.sendDocument(chatId, {
              buffer: buf,
              fileName: media.document_name || "document",
              mime: media.document_mime || "application/octet-stream",
              caption: responseText,
            });
            console.log(`${this.tag} Document sent to ${chatId}`);
            return;
          } catch (err) {
            console.warn(`${this.tag} Document failed, falling back: ${err.message}`);
          }
        }

        // Location
        if (data.location && this._sendHooks.sendLocation) {
          try {
            await this._sendHooks.sendLocation(chatId, data.location, responseText);
            console.log(`${this.tag} Location sent to ${chatId}`);
            return;
          } catch (err) {
            console.warn(`${this.tag} Location failed: ${err.message}`);
          }
        }

        // Contacts
        if (data.contacts?.length > 0 && this._sendHooks.sendContact) {
          try {
            await this._sendHooks.sendContact(chatId, data.contacts, responseText);
            console.log(`${this.tag} Contact(s) sent to ${chatId}`);
            return;
          } catch (err) {
            console.warn(`${this.tag} Contact send failed: ${err.message}`);
          }
        }

        // Poll
        if (data.poll && this._sendHooks.sendPoll) {
          try {
            await this._sendHooks.sendPoll(chatId, data.poll, responseText);
            console.log(`${this.tag} Poll sent to ${chatId}`);
            return;
          } catch (err) {
            console.warn(`${this.tag} Poll failed: ${err.message}`);
          }
        }

        // Card (formatted text)
        if (data.card) {
          try {
            if (this._sendHooks.sendCard) {
              await this._sendHooks.sendCard(chatId, data.card, responseText);
            } else if (this._sendHooks.sendText) {
              await this._sendHooks.sendText(chatId, this.formatCard(data.card, responseText));
            }
            console.log(`${this.tag} Card sent to ${chatId}`);
            return;
          } catch (err) {
            console.warn(`${this.tag} Card failed: ${err.message}`);
          }
        }

        // Default: plain text
        if (responseText && this._sendHooks.sendText) {
          await this._sendHooks.sendText(chatId, responseText);
          console.log(`${this.tag} Reply sent to ${chatId}`);
        }

        // Clear typing
        if (this._sendHooks.clearTyping) {
          try { await this._sendHooks.clearTyping(chatId); } catch (_) {}
        }
      } catch (err) {
        console.error(`${this.tag} Failed to send reply:`, err.message);
      }
    });

    // TTS audio delivery
    await this.redisSub.subscribe("brain:audio", async (message) => {
      try {
        const data = JSON.parse(message);
        if (!data.audio_b64) return;
        if (data.source && data.source !== this.name) return;

        const chatId = data.chat_id;
        if (!chatId || !this.activeChatIds.has(chatId)) return;

        if (this._sendHooks.sendAudio) {
          const buf = Buffer.from(data.audio_b64, "base64");
          await this._sendHooks.sendAudio(chatId, "", buf, data.audio_mime || "audio/mp4");
          console.log(`${this.tag} TTS audio sent to ${chatId}`);
        }
      } catch (err) {
        console.error(`${this.tag} Failed to send TTS audio:`, err.message);
      }
    });
  }

  // --- Lifecycle ---

  /**
   * Start the connector: load config, connect Redis, set up response handler,
   * start pending chat cleanup.
   */
  async start(extraConfigDefaults = {}) {
    console.log(`${this.tag} Sentient ${this.config.bot_name} Connector starting...`);
    this.loadConfig(extraConfigDefaults);
    await this.setupRedis();
    await this.setupResponseHandler();
    this._startCleanupInterval();
  }

  _startCleanupInterval() {
    this._cleanupTimer = setInterval(() => {
      const now = Date.now();
      for (const [chatId, info] of this.pendingChats) {
        if (now - info.timestamp > this.RESPONSE_TIMEOUT_MS) {
          this.pendingChats.delete(chatId);
        }
      }
      for (const [chatId, lastActive] of this.activeChatIds) {
        if (now - lastActive > this.CHAT_IDLE_MS) {
          this.activeChatIds.delete(chatId);
        }
      }
    }, 30_000);
  }

  // --- Helpers ---

  /**
   * Format a card object as markdown text.
   * Used by sendCard fallback and available to platform implementations.
   */
  formatCard(card, fallbackText = "") {
    return [
      card.title ? `*${card.title}*` : "",
      "",
      card.body || fallbackText,
      "",
      card.footer ? `_${card.footer}_` : "",
    ].filter(Boolean).join("\n");
  }

  /**
   * Publish a custom event to Redis (e.g., reactions, status updates).
   * Use this instead of accessing redisPub directly.
   */
  async publishEvent(channel, data) {
    await this.redisPub.publish(channel, JSON.stringify(data));
  }

  // --- Media helpers ---

  static MEDIA_EXTENSIONS = { image: ".jpg", video: ".mp4", audio: ".ogg", sticker: ".webp", document: ".bin", photo: ".jpg", voice: ".ogg", animation: ".mp4" };

  /**
   * Save a buffer to the connector's media directory.
   * @param {Buffer} buffer
   * @param {string} mediaType - e.g., "image", "video", "audio"
   * @returns {Promise<string>} saved file path
   */
  async saveMediaBuffer(buffer, mediaType) {
    const mediaDir = path.join(this.connectorDir, "..", "..", "sandbox", `${this.name}_media`);
    const ext = ConnectorBase.MEDIA_EXTENSIONS[mediaType] || ".bin";
    const filename = `${this.name}_${mediaType}_${Date.now()}${ext}`;
    await fs.promises.mkdir(mediaDir, { recursive: true });
    const mediaPath = path.join(mediaDir, filename);
    await fs.promises.writeFile(mediaPath, buffer);
    return mediaPath;
  }
}

module.exports = ConnectorBase;
