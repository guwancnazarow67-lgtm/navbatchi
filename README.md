# NAVBATCHI — navbatchilikni boshqarish web-dasturi

Python **Flask** + **SQLite** + HTML/CSS/JavaScript. QR-kod orqali ro'yxatga olish, kalendar, Web Push bildirishnomalar,
administrator va foydalanuvchi panellari, Dark/Light rejim, to'liq o'zbekcha interfeys.

## Imkoniyatlar

**Administrator** (`/admin`, alohida login-parol):
foydalanuvchilarni qo'shish/tahrirlash/o'chirish · kalendarda sana bo'yicha navbatchi biriktirish, ko'chirish, o'chirish ·
bir nechta kunga ommaviy biriktirish · QR-kod yaratish va kim QR orqali kirganini ko'rish · bildirishnoma yuborish ·
statistika (oylar, hafta kunlari, foydalanuvchilar) · parolni almashtirish.

**Foydalanuvchi** (`/app`): QR-kod, shaxsiy havola yoki kod orqali kirish · birinchi marta ism-familiya kiritish ·
o'z ismi, bugungi sana, keyingi navbatchilik sanasi · rangli kalendar (o'tgan va kelgusi kunlar) ·
bildirishnomalar (1 kun oldin, navbatchilik kuni, administrator xabarlari).

## Fayllar

```
navbatchi/
├── app.py               # asosiy Flask dasturi (barcha sahifa va API)
├── config.py            # sozlamalar (.env, avtomatik kalitlar)
├── db.py                # SQLite sxemasi
├── notifications.py     # Web Push va avtomatik eslatmalar
├── utils.py             # o'zbekcha sana/vaqt yordamchilari
├── create_admin.py      # administrator yaratish
├── run.py / wsgi.py     # ishga tushirish (waitress / gunicorn)
├── run_windows.bat      # Windows'da bir bosishda ishga tushirish
├── requirements.txt
├── Dockerfile, docker-compose.yml, Caddyfile.example, .env.example
├── templates/           # HTML (admin/, user/)
├── static/              # css/, js/, img/, sw.js (Service Worker)
└── data/                # baza (navbatchi.db) va maxfiy kalitlar — ZAXIRA QILING
```

---

## 1. Windows kompyuterda ishga tushirish (bosqichma-bosqich)

1. **Python o'rnating.** https://www.python.org/downloads/ → Python 3.10 yoki yangiroq.
   O'rnatishda eng pastdagi **«Add python.exe to PATH»** katagini belgilang.
2. **Loyihani oching.** `navbatchi.zip` ni sichqonchaning o'ng tugmasi → *Extract All* bilan oching (masalan `C:\navbatchi`).
3. **`run_windows.bat` ni ikki marta bosing.** U avtomatik:
   - virtual muhit (`venv`) yaratadi,
   - kutubxonalarni o'rnatadi (internet kerak),
   - `.env` faylini yaratadi,
   - administrator hali yo'q bo'lsa, **login va parol so'raydi** (parol kamida 8 ta belgi),
   - dasturni ishga tushiradi.
4. Brauzerda oching: **http://127.0.0.1:5000** (foydalanuvchi) va **http://127.0.0.1:5000/admin** (administrator).
5. To'xtatish: oynada `Ctrl + C`.

Qo'lda (CMD yoki PowerShell) ishga tushirish:

```bat
cd C:\navbatchi
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python create_admin.py
python run.py
```

> Birinchi ishga tushishda `data\secrets.json` yaratiladi (sessiya kaliti va push kalitlari). **Uni o'chirmang va boshqalarga bermang** —
> o'chirsangiz barcha foydalanuvchilarning bildirishnoma obunalari yaroqsiz bo'lib qoladi.

## 2. Administrator hisobini yaratish

- **Windows / Linux:** `python create_admin.py` (login va parol so'raydi). Xuddi shu buyruq mavjud adminning parolini ham yangilaydi.
- **Docker:** `docker compose run --rm web python create_admin.py`
- **Muqobil:** `.env` ichida `ADMIN_USERNAME` va `ADMIN_PASSWORD` yozing — admin yo'q bo'lsa, birinchi ishga tushishda yaratiladi.
  Keyin parolni `.env` dan o'chirib tashlang va panelning «Hisob» bo'limida almashtiring.
- Parollar faqat **hash** ko'rinishida saqlanadi. Login 5–10 marta xato bo'lsa, 15 daqiqaga bloklanadi. Admin sessiyasi 8 soat.

## 3. Foydalanuvchilarni qo'shish va QR-kod

**QR-kod orqali (tavsiya):**
1. Admin panel → **QR-kod** → nom yozing (ixtiyoriy: amal qilish muddati) → «QR-kod yaratish».
2. QR-kodni **PNG** qilib yuklab oling, ekranda ko'rsating yoki chop qiling.
3. Foydalanuvchi telefon kamerasi bilan skanerlaydi → ro'yxatdan o'tish oynasi ochiladi → ism, familiya (va xohlasa telefon)
   kiritadi → tizim uni avtomatik taniydi (xavfsiz sessiya cookie, 1 yil).
4. «QR-kod» sahifasining pastida **kim qachon kirgani** ko'rinadi; «Foydalanuvchilar» jadvalida ham `QR: nomi` belgisi bor.

QR-kod faqat **ro'yxatdan o'tish** sahifasiga olib boradi — administrator paneliga hech qanday huquq bermaydi.
QR-kodni istalgan vaqtda «O'chirish» (faolsizlantirish) mumkin.

**Muhim — telefon kompyuteringizga kira olishi uchun:**
`127.0.0.1` / `localhost` faqat shu kompyuterning o'zida ishlaydi. Telefondan sinash uchun (bir Wi-Fi tarmog'ida):
1. Kompyuter IP manzilini toping: CMD → `ipconfig` → «IPv4 Address» (masalan `192.168.1.10`).
2. `.env` faylida yozing:
   ```
   HOST=0.0.0.0
   BASE_URL=http://192.168.1.10:5000
   ```
3. Dasturni qayta ishga tushiring. Windows Firewall so'rasa — **«Allow access»** ni bosing.
4. Admin panelda **yangi** QR-kod yarating (eskisi `localhost` manzili bilan yaratilgan bo'lishi mumkin) — endi uni telefon ochadi.

> `BASE_URL` o'zgarsa, QR-kod ichidagi manzil ham o'zgaradi, shuning uchun QR-kodni qayta yuklab oling.

**Qo'lda qo'shish:** «Foydalanuvchilar» → «Foydalanuvchi qo'shish». Tizim **shaxsiy havola** beradi (faqat bir marta ko'rsatiladi) —
uni foydalanuvchiga yuboring; havolani ochsa, avtomatik kiradi. Yoki havolani `/login` sahifasiga qo'yib kirishi mumkin.
Telefon almashtirilsa, foydalanuvchi o'z «Profil» bo'limidan yoki admin «havola» tugmasi orqali yangi havola oladi.

## 4. Navbatchilik belgilash

Admin panel → **Kalendar** → sanani bosing → foydalanuvchini tanlang → «Biriktirish».
Bir sanaga bir nechta navbatchi biriktirish mumkin. «Ko'chirish» — boshqa kunga o'tkazadi, «O'chirish» — olib tashlaydi.
Sahifa pastidagi **«Bir nechta kunga biriktirish»** — masalan, har 7 kunda bir marta.

## 5. Bildirishnomalarni yoqish (Web Push)

**Talablar:** Web Push faqat **HTTPS** (yoki `localhost`) da ishlaydi. Ya'ni:
- kompyuterning o'zida `http://127.0.0.1:5000` — ishlaydi;
- Wi-Fi'dagi `http://192.168...` manzilida telefon bildirishnomani **ruxsat so'ramaydi/bloklaydi** — sinash uchun HTTPS kerak
  (serverga joylang yoki Cloudflare Tunnel / ngrok kabi vositadan foydalaning).

**Foydalanuvchi tomoni:** `/app` ga kirganda «Navbatchilik haqidagi bildirishnomalarni olishga ruxsat berasizmi?» oynasi chiqadi:
«Ha, ruxsat beraman» → brauzer ruxsat so'raydi → yoqiladi. «Yo'q» desa, keyin **Profil → Bildirishnoma sozlamalari** dan yoqishi mumkin.
Profilda **«Sinov xabari»** tugmasi bor — hammasi ishlayotganini tekshirish uchun.

**iPhone (iOS 16.4+):** Safari'da saytni oching → «Ulashish» → **«Ekranga qo'shish»** → ilovani shu ikonkadan oching → keyin ruxsat bering.
Oddiy Safari tabida iOS push bermaydi.

**Qachon yuboriladi:** dastur har daqiqada tekshiradi; `NOTIFY_HOUR` (standart 08:00, Toshkent vaqti) dan keyin
- navbatchilikka **1 kun qolganda** («Ertaga navbatchilik»),
- **navbatchilik kuni** («Bugun navbatchilik kuningiz») — har biri bir martadan.
Administrator xabari «Bildirishnomalar» bo'limidan istalgan vaqt yuboriladi.
Sayt yopiq bo'lsa ham bildirishnoma keladi (Service Worker), lekin **server ishlab turishi shart**.

## 6. Serverga joylash (Ubuntu VPS, kichik server — 512 MB RAM yetadi)

Kerak: domen (A-yozuv server IP'siga qaragan), 80 va 443 portlar ochiq.

### Variant A — Docker (eng oson)

```bash
# 1) Docker o'rnatish
curl -fsSL https://get.docker.com | sh

# 2) Loyihani serverga yuklang (scp/WinSCP) va papkaga kiring
cd navbatchi
cp .env.example .env
nano .env        # BASE_URL=https://navbatchi.example.uz   BEHIND_PROXY=1   (COOKIE_SECURE avtomatik yoqiladi)

# 3) Ishga tushirish
docker compose up -d --build

# 4) Administrator yaratish
docker compose run --rm web python create_admin.py

# 5) HTTPS — Caddy (sertifikatni o'zi oladi)
sudo apt install -y caddy
sudo cp Caddyfile.example /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile    # domenni yozing
sudo systemctl reload caddy
```
Tayyor: `https://navbatchi.example.uz` (admin: `/admin`). Loglar: `docker compose logs -f`. Yangilash: `docker compose up -d --build`.

### Variant B — Docker'siz (systemd)

```bash
sudo apt install -y python3-venv caddy
cd /opt && sudo mkdir navbatchi && sudo chown $USER navbatchi   # loyiha fayllarini shu yerga yuklang
cd /opt/navbatchi
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env      # BASE_URL, BEHIND_PROXY=1
./venv/bin/python create_admin.py
```
`/etc/systemd/system/navbatchi.service`:
```ini
[Unit]
Description=NAVBATCHI
After=network.target

[Service]
WorkingDirectory=/opt/navbatchi
ExecStart=/opt/navbatchi/venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 1 --threads 4 wsgi:app
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```
```bash
sudo chown -R www-data /opt/navbatchi/data
sudo systemctl enable --now navbatchi
# Caddy sozlamasi — Variant A dagi 5-qadam bilan bir xil
```
> `--workers 1` — ataylab: eslatma rejalashtiruvchisi bitta jarayonda ishlashi uchun (ko'p worker ham xato qilmaydi, takror xabar yubormaydi).

### Zaxira nusxa
Muhim narsa — `data/` papkasi (`navbatchi.db` va `secrets.json`). Uni vaqti-vaqti bilan nusxalang:
`cp -r data data-backup-$(date +%F)`.

## 7. Xavfsizlik (nimalar qilingan)

- Administrator va foydalanuvchi **alohida sessiya rollari**; admin sahifa va API'lari faqat admin sessiyasi bilan ishlaydi.
- Foydalanuvchi faqat **o'z** navbatchiligi, xabarlari va ma'lumotlarini ko'radi (server tomonida `user_id` sessiyadan olinadi).
- Parollar `scrypt` hash bilan saqlanadi; shaxsiy havola/kodlar bazada faqat **SHA-256 hash** ko'rinishida.
- QR-token faqat ro'yxatdan o'tish sahifasini ochadi; muddatli bo'lishi va o'chirilishi mumkin; ro'yxatdan o'tish tezligi cheklangan.
- CSRF himoyasi (barcha POST/PUT/DELETE), `HttpOnly` + `SameSite=Lax` cookie (HTTPS'da `Secure`), CSP va boshqa xavfsizlik sarlavhalari,
  login urinishlari cheklangan, SQL so'rovlar parametrli, shablonlar avtomatik escape qilinadi.
- Server: Docker konteyneri root bo'lmagan foydalanuvchi bilan ishlaydi.

## 8. Muammolar va yechimlar

| Muammo | Yechim |
|---|---|
| `python` topilmadi | Python'ni qayta o'rnating va «Add to PATH» ni belgilang |
| QR-kodni telefon ochmayapti | `.env` da `BASE_URL` va `HOST=0.0.0.0` ni sozlab, yangi QR yarating (3-bo'lim) |
| Ruxsat oynasi chiqmayapti / push yo'q | HTTPS kerak (5-bo'lim); iPhone'da «Ekranga qo'shish» |
| Brauzerda bildirishnoma «bloklangan» | Sayt sozlamalarida (qulf belgisi) bildirishnomaga ruxsat bering |
| Eslatma kelmayapti | Server ishlab turibdimi? `NOTIFY_HOUR` o'tganmi? Profilda «Sinov xabari»ni bosing |
| `pip install` xato | Internetni tekshiring; `python -m pip install --upgrade pip` |
| Admin parolini unutdim | `python create_admin.py` — o'sha loginni yozib, yangi parol bering |

Dastur nomi: **NAVBATCHI**.
