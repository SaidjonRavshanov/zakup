# Zakup — xarid va ombor tizimi (iiko integratsiyasi)

FastAPI + PostgreSQL backend, Telegram Mini App frontend (React + Vite).

| Hujjat | Mazmuni |
|---|---|
| [`docs/WORKFLOW.md`](docs/WORKFLOW.md) | biznes-jarayon (nima quramiz) |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | arxitektura, ADR, modullar, qatlamlar |
| [`docs/DATABASE.md`](docs/DATABASE.md) | ma'lumotlar modeli |
| [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) | dizayn tizimi (dark + light) |

## Lokal ishga tushirish

Talablar: Python 3.12+, Node 22+, PostgreSQL 16+ (lokal). Docker va Redis hozircha shart emas.

### 1. Baza
```bash
psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE zakup ENCODING 'UTF8' TEMPLATE template0"
psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE zakup_test ENCODING 'UTF8' TEMPLATE template0"
```

### 2. Backend → http://127.0.0.1:8010 (Swagger: `/api/docs`)
```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"        # Linux/macOS: .venv/bin/...
cp .env.example .env
.venv/Scripts/alembic upgrade head
.venv/Scripts/uvicorn zakup.entrypoints.api:app --host 127.0.0.1 --port 8010 --reload --reload-dir src
```

### 2a. Worker (iiko sinxronizatsiyasi) va soxta iiko
```bash
cd backend
.venv/Scripts/python -m zakup.entrypoints.worker          # iiko.sync_runs navbatini bajaradi
# Lokal: haqiqiy iiko o'rniga soxta server (javob formatlari — iikoRMS 9.2)
ZAKUP_FAKE_IIKO_DIR=tests/fixtures/iiko .venv/Scripts/uvicorn --factory tests.fakes.iiko_server:app_from_env --port 8090
```
- `ZAKUP_IIKO_SERVERS` (JSON) — filiallar serverlari. Lokal `.env` da soxta server (`http://127.0.0.1:8090/resto`, login `zakup` / `secret`).
- **Haqiqiy Tarnov serverlari faqat alohida zakup logini bilan.** `BaxodirII` — hisobot sinxronizatsiyasining logini,
  litsenziya bitta API-sessiyaga ruxsat beradi: bir logindan foydalanilsa, tizimlar bir-birini chiqarib yuboradi.
- Sinxronizatsiya: admin → **iiko** sahifasi → "Ma'lumotnoma" / "Xarid narxlari". API iiko'ga o'zi chiqmaydi (ADR-05).

### 3. Frontend → http://127.0.0.1:5173
```bash
cd frontend
npm install
npm run dev            # /api → 127.0.0.1:8010 ga proxy qilinadi
```

- Tarmoqqa ochish (telefondan test): `npm run dev:lan` → `http://<kompyuter-IP>:5173`. Backend `127.0.0.1` da qoladi — `/api` Vite proxy orqali boradi. Windows Firewall'da bir marta (Administrator PowerShell):
  `New-NetFirewallRule -DisplayName "Zakup dev (Vite 5173)" -Direction Inbound -Protocol TCP -LocalPort 5173 -Action Allow -Profile Private`
- Mavzuni majburlash: `?theme=dark` / `?theme=light` / `?theme=system`.
- Kirish: Telegram ichida — avtomatik (`initData`). Brauzerda (faqat dev, `ZAKUP_DEV_AUTH_BYPASS=true`) — Telegram ID qo'lda kiritiladi.
  Birinchi admin: `backend/.env` da `ZAKUP_BOOTSTRAP_ADMIN_IDS=[<telegram_id>]`. Qolgan xodimlar botni ochadi → admin **Xodimlar** sahifasida faollashtiradi va rol beradi.
- Til: `?lang=uz` / `?lang=ru` (yoki Profil sahifasida). Default: saqlangan tanlov → Telegram tili → brauzer tili → uz. Matnlar: `frontend/src/shared/i18n/locales/` — yangi kalit avval `uz.ts` ga, keyin `ru.ts` ga (aks holda TypeScript xato beradi).
- Backend matnlari (xato xabarlari): `backend/src/zakup/platform/i18n.py` — domen faqat kalit beradi (`raise InvalidSupplierError("supplier.inn_format")`), til `Accept-Language` bo'yicha tanlanadi. Katalogda yo'q kalitni `tests/unit/test_i18n.py` ushlaydi.
- Dizayn tizimi vitrini (faqat dev): http://127.0.0.1:5173/dev/ui
- Brauzerda Telegram'siz ishlaydi: Telegram API chaqiruvlari xavfsiz no-op.

> **`localhost` emas, `127.0.0.1`**: Windows'da `localhost` avval IPv6 ga urinadi va har bir DB ulanishida ~2 s yo'qotiladi.
> **Port 8010**: bu mashinada 8000-port boshqa jarayon tomonidan band.
> **`--reload` qotib qolsa** (Windows'da uvicorn ba'zan eski kodda qoladi — log'da `Reloading...` bor, lekin o'zgarish ishlamaydi): serverni to'xtatib, qayta ishga tushiring.

## Sifat tekshiruvlari

```bash
# backend
.venv/Scripts/ruff check src tests alembic && .venv/Scripts/ruff format --check src tests alembic
.venv/Scripts/mypy                 # strict
.venv/Scripts/lint-imports         # arxitektura chegaralari (Clean Architecture)
.venv/Scripts/python -m pytest     # unit + application + integration (zakup_test DB)

# frontend
npm run lint && npx tsc -b && npm run build
```

## Tuzilma

```
backend/src/zakup/
  shared_kernel/     Money, Quantity, UUIDv7, domain event, UnitOfWork port — framework'siz
  platform/          DB, UoW, outbox, Telegram initData, xatolar, health
  modules/catalog/   namunaviy modul: domain → application → infrastructure / api
  bootstrap.py       composition root (DI) — implementatsiyalar faqat shu yerda ulanadi
  entrypoints/api.py FastAPI ilova
frontend/src/        Feature-Sliced: app → pages → widgets → features → entities → shared
```

Yangi modul qo'shish tartibi — `catalog` modulidan nusxa: domain (sof Python) → application (use case + port) → infrastructure (SQL) → api (router) → `bootstrap.py` ga ulash → Alembic migratsiya → `pyproject.toml` dagi import-linter `containers` ga qo'shish.
