# SafeNest Backend

**SafeNest** is a production-grade FastAPI backend for a GBV (Gender-Based Violence) safety and emergency response platform.

## Architecture Overview

```
SafeNest Backend
├── FastAPI (async)
├── PostgreSQL (SQLAlchemy Async ORM)
├── Redis (caching, sessions, OTP)
├── WebSockets (real-time messaging)
├── Celery (background tasks)
├── Alembic (migrations)
└── Docker (containerization)
```

## Features

### Core Modules

1. **Authentication** - WhatsApp-style OTP, JWT tokens, anonymous sessions
2. **SOS Emergency** - One-click alerts, real-time GPS tracking
3. **Evidence Reporting** - Encrypted incident reports with file uploads
4. **Encrypted Messaging** - E2EE chat with WebSocket delivery
5. **Support Centers** - Geolocation-based center discovery
6. **Training Content** - Digital self-defense resources

### Security Features

- JWT authentication with refresh tokens
- Passwordless secure auth (OTP)
- Encrypted file storage abstraction
- Request validation and sanitization
- Rate limiting (placeholder)
- CORS configuration

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Development Setup

1. **Clone and setup environment:**
```bash
cd safenest-backend
cp .env.example .env
# Edit .env with your configuration
```

2. **Run with Docker Compose:**
```bash
docker compose up -d
```

3. **Or run locally:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### Environment Variables

Key variables to configure:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/safenest

# Redis
REDIS_URL=redis://localhost:6379/0

# Security (generate strong keys!)
JWT_SECRET_KEY=your-32-char-secret-key-here
ENCRYPTION_KEY=your-32-char-encryption-key-here

# SMS/OTP (configure for production)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# S3 (optional, for production file storage)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET_NAME=
```

## API Endpoints

### Authentication
```
POST /api/v1/auth/request-otp       # Request OTP
POST /api/v1/auth/verify-otp         # Verify OTP, get tokens
POST /api/v1/auth/anonymous          # Create anonymous session
POST /api/v1/auth/refresh            # Refresh access token
GET  /api/v1/auth/me                 # Get current user
```

### SOS Emergency
```
POST /api/v1/sos/trigger             # Trigger SOS alert
POST /api/v1/sos/location-update     # Update location
GET  /api/v1/sos/status/{id}         # Get alert status
GET  /api/v1/sos/active              # Get active alert
PATCH /api/v1/sos/{id}/status        # Resolve/cancel alert
GET  /api/v1/sos/history             # Alert history
```

### Reporting
```
POST /api/v1/reports/create          # Submit report
POST /api/v1/reports/upload-evidence # Upload evidence
GET  /api/v1/reports/my-reports      # Get my reports
GET  /api/v1/reports/{id}            # Get report details
```

### Messaging
```
POST /api/v1/messages/conversations      # Create conversation
GET  /api/v1/messages/conversations    # List conversations
POST /api/v1/messages/send             # Send message
GET  /api/v1/messages/{conv_id}/messages # Get messages
WS   /api/v1/messages/ws/chat           # WebSocket chat
```

### Support Centers
```
POST /api/v1/support-centers/nearby  # Find nearby centers
GET  /api/v1/support-centers/{id}    # Get center details
```

### Training
```
GET /api/v1/training/categories     # Get categories
GET /api/v1/training/lessons        # Get lessons
GET /api/v1/training/lesson/{id}    # Get lesson details
```

## Project Structure

```
safenest-backend/
├── app/
│   ├── api/
│   │   ├── deps.py              # Dependencies (auth, DB)
│   │   └── v1/
│   │       ├── endpoints/       # API routes
│   │       └── router.py        # API router
│   ├── core/
│   │   ├── config.py            # Settings
│   │   ├── logging.py           # Structured logging
│   │   └── security.py          # JWT, OTP, hashing
│   ├── db/
│   │   ├── database.py          # SQLAlchemy setup
│   │   └── redis.py             # Redis client
│   ├── models/                  # SQLAlchemy models
│   ├── repositories/            # Data access layer
│   ├── schemas/                 # Pydantic models
│   ├── services/                # Business logic
│   ├── utils/                   # Utilities
│   ├── websocket/               # WebSocket handlers
│   └── workers/                 # Celery tasks
├── alembic/                     # Database migrations
├── uploads/                     # Local file storage
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Database Migrations

### Local

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Docker

```bash
# Run migrations
docker compose exec api alembic upgrade head

# Create migration
docker compose exec api alembic revision --autogenerate -m "description"

# Rollback
docker compose exec api alembic downgrade -1
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html
```

## Deployment

### Production Checklist

- [ ] Generate strong `JWT_SECRET_KEY` and `ENCRYPTION_KEY`
- [ ] Configure production database
- [ ] Set up Redis with persistence
- [ ] Configure S3 for file storage
- [ ] Set up SMS provider (Twilio)
- [ ] Enable monitoring (Sentry)
- [ ] Configure rate limiting
- [ ] Set up SSL/TLS
- [ ] Run migrations
- [ ] Configure backups

### Docker Production

```bash
# Build and run
docker compose -f docker-compose.yml up -d

# Scale workers
docker compose up -d --scale celery-worker=4
```

## Security Considerations

1. **Encryption at Rest**
   - Database encryption (PostgreSQL)
   - File encryption (client-side before upload)
   - Key rotation strategy

2. **Encryption in Transit**
   - TLS 1.3 for all communications
   - WebSocket WSS
   - API rate limiting

3. **Authentication**
   - Short-lived JWT tokens (60 min)
   - Refresh tokens (7 days)
   - OTP expiry (5 min)
   - Anonymous session management

4. **Data Privacy**
   - PII minimization
   - Encrypted evidence storage
   - Access logging
   - Data retention policies

## License

Proprietary - SafeNest Project

## Support

For technical support or questions:
- Backend Team: backend@safenest.org

---

**Emergency**: This is a safety-critical system. All deployments must follow security best practices and undergo thorough testing.
