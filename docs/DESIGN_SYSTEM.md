# Zakup — dizayn tizimi v1 ("Neon Lime", dark + light)

> Manba: berilgan "Neon Lime" shabloni (qora `#050505` + neon laym `#BFFF00`, Plus Jakarta Sans 800, Geist Mono, Inter).
> Shablon **landing sahifa** uchun yozilgan. Bizda esa **Telegram Mini App ichidagi ishchi ilova** (telefon, omborda, bir qo'lda ishlash).
> Shuning uchun quyida avval shablon komponentlari tahlil qilinadi, keyin ilovaga moslashtiriladi.

---

## 1. Shablon komponentlarini tahlil qilish

| Shablondagi komponent | Nima qiladi | Ilovada | Qaror |
|---|---|---|---|
| **Header** (logo + mono nav + CTA) | desktop navigatsiya | Telegram'ning o'z header'i bor | ❌ olib tashlanadi → `TopBar` (sahifa nomi + mono kontekst: ombor / rol) |
| **Hero: 3D Glass karta** (`perspective(1000px) rotateX(15deg)`) | fon "jozibasi" | faqat **Dashboard** yuqorisida dekorativ fon, statik | ⚠️ soddalashtiriladi; ro'yxat ekranlarida yo'q |
| **Hero: 12px oq ramkali ulkan sarlavha** `clamp(2.6rem,10vw,8.75rem)` | brending | telefonda joy yeydi | ⚠️ → `DisplayNumber`: Dashboard'dagi asosiy son (masalan, "bugungi xarid summasi"), 2.5–3.5rem |
| **Countdown timer** (tabular-nums) | landing'da hisoblagich | **foydali!** → cut-off'gacha qolgan vaqt, javob deadline, to'lov muddati | ✅ `Countdown` |
| **Status tag** (lokatsiya/status) | meta | ✅ → `StatusBadge` (PO/qabul statuslari), `MonoLabel` |
| **Bento Grid** (3 ustun, min-h 450px) | xususiyatlar | telefon: 2 ustun, kichik kartalar | ✅ `BentoGrid` — Dashboard KPI'lari; min-height olib tashlanadi |
| **Luminosity Card** (radial glow, `01/ETHOS` indeks, sarlavha, tavsif) | asosiy karta | ✅ asosiy konteyner: zayavka, PO, yetkazib beruvchi kartalari | ✅ `Card` (hover → `:active` press holati, chunki telefon) |
| **Laser Button** (laym, pill, glow, nur o'tadi) | CTA | ✅ asosiy amal: "Tasdiqlash", "Qabulni yakunlash" | ✅ `LaserButton` — ekranda **bittadan ko'p emas** |
| **Avatar stack** (5 ta, laym ramka) | social proof | ✅ → zanjirdagi ishtirokchilar (tashabbuskor → tasdiqlovchi → qabul qiluvchi) | ✅ `ActorStack` |
| **Pill form** (blur fon + mono input + tugma) | email yig'ish | ✅ → qidiruv, tez qo'shish | ✅ `SearchPill` |
| **Mobile bottom nav pill** (`rgba(10,10,10,.8)` + blur 20px) | navigatsiya | ✅ asosiy navigatsiya | ✅ `BottomNav` — rolga qarab 4–5 ta element |
| **Noise overlay** (3%) | tekstura | ⚠️ statik PNG/SVG, 2–3%, faqat `body` foni | ⚠️ |
| **Refraction glow** (laym 15% blur) | fon atmosferasi | ⚠️ 1 ta, statik, Dashboard'da | ⚠️ |
| **Scroll-reveal** (40px Y + fade) | landing animatsiyasi | ishchi ro'yxatda **xalaqit beradi** va sekinlashtiradi | ❌ ro'yxatlarda yo'q; faqat sahifaga birinchi kirishda, 12px, 200ms |

**Xulosa:** shablonning *xarakteri* saqlanadi (qora/oq kontrast, laym urg'u, mono meta-yozuvlar, og'ir sarlavhalar, nurlanuvchi kartalar). Landing'ga xos *teatr* (ulkan tipografiya, 3D, scroll-reveal) esa olib tashlanadi yoki faqat Dashboard'da qoladi.

---

## 2. Tokenlar (CSS custom properties)

Mavzu `<html data-theme="dark|light">` orqali almashadi. Default — Telegram'ning `colorScheme` qiymati.

```css
:root,
:root[data-theme="dark"] {
  --bg:            #050505;
  --surface:       #0E0E0E;
  --surface-2:     #161616;
  --text:          #FFFFFF;
  --text-2:        rgba(255,255,255,0.62);  /* asosiy ikkilamchi matn — AA */
  --text-3:        rgba(255,255,255,0.40);  /* faqat dekorativ / meta, ≥ 14px bold */
  --border:        rgba(255,255,255,0.10);
  --border-soft:   rgba(255,255,255,0.05);
  --accent:        #BFFF00;                 /* fon / chiziq / ikonka */
  --accent-ink:    #000000;                 /* laym ustidagi matn */
  --accent-text:   #BFFF00;                 /* laym rangli matn */
  --accent-glow:   rgba(191,255,0,0.30);
  --accent-wash:   rgba(191,255,0,0.05);
  --glass:         rgba(10,10,10,0.80);
  --danger:        #FF4D4F;
  --warning:       #FFB020;
  --info:          #5AA9FF;
  --noise-opacity: 0.03;
  --shadow-card:   none;
}

:root[data-theme="light"] {
  --bg:            #F4F4EF;                 /* iliq oq — sof oqdan ko'zga yumshoq */
  --surface:       #FFFFFF;
  --surface-2:     #ECECE6;
  --text:          #0A0A0A;
  --text-2:        rgba(10,10,10,0.62);
  --text-3:        rgba(10,10,10,0.42);
  --border:        rgba(10,10,10,0.10);
  --border-soft:   rgba(10,10,10,0.06);
  --accent:        #BFFF00;                 /* tugma foni sifatida saqlanadi */
  --accent-ink:    #000000;
  --accent-text:   #456B00;                 /* oq fonda laym matn o'qilmaydi (1.1:1) → zaytun, 5.6:1 */
  --accent-glow:   rgba(120,170,0,0.25);
  --accent-wash:   rgba(191,255,0,0.14);
  --glass:         rgba(255,255,255,0.82);
  --danger:        #D92D20;
  --warning:       #B54708;
  --info:          #1570EF;
  --noise-opacity: 0.02;
  --shadow-card:   0 1px 2px rgba(10,10,10,0.04), 0 8px 24px rgba(10,10,10,0.06);
}
```

### 2.1 Light versiya qanday qurildi
- Qora ↔ oq almashtirilgan, lekin **laym rang tugma foni bo'lib qoladi** (qora matn bilan 17:1 kontrast). Brend tanilishi saqlanadi.
- Laym **matn** sifatida oq fonda o'qilmaydi → `--accent-text: #456B00`.
- Neon glow oq fonda "kir" ko'rinadi → glow kuchsizroq, kartalarga yumshoq soya (`--shadow-card`) qo'shiladi.
- Noise 2% gacha tushirilgan.

### 2.2 Kontrast (WCAG)
| Juftlik | Dark | Light |
|---|---|---|
| `--text` / `--bg` | 20:1 ✅ | 18:1 ✅ |
| `--text-2` / `--bg` | ~7.5:1 ✅ | ~5.6:1 ✅ |
| `--accent-ink` / `--accent` | 17:1 ✅ | 17:1 ✅ |
| `--accent-text` / `--bg` | 17:1 ✅ | 5.6:1 ✅ |

> Shablondagi `rgba(255,255,255,0.4)` ikkilamchi matn ~3.6:1 — oddiy matn uchun **AA dan o'tmaydi**. Shuning uchun u faqat `--text-3` (meta) uchun qoldirildi, asosiy ikkilamchi matn — 0.62.

### 2.3 Telegram bilan sinxronlash
```ts
const tg = window.Telegram.WebApp;
applyTheme(userPref ?? tg.colorScheme);          // 'system' | 'light' | 'dark'
tg.onEvent('themeChanged', () => userPref === 'system' && applyTheme(tg.colorScheme));
// header va fon Telegram oynasi bilan bir xil bo'lsin — "chok" ko'rinmasin
tg.setHeaderColor(getVar('--bg'));
tg.setBackgroundColor(getVar('--bg'));
tg.setBottomBarColor?.(getVar('--bg'));
```
Foydalanuvchi tanlovi (Tizim / Yorug' / Qorong'i) profilda saqlanadi.

---

## 3. Tipografiya

| Rol | Shrift | O'lcham / og'irlik | Ishlatilishi |
|---|---|---|---|
| Display | **Plus Jakarta Sans** 800, uppercase, `-0.05em` | 32–56px, `clamp()` | Dashboard asosiy son, sahifa sarlavhasi |
| Heading | Plus Jakarta Sans 700–800, `-0.03em` | 18–24px | karta sarlavhalari |
| Meta / label | **Geist Mono** 500, uppercase, `0.2em` | 10–12px | `01/ZAYAVKA`, statuslar, sana, raqam, birlik |
| Body | **Inter** 400 | 14–16px, `line-height 1.5` | matn, ro'yxat |
| Raqamlar | Inter / Geist Mono + `tabular-nums` | — | summalar, miqdor, timer — ustunlar tekis turadi |

> ⚠️ **Kirill alifbosi bo'yicha muammo (tekshirildi):** Google Fonts'dagi Plus Jakarta Sans'da faqat `cyrillic-ext` bor (`U+0460-052F`). **Asosiy rus harflari (`U+0400-045F`) yo'q.** Ruscha sarlavhalar boshqa shriftga tushib qoladi.
> Yechim: shrift stekida Plus Jakarta Sans lotin harflari uchun, **Manrope 800** kirill uchun ishlatiladi (`unicode-range` orqali, ikki shrift bir-biriga yaqin geometrik grotesk). Geist Mono va Inter'da kirill bor ✅.

```css
@font-face { font-family: "Display"; font-weight: 800; src: url(/fonts/jakarta-800-latin.woff2) format("woff2");
             unicode-range: U+0000-00FF, U+0100-024F, U+2000-206F; font-display: swap; }
@font-face { font-family: "Display"; font-weight: 800; src: url(/fonts/manrope-800-cyrillic.woff2) format("woff2");
             unicode-range: U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; font-display: swap; }
```

Barcha shriftlar o'zimizda saqlanadi (Google Fonts'ga so'rov yo'q, subset, ~25–35 KB har biri).

---

## 4. Ritm, shakl, harakat

| Token | Qiymat |
|---|---|
| Bo'shliqlar | 4px asos: 4 / 8 / 12 / 16 / 24 / 32 / 48 |
| Sahifa chetlari | 16px |
| Radius | `--r-sm 12px` (input), `--r-md 20px` (ro'yxat qatori), `--r-lg 32px` (karta, shablondagi 2rem), `--r-pill 9999px` |
| Teginish maydoni | ≥ 44×44px (omborda qo'lqopda ham) |
| Easing | `--ease: cubic-bezier(0.16, 1, 0.3, 1)` (shablondan) |
| Davomiylik | 150ms (press), 250ms (sheet, tab), 600ms (laser nur) |
| Kamaytirilgan harakat | `@media (prefers-reduced-motion: reduce)` → barcha animatsiyalar o'chadi |

---

## 5. Komponentlar ro'yxati (`frontend/src/shared/ui`)

### 5.1 Asosiy (shablondan)
| Komponent | Spetsifikatsiya |
|---|---|
| `LaserButton` | `bg: --accent; color: --accent-ink; radius: pill; box-shadow: 0 0 20px --accent-glow`. Bosilganda (`:active`) va hover'da `::after` gradient (transparent → white 40% → transparent) 45° burchakda 0.6s davomida o'tadi — **faqat `transform`** bilan. Variantlar: `primary`, `ghost` (border + `--text`), `danger`. Holatlar: `loading` (spinner, kenglik o'zgarmaydi), `disabled` |
| `Card` (Luminosity) | `radius 32px; border 1px --border-soft; background: radial-gradient(circle at top left, var(--accent-wash) 0, transparent 60%), var(--surface)`. Hover/active → `border-color: rgba(191,255,0,.3)`. Tuzilma: yuqorida `MonoLabel` (`01/ZAYAVKA`), o'rtada sarlavha, pastda tavsif / summa |
| `BentoGrid` | `grid-template-columns: repeat(2, 1fr)` telefon, `repeat(3,…)` ≥ 768px; katta karta `span 2` |
| `BottomNav` | fixed, pill, `--glass` + `backdrop-filter: blur(20px)`, 1px border; aktiv ikonka — `--accent-text` + kichik laym nuqta; `safe-area-inset-bottom` hisobga olinadi |
| `SearchPill` | pill, `--surface-2` fon, chegarasiz mono input, o'ngda ikonka-tugma |
| `ActorStack` | 3–5 avatar, −8px overlap, 2px `--accent` ramka; tugallanmagan bosqich — kulrang punktir |
| `Countdown` | Display shrift + `tabular-nums`; < 1 soat → `--warning`, o'tgan → `--danger` |
| `MonoLabel` | Geist Mono 10–11px, uppercase, `0.24em`, `--text-3` |

### 5.2 Ilovaga xos (shablon uslubida qo'shilgan)
| Komponent | Qayerda |
|---|---|
| `StatusBadge` | PO / zayavka / qabul statuslari: rang + mono matn (rangning o'zi yetarli emas — a11y) |
| `MoneyText`, `QtyText` | so'm formati (`1 250 000 so'm`), birlik bilan miqdor, `tabular-nums` |
| `DiffIndicator` | "buyurtma qilingan → keldi": `10 → 10.5 kg ▲5%`, dopuskda — `--text-2`, tashqarida — `--warning` / `--danger` |
| `ListRow` | ro'yxat qatori, 64–72px, virtualizatsiyaga mos (qat'iy balandlik) |
| `QtyStepper` | qabulda miqdor kiritish: katta −/+ tugmalari, raqamli klaviatura (`inputmode="decimal"`), vergul/nuqta ikkalasi ham qabul qilinadi |
| `PhotoCapture` | nakladnoy fotosi: kamera → siqish (WebP 1600px) → oldindan ko'rish → fonda yuklash, progress |
| `BottomSheet` | filtrlar, pozitsiya tafsilotlari; Telegram `BackButton` bilan bog'langan |
| `SegmentedControl` | tablar (Hammasi / Tasdiqlashda / Yo'lda) |
| `StatTile` | Dashboard KPI: mono label + katta son + o'zgarish % |
| `Skeleton` | yuklanish (spinner o'rniga), shimmer **faqat `transform`** |
| `EmptyState`, `ErrorState` | bo'sh ro'yxat / xato + "Qayta urinish" |
| `OfflineBanner` | "Oflayn · 3 ta o'zgarish navbatda" — mono, `--warning` |
| `Toast` | Telegram `HapticFeedback` bilan birga |
| `ConfirmDialog` | xavfli amallar (bekor qilish, rad etish) — sabab maydoni majburiy |

### 5.3 Telegram'ning tayyor elementlari
- **MainButton / BottomBar** — ekranning asosiy amali uchun (masalan, "Qabulni yakunlash"). Native, tez ishlaydi, klaviatura ustida turadi. `LaserButton` sahifa ichidagi ikkinchi darajali amallar uchun.
- **BackButton** — ichki navigatsiya, `BottomSheet`ni yopish.
- **HapticFeedback** — muvaffaqiyat / xato / tanlov.
- **CloudStorage** — mavzu va filtrlar tanlovi.

---

## 6. Tezlik qoidalari (effektlar uchun)

Telegram WebView arzon Android telefonlarda sekin ishlaydi. Shablondagi effektlar chiroyli, lekin qimmat.

| Effekt | Qoida |
|---|---|
| `backdrop-filter: blur()` | **faqat** `BottomNav`, `BottomSheet` fonida. Ro'yxat qatorlari va kartalarda — **taqiqlangan** (scroll paytida har kadrda qayta chiziladi) |
| Noise overlay | bitta `position: fixed; pointer-events: none` qatlam, **statik 128×128 PNG** (`background-repeat`), SVG `feTurbulence` emas |
| Glow / radial gradient | statik fon; animatsiya qilinmaydi |
| 3D transform | faqat Dashboard'dagi dekorativ blok, `will-change` yo'q, scroll bilan bog'lanmagan |
| Animatsiyalar | faqat `transform` va `opacity`; `box-shadow`, `width`, `top` animatsiya qilinmaydi |
| Kuchsiz qurilma | `navigator.hardwareConcurrency <= 4` yoki `deviceMemory <= 2` → `data-perf="lite"`: blur → to'liq rangli fon, noise va glow o'chadi |
| Ikonkalar | `lucide-react` — faqat ishlatilganlari import qilinadi (tree-shaking) |

---

## 7. Ekranlar (rol bo'yicha BottomNav)

| Rol | BottomNav |
|---|---|
| Tashabbuskor | Bosh sahifa · Zayavkalar · + Yangi · Profil |
| Zakupshik | Bosh sahifa · Zayavkalar · Buyurtmalar · Yetkazib beruvchilar · Profil |
| Tasdiqlovchi | Tasdiqlash (badge) · Buyurtmalar · Hisobot · Profil |
| Omborchi | Bugun keladi · Qabul · Tarix · Profil |
| Buxgalter | To'lovga · Majburiyatlar · Saldo · Profil |
| Nazoratchi | Nazorat · Nizolar · Audit · Profil |

Bir nechta roli bor foydalanuvchi profilda rolni almashtiradi. BottomNav aktiv rolga qarab o'zgaradi.

---

## 8. Keyingi qadam

1. `shared/ui` komponentlarini Storybook'siz, bitta `/dev/ui` sahifasida (faqat dev build) ikkala mavzuda ko'rsatish.
2. Qabul ekrani prototipi (eng ko'p ishlatiladigan va eng murakkab ekran).
