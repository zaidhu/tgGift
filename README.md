# tgGift — Telegram Gift Marketplace Bot

A production-ready Telegram bot that allows users to purchase and send official Telegram Gifts to anyone.

## Features

- **Gift Browsing** — Browse available Telegram Gifts with live catalog from Telegram API
- **Custom Messages** — Attach personal messages to gifts
- **4 Recipient Methods:**
  - Gift Link (recommended) — Generate a shareable link
  - Telegram User ID — Direct input
  - Forward Message — Auto-detect from forwarded message
  - Contact Share — Share recipient's contact
- **Telegram Stars Payment** — Secure payment via Telegram's native currency
- **Refund System** — Automatic refunds on delivery failure + manual approval
- **Gift Links** — Unique tokens with expiration (72 hours)
- **Notifications** — Buyer receives updates at every stage
- **Admin Panel** — Full inline admin commands
- **Analytics** — Revenue, orders, success rate, top gifts/buyers
- **Event-Driven Architecture** — Modular, extensible
- **Background Workers** — Retry, cleanup, scheduled tasks
- **Finance Module** — Auditable transaction ledger

## Tech Stack

| Component | Technology |
|---|---|
| Bot Framework | Aiogram 3.x |
| Language | Python 3.12+ |
| Database | PostgreSQL |
| ORM | SQLAlchemy + Alembic |
| Cache/Queue | Redis + ARQ |
| Deployment | Docker Compose |

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/tgGift.git
cd tgGift
```

### 2. Configure Environment

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
BOT_TOKEN=your_bot_token_from_botfather
BOT_USERNAME=YourBotUsername
ADMIN_ID=your_telegram_user_id
OWNER_ID=your_telegram_user_id
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/tggift
REDIS_URL=redis://redis:6379
ADMIN_CHANNEL_ID=your_admin_channel_id
PAYMENT_CURRENCY=stars
ENVIRONMENT=production
```

### 3. Run with Docker

```bash
docker-compose up -d --build
```

This starts:
- PostgreSQL database
- Redis cache
- Telegram bot
- Background worker

### 4. Run Locally (Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
# Make sure PostgreSQL is running
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/tggift"

# Run migrations
alembic upgrade head

# Start bot
python -m bot.main

# Start worker (separate terminal)
python -m workers.runner
```

## Admin Commands

All admin commands are protected by Telegram User ID. Only users listed in `ADMIN_ID` or `OWNER_ID` can access them.

| Command | Description |
|---|---|
| `/stats` | View platform statistics and analytics |
| `/orders` | View and manage orders |
| `/users` | View user statistics |
| `/payments` | View payment logs and revenue |
| `/refunds` | Approve or reject refund requests |
| `/broadcast` | Send broadcast messages to all users |
| `/system` | Check system health status |
| `/settings` | View and edit bot settings |
| `/search` | Search orders by ID, user, or gift name |
| `/retry` | Retry a failed order (`/retry <order_id>`) |

## User Flow

1. User sends `/start` → Sees welcome message with menu
2. User taps "Send a Gift" → Browses gift catalog
3. User selects a gift → Adds custom message (optional)
4. User chooses recipient method → Selects one of 4 methods
5. User reviews order → Confirms details
6. User pays with Telegram Stars → Payment verified
7. Bot sends the gift → Delivery confirmation
8. Buyer receives notification → Gift delivered

## Database Models

| Table | Description |
|---|---|
| `users` | Telegram user accounts |
| `orders` | Gift orders with full lifecycle |
| `payments` | Payment records (Stars) |
| `refunds` | Refund requests and status |
| `gift_links` | Unique gift share links |
| `queue_jobs` | Background job queue |
| `transactions` | Audit ledger for all money movement |
| `analytics_snapshots` | Daily/monthly aggregated stats |
| `settings` | Bot configuration |
| `referrals` | Referral tracking (future) |
| `wishlists` | User wishlists (future) |
| `loyalty_points` | Loyalty rewards (future) |

## Order Statuses

```
pending → waiting_payment → paid → processing → delivered
                                                        ↓
                                                     failed → refund_pending → refunded
                                                        ↓
                                                     cancelled / expired
```

## Architecture

```
User → Telegram Bot (Aiogram)
         │
         ├── Handlers (user flow)
         ├── Middleware (auth, logging)
         └── Keyboards (inline buttons)

Bot Core:
         ├── Events (dispatcher)
         ├── Listeners (notifications, logs, analytics)
         └── Finance (payments, refunds, ledger)

Services:
         ├── Telegram API (gift sending)
         ├── Payment Service (Stars)
         ├── Gift Link Service
         ├── Refund Service
         ├── Analytics Service
         └── Gift Catalog (live from TG)

Workers:
         ├── Retry Worker (failed deliveries)
         ├── Cleanup Worker (expired links)
         └── Notification Worker
```

## Future Features (Stubs Included)

- **Referral System** — Invite friends, earn rewards
- **Wishlist** — Public gift wishlists
- **AI Messages** — Auto-generate greeting messages
- **Scheduled Gifts** — Send gifts at specific dates/times
- **User Wallet** — Deposit, withdraw, balance tracking
- **Loyalty Program** — Points for repeat customers

## Security

- Admin commands protected by Telegram User ID whitelist
- Payment validation prevents duplicates
- SQL injection prevention via SQLAlchemy
- Rate limiting on handlers
- Environment variable secret management
- Structured logging for audit trail

## License

MIT
