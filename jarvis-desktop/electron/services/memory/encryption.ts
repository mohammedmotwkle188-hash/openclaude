import crypto from "node:crypto";

const ALGO = "aes-256-gcm";
const SALT_LEN = 16;
const IV_LEN = 12;

let cachedKey: Buffer | null = null;

export function deriveKey(passphrase: string, salt: Buffer): Buffer {
  return crypto.scryptSync(passphrase, salt, 32, { N: 2 ** 15, r: 8, p: 1 });
}

export function unlockVault(passphrase: string, salt: Buffer) {
  cachedKey = deriveKey(passphrase, salt);
}

export function lockVault() {
  cachedKey = null;
}

export function isUnlocked() {
  return cachedKey !== null;
}

export function newSalt(): Buffer {
  return crypto.randomBytes(SALT_LEN);
}

export function encryptField(plaintext: string): string {
  if (!cachedKey) throw new Error("Vault is locked — set a passphrase in Settings first.");
  const iv = crypto.randomBytes(IV_LEN);
  const cipher = crypto.createCipheriv(ALGO, cachedKey, iv);
  const enc = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([iv, tag, enc]).toString("base64");
}

export function decryptField(payload: string): string {
  if (!cachedKey) throw new Error("Vault is locked — set a passphrase in Settings first.");
  const buf = Buffer.from(payload, "base64");
  const iv = buf.subarray(0, IV_LEN);
  const tag = buf.subarray(IV_LEN, IV_LEN + 16);
  const enc = buf.subarray(IV_LEN + 16);
  const decipher = crypto.createDecipheriv(ALGO, cachedKey, iv);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(enc), decipher.final()]).toString("utf8");
}
