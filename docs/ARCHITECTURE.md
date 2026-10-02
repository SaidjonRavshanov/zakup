# Zakup — arxitektura v1

> Asos: [`WORKFLOW.md`](WORKFLOW.md) (biznes-jarayon). Bu hujjat — **qanday quramiz**.
> Bog'liq: [`DATABASE.md`](DATABASE.md) (ma'lumotlar modeli), [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md) (UI).

---

## 0. Asosiy qarorlar (ADR qisqacha)

| # | Qaror | Nega | Rad etilgan variant |
|---|---|---|---|
| ADR-01 | **Modular monolith**, bitta kod bazasi, bir nechta process (api / worker / scheduler / bot) | Jamoa kichik, bitta PostgreSQL, audit va pul uchun tranzaksion izchillik kerak. Modul chegaralari qat'iy — keyin servisga ajratish oson | Mikroservislar: distributed tranzaksiya, ortiqcha DevOps |
| ADR-02 | **Clean Architecture** har bir modul ichida: `domain → application → infrastructure / api` | Biznes qoidalar (formula, dopusklar, rollar) framework'dan mustaqil va test qilinadi | "Fat router + ORM model" — tez boshlanadi, keyin chalkashadi |
| ADR-03 | **CQRS-lite**: yozish — domain + Unit of Work; o'qish — to'g'ridan-to'g'ri SQL → DTO | O'qish 90% trafik; ORM hydratsiyasisiz tez | To'liq CQRS + event sourcing: bu loyiha uchun ortiqcha |
| ADR-04 | **Transactional Outbox** — iiko, Telegram, PDF uchun | "Bazaga yozildi, lekin iikoga ketmadi" holati bo'lmaydi; retry xavfsiz | Router ichidan to'g'ridan-to'g'ri HTTP chaqiruv |
| ADR-05 | **iiko bilan faqat bitta connector-worker** gaplashadi (Redis lock, bitta sessiya, `logout` finally'da) | iiko litsenziyasi bitta aktiv sessiyaga ruxsat beradi (WORKFLOW B1, B15) | API process'dan to'g'ridan-to'g'ri chaqirish |
| ADR-06 | **Telegram Mini App** (SPA) + **aiogram 3** bot | Foydalanuvchilar Telegram'da; login avtomatik (initData) | Alohida mobil ilova |
| ADR-07 | Frontend: **React 19 + Vite + TypeScript**, TanStack Query, Tailwind v4 | Ekotizim, tezlik, kichik bundle (budjet pastda) | Next.js — SSR Mini App uchun foyda bermaydi |
| ADR-08 | **Oflayn qabul** — IndexedDB outbox + idempotency key | Omborda internet yo'q bo'lishi mumkin (WORKFLOW B8) | Faqat onlayn |
| ADR-09 | Pul — `numeric(18,2)`, miqdor — `numeric(18,4)`, **hech qachon float** | Saldo kopeykagacha mos kelishi shart | `float` |
| ADR-10 | PK — **UUIDv7** | Klientda generatsiya (oflayn), vaqt bo'yicha tartiblangan → B-tree indeks shishmaydi | `serial` (oflaynda ishlamaydi), UUIDv4 (indeks fragmentatsiyasi) |

---

## 1. Kontekst (C4 — 1-daraja)

```
 ┌────────────┐  Telegram Mini App   ┌───────────────────────────┐   iikoServer API   ┌──────────┐
 │ Xodimlar   │ ───────────────────► │                           │ ◄────────────────► │   iiko   │
 │ (7 rol)    │ ◄── bot xabarlari ── │       ZAKUP TIZIMI        │                    └──────────┘
 └────────────┘                      │                           │   SMTP / Telegram  ┌──────────────┐
 ┌────────────┐  imzolangan havola   │                           │ ─────────────────► │ Yetkazib     │
 │ Yetkazib   │ ───────────────────► │                           │                    │ beruvchilar  │
 │ beruvchi   │  (ro'yxatsiz sahifa) └───────────────────────────┘                    └──────────────┘
 └────────────┘
```

## 2. Konteynerlar (C4 — 2-daraja)

```
                         ┌───────────────── Caddy (TLS, brotli, static, rate-limit) ─────────────────┐
                         │                                                                           │
             /app/* ─────┤  SPA (Vite build, immutable hash assets)                                  │
             /api/* ─────┤──► api      (FastAPI, uvicorn+uvloop, N worker)                           │
             /tg/hook ───┤──► bot      (aiogram 3, webhook)                                          │
                         └──────────────────────────┬────────────────────────────────────────────────┘
                                                    │
        ┌────────────────────┬──────────────────────┼─────────────────────┬────────────────────┐
        ▼                    ▼                      ▼                     ▼                    ▼
  ┌───────────┐       ┌─────────────┐        ┌────────────┐        ┌────────────┐       ┌────────────┐
  │PostgreSQL │       │   Redis     │        │  worker    │        │ scheduler  │       │ MinIO / S3 │
  │ 16        │       │ cache,      │        │ (Taskiq)   │        │ (cron:     │       │ foto,      │
  │ + PgBouncer│      │ queue, lock │        │ outbox,    │        │ sync, avto-│       │ PDF        │
  └───────────┘       └─────────────┘        │ iiko, PDF, │        │ zayavka)   │       └────────────┘
                                             │ notify     │        └────────────┘
                                             └─────┬──────┘
                                                   │ yagona sessiya (Redis lock)
                                                   ▼
                                               iikoServer
```

| Process | Vazifa | Masshtab |
|---|---|---|
| `api` | HTTP so'rovlar, faqat DB + Redis bilan ishlaydi, **tashqi API'ga chiqmaydi** | gorizontal (CPU soni bo'yicha) |
| `worker` | outbox'ni o'qish, iiko eksport, PDF, xabarlar, sinxronizatsiya | navbatlar bo'yicha; `iiko` navbati — **concurrency=1** |
| `scheduler` | cron: iiko sync, avto-zayavka 06:00, eslatmalar, mat. view refresh | 1 instance (leader lock) |
| `bot` | Telegram webhook, inline tugmalar (tasdiqlash, yetkazib beruvchi javobi) | 1–2 |

Bitta Docker image, har xil `entrypoint` → kod takrorlanmaydi.

---

## 3. Modullar (bounded context)

| Modul | Mas'uliyati | WORKFLOW |
|---|---|---|
| `identity` | foydalanuvchi, rol, omborga ruxsat, tasdiqlash limitlari, Telegram auth | 2-bo'lim |
| `catalog` | iiko'dan tovar, ombor, yetkazib beruvchi; **xarid kartochkasi**, birlik konvertatsiyasi, yetkazib beruvchi artikullari, prayslar | B1, B3, B6 |
| `planning` | qoldiq snapshot, sarf, hafta kuni profili, ehtiyoj hisobi | B2, B3 |
| `procurement` | zayavka, tasdiqlash, PO, yetkazib beruvchi javobi | B4–B7 |
| `receiving` | qabul, farqlar, nizo (dispute), qaytarish | B8, B9 |
| `finance` | majburiyat (nakladnoy), to'lov zayavkasi, to'lov, taqsimlash, saldo | B12 |
| `integration_iiko` | connector, sinxronizatsiya, kirim eksporti, teskari solishtirish | B1, B10, B15 |
| `notifications` | Telegram/email, PDF hujjatlar, yetkazilganini tasdiqlash | B11 |
| `audit` | o'zgarmas audit-log, nazoratchi ekrani | B13 |
| `analytics` | read-model'lar, materialized view'lar, hisobotlar | B14 |
| `shared_kernel` | `Money`, `Quantity`, `Unit`, `EntityId`, `Clock`, domain event bazasi, xatolar | — |

### 3.1 Modullar orasidagi qoidalar

1. Modul boshqa modulning **faqat `application` qatlamidagi public interfeysini** (facade / query service) chaqiradi. Boshqa modulning ORM modeli, jadvali, repository'si — **taqiqlangan**.
2. Asinxron reaksiya — **domain event** orqali: `ReceiptCompleted` → `finance` majburiyat yaratadi, `integration_iiko` eksport navbatiga qo'yadi, `notifications` akt yuboradi. `receiving` ular haqida hech narsa bilmaydi (Open/Closed).
3. Bog'liqlik yo'nalishi (sikl yo'q):
   ```
   identity, catalog ◄── planning ◄── procurement ◄── receiving ◄── finance
                   ▲                                                 │
   audit, notifications, analytics, integration_iiko — event'larga obuna bo'ladi
   ```
4. Chegaralar **`import-linter`** bilan CI'da tekshiriladi — qoida buzilsa build yiqiladi.

---

## 4. Modul ichidagi qatlamlar (Clean Architecture)

```
api ───────────► application ───────────► domain
(FastAPI router,  (use case, DTO, port      (entity, value object,
 Pydantic schema,  interfeyslari, UoW)        status machine, policy,
 dependency)            ▲                     domain event, repository Protocol)
                        │ implementatsiya qiladi
infrastructure ─────────┘
(SQLAlchemy repo, iiko HTTP client, S3, Telegram)
```

| Qatlam | Nima bor | Nimani import qila oladi |
|---|---|---|
| `domain` | sof Python: `PurchaseOrder`, `Money`, `DemandCalculator`, `ToleranceRule`, `SegregationOfDutiesPolicy` | faqat `shared_kernel` |
| `application` | `ApprovePurchaseRequest`, `CompleteReceipt` handler'lari; port'lar: `IikoGateway`, `Notifier`, `FileStorage`, `UnitOfWork` | `domain` |
| `infrastructure` | port'larning implementatsiyasi | `application`, `domain` |
| `api` | HTTP ↔ use case moslashtirish, **biznes mantiq yo'q** | `application` |

**Composition root** — `zakup/bootstrap.py`: barcha implementatsiyalar shu yerda port'larga ulanadi. Router faqat abstraksiyani biladi: `Depends(Stub(ListSuppliers))`, haqiqiy factory `app.dependency_overrides` orqali ulanadi (`platform/di.py`). Tashqi DI kutubxonasi kerak emas; murakkablashsa — `dishka`. Boshqa hech qayerda konkret klass yaratilmaydi.

### 4.1 SOLID — loyihada qanday qo'llanadi

| Prinsip | Aniq misol |
|---|---|
| **S** — Single Responsibility | `DemandCalculator` faqat hisoblaydi; zayavka yaratish — `GenerateAutoRequest` use case; saqlash — repository. Router faqat HTTP'ni o'giradi |
| **O** — Open/Closed | Yetkazib beruvchiga yuborish kanali — `SupplierChannel` interfeysi (`TelegramChannel`, `EmailChannel`, keyin `WhatsAppChannel`) — yangi kanal qo'shish mavjud kodni o'zgartirmaydi. Tasdiqlash matritsasi — `ApprovalRule` ro'yxati, konfiguratsiyadan |
| **L** — Liskov | Har bir `SupplierChannel` bir xil kontraktni bajaradi: `send(po) -> DeliveryReceipt`, xatoda faqat `ChannelError` tashlaydi |
| **I** — Interface Segregation | `IikoCatalogReader`, `IikoStockReader`, `IikoInvoiceWriter` — alohida port'lar. `planning` yozish metodlarini ko'rmaydi |
| **D** — Dependency Inversion | Use case `IikoInvoiceWriter` Protocol'ga bog'liq, `httpx` ga emas. Testda — `FakeIikoInvoiceWriter` |

### 4.2 Clean code qoidalari (majburiy)

- Python 3.12, **`mypy --strict`**, **`ruff`** (lint + format), `import-linter`, pre-commit.
- Funksiya ≤ 40 qator, use case — bitta public metod `__call__` / `execute`.
- Domain'da `None` qaytarib xatoni yashirish yo'q — aniq exception (`ToleranceExceeded`, `RoleConflict`).
- Magic number yo'q: dopusklar, limitlar — `settings` jadvalida yoki konfiguratsiyada.
- Nomlar — inglizcha, domen terminlari lug'ati: [`§11`](#11-domen-lugati).
- Har bir PR: testlar + migratsiya + (kerak bo'lsa) ADR.

---

## 5. Status mashinalari

WORKFLOW 16-bo'limdagi yagona zanjir **uchta mustaqil agregatga** bo'linadi (bitta zayavka → bir nechta PO → har PO'dan bir nechta qabul → har qabuldan majburiyat). Har biri domain'da `transition(to, actor, reason)` orqali o'zgaradi; ruxsat etilmagan o'tish — exception.

**PurchaseRequest (zayavka)**
```
DRAFT → PENDING_APPROVAL → APPROVED | PARTIALLY_APPROVED → SPLIT (PO'larga bo'lindi)
              │   ▲
              │   └── RETURNED (izoh bilan qaytarildi) → DRAFT
              └──► REJECTED                          CANCELLED (SPLIT gacha)
```

**PurchaseOrder (PO)**
```
CREATED → SENT → CONFIRMED | PARTIALLY_CONFIRMED → RECEIVING → RECEIVED | PARTIALLY_RECEIVED → CLOSED
            │        │
            │        └─(narx/miqdor dopuskdan tashqari)→ REAPPROVAL → CONFIRMED | CANCELLED
            └─ (javob yo'q, deadline) → eslatma → eskalatsiya
CANCELLED (RECEIVING gacha)
```

**Receipt (qabul)**
```
IN_PROGRESS → SUBMITTED → [farq dopuskda] → ACCEPTED → EXPORTING → POSTED_TO_IIKO
                   │                                     │
                   └─[dopuskdan tashqari]→ DISPUTED ─────┘ (nizo yopilgach)
                                               EXPORT_FAILED (retry navbatida)
POSTED_TO_IIKO → CORRECTED (yangi versiya + iiko'da storno)
```

**Obligation (to'lov majburiyati)**
```
OPEN → PARTIALLY_PAID → PAID          BLOCKED (nizo ochiq) ⇄ OPEN
```

**Dispute:** `OPEN → IN_REVIEW → RESOLVED(accepted | return | discount | replacement)`.

---

## 6. Asosiy oqimlar

### 6.1 Avto-zayavka (06:00)
```
scheduler ──► GenerateAutoRequests(store)
               ├─ planning.query: qoldiq + yo'ldagi + kunlik prognoz (hafta kuni profili)
               ├─ DemandCalculator (sof funksiya, unit test)
               ├─ PurchaseRequest(DRAFT) + har pozitsiyada "nega shuncha" izohi
               └─ outbox: RequestDrafted ──► bot: tashabbuskorga xabar
```

### 6.2 Qabul → iiko → to'lov
```
Mini App (oflayn bo'lishi mumkin)
  └─ POST /receipts/{id}/lines  (Idempotency-Key)  ─┐
  └─ POST /receipts/{id}/photos (pre-signed S3 URL) │ api: bitta tranzaksiya
  └─ POST /receipts/{id}/submit ────────────────────┘   ├─ Receipt.submit() → ToleranceRule
                                                        ├─ farq > dopusk → Dispute
                                                        ├─ outbox: ReceiptAccepted
                                                        └─ COMMIT
worker (outbox relay, 1 sek)
  ├─ integration_iiko: ExportIncomingInvoice  [navbat iiko, concurrency=1, retry 2^n]
  │     └─ idempotency: biz.receipt_id ↔ iiko.document_id jadvali
  ├─ finance: Obligation(OPEN, due = qabul sanasi + kechiktirish)
  └─ notifications: qabul akti PDF → buxgalter, nazoratchi
```

### 6.3 iiko connector
```
worker(iiko navbati) ──► Redis lock "iiko:session" (TTL + heartbeat)
                         ├─ auth → token
                         ├─ navbatdagi barcha joblarni shu token bilan bajarish (batch)
                         └─ finally: logout
```
- Circuit breaker: ketma-ket 5 xato → 5 daqiqa pauza, adminga xabar.
- Har bir chaqiruv `integration_log` ga yoziladi (so'rov, javob kodi, davomiyligi, xato).
- Sinxronizatsiya **inkremental**, kalit — iiko GUID; `upsert ... ON CONFLICT (iiko_id)`.

---

## 7. Xavfsizlik

| Mavzu | Yechim |
|---|---|
| Kirish | Mini App `initData` → backend **HMAC-SHA256 (bot token)** bilan tekshiradi, `auth_date` ≤ 1 soat → access JWT (15 daq) + refresh (7 kun, rotatsiya, Redis'da revoke) |
| Ro'yxat | Foydalanuvchini **admin faollashtiradi** (telegram_id bog'lanadi). Begona Telegram akkaunt — 403 |
| Ruxsat | RBAC + **ombor bo'yicha scope** (`user_store_roles`). Tekshiruv — application qatlamida `Authorizer` port orqali, router'da emas |
| Rollar ajratilishi | `SegregationOfDutiesPolicy` (domain): tasdiqlovchi ≠ tashabbuskor, qabul qiluvchi ≠ zakupshik, to'lovchi ≠ qabul qiluvchi. Ruxsat etilgan birlashtirish → `role_conflict=true` flag + audit |
| Yetkazib beruvchi havolasi | imzolangan token (PO id + muddat + bir martalik nonce), faqat shu PO'ni ko'radi |
| Fayllar | S3 pre-signed URL (yuklash 5 daq, o'qish 10 daq), MIME/hajm tekshiruvi, klientda siqish |
| Audit | `audit.log` — faqat INSERT; DB roli `app_rw` uchun UPDATE/DELETE `REVOKE` qilingan |
| Boshqa | rate-limit (Caddy + Redis), CORS faqat Mini App domeni, sirlar `.env`/secret manager'da, iiko paroli — shifrlangan |

---

## 8. Tezlik va optimizatsiya

### 8.1 Maqsadli ko'rsatkichlar (SLO)
| Ko'rsatkich | Maqsad |
|---|---|
| API p95 (o'qish) | < 80 ms |
| API p95 (yozish) | < 150 ms |
| Mini App birinchi ochilish (4G) | < 1.5 s (LCP) |
| Qayta ochilish (kesh) | < 400 ms |
| JS bundle (boshlang'ich, gzip) | < 120 KB |
| Qabul ekranida miqdor kiritish | 0 kutish (optimistic UI) |

### 8.2 Backend
- `uvicorn` + `uvloop` + `httptools`; `ORJSONResponse` default.
- `asyncpg` pool + **PgBouncer (transaction mode)**; `statement_cache_size=0` PgBouncer bilan.
- O'qish endpoint'lari — SQLAlchemy **Core / raw SQL → Pydantic DTO** (ORM obyekt yaratilmaydi). Ro'yxatlar — **keyset pagination** (`WHERE (created_at, id) < (...)`), `OFFSET` yo'q.
- N+1 yo'q: bitta so'rovda `JOIN` / `json_agg`; testda so'rovlar sonini tekshiruvchi fixture.
- Ma'lumotnomalar (tovar, ombor, yetkazib beruvchi) — Redis kesh + **ETag / `If-None-Match`** → 304. Sinxronizatsiyadan keyin kesh versiyasi oshiriladi.
- Og'ir ishlar (PDF, OLAP sync, prognoz, hisobotlar) — faqat `worker`da. API hech qachon tashqi tizimni kutmaydi.
- Analitika — **materialized view** (`REFRESH ... CONCURRENTLY`, scheduler orqali).

### 8.3 Frontend
- Route bo'yicha **code-splitting** (`React.lazy`), umumiy vendor chunk.
- TanStack Query: `staleTime` ma'lumotnomalar uchun 1 soat, kesh **IndexedDB'ga persist** → qayta ochilganda darhol ko'rinadi.
- Uzun ro'yxatlar — `@tanstack/react-virtual`.
- Shriftlar — o'zimizda, `woff2`, **subset** (latin + cyrillic), `preload`, `font-display: swap`. 3 ta oila × 2–3 og'irlik.
- Rasm — klientda WebP, maks. 1600 px, ~200 KB.
- Og'ir effektlar (blur, 3D, noise) uchun cheklovlar — [`DESIGN_SYSTEM.md §6`](DESIGN_SYSTEM.md).
- Assets: hash nom + `Cache-Control: immutable, max-age=31536000`; `index.html` — `no-cache`.

---

## 9. Ishonchlilik

- **Outbox relay**: `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 100` → bir nechta worker xavfsiz.
- **Idempotency**: API yozish endpoint'lari `Idempotency-Key` header qabul qiladi (`idempotency_keys` jadvali, 48 soat). iiko eksporti — `receipt_id` bo'yicha unique.
- **Optimistic locking**: agregatlarda `version` ustuni → parallel tahrirda 409.
- **Oflayn**: Mini App'da Dexie (IndexedDB) outbox, ulanish tiklanganda tartib bilan yuboriladi; server ziddiyatni 409 bilan qaytaradi → foydalanuvchiga ko'rsatiladi.
- iiko ishlamasa: ma'lumotnomalar keshdan, kirim navbatda kutadi, qabul to'xtamaydi.
- Zaxira: `pgBackRest` (kunlik to'liq + WAL, 14 kun), S3 bucket versioning. Oyiga bir marta tiklash sinovi.

## 10. Kuzatuv (observability)

- `structlog` JSON log, har so'rovda `request_id` / `user_id` / `store_id`.
- Prometheus metrikalar: so'rov davomiyligi, outbox lag, iiko xatolari, navbat uzunligi.
- Sentry — backend va frontend.
- Alertlar adminga Telegram orqali: outbox lag > 5 daq, iiko circuit open, eksport xatosi.

---

## 11. Domen lug'ati

| Ruscha (WORKFLOW) | Kodda |
|---|---|
| Заявка | `PurchaseRequest` |
| Заказ поставщику | `PurchaseOrder` |
| Приёмка | `Receipt` |
| Расхождение / спор | `Discrepancy` / `Dispute` |
| Приходная накладная iiko | `IncomingInvoice` |
| Обязательство | `Obligation` |
| Заявка на оплату / платёж | `PaymentRequest` / `Payment` |
| Карточка закупа | `PurchaseCard` |
| В пути | `in_transit_qty` |
| Допуск | `Tolerance` |
| Совмещение ролей | `role_conflict` |

---

## 12. Repozitoriy tuzilmasi

```
zakup/
├── backend/
│   ├── pyproject.toml              # uv, ruff, mypy, import-linter
│   ├── alembic/
│   ├── src/zakup/
│   │   ├── bootstrap.py            # composition root (DI)
│   │   ├── settings.py             # pydantic-settings
│   │   ├── entrypoints/            # api.py, worker.py, scheduler.py, bot.py
│   │   ├── shared_kernel/          # Money, Quantity, Unit, events, errors, clock
│   │   ├── platform/               # db (engine, UoW), redis, outbox, idempotency, auth, logging
│   │   └── modules/
│   │       ├── procurement/
│   │       │   ├── domain/         # purchase_request.py, purchase_order.py, policies.py, events.py
│   │       │   ├── application/    # commands/, queries/, ports.py, dto.py
│   │       │   ├── infrastructure/ # repositories.py, tables.py, mappers.py
│   │       │   └── api/            # router.py, schemas.py
│   │       ├── catalog/ planning/ receiving/ finance/
│   │       ├── integration_iiko/ notifications/ audit/ analytics/ identity/
│   └── tests/
│       ├── unit/                   # domain — DB'siz, millisekundlar
│       ├── application/            # fake port'lar bilan
│       ├── integration/            # testcontainers PostgreSQL
│       └── contract/               # iiko javoblari (yozib olingan fixture'lar)
├── frontend/
│   ├── package.json                # vite, react, ts strict, tailwind v4
│   └── src/
│       ├── app/                    # router, providers, telegram init, theme
│       ├── shared/
│       │   ├── ui/                 # dizayn tizimi komponentlari (DESIGN_SYSTEM.md)
│       │   ├── api/                # fetch client, query keys, idempotency
│       │   ├── offline/            # Dexie outbox
│       │   └── lib/                # formatlash (so'm, miqdor), sana
│       ├── entities/               # product, supplier, order (tiplar + kichik UI)
│       ├── features/               # approve-request, receive-line, capture-invoice-photo
│       └── pages/                  # dashboard, requests, orders, receiving, payments, control
├── deploy/
│   ├── docker-compose.yml
│   ├── Caddyfile
│   └── postgres/ (pgbouncer.ini, backup)
└── docs/
    ├── WORKFLOW.md  ARCHITECTURE.md  DATABASE.md  DESIGN_SYSTEM.md
    └── adr/
```

Frontend — **Feature-Sliced Design** (soddalashtirilgan): `pages → features → entities → shared`, yuqoridan pastga import.

## 13. Texnologiyalar

| Qatlam | Tanlov |
|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.1 (async, Core) + asyncpg, Alembic, Stub-DI (`dependency_overrides`), Taskiq + Redis, aiogram 3, httpx, WeasyPrint (PDF), structlog |
| DB | PostgreSQL 16, PgBouncer, Redis 7 |
| Frontend | React 19, Vite, TypeScript strict, Tailwind v4, TanStack Query / Router / Virtual, Dexie, o'zimizning i18n (uz/ru, tipli lug'at, kutubxonasiz), o'zimizning yupqa Telegram adapteri (`shared/lib/telegram.ts`, SDK bundle'siz), zod |
| Sifat | ruff, mypy strict, import-linter, pytest + testcontainers, Vitest, Playwright (asosiy oqimlar), ESLint |
| Infra | Docker Compose, Caddy, MinIO, pgBackRest, Prometheus + Grafana, Sentry, GitHub Actions |

## 14. Bosqichlar (MVP → to'liq)

| Bosqich | Tarkib |
|---|---|
| **0. Poydevor** | repo, CI, docker-compose, platform (DB, UoW, outbox, auth initData), dizayn tizimi asoslari |
| **1. Ma'lumotnomalar** | iiko connector + sync (tovar, ombor, yetkazib beruvchi, qoldiq), xarid kartochkasi |
| **2. Zayavka → PO** | qo'lda zayavka, tasdiqlash matritsasi, PO, Telegram/PDF yuborish, javobni qo'lda kiritish |
| **3. Qabul → iiko** | oflayn qabul, foto, farqlar, nizo, kirim eksporti |
| **4. Moliya** | majburiyatlar, to'lov zayavkasi, saldo, muddati o'tganlar |
| **5. Avto-zakup** | sarf, hafta kuni profili, ehtiyoj hisobi, avto-zayavka |
| **6. Nazorat va analitika** | nazoratchi ekrani, narx dinamikasi, yetkazib beruvchi reytingi, dayjestlar |

## 15. Lokal muhit (hozirgi bosqich)

| Production rejasi | Lokal hozir | Sabab |
|---|---|---|
| Docker Compose | to'g'ridan-to'g'ri `uvicorn` + `vite` | mashinada Docker yo'q |
| PostgreSQL 16 + PgBouncer | lokal PostgreSQL 17, PgBouncer'siz | yetarli |
| Redis (kesh, navbat, lock) | yo'q — hali kerakli modul (worker, iiko) yozilmagan | worker bosqichida qo'shiladi |
| Caddy | Vite dev proxy `/api → 127.0.0.1:8010` | — |

Ishga tushirish: [`README.md`](../README.md).

## 16. Ochiq savollar (WORKFLOW §18 ga qo'shimcha)

1. Hosting: VPS (qaysi provayder / mamlakat) yoki restoran serveri? iikoServer'ga tarmoq orqali kirish bormi (VPN)?
2. ~~Interfeys tili~~ — hal qilindi: **o'zbek (lotin) + rus**, profilda almashtiriladi (§13, `frontend/src/shared/i18n`).
3. Nechta foydalanuvchi va nechta nuqta bo'ladi? Bu PgBouncer va worker sonini aniqlaydi.
4. Narxlar QQS bilan yoki QQSsiz yuritiladi?
