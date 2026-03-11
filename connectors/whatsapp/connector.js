/**
 * WhatsApp Connector — bridges WhatsApp messages to the Sentient brain via Redis.
 *
 * Uses ConnectorBase for Redis, config, access control, and response dispatch.
 * This file handles WhatsApp-specific Baileys integration.
 *
 * First run: displays QR code in terminal for WhatsApp Web pairing.
 * Session persists in ./auth_store/ so subsequent runs reconnect automatically.
 */

const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
  downloadMediaMessage,
} = require("@whiskeysockets/baileys");
const ConnectorBase = require("../lib/connector-base");
const qrcode = require("qrcode-terminal");
const https = require("https");
const http = require("http");
const path = require("path");

const AUTH_DIR = path.join(__dirname, "auth_store");

const connector = new ConnectorBase("whatsapp", __dirname);

// --- WhatsApp-specific: group detection ---
connector.setGroupDetector((chatId) => String(chatId).endsWith("@g.us"));

// Minimal logger to suppress verbose Baileys output
const logger = {
  level: "silent",
  trace: () => {},
  debug: () => {},
  info: () => {},
  warn: (...args) => console.warn("[WA-LIB]", ...args),
  error: (...args) => console.error("[WA-LIB]", ...args),
  fatal: (...args) => console.error("[WA-LIB FATAL]", ...args),
  child: () => logger,
};

function extractPhoneNumber(jid) {
  return jid.replace(/@.*$/, "");
}

// --- Media helpers ---

async function downloadAndSaveMedia(msg, mediaType) {
  try {
    const buffer = await downloadMediaMessage(msg, "buffer", {});
    const mediaPath = await connector.saveMediaBuffer(buffer, mediaType);
    return { buffer, path: mediaPath, size: buffer.length };
  } catch (err) {
    console.warn(`[WA] Failed to download ${mediaType}: ${err.message}`);
    return null;
  }
}

function getMime(msg) {
  return (
    msg.message?.imageMessage?.mimetype ||
    msg.message?.videoMessage?.mimetype ||
    msg.message?.audioMessage?.mimetype ||
    msg.message?.stickerMessage?.mimetype ||
    msg.message?.documentMessage?.mimetype ||
    ""
  );
}

// --- WhatsApp socket ---
let currentSock = null;

// --- Send hooks ---
connector.setSendHooks({
  async sendText(chatId, text) {
    await currentSock.sendMessage(chatId, { text });
  },

  async sendImage(chatId, caption, imageBuffer, mime) {
    await currentSock.sendMessage(chatId, {
      image: imageBuffer,
      caption,
      mimetype: mime,
    });
  },

  async sendGif(chatId, caption, gifUrl) {
    let mp4Url = gifUrl;
    if (mp4Url.includes("media.tenor.com")) {
      mp4Url = mp4Url
        .replace(/AAAAC\//, "AAAPo/")
        .replace(/AAAAM\//, "AAAPo/")
        .replace(/\.gif$/, ".mp4");
    }
    const gifBuffer = await new Promise((resolve, reject) => {
      const get = mp4Url.startsWith("https") ? https.get : http.get;
      get(mp4Url, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          get(res.headers.location, (res2) => {
            const chunks = [];
            res2.on("data", (c) => chunks.push(c));
            res2.on("end", () => resolve(Buffer.concat(chunks)));
            res2.on("error", reject);
          });
          return;
        }
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => resolve(Buffer.concat(chunks)));
        res.on("error", reject);
      }).on("error", reject);
    });
    await currentSock.sendMessage(chatId, {
      video: gifBuffer,
      caption,
      gifPlayback: true,
      mimetype: "video/mp4",
    });
  },

  async sendAudio(chatId, text, audioBuffer, mime) {
    if (text) {
      await currentSock.sendMessage(chatId, { text });
    }
    await currentSock.sendMessage(chatId, {
      audio: audioBuffer,
      mimetype: mime,
      ptt: true,
    });
  },

  async sendSticker(chatId, stickerBuffer, text) {
    await currentSock.sendMessage(chatId, { sticker: stickerBuffer });
    if (text) {
      await currentSock.sendMessage(chatId, { text });
    }
  },

  async sendDocument(chatId, { buffer, fileName, mime, caption }) {
    await currentSock.sendMessage(chatId, {
      document: buffer,
      mimetype: mime,
      fileName,
      caption,
    });
  },

  async sendLocation(chatId, location, text) {
    await currentSock.sendMessage(chatId, {
      location: {
        degreesLatitude: location.latitude,
        degreesLongitude: location.longitude,
        name: location.name || "",
        address: location.address || "",
      },
    });
    if (text) {
      await currentSock.sendMessage(chatId, { text });
    }
  },

  async sendContact(chatId, contacts, text) {
    const vcards = contacts.map((c) => {
      if (c.vcard) return c.vcard;
      return [
        "BEGIN:VCARD",
        "VERSION:3.0",
        `FN:${c.name || "Contact"}`,
        c.phone ? `TEL;type=CELL:${c.phone}` : "",
        "END:VCARD",
      ].filter(Boolean).join("\n");
    });
    await currentSock.sendMessage(chatId, {
      contacts: {
        displayName: contacts[0].name || "Contact",
        contacts: vcards.map((vcard) => ({ vcard })),
      },
    });
    if (text) {
      await currentSock.sendMessage(chatId, { text });
    }
  },

  async sendPoll(chatId, poll, text) {
    await currentSock.sendMessage(chatId, {
      poll: {
        name: poll.name || "Poll",
        values: poll.options || [],
        selectableCount: poll.selectable_count || 1,
      },
    });
    if (text) {
      await currentSock.sendMessage(chatId, { text });
    }
  },

  async sendCard(chatId, card, text) {
    await currentSock.sendMessage(chatId, { text: connector.formatCard(card, text) });
  },

  async sendReaction(chatId, emoji, msgKey) {
    await currentSock.sendMessage(chatId, {
      react: { text: emoji, key: msgKey },
    });
  },

  async sendTyping(chatId) {
    await currentSock.presenceSubscribe(chatId);
    await currentSock.sendPresenceUpdate("composing", chatId);
  },

  async clearTyping(chatId) {
    await currentSock.sendPresenceUpdate("paused", chatId);
  },
});

// --- WhatsApp connection ---

async function startWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();
  console.log(`[WA] Using WA Web version: ${version.join(".")}`);

  const sock = makeWASocket({
    auth: state,
    logger,
    version,
    syncFullHistory: false,
    connectTimeoutMs: 60000,
  });
  currentSock = sock;

  sock.ev.process(async (events) => {
    // Connection + QR handling
    if (events["connection.update"]) {
      const { connection, lastDisconnect, qr } = events["connection.update"];

      if (qr) {
        console.log("\n[WA] Scan this QR code with WhatsApp -> Linked Devices -> Link a Device:\n");
        qrcode.generate(qr, { small: true });
      }

      if (connection === "close") {
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
        console.log(`[WA] Connection closed (status: ${statusCode}). ${shouldReconnect ? "Reconnecting..." : "Logged out."}`);
        if (shouldReconnect) {
          setTimeout(() => startWhatsApp(), 3000);
        }
      } else if (connection === "open") {
        console.log("[WA] Connected to WhatsApp");
      }
    }

    if (events["creds.update"]) {
      await saveCreds();
    }

    // Handle incoming messages
    if (events["messages.upsert"]) {
      const { messages, type } = events["messages.upsert"];
      if (type !== "notify") return;

      for (const msg of messages) {
        const chatId = msg.key.remoteJid;
        if (chatId === "status@broadcast") continue;

        const text =
          msg.message?.conversation ||
          msg.message?.extendedTextMessage?.text ||
          msg.message?.imageMessage?.caption ||
          msg.message?.videoMessage?.caption ||
          "";

        const mediaType = msg.message?.imageMessage ? "image"
          : msg.message?.videoMessage ? "video"
          : msg.message?.audioMessage ? "audio"
          : msg.message?.stickerMessage ? "sticker"
          : msg.message?.documentMessage ? "document"
          : null;

        const locationMsg = msg.message?.locationMessage || msg.message?.liveLocationMessage || null;
        const contactMsg = msg.message?.contactMessage || null;
        const contactsArrayMsg = msg.message?.contactsArrayMessage || null;
        const pollCreation = msg.message?.pollCreationMessage || msg.message?.pollCreationMessageV3 || null;
        const reactionMsg = msg.message?.reactionMessage || null;

        const participant = msg.key.participantAlt || msg.key.participant || chatId;
        const senderPhone = extractPhoneNumber(participant);

        // Handle reactions separately
        if (reactionMsg) {
          console.log(`[WA] ${senderPhone}: reacted ${reactionMsg.text}`);
          await connector.publishEvent("brain:event", {
            type: "reaction",
            emoji: reactionMsg.text,
            sender: senderPhone,
            chat_id: chatId,
            reacted_msg_key: reactionMsg.key,
            timestamp: Date.now(),
          });
          continue;
        }

        // Skip bot's own programmatic replies
        if (msg.key.fromMe && !msg.key.participant) continue;

        // Build normalized message for ConnectorBase
        const normalized = {
          chatId,
          senderId: senderPhone,
          senderName: msg.pushName || "",
          text,
          msgKey: msg.key,
        };

        // Download media
        if (mediaType) {
          const saved = await downloadAndSaveMedia(msg, mediaType);
          if (saved) {
            normalized.media = {
              type: mediaType,
              path: saved.path,
              mime: getMime(msg),
              size: saved.size,
              buffer: saved.buffer,
            };
          }
        }

        // Location
        if (locationMsg) {
          normalized.location = {
            latitude: locationMsg.degreesLatitude,
            longitude: locationMsg.degreesLongitude,
            name: locationMsg.name || "",
            address: locationMsg.address || "",
          };
        }

        // Contacts
        if (contactMsg) {
          normalized.contacts = [{
            name: contactMsg.displayName || "",
            vcard: contactMsg.vcard || "",
          }];
        }
        if (contactsArrayMsg) {
          normalized.contacts = (contactsArrayMsg.contacts || []).map((c) => ({
            name: c.displayName || "",
            vcard: c.vcard || "",
          }));
        }

        // Poll
        if (pollCreation) {
          normalized.poll = {
            name: pollCreation.name || "",
            options: (pollCreation.options || []).map((o) => o.optionName || ""),
            selectable_count: pollCreation.selectableOptionsCount || 1,
          };
        }

        await connector.handleIncoming(normalized);
      }

      // Mark processed messages as read
      const readKeys = messages
        .filter((m) => !m.key.fromMe && connector.activeChatIds.has(m.key.remoteJid))
        .map((m) => m.key);
      if (readKeys.length) {
        try { await sock.readMessages(readKeys); } catch (_) {}
      }
    }

    // Handle reactions from others
    if (events["messages.reaction"]) {
      for (const reaction of events["messages.reaction"]) {
        console.log(`[WA] Reaction: ${reaction.reaction?.text} on ${reaction.key?.id}`);
      }
    }
  });

  return sock;
}

// --- Main ---
async function main() {
  await connector.start();
  await startWhatsApp();
  console.log("[WA] Connector running. Send a WhatsApp message to interact with the brain.");
}

main().catch((err) => {
  console.error("[WA] Fatal:", err);
  process.exit(1);
});
