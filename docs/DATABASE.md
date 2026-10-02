# Zakup — ma'lumotlar bazasi (PostgreSQL 16)

> Arxitektura: [`ARCHITECTURE.md`](ARCHITECTURE.md). Bu yerda — konvensiyalar, sxemalar, asosiy jadvallar va indekslar.
> Ustunlarning yakuniy ro'yxati Alembic migratsiyalarida bo'ladi; bu hujjat — dizayn.

---

## 1. Konvensiyalar

| Qoida | Qiymat |
|---|---|
| Sxema | **har bir modulga bitta PostgreSQL sxemasi**: `identity`, `catalog`, `planning`, `procurement`, `receiving`, `finance`, `iiko`, `notify`, `audit`, `analytics`, `platform` |
| PK | `id uuid` — **UUIDv7** (ilovada generatsiya qilinadi, oflaynda ham) |
| Tashqi ID | `iiko_id uuid UNIQUE` — iiko GUID, sinxronizatsiya kaliti |
| Vaqt | faqat `timestamptz`, UTC'da saqlanadi; ko'rsatishda `Asia/Tashkent` |
| Sana | biznes sanasi (`delivery_date`, `due_date`) — `date` |
| Pul | `numeric(18,2)` + `currency char(3) DEFAULT 'UZS'` |
| Miqdor | `numeric(18,4)`; birlik har doim yonida (`unit_id`) |
| Narx (birlik uchun) | `numeric(18,4)` (bo'linishda yo'qotish bo'lmasligi uchun) |
| Status | `text` + `CHECK (status IN (...))` — enum'dan ko'ra migratsiya oson |
| Audit maydonlari | `created_at`, `created_by`, `updated_at`, `updated_by`, `version int` (optimistic lock) |
| O'chirish | **DELETE yo'q** biznes jadvallarida. Ma'lumotnomalar — `archived_at`; hujjatlar — storno/yangi versiya |
| FK | modul ichida — haqiqiy `FOREIGN KEY`; modullar orasida — ham FK (bitta baza), lekin kodda faqat ID orqali ishlatiladi |
| Nomlar | `snake_case`, jadval — ko'plik (`purchase_orders`), FK — `<entity>_id` |

---

## 2. Sxemalar va jadvallar

### 2.1 `identity`
| Jadval | Asosiy ustunlar |
|---|---|
| `users` | id, telegram_id `bigint UNIQUE`, full_name, phone, locale, is_active, activated_by |
| `roles` | code (`initiator`, `buyer`, `approver`, `storekeeper`, `accountant`, `auditor`, `admin`) |
| `user_store_roles` | user_id, store_id, role_code — **PK (user_id, store_id, role_code)** |
| `approval_limits` | role_code, store_id NULL, category_id NULL, max_amount |
| `refresh_tokens` | id, user_id, token_hash, expires_at, revoked_at |

### 2.2 `catalog`
| Jadval | Asosiy ustunlar |
|---|---|
| `stores` | id, iiko_id, department_iiko_id, name, address, archived_at |
| `units` | id, iiko_id, code (`kg`, `l`, `pcs`) |
| `products` | id, iiko_id, name, article, base_unit_id, category_id, product_type, archived_at, synced_at |
| `product_categories` | id, iiko_id, parent_id, name, monthly_budget |
| `suppliers` | id, iiko_id, name, inn, vat_mode, payment_terms (`prepay`/`on_delivery`/`deferred`), deferral_days, credit_limit, min_order_amount, order_cutoff time, order_weekdays `int[]`, delivery_weekdays `int[]`, lead_time_days, contacts jsonb, archived_at |
| `supplier_products` | id, supplier_id, product_id, supplier_sku, supplier_name, **pack_unit**, **pack_factor** (1 qop = 25 kg), **order_multiple**, price, price_valid_from — `UNIQUE (supplier_id, product_id, supplier_sku)` |
| `supplier_price_history` | supplier_product_id, price, valid_from, source (`iiko`/`manual`/`supplier_response`/`receipt`) |
| `purchase_cards` | id, product_id, store_id, mode (`auto`/`manual`/`disabled`), safety_stock, coverage_days, shelf_life_days, primary_supplier_id, alternative_supplier_id, seasonal_factor — `UNIQUE (product_id, store_id)` |

> `supplier_products` — WORKFLOW'dagi 17-bo'shliq ("tovar ↔ yetkazib beruvchi tovari" mosligi) va 1-bo'shliq (birliklar).

### 2.3 `planning`
| Jadval | Asosiy ustunlar |
|---|---|
| `stock_snapshots` | store_id, product_id, qty, taken_at — **oxirgi qiymat** `stock_current` (PK store_id+product_id) da, tarix — oy bo'yicha partitsiya |
| `consumption_daily` | store_id, product_id, day `date`, qty, is_anomaly — PK (store_id, product_id, day); **oy bo'yicha RANGE partitsiya** |
| `anomaly_days` | store_id, day, reason (`banquet`/`holiday`/`inventory`) |
| `demand_profiles` | store_id, product_id, weekday 0–6, avg_qty, window_days, computed_at |

### 2.4 `procurement`
| Jadval | Asosiy ustunlar |
|---|---|
| `purchase_requests` | id, number, store_id, type (`auto`/`manual`/`event`), status, needed_by, total_amount, initiator_id, version |
| `purchase_request_lines` | id, request_id, product_id, qty_suggested, qty_final, adjust_reason, calc_snapshot jsonb (*nega shuncha*: sarf, qoldiq, yo'lda, formula), expected_supplier_id, expected_price, approval_state |
| `approvals` | id, request_id \| po_id, step, approver_id, decision (`approved`/`partial`/`returned`/`rejected`), comment, role_conflict bool, decided_at |
| `purchase_orders` | id, number, request_id, supplier_id, store_id, delivery_date, status, sent_at, sent_channel, response_deadline, total_amount, version — **bitta PO = yetkazib beruvchi + ombor + sana** |
| `purchase_order_lines` | id, po_id, request_line_id, product_id, supplier_product_id, qty_ordered (yetkazib beruvchi birligida), qty_base, price_ordered, qty_confirmed, price_confirmed, response (`confirmed`/`price_changed`/`qty_changed`/`out_of_stock`/`substituted`), qty_received_total |
| `supplier_response_tokens` | po_id, token_hash, expires_at, used_at |

### 2.5 `receiving`
| Jadval | Asosiy ustunlar |
|---|---|
| `receipts` | id, number, po_id, store_id, status, received_by, supplier_invoice_no, esf_no, supplier_invoice_date, total_fact, submitted_at, version, parent_receipt_id (tuzatish versiyasi) |
| `receipt_lines` | id, receipt_id, po_line_id NULL, product_id, qty_fact, price_fact, vat_rate, qty_defect, defect_reason, is_substitution, batch_no, expiry_date |
| `receipt_attachments` | id, receipt_id, line_id NULL, kind (`invoice_photo`/`defect_photo`), s3_key, sha256, size |
| `discrepancies` | id, receipt_line_id, kind (`qty`/`price_up`/`price_down`/`short`/`defect`/`substitution`), expected, actual, within_tolerance bool |
| `disputes` | id, receipt_id, status, owner_id, due_at, resolution (`accepted`/`return`/`discount`/`replacement`), resolution_amount |
| `dispute_messages` | id, dispute_id, author_id, body, created_at |

### 2.6 `finance`
| Jadval | Asosiy ustunlar |
|---|---|
| `obligations` | id, supplier_id, receipt_id UNIQUE, amount, due_date, status, blocked_reason |
| `supplier_credits` | id, supplier_id, kind (`prepayment`/`return`/`dispute_discount`), amount, source_id |
| `payment_requests` | id, supplier_id, status, requested_by, approved_by, total |
| `payments` | id, payment_request_id, amount, method (`cash`/`transfer`), paid_at, paid_by, proof_s3_key |
| `payment_allocations` | payment_id, obligation_id, amount — **to'lov aniq nakladnoyga bog'lanadi** |
| `reconciliations` | id, supplier_id, period, our_balance, iiko_balance, supplier_balance, diff |

Saldo **saqlanmaydi**, hisoblanadi (view `finance.supplier_balance_v`): `obligations − allocations − credits`. Tez ishlashi uchun `analytics` da materialized view bor.

### 2.7 `iiko`
| Jadval | Asosiy ustunlar |
|---|---|
| `sync_state` | entity (`products`/`stores`/...), last_success_at, cursor, last_error |
| `invoice_exports` | receipt_id **UNIQUE**, iiko_document_id, iiko_document_number, status, attempts, last_error, posted bool |
| `integration_log` | id, method, path, http_status, duration_ms, error, created_at — kun bo'yicha partitsiya, 30 kun |
| `foreign_invoices` | iiko_document_id, store_id, supplier_id, date, amount, matched_receipt_id NULL — *tizimdan tashqari kirimlar* |

### 2.8 `platform`, `audit`, `notify`
| Jadval | Asosiy ustunlar |
|---|---|
| `platform.outbox` | id, aggregate_type, aggregate_id, event_type, payload jsonb, created_at, processed_at NULL, attempts, next_attempt_at |
| `platform.idempotency_keys` | key, user_id, request_hash, response_status, response_body jsonb, created_at (48 soat) |
| `platform.settings` | key, value jsonb, store_id NULL — dopusklar, jadval, limitlar |
| `audit.log` | id, occurred_at, actor_id, action, entity_type, entity_id, before jsonb, after jsonb, reason, role_conflict, request_id — **faqat INSERT**, oy bo'yicha partitsiya |
| `notify.messages` | id, recipient_id, channel, template, payload, status, sent_at, acknowledged_at |
| `notify.documents` | id, kind (`receipt_act`/`discrepancy_protocol`/`payment_register`), entity_id, s3_key |

---

## 3. Indekslar (asosiylari)

```sql
-- faol hujjatlar ro'yxati (keyset pagination)
CREATE INDEX ON procurement.purchase_orders (store_id, status, created_at DESC, id DESC);
-- "yo'lda" hisoblash: faqat ochiq PO qatorlari (partial index)
CREATE INDEX ON procurement.purchase_order_lines (product_id)
  WHERE qty_received_total < qty_base;
-- outbox relay
CREATE INDEX ON platform.outbox (next_attempt_at) WHERE processed_at IS NULL;
-- muddati o'tgan majburiyatlar
CREATE INDEX ON finance.obligations (supplier_id, due_date) WHERE status IN ('OPEN','PARTIALLY_PAID');
-- tovar qidiruvi (rus / o'zbek)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ON catalog.products USING gin (name gin_trgm_ops);
-- audit: entity tarixi
CREATE INDEX ON audit.log (entity_type, entity_id, occurred_at);
```

Qoida: har bir yangi so'rov `EXPLAIN (ANALYZE, BUFFERS)` bilan tekshiriladi; `pg_stat_statements` yoqilgan.

## 4. Audit-log o'zgarmasligi

```sql
REVOKE UPDATE, DELETE, TRUNCATE ON audit.log FROM app_rw;
-- qo'shimcha himoya
CREATE TRIGGER audit_log_immutable BEFORE UPDATE OR DELETE ON audit.log
  FOR EACH ROW EXECUTE FUNCTION audit.raise_immutable();
```
Audit yozuvi biznes o'zgarishi bilan **bitta tranzaksiyada** yoziladi (application qatlamida, UoW orqali), trigger orqali emas: trigger kim va nima uchun o'zgartirganini bilmaydi.

## 5. DB rollari

| Rol | Huquq |
|---|---|
| `app_migrator` | DDL (faqat Alembic) |
| `app_rw` | api/worker: SELECT/INSERT/UPDATE; audit.log — faqat INSERT |
| `app_ro` | analitika, nazoratchi hisobotlari, BI |

## 6. Ulanish va pool

- PgBouncer `pool_mode=transaction`, `default_pool_size` ≈ 2 × CPU yadrolari.
- SQLAlchemy: `pool_size=10, max_overflow=5` (har bir api process), `connect_args={"statement_cache_size": 0}`.
- `statement_timeout = 5s` (api), `30s` (worker), `idle_in_transaction_session_timeout = 10s`.
