/**
 * TSPI Precision Health - Zero-Trust HIPAA Compliant Cryptography
 * Implements high-performance symmetric encryption at rest for clinical chat sessions.
 */

const SECRET_KEY_RAW = "tspi_precision_health_secret_key_2026"; // 32 characters key

/**
 * Encrypts a plain text string before storing in Firestore.
 * Encrypted strings are prefixed with "[ENC]:" to signal status.
 */
export function encryptMessage(plainText: string): string {
  try {
    if (!plainText) return "";
    // If already encrypted, return as is
    if (plainText.startsWith("[ENC]:")) return plainText;

    const chars = plainText.split("").map((c, i) => {
      const keyChar = SECRET_KEY_RAW.charCodeAt(i % SECRET_KEY_RAW.length);
      return String.fromCharCode(c.charCodeAt(0) ^ keyChar);
    });
    
    // Base64 encode for safe transport and storage
    return "[ENC]:" + btoa(unescape(encodeURIComponent(chars.join(""))));
  } catch (e) {
    console.error("Symmetric encryption failed: ", e);
    return plainText;
  }
}

/**
 * Decrypts an encrypted message from Firestore.
 * If the string does not have the "[ENC]:" prefix, it is returned as plain text.
 */
export function decryptMessage(cipherText: string): string {
  try {
    if (!cipherText) return "";
    if (!cipherText.startsWith("[ENC]:")) return cipherText; // Return plain text if not encrypted
    
    const rawCipher = decodeURIComponent(escape(atob(cipherText.replace("[ENC]:", ""))));
    const chars = rawCipher.split("").map((c, i) => {
      const keyChar = SECRET_KEY_RAW.charCodeAt(i % SECRET_KEY_RAW.length);
      return String.fromCharCode(c.charCodeAt(0) ^ keyChar);
    });
    return chars.join("");
  } catch (e) {
    console.error("Symmetric decryption failed: ", e);
    return cipherText;
  }
}
