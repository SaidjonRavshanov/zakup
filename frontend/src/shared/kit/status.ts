/** Hujjat holati → yorliq (lug'at kaliti) + rang (prototipdagi bdg() jadvali bo'yicha). */
import type { Zk, ZkKey } from '@/shared/i18n/use-zk'
import type { Tone } from './primitives'

type Map = Record<string, [ZkKey, Tone]>

const REQUEST: Map = {
  DRAFT: ['req_draft', 'neutral'],
  PENDING_APPROVAL: ['req_pending', 'accent'],
  APPROVED: ['req_approved', 'solid'],
  PARTIALLY_APPROVED: ['req_partial', 'solid'],
  SPLIT: ['req_ordered', 'ok'],
  REJECTED: ['req_rejected', 'danger'],
  CANCELLED: ['req_cancelled', 'neutral'],
}

const ORDER: Map = {
  CREATED: ['po_created', 'neutral'],
  SENT: ['po_sent', 'accent'],
  CONFIRMED: ['po_confirmed', 'solid'],
  PARTIALLY_CONFIRMED: ['po_partial', 'solid'],
  REAPPROVAL: ['po_reapproval', 'warn'],
  RECEIVING: ['po_confirmed', 'solid'],
  RECEIVED: ['po_received', 'ok'],
  CLOSED: ['po_received', 'ok'],
  PARTIALLY_RECEIVED: ['po_received_part', 'warn'],
  CANCELLED: ['po_cancelled', 'neutral'],
}

const RECEIPT: Map = { ACCEPTED: ['rc_accepted', 'ok'], DISPUTED: ['rc_dispute', 'warn'] }
const IIKO: Map = { pending: ['ik_queued', 'neutral'], exported: ['ik_ok', 'ok'], failed: ['ik_err', 'danger'] }
const PAYMENT: Map = {
  SUBMITTED: ['pay_pending', 'accent'],
  APPROVED: ['pay_approved', 'solid'],
  PAID: ['pay_paid', 'ok'],
  REJECTED: ['pay_rejected', 'danger'],
  CANCELLED: ['pay_cancelled', 'neutral'],
}
const INVOICE: Map = {
  OPEN: ['inv_unpaid', 'neutral'],
  PARTIALLY_PAID: ['inv_partial', 'accent'],
  PAID: ['inv_paid', 'ok'],
  BLOCKED: ['inv_dispute', 'warn'],
  OVERDUE: ['inv_overdue', 'danger'],
}
const JOB: Map = {
  queued: ['job_queued', 'neutral'],
  running: ['job_run', 'accent'],
  done: ['job_done', 'ok'],
  failed: ['job_err', 'danger'],
}

const KIND = { request: REQUEST, order: ORDER, receipt: RECEIPT, iiko: IIKO, payment: PAYMENT, invoice: INVOICE, job: JOB }
export type StatusKind = keyof typeof KIND

export function status(z: Zk, kind: StatusKind, value: string): { label: string; tone: Tone } {
  const entry = KIND[kind][value]
  return entry ? { label: z[entry[0]], tone: entry[1] } : { label: value, tone: 'neutral' }
}
