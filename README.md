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
7. **Operator RBAC** - Enterprise role-based access control for institutional staff (police, legal, NGO, etc.)

### Security Features

- JWT authentication with refresh tokens (dual domain: survivor + operator)
- Passwordless secure auth (OTP) for survivors
- Enterprise RBAC with 100+ granular permissions
- Redis-cached permission resolution
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
# Build or rebuild after dependency changes
docker compose build api celery-worker

docker compose up -d

# Run migrations
docker compose exec api alembic upgrade head

# Seed RBAC roles and permissions
docker compose exec api python scripts/rbac_seed.py

# Create first super admin
docker compose exec api python scripts/create_admin.py
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

# Seed RBAC roles and permissions
python scripts/rbac_seed.py

# Create first super admin
python scripts/create_admin.py

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

#### `POST /api/v1/auth/request-otp`
Request OTP for phone verification.

**Request Body:**
```json
{
  "phone_number": "string (10-20 chars, min 8 digits)",
  "country_code": "string (default: +1, pattern: ^\\+[1-9]\\d{0,3}$)"
}
```

**Response:**
```json
{
  "message": "string",
  "expires_in": "integer (seconds)"
}
```

---

#### `POST /api/v1/auth/verify-otp`
Verify OTP and authenticate user.

**Request Body:**
```json
{
  "phone_number": "string (10-20 chars)",
  "otp_code": "string (4-8 digits)",
  "country_code": "string (optional)"
}
```

**Response:** `TokenResponse`
```json
{
  "access_token": "string (JWT)",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": "integer (seconds)",
  "user": {
    "id": "UUID",
    "phone_number": "string | null",
    "country_code": "string | null",
    "is_anonymous": "boolean",
    "is_verified": "boolean",
    "language_preference": "string (default: en)",
    "status": "string",
    "last_login_at": "datetime | null",
    "created_at": "datetime",
    "trusted_contacts": "TrustedContactResponse[] | null"
  }
}
```

---

#### `POST /api/v1/auth/anonymous`
Create anonymous session for unauthenticated access.

**Request Body:**
```json
{
  "device_fingerprint": "string (optional, max 64 chars)",
  "language_preference": "string (default: en, max 10 chars)"
}
```

**Response:** `AnonymousSessionResponse`
```json
{
  "session_token": "string (JWT)",
  "user": "UserResponse",
  "expires_at": "datetime"
}
```

---

#### `POST /api/v1/auth/refresh`
Refresh access token using refresh token.

**Request Body:** Form data with `refresh_token: string`

**Response:** `TokenResponse`

---

#### `GET /api/v1/auth/me`
Get current authenticated user information.

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `UserResponse`

---

#### `PATCH /api/v1/auth/me`
Update current user profile.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{
  "nickname": "string (optional, max 50 chars)",
  "language_preference": "string (optional, max 10 chars)",
  "emergency_message_template": "string (optional, max 500 chars)"
}
```

**Response:** `UserResponse`

---

#### `GET /api/v1/auth/trusted-contacts`
Get user's trusted contacts.

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `TrustedContactResponse[]`
```json
[
  {
    "id": "UUID",
    "name": "string (1-100 chars)",
    "phone_number": "string (8-20 chars)",
    "relationship": "string | null (max 50 chars)",
    "priority": "integer (1-5, default: 1)",
    "notify_sms": "boolean (default: true)",
    "notify_push": "boolean (default: true)",
    "is_verified": "boolean",
    "created_at": "datetime"
  }
]
```

---

#### `POST /api/v1/auth/trusted-contacts`
Add a trusted contact.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:** `TrustedContactCreate`
```json
{
  "name": "string (1-100 chars)",
  "phone_number": "string (8-20 chars)",
  "relationship": "string (optional, max 50 chars)",
  "priority": "integer (1-5, default: 1)",
  "notify_sms": "boolean (default: true)",
  "notify_push": "boolean (default: true)"
}
```

**Response:** `TrustedContactResponse`

---

#### `DELETE /api/v1/auth/trusted-contacts/{contact_id}`
Remove a trusted contact.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**
```json
{
  "success": true,
  "message": "string"
}
```

---

### SOS Emergency

#### `POST /api/v1/sos/trigger`
Trigger an SOS emergency alert.

**Headers:** `Authorization: Bearer <access_token>` (verified users only)

**Request Body:** `SOSCreate`
```json
{
  "latitude": "float (-90 to 90)",
  "longitude": "float (-180 to 180)",
  "accuracy": "float (optional, >= 0)",
  "altitude": "float (optional)",
  "speed": "float (optional)",
  "heading": "float (optional)",
  "battery_level": "integer (optional, 0-100)",
  "network_type": "string (optional)",
  "alert_type": "string (default: manual, values: manual|timer|gesture|voice)",
  "message": "string (optional, max 500 chars)",
  "triggered_by_device_id": "string (optional, max 64 chars)",
  "client_created_at": "datetime (optional)",
  "offline_id": "string (optional, max 64 chars)"
}
```

**Response:** `SOSResponse`
```json
{
  "id": "UUID",
  "user_id": "UUID",
  "status": "string (active|resolved|cancelled)",
  "alert_type": "string",
  "severity": "string",
  "initial_latitude": "float",
  "initial_longitude": "float",
  "initial_accuracy": "float | null",
  "initial_address": "string | null",
  "message": "string | null",
  "contacts_notified": "integer",
  "created_at": "datetime",
  "updated_at": "datetime | null",
  "client_created_at": "datetime | null",
  "offline_id": "string | null"
}
```

---

#### `POST /api/v1/sos/location-update`
Update location for an active SOS alert.

**Headers:** `Authorization: Bearer <access_token>` (verified users only)

**Request Body:** `LocationPingCreate`
```json
{
  "alert_id": "UUID",
  "latitude": "float (-90 to 90)",
  "longitude": "float (-180 to 180)",
  "accuracy": "float (optional, >= 0)",
  "altitude": "float (optional)",
  "speed": "float (optional)",
  "heading": "float (optional)",
  "battery_level": "integer (optional, 0-100)",
  "network_type": "string (optional)",
  "signal_strength": "integer (optional)",
  "recorded_at": "datetime",
  "offline_sequence": "integer (optional)"
}
```

**Response:** `LocationPingResponse`
```json
{
  "id": "UUID",
  "alert_id": "UUID",
  "latitude": "float",
  "longitude": "float",
  "accuracy": "float | null",
  "recorded_at": "datetime",
  "received_at": "datetime"
}
```

---

#### `POST /api/v1/sos/location-batch`
Batch update locations (for offline sync).

**Headers:** `Authorization: Bearer <access_token>` (verified users only)

**Request Body:**
```json
{
  "alert_id": "UUID",
  "locations": "LocationPingCreate[]"
}
```

**Response:**
```json
{
  "message": "string",
  "locations": "LocationPingResponse[]"
}
```

---

#### `GET /api/v1/sos/status/{alert_id}`
Get status and location history of an SOS alert.

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `SOSWithLocationsResponse`
```json
{
  "id": "UUID",
  "user_id": "UUID",
  "status": "string",
  "alert_type": "string",
  "severity": "string",
  "initial_latitude": "float",
  "initial_longitude": "float",
  "initial_accuracy": "float | null",
  "initial_address": "string | null",
  "message": "string | null",
  "contacts_notified": "integer",
  "created_at": "datetime",
  "updated_at": "datetime | null",
  "client_created_at": "datetime | null",
  "offline_id": "string | null",
  "recent_locations": "LocationPingResponse[]"
}
```

---

#### `GET /api/v1/sos/active`
Get active SOS alert for current user, if any.

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `SOSResponse | null`

---

#### `PATCH /api/v1/sos/{alert_id}/status`
Update SOS alert status (resolve or cancel).

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:** `SOSStatusUpdate`
```json
{
  "status": "string (resolved|cancelled)",
  "resolution_notes": "string (optional, max 1000 chars)"
}
```

**Response:** `SOSResponse`

---

#### `GET /api/v1/sos/history`
Get SOS alert history for current user.

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**
- `limit` (optional, default: 20)

**Response:** `SOSResponse[]`

---

### Reporting

#### `POST /api/v1/reports/create`
Create a new incident report.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:** `IncidentReportCreate`
```json
{
  "report_type": "string (assault|harassment|domestic_violence|stalking|threat|other)",
  "incident_date": "datetime (optional)",
  "incident_latitude": "float (optional, -90 to 90)",
  "incident_longitude": "float (optional, -180 to 180)",
  "incident_address": "string (optional, max 500 chars)",
  "description_encrypted": "string (min 1 char, client-encrypted)",
  "encryption_metadata": "object",
  "is_anonymous": "boolean (default: false)",
  "reporter_age_range": "string (optional: 18-24|25-34|35-44|45-54|55-64|65+|prefer_not_say)",
  "reporter_gender": "string (optional)",
  "follow_up_preference": "string (default: none)",
  "contact_email_encrypted": "string (optional)",
  "contact_phone_encrypted": "string (optional)",
  "client_created_at": "datetime (optional)",
  "offline_id": "string (optional, max 64 chars)"
}
```

**Response:** `IncidentReportResponse`
```json
{
  "id": "UUID",
  "report_number": "string",
  "report_type": "string",
  "status": "string",
  "is_anonymous": "boolean",
  "incident_date": "datetime | null",
  "incident_latitude": "float | null",
  "incident_longitude": "float | null",
  "encryption_metadata": "object | null",
  "created_at": "datetime",
  "updated_at": "datetime | null",
  "client_created_at": "datetime | null",
  "offline_id": "string | null"
}
```

---

#### `GET /api/v1/reports/my-reports`
Get current user's incident reports.

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**
- `skip` (optional, default: 0)
- `limit` (optional, default: 20)

**Response:** `IncidentReportResponse[]`

---

#### `GET /api/v1/reports/{report_id}`
Get specific report with evidence.

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `ReportWithEvidenceResponse`
```json
{
  "id": "UUID",
  "report_number": "string",
  "report_type": "string",
  "status": "string",
  "is_anonymous": "boolean",
  "incident_date": "datetime | null",
  "incident_latitude": "float | null",
  "incident_longitude": "float | null",
  "encryption_metadata": "object | null",
  "created_at": "datetime",
  "updated_at": "datetime | null",
  "client_created_at": "datetime | null",
  "offline_id": "string | null",
  "evidence_files": [
    {
      "id": "UUID",
      "report_id": "UUID",
      "file_type": "string (image|audio|video|document)",
      "mime_type": "string",
      "file_size_bytes": "integer",
      "storage_path": "string",
      "encryption_metadata": "object | null",
      "file_hash_sha256": "string",
      "has_gps_metadata": "boolean",
      "processing_status": "string",
      "virus_scan_status": "string",
      "uploaded_at": "datetime",
      "thumbnail_path": "string | null",
      "offline_id": "string | null"
    }
  ]
}
```

---

#### `POST /api/v1/reports/upload-evidence`
Upload encrypted evidence file for a report.

**Headers:** `Authorization: Bearer <access_token>`
**Content-Type:** `multipart/form-data`

**Form Fields:**
- `report_id`: UUID (required)
- `file_type`: string (required, pattern: image|audio|video|document)
- `encryption_metadata`: string (required, valid JSON)
- `file_hash_sha256`: string (required)
- `has_gps_metadata`: boolean (default: false)
- `gps_latitude`: float (optional)
- `gps_longitude`: float (optional)
- `recorded_at`: string (optional, ISO datetime)
- `offline_id`: string (optional)
- `file`: UploadFile (required)

**Response:** `EvidenceFileResponse`

---

### Messaging

#### `POST /api/v1/messages/conversations`
Create a new conversation.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:** `ConversationCreate`
```json
{
  "conversation_type": "string (default: direct, values: direct|group|support|anonymous)",
  "participant_ids": "UUID[] (max 50, default: [])",
  "title": "string (optional, max 100 chars)",
  "support_center_id": "UUID (optional)"
}
```

**Response:** `ConversationResponse`
```json
{
  "id": "UUID",
  "conversation_type": "string",
  "title": "string | null",
  "is_encrypted": "boolean",
  "encryption_type": "string",
  "last_message_at": "datetime | null",
  "created_at": "datetime",
  "participants": [
    {
      "id": "UUID",
      "user_id": "UUID",
      "role": "string",
      "joined_at": "datetime",
      "last_read_at": "datetime | null"
    }
  ]
}
```

---

#### `GET /api/v1/messages/conversations`
Get user's conversations.

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**
- `skip` (optional, default: 0)
- `limit` (optional, default: 20)

**Response:** `ConversationResponse[]`

---

#### `GET /api/v1/messages/conversations/{conversation_id}`
Get specific conversation.

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `ConversationResponse`

---

#### `POST /api/v1/messages/conversations/{conversation_id}/join`
Join a conversation.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**
```json
{
  "message": "string"
}
```

---

#### `POST /api/v1/messages/conversations/{conversation_id}/leave`
Leave a conversation.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**
```json
{
  "message": "string"
}
```

---

#### `GET /api/v1/messages/conversations/{conversation_id}/messages`
Get messages in a conversation.

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**
- `skip` (optional, default: 0)
- `limit` (optional, default: 50)

**Response:** `MessageResponse[]`
```json
[
  {
    "id": "UUID",
    "conversation_id": "UUID",
    "sender_id": "UUID | null",
    "encrypted_content": "string",
    "encryption_metadata": "string",
    "content_type": "string (text|image|audio|file|location)",
    "status": "string (pending|sent|delivered|read|failed)",
    "sent_at": "datetime | null",
    "delivered_at": "datetime | null",
    "is_edited": "boolean",
    "is_deleted": "boolean",
    "server_created_at": "datetime",
    "client_created_at": "datetime | null"
  }
]
```

---

#### `POST /api/v1/messages/send`
Send a message to a conversation.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:** `MessageCreate`
```json
{
  "conversation_id": "UUID",
  "encrypted_content": "string (min 1 char)",
  "encryption_metadata": "string",
  "content_type": "string (default: text, values: text|image|audio|file|location)",
  "reply_to_message_id": "UUID (optional)",
  "attachment_encrypted": "boolean (default: false)",
  "attachment_storage_path": "string (optional)",
  "attachment_metadata_encrypted": "string (optional)",
  "client_created_at": "datetime",
  "offline_sequence": "integer (optional)"
}
```

**Response:** `MessageResponse`

---

#### `POST /api/v1/messages/conversations/{conversation_id}/read`
Mark all messages in conversation as read.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**
```json
{
  "message": "string"
}
```

---

#### `WS /api/v1/messages/ws/chat?token=<access_token>`
WebSocket endpoint for real-time chat.

**Query Parameters:**
- `token`: string (required, JWT access token)

**Close Codes:**
- `4001`: Token required

---

### Support Centers

#### `POST /api/v1/support-centers/nearby`
Find support centers near a location.

**Request Body:** `SupportCenterNearbyRequest`
```json
{
  "latitude": "float (-90 to 90)",
  "longitude": "float (-180 to 180)",
  "radius_km": "float (default: 10.0, 0.1-100)",
  "center_types": "string[] (optional)",
  "is_24_7": "boolean (optional)",
  "provides_medical": "boolean (optional)",
  "provides_legal": "boolean (optional)",
  "provides_shelter": "boolean (optional)"
}
```

**Response:** `SupportCenterResponse[]`
```json
[
  {
    "id": "UUID",
    "name": "string",
    "center_type": "string",
    "category_tags": "string | null",
    "address": "string",
    "city": "string | null",
    "state": "string | null",
    "country": "string | null",
    "postal_code": "string | null",
    "latitude": "float",
    "longitude": "float",
    "distance_km": "float | null",
    "phone_primary": "string | null",
    "phone_emergency": "string | null",
    "email": "string | null",
    "website": "string | null",
    "is_24_7": "boolean",
    "operating_hours": "string | null",
    "languages_supported": "string | null",
    "provides_medical": "boolean",
    "provides_legal": "boolean",
    "provides_shelter": "boolean",
    "provides_counseling": "boolean",
    "provides_emergency_response": "boolean",
    "provides_anonymous_support": "boolean",
    "wheelchair_accessible": "boolean",
    "gender_specific": "string | null",
    "is_verified": "boolean",
    "rating_average": "float",
    "rating_count": "integer",
    "is_active": "boolean"
  }
]
```

---

#### `GET /api/v1/support-centers/{center_id}`
Get support center details.

**Response:** `SupportCenterResponse`

---

#### `GET /api/v1/support-centers/type/{center_type}`
Get support centers by type.

**Query Parameters:**
- `city` (optional)

**Response:** `SupportCenterResponse[]`

---

#### `GET /api/v1/support-centers/verified/list`
Get verified support centers.

**Query Parameters:**
- `limit` (optional, default: 100)

**Response:** `SupportCenterResponse[]`

---

### Training

#### `GET /api/v1/training/categories`
Get all training categories.

**Query Parameters:**
- `featured` (optional, default: false)
- `limit` (optional, default: 50)

**Response:** `TrainingCategoryResponse[]`
```json
[
  {
    "id": "UUID",
    "name": "string",
    "slug": "string",
    "description": "string | null",
    "icon_name": "string | null",
    "color_code": "string | null",
    "sort_order": "integer",
    "is_active": "boolean",
    "is_featured": "boolean",
    "lesson_count": "integer"
  }
]
```

---

#### `GET /api/v1/training/categories/{slug}`
Get category by slug.

**Response:** `TrainingCategoryResponse`

---

#### `GET /api/v1/training/lessons`
Get training lessons.

**Query Parameters:**
- `skip` (optional, default: 0)
- `limit` (optional, default: 50)
- `category_id` (optional, UUID)

**Response:** `TrainingLessonResponse[]`
```json
[
  {
    "id": "UUID",
    "title": "string",
    "slug": "string",
    "description": "string | null",
    "duration_minutes": "integer | null",
    "difficulty_level": "string",
    "is_active": "boolean",
    "is_premium": "boolean",
    "category_id": "UUID",
    "thumbnail_url": "string | null",
    "view_count": "integer",
    "sort_order": "integer",
    "created_at": "datetime"
  }
]
```

---

#### `GET /api/v1/training/lesson/{lesson_id}`
Get lesson details.

**Response:** `TrainingLessonDetail`
```json
{
  "id": "UUID",
  "title": "string",
  "slug": "string",
  "description": "string | null",
  "duration_minutes": "integer | null",
  "difficulty_level": "string",
  "is_active": "boolean",
  "is_premium": "boolean",
  "category_id": "UUID",
  "thumbnail_url": "string | null",
  "view_count": "integer",
  "sort_order": "integer",
  "created_at": "datetime",
  "content_blocks": [
    {
      "type": "string (text|video|audio|image|quiz|interactive)",
      "content": "string | null",
      "url": "string | null",
      "metadata": "object | null"
    }
  ] | null,
  "video_url": "string | null",
  "audio_url": "string | null",
  "pdf_url": "string | null",
  "tags": "string | null",
  "related_lesson_ids": "string[] | null",
  "completion_count": "integer",
  "rating_average": "float",
  "rating_count": "integer"
}
```

---

#### `GET /api/v1/training/lesson/slug/{slug}`
Get lesson by slug.

**Response:** `TrainingLessonResponse`

---

### Operator RBAC (Enterprise Admin)

Separate authentication and authorization system for institutional operators (police, legal, counselors, NGO staff, etc.). Completely isolated from mobile survivor authentication.

#### Authentication

##### `POST /api/v1/operator/auth/login`
Operator login with email/password.

**Request Body:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response:** `OperatorTokenResponse`
```json
{
  "access_token": "string (JWT)",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "UUID",
    "full_name": "string",
    "email": "string",
    "roles": ["string"]
  }
}
```

##### `POST /api/v1/operator/auth/refresh`
Refresh operator access token.

**Request Body:**
```json
{
  "refresh_token": "string"
}
```

##### `GET /api/v1/operator/auth/me`
Get current operator profile.

**Headers:** `Authorization: Bearer <operator_access_token>`

---

#### Permission Registry

##### `GET /api/v1/operator/permissions`
List all system permissions grouped by module.

**Headers:** `Authorization: Bearer <operator_access_token>`

---

#### Role Management

##### `GET /api/v1/operator/roles`
List all roles.

##### `POST /api/v1/operator/roles`
Create new role.

**Request Body:**
```json
{
  "name": "string",
  "description": "string",
  "is_system": false
}
```

##### `PUT /api/v1/operator/roles/{id}`
Update role.

##### `POST /api/v1/operator/roles/{id}/assign-permissions`
Assign permissions to role.

**Request Body:**
```json
{
  "permission_codes": ["sos.view", "cases.view"],
  "replace_existing": false
}
```

---

#### Operator User Management

##### `GET /api/v1/operator/users`
List operator users.

##### `POST /api/v1/operator/users`
Create operator user.

**Request Body:**
```json
{
  "full_name": "string",
  "email": "string",
  "password": "string",
  "phone": "string (optional)",
  "is_active": true,
  "is_super_admin": false
}
```

##### `POST /api/v1/operator/users/{id}/assign-roles`
Assign roles to user.

##### `POST /api/v1/operator/users/{id}/assign-direct-permissions`
Assign direct permission overrides to user.

**Request Body:**
```json
{
  "permissions": [
    {"permission_code": "cases.view", "granted": true, "reason": "Direct case access"}
  ],
  "replace_existing": false
}
```

---

#### Current Session

##### `GET /api/v1/operator/me/permissions`
Get effective permissions for current operator.

**Response:**
```json
{
  "user_id": "UUID",
  "permissions": ["sos.view", "cases.view", ...],
  "role_permissions": [...],
  "direct_grants": [...],
  "direct_denies": [],
  "cached": false,
  "expires_at": "datetime"
}
```

##### `GET /api/v1/operator/me/sidebar`
Get dynamic sidebar menu based on permissions.

---

### Permission Codes Reference

| Module | Permissions |
|--------|-------------|
| **SOS** | `sos.view`, `sos.respond`, `sos.assign`, `sos.escalate`, `sos.close` |
| **Cases** | `cases.view`, `cases.create`, `cases.update`, `cases.resolve`, `cases.escalate`, `cases.delete`, `cases.assign` |
| **Evidence** | `evidence.view`, `evidence.upload`, `evidence.download`, `evidence.delete`, `evidence.verify` |
| **Users** | `users.view`, `users.create`, `users.update`, `users.delete`, `users.deactivate`, `users.view_analytics` |
| **Roles** | `roles.view`, `roles.create`, `roles.update`, `roles.delete`, `roles.assign_permissions` |
| **Operators** | `operators.view`, `operators.create`, `operators.update`, `operators.delete`, `operators.assign_roles`, `operators.assign_permissions`, `operators.deactivate`, `operators.toggle_super_admin` |
| **Analytics** | `analytics.view`, `analytics.view_dashboard`, `analytics.export`, `analytics.view_sensitive` |
| **Audit** | `audit_logs.view`, `audit_logs.view_sensitive` |
| **Support Centers** | `support_centers.view`, `support_centers.create`, `support_centers.update`, `support_centers.delete`, `support_centers.verify`, `support_centers.manage_own` |
| **Training** | `training.view`, `training.create`, `training.update`, `training.delete`, `training.manage_categories`, `training.publish` |
| **Messages** | `messages.view_all`, `messages.respond`, `messages.moderate` |
| **System** | `system.configure`, `system.view_settings`, `system.manage_integrations`, `system.backup_restore` |

---

## Project Structure

```
safenest-backend/
├── app/
│   ├── api/
│   │   ├── deps.py              # Dependencies (auth, DB)
│   │   └── v1/
│   │       ├── endpoints/       # API routes
│   │       └── router.py        # API router
│   ├── admin_api/               # Operator RBAC admin endpoints
│   │   ├── router.py            # /api/v1/operator routes
│   │   ├── auth.py              # Operator login/refresh/me
│   │   ├── permissions.py       # Permission registry
│   │   ├── roles.py             # Role management
│   │   ├── users.py             # Operator user management
│   │   └── me.py                # Current operator session
│   ├── core/
│   │   ├── config.py            # Settings
│   │   ├── logging.py           # Structured logging
│   │   └── security.py          # JWT, OTP, hashing
│   ├── db/
│   │   ├── database.py          # SQLAlchemy setup
│   │   └── redis.py             # Redis client
│   ├── models/                  # SQLAlchemy models (survivor app)
│   ├── operator_models/         # SQLAlchemy models (operator RBAC)
│   │   └── operator.py          # OperatorUser, Role, links, overrides
│   ├── operator_schemas/        # Pydantic schemas (operator RBAC)
│   ├── operator_repositories/   # Data access layer (operator RBAC)
│   ├── operator_services/     # Business logic (operator RBAC)
│   ├── operator_auth/           # Operator JWT auth dependencies
│   ├── rbac/                    # Role-based access control
│   │   ├── permission_enum.py   # PermissionEnum source of truth
│   │   └── services/            # Permission resolver
│   ├── repositories/            # Data access layer (survivor app)
│   ├── schemas/                 # Pydantic models (survivor app)
│   ├── services/                # Business logic (survivor app)
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

### Docker (Recommended)

When using Docker Compose, run migrations inside the container:

```bash
# Run all migrations (including Operator RBAC)
docker compose exec api alembic upgrade head

# Check migration status
docker compose exec api alembic current

# View migration history
docker compose exec api alembic history

# Create new migration
docker compose exec api alembic revision --autogenerate -m "description"

# Rollback one revision
docker compose exec api alembic downgrade -1

# Rollback to specific revision
docker compose exec api alembic downgrade <revision_id>

# Reset all migrations (development only!)
docker compose exec api alembic downgrade base
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
- [ ] **Initialize operator RBAC system (see Database Migrations section)**
- [ ] Create first super admin user
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
   - Dual-domain JWT: survivor (mobile) + operator (web admin)
   - Short-lived access tokens (60 min)
   - Refresh tokens (7 days)
   - OTP expiry (5 min) for survivors
   - Password-based for operators
   - Anonymous session management
   - Role-based access control (RBAC)
   - Permission caching in Redis

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
