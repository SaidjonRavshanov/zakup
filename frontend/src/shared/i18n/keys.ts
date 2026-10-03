/** Lug'at kalitlari — entities bilan bir xil bo'lishi kerak (shared entities'ni import qila olmaydi). */
export type PurchaseOrderStatusKey =
  | 'CREATED'
  | 'SENT'
  | 'CONFIRMED'
  | 'PARTIALLY_CONFIRMED'
  | 'REAPPROVAL'
  | 'RECEIVING'
  | 'RECEIVED'
  | 'PARTIALLY_RECEIVED'
  | 'CLOSED'
  | 'CANCELLED'

export type RoleKey = 'initiator' | 'buyer' | 'approver' | 'storekeeper' | 'accountant' | 'auditor' | 'admin'

/** O'lchov birligi kodi (iiko birliklari shu kodlarga moslanadi). */
export type UnitCode = 'kg' | 'g' | 'l' | 'ml' | 'pcs' | 'pack' | 'box' | 'bag'

/** Backend xato kodlari (`{"code": ...}`) — backend/src/zakup/platform/i18n.py bilan mos. */
export type ErrorCode =
  | 'validation_error'
  | 'not_found'
  | 'conflict'
  | 'permission_denied'
  | 'invalid_transition'
  | 'internal_error'
  | 'duplicate_inn'
  | 'invalid_supplier'
  | 'invalid_init_data'
  | 'account_pending'
  | 'unauthenticated'
  | 'invalid_token'
  | 'invalid_refresh_token'
  | 'self_lockout'
  | 'invalid_user'
  | 'network_error'
  | 'unknown'
