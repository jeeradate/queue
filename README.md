# MediQueue — Smart Queue Management System (PWA)
MediQueue เป็นระบบจัดการคิวในโรงพบาล เพื่อให้ผู้ใช้หรือคนไข้สามารถติดตามคิวทาง โทรศัพท์ และใช้เวลารอคอยโดยไม่ต้องรอที่่จุดบริการ

MediQueue lets patients follow a hospital queue from their phone, gives staff a
one-tap console for calling tickets, and lets administrators shape each display —
all in a single Python codebase.

Built with **NiceGUI** (server-driven UI over WebSocket), **SQLModel** (SQLite or
PostgreSQL) and **uv** for dependency management.

---
## ข้อดีและความจำเป็น 
#### 1. ข้อดีของระบบ (System Advantages)
- **Mobile Freedom & Reduced Crowding:** คนไข้ไม่ต้องนั่งรอหน้าห้องตรวจหนาแน่น มีอิสระในการเดินไปทำธุระ ทานอาหาร หรือพักผ่อนรอบโรงพยาบาล
- **Progressive Web App (PWA) Ready:** ไม่ต้องติดตั้งแอปพลิเคชันจาก Store ให้ยุ่งยาก แค่กดเข้าลิงก์หรือเพิ่มเป็น icon หน้าจอหลัก (Add to Home Screen) ก็ใช้งานได้ทันที
- **Real-Time State Persistence:** ระบบจดจำหมายเลขหน้าจอและสถานะล่าสุดของผู้ป่วยผ่าน Database ช่วยให้เปิดปิดแอปเช็กคิวได้ตลอดเวลาโดยไม่หลุด
- **Low Infrastructure Cost:** พัฒนาด้วยเทคโนโลยีสายพันธุ์ Python เบาๆ (Python + NiceGUI + SQLModel) รันบน VPS Hosting ทั่วไป ประหยัดต้นทุนค่าเซิร์ฟเวอร์
#### 2. ความจำเป็นของระบบ (Necessity)
- **Infection Control:** ลดความเสี่ยงในการแพร่กระจายของโรคทางเดินหายใจจากการแออัดในพื้นที่ปิด
- **Patient Satisfaction (PX):** ลดความเครียด ความวิตกกังวล และความหงุดหงิดของผู้ป่วยและญาติในการรอคอยบริการทางการแพทย์
#### 3. ขนาดโรงพยาบาลที่เหมาะสม (Target Hospital Scale)
- เหมาะสำหรับ **โรงพยาบาลชุมชน (รพช.), โรงพยาบาลเอกชนขนาดกลาง, คลินิกเฉพาะทางขนาดใหญ่ หรือศูนย์สุขภาพชุมชน (รพ.สต. ขนาดใหญ่)** ที่ต้องการระบบจัดคิวอัจฉริยะแบบประหยัดงบ ไม่ซับซ้อนเท่าโรงพยาบาลรัฐขนาดใหญ่ระดับตติยภูมิที่มีระบบ HIS ขนาดยักษ์ครอบอยู่แล้ว
## Features

### Patients (public)
- Mobile-first live queue page at `/`.
- Pick a counter and see the number being served, waiting count, estimated wait
  and the next 5 queue numbers (with a `+N more waiting` note).
- Updates arrive instantly over the existing NiceGUI WebSocket connection — no
  page refresh and no polling from the browser.
- The selected counter is remembered per device (server-side session storage).
- Installable PWA with manifest, icons and an offline fallback page.
- Full-screen wall display per counter at `/display/{counter_id}`.

### Staff (`/staff`)
- Select the counter they are working at.
- Issue the next ticket (sequential numbering per counter).
- Issue a ticket with a custom alphanumeric number (`A12`, `B-03`, `VIP 1`) and
  edit the number of any waiting or serving ticket.
- **Call next**, call a specific waiting ticket, **complete**, **skip** or
  **recall** the current ticket.
- Reorder the waiting queue with up/down controls.
- Reset a queue (deletes all tickets and restarts numbering at `#1`).
- Every change is pushed to every connected screen immediately.

### Admin (`/admin`)
- Live overview: counters, active counters, waiting and serving totals.
- Add counters, edit number/label, activate/deactivate, delete.
- "Set total counters" creates every missing counter from `#1` up to `N`
  without deleting, renumbering or relabeling existing counters.
- Per-counter display layout:
  - show/hide next numbers, waiting count, estimated wait and custom message;
  - custom message text;
  - accent colour (validated `#rrggbb`);
  - average service minutes used for the ETA estimate.

### Security
- Separate staff and admin PINs (environment variables, constant-time compare).
- Role stored in signed server-side session storage; protected pages redirect to
  `/login`.
- PINs are intentionally simple for ward kiosks — put MediQueue behind HTTPS and,
  for internet-facing deployments, an SSO/reverse-proxy layer as well.

---

## Project structure

```
app/
  main.py                 # bootstrap + HTTP routes + ui.run
  bootstrap.py            # engine/service singletons and seed data
  config.py               # environment-driven settings
  database.py             # engine creation and schema creation
  models.py               # SQLModel tables (Counter, Ticket) + DisplayLayout
  services/
    queue_service.py      # all queue logic and transactions
    realtime.py           # in-process pub/sub for WebSocket refreshes
  ui/
    theme.py              # PWA head tags, CSS, shared header
    session.py            # role storage, PIN validation, route guard
    auth.py               # /login, /logout
    patient.py            # /            (patient PWA)
    display.py            # /display/{id}  (wall screen)
    staff.py              # /staff
    admin.py              # /admin
static/
  manifest.webmanifest    # PWA manifest
  sw.js                   # service worker (served at /sw.js for full scope)
  offline.html            # offline fallback
  icons/                  # 192/512/maskable PNG icons
scripts/generate_icons.ps1
tests/test_queue_service.py
```

---

## Quick start การเริ่มต้นใช้งาน

```bash
# 1. Install dependencies (creates .venv and uv.lock) update ระบบ
uv sync

# 2. (Optional) copy and edit configuration เพื่อแก้ไขระหัส
cp .env.example .env

# 3. Run the app เริ่ม Run โปรแกรม
uv run mediqueue
#    or: uv run python -m app.main
```

Open <http://localhost:8080> (or <http://127.0.0.1:8080>). Do **not** open
`http://0.0.0.0:8080` — `0.0.0.0` is a bind address, not a browser destination.

| Route | Who | Purpose |
| --- | --- | --- |
| `/` | Patients | Live queue tracker (PWA start URL) |
| `/display/{counter_id}` | Wall screens | Full-screen display for one counter |
| `/staff` | Staff | Queue operations console |
| `/admin` | Admin | Counter and layout management |
| `/login`, `/logout` | Staff/Admin | PIN sign-in / sign-out |
| `/healthz` | Ops | JSON health probe |
| `/sw.js`, `/static/*` | Browser | PWA assets |

### Default PINs

| Role | Environment variable | Default |
| --- | --- | --- |
| Admin | `MEDIQUEUE_ADMIN_PIN` | `1234` |
| Staff | `MEDIQUEUE_STAFF_PIN` | `5678` |

> Change both before exposing the app. They are only defaults for local trials.

On a fresh database three counters are seeded: **Registration**, **Blood Test**
and **Pharmacy**. Disable with `MEDIQUEUE_SEED_DEFAULTS=0`.

---

## Using MediQueue

A walkthrough of each role. UI labels below match what is on screen.

> One browser session holds one staff/admin role at a time. Sign out (top-right)
> or use a separate browser/incognito window to switch roles. Patients never
> need to sign in.

### Admin — counters and display layouts

1. Open `/admin`, choose **Admin**, enter the admin PIN and press **Sign in**.
2. The overview updates live: counters, active counters, waiting and serving.
3. **Add a counter** — enter a number and label (e.g. `4` / `X-Ray Room`), then
   press **Add counter**.
4. **Set total counters** — enter a total (e.g. `6`) and press **Apply total**.
   Every missing counter from `1..N` is created; existing counters are untouched.
   Use it to prepare a fresh set of counters in one step, for example `5` to
   get `#1`–`#5`. It does **not** delete, renumber or relabel existing counters,
   and it does **not** clear any queue. New counters are named `Counter N`;
   rename them with the pencil button. Use **Add a counter** instead when you
   need one specific number (e.g. `#8`) and label.
5. **Edit a counter** — press the pencil button on its row to change the number,
   label, active state and display layout:
   - show/hide next numbers, waiting count, estimated wait and the message;
   - custom message text;
   - accent colour (`#rrggbb`) and average service minutes (1–120) used for ETA.
6. **Delete a counter** — press the bin button and confirm. Its tickets are
   deleted as well.
7. Changes reach patient pages and wall displays instantly. Newly added or
   deleted counters appear in the patient/staff counter pickers after a reload.

### Staff — call, reorder and reset queues

1. Open `/staff`, enter the staff PIN and press **Sign in**.
2. Select the **Counter** you are working at (remembered per browser).
3. Controls:
   - **Issue ticket** — create the next sequential number for this counter.
   - **Custom ticket** — issue a ticket with a number you type yourself, for
     example `A12`, `B-03` or `VIP 1`.
   - **Pencil (✎)** on the serving card or any waiting row — change that
     ticket's number; letters, digits, spaces, `-` and `_` are allowed (max 20
     characters). Numbers must be unique within the counter (ignoring case), so
     `A1` and `a1` cannot both exist. A purely numeric entry also moves the
     counter's next auto-issued number.
   - **Call next** — complete the current ticket and call the first waiting one.
   - **Call** (in the waiting list) — serve that specific ticket.
   - **Complete / Skip / Recall** — finish, skip or re-announce the current ticket.
   - **↑ / ↓** — move a waiting ticket one step up or down.
   - **Reset queue** — after confirmation, delete every ticket of this counter;
     numbering restarts at `#1`.
4. Every action is pushed to every connected patient and display page.

### Patient — track a queue on a phone

1. Open `/` (no sign-in required).
2. Select the **Counter / screen** printed on the ticket.
3. The card shows the number being served, waiting count, estimated wait,
   completed count, the custom message and the **Next 5 in line** numbers, so
   patients can judge when to return. When more than five tickets are waiting,
   a `+N more waiting` note appears below the list. Updates arrive automatically
   over the WebSocket.
4. The selection is remembered after the app or browser is closed.
5. Install as an app:
   - **Android/Chrome** — menu ⋮ → *Install app* / *Add to Home screen*.
   - **iPhone/Safari** — Share → *Add to Home Screen*.

### Wall display / kiosk

1. Open `/display/{id}` for each counter (e.g. `/display/1`).
2. Use full-screen mode (F11) and disable screen sleep on the TV.
3. Which elements are visible follows the admin layout settings per counter.

### A typical day

1. Admin sets counters/labels and opens the wall displays.
2. Staff sign in at their own counter and issue tickets as patients arrive.
3. Staff press **Call next** (or **Call** for a specific ticket); phones and
   displays update instantly.
4. Press **Complete** when service is done, or **Call next** to finish and advance.
5. Use **Reset queue** at the start of a new session when numbering must restart.

### First-run troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ERR_ADDRESS_INVALID` for `http://0.0.0.0:8080` | `0.0.0.0` is a bind address, not a destination | Open `http://127.0.0.1:8080` or `http://localhost:8080` |
| `ERR_CONNECTION_REFUSED` | Nothing is listening on the port (server stopped or crashed) | In a terminal at the repo root run `uv run mediqueue`, keep it open and wait for `NiceGUI ready to go` |
| `[Errno 10048] address already in use` | Another process holds the port | Stop the old process or start with `$env:MEDIQUEUE_PORT='8081'; uv run mediqueue` |
| `ModuleNotFoundError: No module named 'app'` | Running `python app/main.py` directly instead of the module | Run `uv run mediqueue` (or `uv run python -m app.main`) from the repo root |
| Phone cannot reach the server | Bound to `127.0.0.1` or the firewall blocks the port | Bind `MEDIQUEUE_HOST=0.0.0.0`, open `http://<PC-LAN-IP>:8080` and allow TCP 8080 in the firewall |
| Page loads but numbers never change | More than one server process or no WebSocket connection | Run exactly one worker and check the browser console for socket errors |

---

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `MEDIQUEUE_HOST` | `0.0.0.0` | Bind address |
| `MEDIQUEUE_PORT` | `8080` | HTTP port |
| `MEDIQUEUE_STORAGE_SECRET` | dev placeholder | **Set a long random value** — signs session cookies |
| `MEDIQUEUE_DATABASE_URL` | `sqlite:///data/mediqueue.db` | Any SQLAlchemy URL |
| `MEDIQUEUE_ADMIN_PIN` | `1234` | Admin PIN |
| `MEDIQUEUE_STAFF_PIN` | `5678` | Staff PIN |
| `MEDIQUEUE_SEED_DEFAULTS` | `1` | Seed demo counters on an empty DB |
| `MEDIQUEUE_SESSION_MAX_AGE` | 1 year | Session cookie lifetime, seconds |

`.env` is loaded automatically when present. PostgreSQL example:

```bash
uv add "psycopg[binary]"
export MEDIQUEUE_DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/mediqueue"
```

---

## How real-time updates work

NiceGUI keeps one WebSocket per browser client. Every queue mutation calls
`hub.publish()` (`app/services/realtime.py`); each open page has an async
listener that refreshes only its dynamic panel. The result is instant updates
without browser polling.

The hub is **in-process**. Run exactly one worker process per database (the
default). For a multi-worker deployment, replace the hub with Redis pub/sub or
run a single worker behind your reverse proxy.

---

## PWA notes

- `manifest.webmanifest`, icons and the service worker are served from the app.
- `/sw.js` is exposed at the root (with `Service-Worker-Allowed: /`) so the
  worker can control every page.
- Installability requires **HTTPS** (localhost is exempt) and a valid manifest —
  both are handled when you deploy behind TLS.
- The service worker keeps the app shell and falls back to
  `static/offline.html` when the phone has no connection. Live numbers always
  need the server connection.

Regenerate the icons on Windows (optional):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\generate_icons.ps1
```

---

## Tests

```bash
uv run pytest -q
```

The suite covers counter CRUD, sequential ticket issuing, custom alphanumeric
numbers and renumbering rules, call/complete/skip/recall, reordering, queue reset
with numbering restart, layout persistence and counter summaries.

---

## Production checklist

1. Set `MEDIQUEUE_STORAGE_SECRET` to a long random string and change both PINs.
2. Use HTTPS (reverse proxy such as Caddy/Nginx) — required for PWA install.
3. Persist the database and NiceGUI storage:
   - SQLite: mount `data/` (or point `MEDIQUEUE_DATABASE_URL` elsewhere).
   - Sessions: NiceGUI writes `.nicegui/` next to the app; mount it or set
     `NICEGUI_STORAGE_PATH`.
4. Run one server process (`uv run mediqueue`); see the real-time note above.
5. Back up the database regularly.

### Docker

```bash
docker build -t mediqueue .
docker run -p 8080:8080 -v mediqueue-data:/data \
  -e MEDIQUEUE_STORAGE_SECRET="$(openssl rand -hex 32)" \
  -e MEDIQUEUE_ADMIN_PIN=change-me \
  -e MEDIQUEUE_STAFF_PIN=change-me-too \
  mediqueue
```

### systemd (sketch)

```ini
[Service]
WorkingDirectory=/opt/mediqueue
EnvironmentFile=/opt/mediqueue/.env
ExecStart=/opt/mediqueue/.venv/bin/mediqueue
Restart=always
```

---

## Resetting data

- Remove `data/mediqueue.db` (SQLite) to start over; tables are recreated on the
  next start and demo counters are seeded again.
- Queue reset inside the staff console only clears tickets for the selected
  counter.
