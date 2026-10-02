import type { Messages } from '@/shared/i18n'
import type { ErrorCode } from '@/shared/i18n/keys'
import { ApiError } from './client'

const isErrorCode = (code: string, t: Messages): code is ErrorCode => code in t.errors

/**
 * Foydalanuvchiga ko'rsatiladigan xato matni.
 * Backend xabarni allaqachon tilda qaytaradi (Accept-Language); u bo'lmasa — kod bo'yicha lug'at.
 */
export function describeError(error: unknown, t: Messages): string {
  if (error instanceof ApiError) {
    if (error.message && error.message !== error.code) return error.message
    return isErrorCode(error.code, t) ? t.errors[error.code] : t.errors.unknown
  }
  if (error instanceof TypeError) return t.errors.network_error // fetch: tarmoq yo'q
  return t.errors.unknown
}
