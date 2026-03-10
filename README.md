# 🏨 Hotel Hotspot Manager

Hotel booking থেকে automatically Mikrotik Hotspot user create/delete করার full automation system।

## Features
- ✅ Multi-hotel support (যেকোনো সংখ্যক hotel add করা যাবে)
- ✅ MSSQL থেকে confirmed booking auto-read
- ✅ Booking confirm হলেই Mikrotik hotspot user create
- ✅ Checkout time এ automatically user delete
- ✅ Mikrotik API (port 8728) + RADIUS support
- ✅ Live dashboard with real-time stats
- ✅ Manual user create/delete
- ✅ Auto sync scheduler (configurable interval)
- ✅ Full sync logs with history
- ✅ Coolify/Docker Compose compatible

## Quick Start (Coolify)

### 1. Repository তে এই files upload করুন

### 2. `.env` file তৈরি করুন
```bash
cp .env.example .env
# এবং values গুলো আপনার মতো করে change করুন
```

### 3. Coolify তে deploy করুন
- New Resource → Docker Compose
- Repository point করুন
- Environment variables set করুন
- Deploy!

### 4. First login
```
URL: http://your-domain
Email: admin@hotel.com  (বা .env এ যা দিয়েছেন)
Password: admin123
```

---

## MSSQL Table Structure

আপনার hotel database এ যে table আছে সেটার column নাম দিতে হবে। Example:

```sql
-- Example booking table
CREATE TABLE Bookings (
    BookingID INT PRIMARY KEY,
    GuestName VARCHAR(255),
    Phone VARCHAR(50),
    RoomNumber VARCHAR(50),
    CheckInDate DATETIME,
    CheckOutDate DATETIME,
    Status VARCHAR(50)  -- 'Confirmed', 'Cancelled', etc.
)
```

Web UI তে Hotel add করার সময় এই column names গুলো configure করতে হবে।
**Column name জানা না থাকলে**: Hotel settings এ "Fetch Tables" button দিয়ে live থেকে দেখতে পারবেন।

---

## Hotspot Username Format

Username তৈরি হয়: `room{RoomNumber}_{FirstName}`

উদাহরণ:
- Room: `101`, Guest: `John Smith` → `room101_john`
- Room: `A5`, Guest: `রাহেলা বেগম` → `roomA5_রাহেলা`

---

## Sync Flow

```
MSSQL DB
   ↓ (every N minutes)
Confirmed Bookings fetch
   ↓
New bookings? → Create Mikrotik user + RADIUS (optional)
   ↓
Checkout time passed? → Delete Mikrotik user
   ↓
Log everything
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | App DB password | `hotelpass123` |
| `SECRET_KEY` | JWT secret | change this! |
| `ADMIN_EMAIL` | Admin login email | `admin@hotel.com` |
| `ADMIN_PASSWORD` | Admin login password | `admin123` |
| `CORS_ORIGINS` | Allowed origins | `http://localhost` |

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Browser   │────▶│    Nginx     │────▶│  React UI   │
└─────────────┘     │  (port 80)   │     └─────────────┘
                    │              │────▶│  FastAPI    │
                    └──────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┤
                    ▼              ▼            ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │PostgreSQL│  │  MSSQL   │  │ Mikrotik │
              │(App DB)  │  │(Hotel DB)│  │  Router  │
              └──────────┘  └──────────┘  └──────────┘
```

---

## Troubleshooting

**MSSQL connection fails:**
- ODBC Driver 18 installed (Docker এ automatically হয়)
- `TrustServerCertificate=yes` already set
- Firewall এ port 1433 open আছে কিনা check করুন

**Mikrotik connection fails:**
- RouterOS API enabled আছে কিনা: `IP → Services → api` (port 8728)
- Username/password সঠিক কিনা
- Hotspot server name সঠিক কিনা

**Users created কিন্তু internet কাজ করছে না:**
- Hotspot profile সঠিক কিনা check করুন
- Mikrotik এ hotspot properly configured আছে কিনা check করুন
