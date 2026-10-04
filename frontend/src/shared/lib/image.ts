/**
 * Telefon kamerasi fotosi 4–8 MB — ombor internetida sekin. Yuborishdan oldin siqamiz (ARCHITECTURE §7):
 * uzun tomoni ≤ 1600 px, JPEG 0.8 → odatda 200–400 KB, nakladnoy matni o'qiladi.
 */
const MAX_SIDE = 1600
const QUALITY = 0.8

export async function compressImage(file: Blob): Promise<Blob> {
  if (!file.type.startsWith('image/')) return file
  try {
    const bitmap = await createImageBitmap(file)
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * scale)
    canvas.height = Math.round(bitmap.height * scale)
    canvas.getContext('2d')?.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close()
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', QUALITY))
    return blob && blob.size < file.size ? blob : file
  } catch {
    return file // eski brauzer — asl fayl
  }
}
