# CLAUDE.md - Mattilda Backend Challenge

## 🎯 Project Overview

**Challenge**: Backend system for school billing management
**Company**: Mattilda (EdTech - Schools, Students, Billing)
**Candidate**: Jonathan Avila - Senior Backend Engineer
**Time Limit**: 48 hours

## 📋 Requirements Summary

### Core Entities
- **Schools**: Educational institutions
- **Students**: Enrolled in schools
- **Invoices**: Billing documents for students
- **Payments** (additional): Track payment transactions

### Key Business Questions to Answer
1. How much does a student owe to a school?
2. How much do all students owe to a school?
3. How many students does a school have?
4. What is the account statement for a school or student?

### Technical Stack (Required)
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy (async)
- **Containerization**: Docker + Docker Compose
- **Documentation**: OpenAPI/Swagger (auto-generated)

## 🏗️ Architecture Decisions

### Pattern: Clean Architecture (Onion)
```
src/
├── domain/           # Business entities & interfaces
├── application/      # Use cases & services
├── infrastructure/   # Database, external services
└── api/              # FastAPI routes & schemas
```

### Why This Pattern?
- Aligns with Jonathan's experience (NTT DATA project)
- Clear separation of concerns
- Easy to test
- Scalable for future requirements

## 📊 Data Model Design

### ERD (Entity Relationship)
```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   SCHOOL    │       │   STUDENT   │       │   INVOICE   │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │───┐   │ id (PK)     │───┐   │ id (PK)     │
│ name        │   │   │ school_id(FK)│   │   │ student_id  │
│ address     │   └──>│ first_name  │   └──>│ amount      │
│ phone       │       │ last_name   │       │ due_date    │
│ email       │       │ email       │       │ status      │
│ created_at  │       │ grade       │       │ description │
│ updated_at  │       │ enrolled_at │       │ created_at  │
│ is_active   │       │ is_active   │       │ updated_at  │
└─────────────┘       └─────────────┘       └─────────────┘
                                                   │
                                                   │
                                            ┌──────┴──────┐
                                            │   PAYMENT   │
                                            ├─────────────┤
                                            │ id (PK)     │
                                            │ invoice_id  │
                                            │ amount      │
                                            │ payment_date│
                                            │ method      │
                                            │ reference   │
                                            │ created_at  │
                                            └─────────────┘
```

### Invoice Status Enum
- `PENDING`: Not paid
- `PARTIAL`: Partially paid
- `PAID`: Fully paid
- `OVERDUE`: Past due date, not paid
- `CANCELLED`: Voided invoice

### Payment Methods Enum
- `CASH`
- `BANK_TRANSFER`
- `CREDIT_CARD`
- `DEBIT_CARD`
- `OTHER`

## 🔌 API Endpoints Design

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
| GET | `/api/v1/invoices/{id}/payments` | Payments for invoice |

## 📄 Account Statement Response Schemas

### School Statement
```json
{
  "school_id": "uuid",
  "school_name": "string",
  "period": {
    "from": "date",
    "to": "date"
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
      "student_name": "string",
      "amount": 500.00,
      "paid_amount": 200.00,
      "pending_amount": 300.00,
      "status": "PARTIAL",
      "due_date": "date"
    }
  ],
  "generated_at": "datetime"
}
```

### Student Statement
```json
{
  "student_id": "uuid",
  "student_name": "string",
  "school_name": "string",
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
  "generated_at": "datetime"
}
```

## 📁 Project Structure

```
mattilda-challenge/
├── CLAUDE.md                    # This file
├── README.md                    # Project documentation
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # App container
├── .env.example                 # Environment template
├── .gitignore
├── pyproject.toml               # Dependencies (Poetry)
├── alembic.ini                  # Migrations config
├── alembic/                     # Migration files
│   └── versions/
├── tests/                       # Test suite
│   ├── conftest.py
│   ├── unit/
│   └── integration/
└── src/
    ├── __init__.py
    ├── main.py                  # FastAPI app entry
    ├── config.py                # Settings & env vars
    ├── domain/                  # Business logic
    │   ├── __init__.py
    │   ├── entities/
    │   │   ├── school.py
    │   │   ├── student.py
    │   │   ├── invoice.py
    │   │   └── payment.py
    │   ├── enums.py
    │   └── exceptions.py
    ├── application/             # Use cases
    │   ├── __init__.py
    │   ├── services/
    │   │   ├── school_service.py
    │   │   ├── student_service.py
    │   │   ├── invoice_service.py
    │   │   └── payment_service.py
    │   └── dto/
    │       └── statements.py
    ├── infrastructure/          # External concerns
    │   ├── __init__.py
    │   ├── database/
    │   │   ├── connection.py
    │   │   ├── models.py        # SQLAlchemy models
    │   │   └── repositories/
    │   │       ├── base.py
    │   │       ├── school_repo.py
    │   │       ├── student_repo.py
    │   │       ├── invoice_repo.py
    │   │       └── payment_repo.py
    │   └── migrations/
    └── api/                     # Presentation layer
        ├── __init__.py
        ├── dependencies.py      # DI container
        ├── middlewares.py
        ├── schemas/             # Pydantic models
        │   ├── school.py
        │   ├── student.py
        │   ├── invoice.py
        │   ├── payment.py
        │   └── statements.py
        └── routes/
            ├── __init__.py
            ├── schools.py
            ├── students.py
            ├── invoices.py
            └── payments.py
```

## 🐳 Docker Configuration

### Services
1. **api**: FastAPI application (port 8000)
2. **db**: PostgreSQL 15 (port 5432)
3. **pgadmin** (optional): Database GUI (port 5050)

### Environment Variables
```env
# Database
POSTGRES_USER=mattilda
POSTGRES_PASSWORD=mattilda_secret
POSTGRES_DB=mattilda_db
DATABASE_URL=postgresql+asyncpg://mattilda:mattilda_secret@db:5432/mattilda_db

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
```

## ✅ Implementation Checklist

### Phase 1: Setup (2-3 hours)
- [ ] Initialize project structure
- [ ] Configure Docker & Docker Compose
- [ ] Setup PostgreSQL connection
- [ ] Configure SQLAlchemy async
- [ ] Setup Alembic migrations
- [ ] Create base models

### Phase 2: Core Models (3-4 hours)
- [ ] School model & repository
- [ ] Student model & repository
- [ ] Invoice model & repository
- [ ] Payment model & repository
- [ ] Create initial migration
- [ ] Test database operations

### Phase 3: CRUD Endpoints (4-5 hours)
- [ ] Schools CRUD
- [ ] Students CRUD
- [ ] Invoices CRUD
- [ ] Payments CRUD
- [ ] Validation & error handling
- [ ] Pagination implementation

### Phase 4: Business Logic (3-4 hours)
- [ ] School statement endpoint
- [ ] Student statement endpoint
- [ ] Invoice status auto-update
- [ ] Payment processing logic
- [ ] Overdue invoice detection

### Phase 5: Polish (2-3 hours)
- [ ] API documentation (OpenAPI)
- [ ] README with setup instructions
- [ ] Seed data script
- [ ] Basic tests
- [ ] Code review & cleanup

## 🧪 Testing Strategy

### Unit Tests
- Service layer logic
- Entity validations
- Business rules

### Integration Tests
- Repository operations
- API endpoints
- Database transactions

### Test Commands
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_invoice_service.py
```

## 🚀 Quick Start Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Run migrations
docker-compose exec api alembic upgrade head

# Access API docs
open http://localhost:8000/docs

# Access pgAdmin
open http://localhost:5050
```

## 💡 Bonus Points (If Time Allows)

1. **Soft Deletes**: Use `is_active` flag instead of hard deletes
2. **Audit Fields**: `created_at`, `updated_at`, `created_by`
3. **Filtering**: Query params for list endpoints
4. **Bulk Operations**: Create multiple invoices at once
5. **Export**: Generate PDF/CSV statements
6. **Webhooks**: Notify on overdue invoices
7. **Rate Limiting**: Protect API endpoints
8. **Health Check**: `/health` endpoint for Docker

## 📝 Notes for Development

### Code Style
- Use type hints everywhere
- Follow PEP 8
- Docstrings for public methods
- Async/await for all I/O operations

### Git Commits
- feat: New feature
- fix: Bug fix
- refactor: Code restructuring
- docs: Documentation
- test: Adding tests
- chore: Maintenance

### Key Libraries
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy[asyncio]>=2.0.25
asyncpg>=0.29.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
alembic>=1.13.0
python-dotenv>=1.0.0
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx>=0.26.0
```

---

## 🎯 Success Criteria

The challenge evaluates:
1. **Data Modeling**: Proper relationships and normalization
2. **API Design**: RESTful, consistent, documented
3. **Code Quality**: Clean, readable, maintainable
4. **Business Logic**: Correct calculations and status management
5. **Docker Setup**: Working containerized environment
6. **Time Management**: Prioritize core features over extras

---

*Last updated: $(date)*
*Challenge deadline: 48 hours from start*
