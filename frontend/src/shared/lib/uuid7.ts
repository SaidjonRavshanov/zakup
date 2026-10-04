/**
 * UUIDv7 (RFC 9562) — klientda yaratiladi (ADR-10): oflayn hujjat ID'si va idempotentlik kaliti.
 * 48 bit vaqt (ms) + versiya 7 + 74 bit tasodifiy.
 */
export function uuid7(): string {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  let ms = Date.now()
  for (let i = 5; i >= 0; i--) {
    bytes[i] = ms % 256
    ms = Math.floor(ms / 256)
  }
  bytes[6] = (bytes[6]! & 0x0f) | 0x70
  bytes[8] = (bytes[8]! & 0x3f) | 0x80
  const hex = [...bytes].map((b) => b.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
