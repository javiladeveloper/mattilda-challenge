# Mattilda Backend Challenge

Backend system for school billing management built with FastAPI, PostgreSQL, and SQLAlchemy.

**Challenge**: School Billing Management System
**Candidate**: Jonathan Avila - Senior Backend Engineer
**Duration**: 48 hours

## Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.11+ |
| Framework | FastAPI |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Cache | Redis 7 |
| Auth | JWT (python-jose + bcrypt) |
| Validation | Pydantic 2.0 |
| Logging | Structlog |
| Testing | Pytest + pytest-asyncio |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Cloud | AWS ECS Fargate (simulated) |
| AI Agent | OpenAI GPT-4o |

## Architecture

### Clean Architecture (Onion Pattern)

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│    (FastAPI Routes, Pydantic Schemas, Dependencies)          │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                         │
│         (Services, Use Cases, DTOs, Business Logic)          │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                            │
│        (Entities, Enums, Exceptions, Interfaces)             │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                       │
│      (Database, Repositories, Cache, External Services)      │
└─────────────────────────────────────────────────────────────┘
```

## Database Design

### Entity Relationship Diagram

```mermaid
erDiagram
    SCHOOLS ||--o{ STUDENTS : "has many"
    SCHOOLS ||--o{ GRADES : "has many"
    SCHOOLS ||--o{ BILLING_ITEMS : "has many"
    GRADES ||--o{ STUDENTS : "has many"
    STUDENTS ||--o{ INVOICES : "has many"
    INVOICES ||--o{ PAYMENTS : "has many"
    BILLING_ITEMS ||--o{ INVOICES : "referenced by"

    SCHOOLS {
        uuid id PK
        varchar name
        varchar address
        varchar phone
        varchar email
        boolean is_active
        timestamp created_at
    }

    GRADES {
        uuid id PK
        uuid school_id FK
        varchar name
        decimal monthly_fee
        boolean is_active
    }

    BILLING_ITEMS {
        uuid id PK
        uuid school_id FK
        varchar name
        decimal amount
        boolean is_recurring
    }

    STUDENTS {
        uuid id PK
        uuid school_id FK
        uuid grade_id FK
        varchar first_name
        varchar last_name
        varchar email
        boolean is_active
    }

    INVOICES {
        uuid id PK
        uuid student_id FK
        uuid billing_item_id FK
        varchar invoice_type
        decimal amount
        date due_date
        varchar status
    }

    PAYMENTS {
        uuid id PK
        uuid invoice_id FK
        decimal amount
        date payment_date
        varchar method
    }

    USERS {
        uuid id PK
        varchar username
        varchar email
        varchar hashed_password
        boolean is_active
    }
```

### Database Tables

#### schools
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR(255) | School name |
| `address` | VARCHAR(500) | Physical address |
| `phone` | VARCHAR(50) | Contact phone |
| `email` | VARCHAR(255) | Contact email |
| `is_active` | BOOLEAN | Soft delete flag |
| `created_at` | TIMESTAMPTZ | Creation timestamp |

#### grades
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `school_id` | UUID | FK → schools.id |
| `name` | VARCHAR(100) | Grade name (e.g., "5th Grade") |
| `monthly_fee` | NUMERIC(12,2) | Monthly tuition fee |
| `is_active` | BOOLEAN | Soft delete flag |

#### billing_items
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `school_id` | UUID | FK → schools.id |
| `name` | VARCHAR(200) | Item name |
| `description` | TEXT | Detailed description |
| `amount` | NUMERIC(12,2) | Default amount |
| `is_recurring` | BOOLEAN | Monthly recurring charge |
| `academic_year` | VARCHAR(20) | Academic year (e.g., "2024-2025") |

#### students
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `school_id` | UUID | FK → schools.id |
| `grade_id` | UUID | FK → grades.id |
| `first_name` | VARCHAR(100) | First name |
| `last_name` | VARCHAR(100) | Last name |
| `email` | VARCHAR(255) | Contact email |
| `enrolled_at` | DATE | Enrollment date |
| `is_active` | BOOLEAN | Soft delete flag |

#### invoices
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `student_id` | UUID | FK → students.id |
| `billing_item_id` | UUID | FK → billing_items.id (optional) |
| `invoice_type` | VARCHAR(20) | TUITION, ENROLLMENT, FEE, CUSTOM |
| `amount` | NUMERIC(12,2) | Invoice amount |
| `due_date` | DATE | Payment due date |
| `status` | VARCHAR(20) | PENDING, PARTIAL, PAID, OVERDUE, CANCELLED |
| `description` | TEXT | Charge description |

#### payments
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `invoice_id` | UUID | FK → invoices.id |
| `amount` | NUMERIC(12,2) | Payment amount |
| `payment_date` | DATE | Payment date |
| `method` | VARCHAR(20) | CASH, BANK_TRANSFER, CREDIT_CARD, DEBIT_CARD, OTHER |
| `reference` | VARCHAR(255) | External reference |

#### users
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `username` | VARCHAR(100) | Login username (unique) |
| `email` | VARCHAR(255) | Email address (unique) |
| `hashed_password` | VARCHAR(255) | Bcrypt hash |
| `is_active` | BOOLEAN | Account active |

### Invoice Status Flow

```mermaid
stateDiagram-v2
    [*] --> PENDING: Invoice Created
    PENDING --> PARTIAL: Partial Payment
    PENDING --> PAID: Full Payment
    PENDING --> OVERDUE: Past Due Date
    PENDING --> CANCELLED: Voided
    PARTIAL --> PAID: Remaining Paid
    PARTIAL --> OVERDUE: Past Due Date
    OVERDUE --> PARTIAL: Partial Payment
    OVERDUE --> PAID: Full Payment
    PAID --> [*]
    CANCELLED --> [*]
```

### Database Views (Reports)

The database includes pre-built views for reporting, exposed via `/api/v1/reports/*`:

| View | Endpoint | Description |
|------|----------|-------------|
| `v_student_balance` | `/reports/students/balance` | Current financial balance per student |
| `v_school_summary` | `/reports/schools/summary` | Financial summary by school |
| `v_invoice_details` | `/reports/invoices/details` | Complete invoice information |
| `v_payment_history` | `/reports/payments/history` | Payment history with details |
| `v_overdue_invoices` | `/reports/invoices/overdue` | Overdue invoices for collections |
| `v_daily_collections` | `/reports/collections/daily` | Daily payments by school |
| `v_monthly_revenue` | `/reports/revenue/monthly` | Monthly revenue statistics |

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **UUID Primary Keys** | Security (no sequential guessing), distributed systems ready |
| **Soft Deletes** | Audit trail, data recovery, referential integrity |
| **NUMERIC(12,2)** | Exact decimal for money (no float errors), up to $9.99B |
| **TIMESTAMPTZ** | UTC storage with automatic timezone conversion |
| **Computed Properties** | `paid_amount`, `pending_amount` always accurate |
| **Immutable Payments** | Financial audit compliance, no accidental modifications |
| **Composite Indexes** | Optimized for common query patterns |

### Migrations

Migrations are managed with Alembic in `alembic/versions/`:

1. `001_initial_migration.py` - Creates schools, students, invoices, payments
2. `002_add_users_table.py` - Adds users table for authentication
3. `003_add_report_views.py` - Creates database views for reporting
4. `1c309ae71d2f_add_grades_and_billing_items.py` - Adds grades and billing_items
5. `004_update_report_views.py` - Updates views to use grades table

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd mattilda-backend
```

2. **Copy environment file**:
```bash
cp .env.example .env
```

3. **Start all services**:
```bash
docker-compose up -d
```

4. **Run database migrations**:
```bash
docker-compose exec api alembic upgrade head
```

5. **Access the API documentation**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health

### Load Sample Data (Optional)

```bash
docker-compose exec api python scripts/seed.py
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login and get JWT token |
| GET | `/api/v1/auth/me` | Get current user info |

### Schools
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/schools` | List all schools (paginated) |
| GET | `/api/v1/schools/{id}` | Get school by ID |
| POST | `/api/v1/schools` | Create new school |
| PUT | `/api/v1/schools/{id}` | Update school |
| DELETE | `/api/v1/schools/{id}` | Soft delete school |
| GET | `/api/v1/schools/{id}/statement` | **Account statement** |
| GET | `/api/v1/schools/{id}/students` | List school's students |

### Students
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/students` | List all students (paginated) |
| GET | `/api/v1/students/{id}` | Get student by ID |
| POST | `/api/v1/students` | Create new student |
| PUT | `/api/v1/students/{id}` | Update student |
| DELETE | `/api/v1/students/{id}` | Soft delete student |
| GET | `/api/v1/students/{id}/statement` | **Account statement** |
| GET | `/api/v1/students/{id}/invoices` | List student's invoices |

### Invoices
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/invoices` | List all invoices (paginated, filterable) |
| GET | `/api/v1/invoices/{id}` | Get invoice by ID |
| POST | `/api/v1/invoices` | Create new invoice |
| PUT | `/api/v1/invoices/{id}` | Update invoice |
| DELETE | `/api/v1/invoices/{id}` | Cancel invoice |

### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/payments` | List all payments |
| POST | `/api/v1/payments` | Register payment |
| GET | `/api/v1/payments/invoice/{id}` | Payments for invoice |

### Grades
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/grades` | List all grades (filterable by school) |
| GET | `/api/v1/grades/{id}` | Get grade by ID |
| POST | `/api/v1/grades` | Create new grade with monthly fee |
| PUT | `/api/v1/grades/{id}` | Update grade |
| DELETE | `/api/v1/grades/{id}` | Soft delete grade |

### Billing Items
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/billing-items` | List billing items (filterable by school) |
| GET | `/api/v1/billing-items/{id}` | Get billing item by ID |
| POST | `/api/v1/billing-items` | Create new billing item |
| PUT | `/api/v1/billing-items/{id}` | Update billing item |
| DELETE | `/api/v1/billing-items/{id}` | Soft delete billing item |

### Reports (Database Views)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/reports/students/balance` | Student balances with debt |
| GET | `/api/v1/reports/schools/summary` | School financial summary |
| GET | `/api/v1/reports/invoices/details` | Detailed invoice info |
| GET | `/api/v1/reports/invoices/overdue` | Overdue invoices for collections |
| GET | `/api/v1/reports/payments/history` | Complete payment history |
| GET | `/api/v1/reports/collections/daily` | Daily collections by school |
| GET | `/api/v1/reports/revenue/monthly` | Monthly revenue statistics |

### AI Agent (Optional)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ai/risk-analysis/{student_id}` | Analyze payment risk for student |
| POST | `/api/v1/ai/collection-message` | Generate collection reminder message |
| POST | `/api/v1/ai/collection-message/{student_id}` | Generate message with student data |
| POST | `/api/v1/ai/assistant` | Conversational assistant for billing |
| POST | `/api/v1/ai/executive-summary` | AI-generated executive report |
| GET | `/api/v1/ai/status` | Check AI agent availability |

> **Note**: AI endpoints work **with or without** an OpenAI API key. Without a key, the system uses rule-based fallback logic that provides functional (though less sophisticated) responses.

## Key Business Features

### 1. Student Debt Tracking
Calculate how much a student owes to a school.

### 2. School-wide Debt Summary
Total pending payments across all students.

### 3. Student Count
Number of students per school (active and total).

### 4. Account Statements
Detailed financial reports for schools and students.

### School Statement Response Example
```json
{
  "school_id": "uuid",
  "school_name": "Colegio San Jose",
  "period": {
    "from": "2024-01-01",
    "to": "2024-12-31"
  },
  "summary": {
    "total_students": 150,
    "active_students": 145,
    "total_invoiced": 50000.00,
    "total_paid": 35000.00,
    "total_pending": 15000.00,
    "total_overdue": 5000.00
  },
  "invoices": [
    {
      "id": "uuid",
      "student_name": "Juan Perez",
      "amount": 500.00,
      "paid_amount": 200.00,
      "pending_amount": 300.00,
      "status": "PARTIAL",
      "due_date": "2024-03-15"
    }
  ],
  "generated_at": "2024-03-20T10:30:00Z"
}
```

### Student Statement Response Example
```json
{
  "student_id": "uuid",
  "student_name": "Juan Perez",
  "school_name": "Colegio San Jose",
  "summary": {
    "total_invoiced": 2500.00,
    "total_paid": 2000.00,
    "total_pending": 500.00,
    "total_overdue": 0.00
  },
  "invoices": [
    {
      "id": "uuid",
      "description": "Mensualidad Marzo 2024",
      "amount": 500.00,
      "paid_amount": 500.00,
      "pending_amount": 0.00,
      "status": "PAID",
      "due_date": "2024-03-15",
      "payments": [
        {
          "amount": 500.00,
          "date": "2024-03-10",
          "method": "BANK_TRANSFER"
        }
      ]
    }
  ],
  "generated_at": "2024-03-20T10:30:00Z"
}
```

### 5. Payment Validation
- Prevents overpayments (payment > pending amount)
- Blocks payments to cancelled invoices
- Auto-updates invoice status (PENDING -> PARTIAL -> PAID)

## Bonus Features Implemented

| Feature | Description |
|---------|-------------|
| Redis Cache | Configurable caching for read endpoints |
| JWT Authentication | Secure API access with token-based auth |
| Structured Logging | JSON logs with structlog for observability |
| Health Check | `/health` endpoint for container orchestration |
| Pagination | All list endpoints support pagination |
| Soft Deletes | Entities are deactivated, not deleted |
| CI/CD Pipeline | GitHub Actions with tests and coverage |
| AWS Infrastructure | CloudFormation template (simulated) |
| **AI Agent** | Intelligent collection assistant (optional) |

## AI Collection Agent (Optional Feature)

The system includes an AI-powered collection agent that provides intelligent assistance for billing management. **This feature is completely optional** - the core system works perfectly without it.

### Capabilities

| Feature | Description |
|---------|-------------|
| **Risk Analysis** | Analyzes student payment history and predicts likelihood of late payments |
| **Message Generator** | Creates personalized collection messages (Email, SMS, WhatsApp) |
| **Assistant** | Conversational AI for billing inquiries |
| **Executive Summary** | Generates reports with insights and recommendations |

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Agent Request                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │ API Key Set?  │
              └───────┬───────┘
                      │
           ┌──────────┴──────────┐
           │                     │
           ▼                     ▼
    ┌─────────────┐       ┌─────────────┐
    │  OpenAI     │       │  Fallback   │
    │  GPT-4o     │       │  (Rules)    │
    └─────────────┘       └─────────────┘
           │                     │
           └──────────┬──────────┘
                      ▼
              ┌───────────────┐
              │   Response    │
              └───────────────┘
```

### Configuration

To enable AI features with OpenAI:

```bash
# In your .env file
OPENAI_API_KEY=sk-your-api-key-here
```

Without the API key, the agent uses **rule-based fallback logic** that:
- Calculates risk scores based on payment patterns
- Generates template-based collection messages
- Provides helpful responses for common questions

### Example: Risk Analysis Response

```json
{
  "student_id": "uuid",
  "risk_level": "MEDIUM",
  "risk_score": 45,
  "risk_factors": [
    {
      "factor": "Algunos pagos tardíos",
      "impact": "MEDIUM",
      "description": "Entre 20-50% de pagos fueron tardíos"
    }
  ],
  "recommendations": [
    "Enviar recordatorio de pago",
    "Ofrecer opciones de pago flexibles"
  ],
  "predicted_payment_probability": 0.55,
  "suggested_action": "Enviar recordatorio de pago",
  "analysis_summary": "El estudiante presenta un nivel de riesgo MEDIUM..."
}

## Project Structure

```
mattilda-backend/
├── .aws/                     # AWS infrastructure
│   ├── cloudformation-template.yml
│   ├── task-definition.json
│   └── README.md
├── .github/
│   └── workflows/
│       └── ci-cd.yml         # CI/CD pipeline
├── src/
│   ├── domain/               # Business entities & enums
│   │   ├── enums.py
│   │   └── exceptions.py
│   ├── application/          # Use cases & services
│   │   ├── services/
│   │   └── dto/
│   ├── infrastructure/       # Database, cache, logging
│   │   ├── database/
│   │   │   ├── models.py
│   │   │   ├── connection.py
│   │   │   └── repositories/
│   │   ├── cache/
│   │   └── logging/
│   └── api/                  # FastAPI routes & schemas
│       ├── auth/
│       ├── routes/
│       └── schemas/
├── alembic/                  # Database migrations
├── tests/                    # Test suite (53 tests)
│   ├── unit/
│   └── integration/
├── scripts/                  # Utility scripts
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.prod
└── pyproject.toml
```

## Development

### Running Tests

```bash
# Run all tests
docker-compose exec api pytest

# Run with verbose output
docker-compose exec api pytest -v

# Run specific test file
docker-compose exec api pytest tests/unit/test_invoice_service.py
```

### Running with Coverage

```bash
# Generate coverage report
docker-compose exec api pytest --cov=src --cov-report=html --cov-report=term

# View HTML report (generated in htmlcov/index.html)
```

### Database Operations

```bash
# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Apply all migrations
docker-compose exec api alembic upgrade head

# Rollback one migration
docker-compose exec api alembic downgrade -1

# View migration history
docker-compose exec api alembic history
```

### View Logs

```bash
# All services
docker-compose logs -f

# API only
docker-compose logs -f api

# Database only
docker-compose logs -f db
```

## CI/CD Pipeline

The project includes a GitHub Actions workflow (`.github/workflows/ci-cd.yml`) with the following stages:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Lint     │────▶│    Test     │────▶│    Build    │────▶│   Deploy    │
│  (Ruff,     │     │  (Pytest +  │     │  (Docker +  │     │  (AWS ECS   │
│   Black)    │     │  Coverage)  │     │   Trivy)    │     │  Simulated) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

| Job | Description |
|-----|-------------|
| **lint** | Code quality with Ruff, Black, isort |
| **test** | Pytest with PostgreSQL + Redis services, coverage report |
| **build** | Docker image build, security scan with Trivy |
| **deploy-staging** | Deploy to staging (develop branch) - Simulated |
| **deploy-production** | Deploy to production (main branch) - Simulated |

## AWS Deployment (Simulated)

The `.aws/` directory contains infrastructure-as-code for deploying to AWS:

### Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │                 AWS Cloud                   │
                    │                                             │
    Users ─────────▶│  ALB (HTTPS) ─▶ ECS Fargate ─▶ RDS + Redis │
                    │                   (2 tasks)                 │
                    └─────────────────────────────────────────────┘
```

### Files

| File | Description |
|------|-------------|
| `cloudformation-template.yml` | VPC, ECS, RDS, ElastiCache, ALB |
| `task-definition.json` | ECS Fargate task definition |
| `Dockerfile.prod` | Production multi-stage image |

### Estimated Monthly Cost

| Service | Staging | Production |
|---------|---------|------------|
| ECS Fargate | ~$30 | ~$60 |
| RDS PostgreSQL | ~$15 | ~$30 |
| ElastiCache Redis | ~$12 | ~$12 |
| ALB | ~$20 | ~$20 |
| **Total** | **~$77** | **~$122** |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | postgresql+asyncpg://... |
| `REDIS_URL` | Redis connection string | redis://redis:6379/0 |
| `SECRET_KEY` | JWT secret key | (change in production!) |
| `DEBUG` | Enable debug mode | true |
| `CACHE_TTL` | Cache TTL in seconds | 300 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiration | 30 |
| `OPENAI_API_KEY` | OpenAI API key (optional) | (empty - uses fallback) |

## Docker Services

| Service | Port | Description |
|---------|------|-------------|
| api | 8000 | FastAPI application |
| db | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache |
| pgadmin | 5050 | Database admin UI |

### Accessing pgAdmin

1. Open http://localhost:5050
2. Login: `admin@admin.com` / `admin`
3. Add server:
   - Host: `db`
   - Port: `5432`
   - User: `mattilda`
   - Password: `mattilda_secret`

## API Authentication Example

### 1. Register a user

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@test.com",
    "password": "secret123"
  }'
```

### 2. Login to get token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret123"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 3. Use token in requests

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

## Testing

The project includes **53 tests** covering:

- **Unit tests**: Domain logic, services, business rules
- **Integration tests**: API endpoints, database operations

### Test Coverage

```bash
docker-compose exec api pytest --cov=src --cov-report=term-missing
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs api

# Rebuild containers
docker-compose down && docker-compose up -d --build
```

### Database connection issues

```bash
# Verify database is running
docker-compose ps db

# Check database logs
docker-compose logs db
```

### Reset everything

```bash
# Stop and remove all containers, volumes
docker-compose down -v

# Start fresh
docker-compose up -d
docker-compose exec api alembic upgrade head
```

## License

MIT

---

**Built with** FastAPI, PostgreSQL, Redis, Docker
**Challenge completed by**: Jonathan Avila
