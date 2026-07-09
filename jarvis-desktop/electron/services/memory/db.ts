import path from "node:path";
import fs from "node:fs";
import Database from "better-sqlite3";
import { app } from "electron";
import { decryptField, encryptField, isUnlocked, newSalt } from "./encryption";
import type { ChatMessage, ReminderItem } from "../../../shared/types";

let db: Database.Database;

export function initDb() {
  const dir = app.getPath("userData");
  fs.mkdirSync(dir, { recursive: true });
  db = new Database(path.join(dir, "jarvis-memory.db"));
  db.pragma("journal_mode = WAL");

  db.exec(`
    CREATE TABLE IF NOT EXISTS vault_meta (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      salt TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS messages (
      id TEXT PRIMARY KEY,
      role TEXT NOT NULL,
      body TEXT NOT NULL,
      provider TEXT,
      timestamp INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS memories (
      key TEXT PRIMARY KEY,
      body TEXT NOT NULL,
      updated_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS reminders (
      id TEXT PRIMARY KEY,
      text TEXT NOT NULL,
      due_at INTEGER NOT NULL,
      done INTEGER NOT NULL DEFAULT 0
    );
  `);

  return db;
}

export function getOrCreateSalt(): Buffer {
  const row = db.prepare("SELECT salt FROM vault_meta WHERE id = 1").get() as { salt: string } | undefined;
  if (row) return Buffer.from(row.salt, "base64");
  const salt = newSalt();
  db.prepare("INSERT INTO vault_meta (id, salt) VALUES (1, ?)").run(salt.toString("base64"));
  return salt;
}

export function hasVaultBeenInitialized(): boolean {
  const row = db.prepare("SELECT salt FROM vault_meta WHERE id = 1").get();
  return !!row;
}

export function saveMessage(msg: ChatMessage) {
  const body = isUnlocked() ? encryptField(msg.text) : msg.text;
  db.prepare("INSERT INTO messages (id, role, body, provider, timestamp) VALUES (?, ?, ?, ?, ?)").run(
    msg.id,
    msg.role,
    body,
    msg.provider ?? null,
    msg.timestamp,
  );
}

export function loadHistory(limit = 200): ChatMessage[] {
  const rows = db
    .prepare("SELECT id, role, body, provider, timestamp FROM messages ORDER BY timestamp ASC LIMIT ?")
    .all(limit) as Array<{ id: string; role: ChatMessage["role"]; body: string; provider: string | null; timestamp: number }>;

  return rows.map((r) => {
    let text = r.body;
    if (isUnlocked()) {
      try {
        text = decryptField(r.body);
      } catch {
        text = "[locked — unlock vault to view]";
      }
    } else {
      text = "[locked — set passphrase in Settings to decrypt]";
    }
    return {
      id: r.id,
      role: r.role,
      text,
      timestamp: r.timestamp,
      provider: (r.provider as ChatMessage["provider"]) ?? undefined,
    };
  });
}

export function clearHistory() {
  db.prepare("DELETE FROM messages").run();
}

export function rememberFact(key: string, value: string) {
  const body = isUnlocked() ? encryptField(value) : value;
  db.prepare(
    "INSERT INTO memories (key, body, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET body = excluded.body, updated_at = excluded.updated_at",
  ).run(key, body, Date.now());
}

export function recallFacts(): Record<string, string> {
  const rows = db.prepare("SELECT key, body FROM memories").all() as Array<{ key: string; body: string }>;
  const out: Record<string, string> = {};
  for (const r of rows) {
    try {
      out[r.key] = isUnlocked() ? decryptField(r.body) : "[locked]";
    } catch {
      out[r.key] = "[locked]";
    }
  }
  return out;
}

export function addReminder(item: ReminderItem) {
  db.prepare("INSERT INTO reminders (id, text, due_at, done) VALUES (?, ?, ?, 0)").run(item.id, item.text, item.dueAt);
}

export function listReminders(): ReminderItem[] {
  const rows = db.prepare("SELECT id, text, due_at as dueAt, done FROM reminders ORDER BY due_at ASC").all() as Array<{
    id: string;
    text: string;
    dueAt: number;
    done: number;
  }>;
  return rows.map((r) => ({ ...r, done: !!r.done }));
}

export function toggleReminder(id: string) {
  db.prepare("UPDATE reminders SET done = 1 - done WHERE id = ?").run(id);
}
