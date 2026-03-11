/**
 * Telegram Connector — bridges Telegram bot messages to the Sentient brain via Redis.
 *
 * Uses ConnectorBase for Redis, config, access control, and response dispatch.
 * This file handles Telegram-specific Telegraf integration.
 *
 * Auth: BOT_TOKEN from @BotFather (no QR, no session persistence needed)
 */

const { Telegraf } = require("telegraf");
const ConnectorBase = require("../lib/connector-base");
const path = require("path");
const fs = require("fs");
const https = require("https");

const connector = new ConnectorBase("telegram", __dirname);

// --- Telegram-specific: group detection ---
connector.setGroupDetector((chatId) => Number(chatId) < 0);

// Override addressesBot for Telegram (/command and @mention support)
connector.addressesBot = function (text) {
  const lower = text.toLowerCase().trim();
  if (lower.startsWith("/")) return true;
  if (connector.platformData.botUsername && lower.includes(`@${connector.platformData.botUsername}`)) return true;
  for (const name of connector.botNames) {
    if (lower.startsWith(name)) {
      const after = lower[name.length];
      if (!after || ",: .!?\n".includes(after)) return true;
    }
  }
  return false;
};

// Override stripBotPrefix for Telegram
connector.stripBotPrefix = function (text) {
  let result = text;
  const lower = result.toLowerCase().trim();
  if (lower.startsWith("/")) {
    result = result.replace(/^\/\w+(@\w+)?\s*/, "").trim();
    if (result) return result;
    return text;
  }
  if (connector.platformData.botUsername) {
    result = result.replace(new RegExp(`@${connector.platformData.botUsername}\\s*`, "gi"), "").trim();
  }
  for (const name of connector.botNames) {
    if (lower.startsWith(name)) {
      const after = lower[name.length];
      if (!after || ",: .!?\n".includes(after)) {
        let stripped = result.trim().substring(name.length);
        stripped = stripped.replace(/^[,:\s.!?]+/, "").trim();
        return stripped || text;
      }
    }
  }
  return result;
};

// --- Media helpers ---

async function downloadFile(ctx, fileId) {
  try {
    const link = await ctx.telegram.getFileLink(fileId);
    const url = link.href || link.toString();
    const buffer = await new Promise((resolve, reject) => {
      https.get(url, (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => resolve(Buffer.concat(chunks)));
        res.on("error", reject);
      }).on("error", reject);
    });
    return buffer;
  } catch (err) {
    console.warn(`[TG] Download failed: ${err.message}`);
    return null;
  }
}

async function downloadAndSaveMedia(ctx, fileId, mediaType) {
  const buffer = await downloadFile(ctx, fileId);
  if (!buffer) return null;
  const mediaPath = await connector.saveMediaBuffer(buffer, mediaType);
  return { buffer, path: mediaPath, size: buffer.length };
}

// --- Bot setup ---

const configFile = path.join(__dirname, "config.json");
let botToken = "";
if (fs.existsSync(configFile)) {
  try {
    const loaded = JSON.parse(fs.readFileSync(configFile, "utf8"));
    botToken = loaded.bot_token || "";
  } catch (_) {}
}
if (!botToken) {
  console.error("[TG] FATAL: No bot_token in config.json. Get one from @BotFather.");
  process.exit(1);
}

const bot = new Telegraf(botToken);
connector.platformData.botUsername = null;

// --- Send hooks ---
connector.setSendHooks({
  async sendText(chatId, text) {
    try {
      await bot.telegram.sendMessage(chatId, text, { parse_mode: "Markdown" });
    } catch (_) {
      await bot.telegram.sendMessage(chatId, text);
    }
  },

  async sendImage(chatId, caption, imageBuffer, mime) {
    await bot.telegram.sendPhoto(chatId, { source: imageBuffer }, { caption });
  },

  async sendGif(chatId, caption, gifUrl) {
    await bot.telegram.sendAnimation(chatId, gifUrl, { caption });
  },

  async sendAudio(chatId, text, audioBuffer, mime) {
    if (text) {
      try {
        await bot.telegram.sendMessage(chatId, text, { parse_mode: "Markdown" });
      } catch (_) {
        await bot.telegram.sendMessage(chatId, text);
      }
    }
    await bot.telegram.sendVoice(chatId, { source: audioBuffer });
  },

  async sendSticker(chatId, stickerBuffer, text) {
    await bot.telegram.sendSticker(chatId, { source: stickerBuffer });
    if (text) {
      await bot.telegram.sendMessage(chatId, text, { parse_mode: "Markdown" });
    }
  },

  async sendDocument(chatId, { buffer, fileName, mime, caption }) {
    await bot.telegram.sendDocument(chatId, { source: buffer, filename: fileName }, { caption });
  },

  async sendLocation(chatId, location, text) {
    await bot.telegram.sendLocation(chatId, location.latitude, location.longitude);
    if (text) {
      await bot.telegram.sendMessage(chatId, text, { parse_mode: "Markdown" });
    }
  },

  async sendContact(chatId, contacts, text) {
    const c = contacts[0];
    await bot.telegram.sendContact(chatId, c.phone || "", c.name || "Contact");
    if (text) {
      await bot.telegram.sendMessage(chatId, text, { parse_mode: "Markdown" });
    }
  },

  async sendPoll(chatId, poll, text) {
    await bot.telegram.sendPoll(chatId, poll.name || "Poll", poll.options || [], {
      allows_multiple_answers: (poll.selectable_count || 1) > 1,
    });
    if (text) {
      await bot.telegram.sendMessage(chatId, text, { parse_mode: "Markdown" });
    }
  },

  async sendCard(chatId, card, text) {
    await bot.telegram.sendMessage(chatId, connector.formatCard(card, text), { parse_mode: "Markdown" });
  },

  async sendTyping(chatId) {
    await bot.telegram.sendChatAction(chatId, "typing");
  },
});

// --- Message handler ---
bot.on("message", async (ctx) => {
  if (!connector.platformData.botUsername && ctx.botInfo?.username) {
    connector.platformData.botUsername = ctx.botInfo.username.toLowerCase();
  }

  const chatId = ctx.chat.id;
  const userId = ctx.from?.id;
  const text = ctx.message.text || ctx.message.caption || "";

  let mediaType = null;
  let fileId = null;

  if (ctx.message.photo) {
    mediaType = "photo";
    fileId = ctx.message.photo[ctx.message.photo.length - 1].file_id;
  } else if (ctx.message.video) {
    mediaType = "video";
    fileId = ctx.message.video.file_id;
  } else if (ctx.message.audio) {
    mediaType = "audio";
    fileId = ctx.message.audio.file_id;
  } else if (ctx.message.voice) {
    mediaType = "voice";
    fileId = ctx.message.voice.file_id;
  } else if (ctx.message.sticker) {
    mediaType = "sticker";
    fileId = ctx.message.sticker.file_id;
  } else if (ctx.message.animation) {
    mediaType = "animation";
    fileId = ctx.message.animation.file_id;
  } else if (ctx.message.document) {
    mediaType = "document";
    fileId = ctx.message.document.file_id;
  }

  const senderName = [ctx.from?.first_name, ctx.from?.last_name].filter(Boolean).join(" ");
  const normalized = {
    chatId: String(chatId),
    senderId: String(userId),
    senderName,
    text,
    extra: {
      language_code: ctx.from?.language_code || "",
      msg_id: ctx.message.message_id,
    },
  };

  if (mediaType && fileId) {
    const saved = await downloadAndSaveMedia(ctx, fileId, mediaType);
    if (saved) {
      const mappedType = mediaType === "photo" ? "image"
        : mediaType === "voice" ? "audio"
        : mediaType === "animation" ? "video" : mediaType;
      normalized.media = {
        type: mappedType,
        path: saved.path,
        mime: mediaType === "photo" ? "image/jpeg"
          : mediaType === "voice" ? "audio/ogg"
          : mediaType === "animation" ? "video/mp4" : "",
        size: saved.size,
        buffer: saved.buffer,
      };
    }
  }

  if (ctx.message.location) {
    normalized.location = {
      latitude: ctx.message.location.latitude,
      longitude: ctx.message.location.longitude,
    };
  }

  if (ctx.message.contact) {
    const c = ctx.message.contact;
    normalized.contacts = [{
      name: `${c.first_name || ""} ${c.last_name || ""}`.trim(),
      phone: c.phone_number || "",
    }];
  }

  if (ctx.message.poll) {
    const p = ctx.message.poll;
    normalized.poll = {
      name: p.question || "",
      options: (p.options || []).map((o) => o.text || ""),
      selectable_count: p.allows_multiple_answers ? 0 : 1,
    };
  }

  await connector.handleIncoming(normalized);
});

// --- Main ---
async function main() {
  await connector.start();
  bot.launch();
  connector.platformData.botUsername = (await bot.telegram.getMe()).username?.toLowerCase();
  console.log("[TG] Bot launched. Listening for messages...");

  process.once("SIGINT", () => bot.stop("SIGINT"));
  process.once("SIGTERM", () => bot.stop("SIGTERM"));
}

main().catch((err) => {
  console.error("[TG] Fatal:", err);
  process.exit(1);
});
