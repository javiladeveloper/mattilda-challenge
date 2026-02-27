# Database Design - Mattilda Backend

This document describes the database schema design, entity relationships, and design decisions for the Mattilda school billing management system.

## Overview

The database uses **PostgreSQL 15** with **SQLAlchemy 2.0 (async)** as the ORM. The schema follows normalized database design principles (3NF) while optimizing for the specific query patterns required by the application.

## Entity Relationship Diagram (ERD)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌─────────────────┐         ┌─────────────────┐         ┌───────────────┐ │
│  │     schools     │         │    students     │         │   invoices    │ │
│  ├─────────────────┤         ├─────────────────┤         ├───────────────┤ │
│  │ PK id (UUID)    │───┐     │ PK id (UUID)    │───┐     │ PK id (UUID)  │ │
│  │    name         │   │     │ FK school_id    │   │     │ FK student_id │ │
│  │    address      │   │     │    first_name   │   │     │    amount     │ │
│  │    phone        │   └────>│    last_name    │   └────>│    due_date   │ │
│  │    email        │   1:N   │    email        │   1:N   │    status     │ │
│  │    is_active    │         │    grade        │         │    description│ │
│  │    created_at   │         │    enrolled_at  │         │    created_at │ │
│  │    updated_at   │         │    is_active    │         │    updated_at │ │
│  └─────────────────┘         │    created_at   │         └───────┬───────┘ │
│                              │    updated_at   │                 │         │
│                              └─────────────────┘                 │         │
│                                                                  │ 1:N     │
│  ┌─────────────────┐                                             │         │
│  │     users       │                               ┌─────────────┴───────┐ │
│  ├─────────────────┤                               │      payments       │ │
│  │ PK id (UUID)    │                               ├─────────────────────┤ │
│  │    username     │                               │ PK id (UUID)        │ │
│  │    email        │                               │ FK invoice_id       │ │
│  │    hashed_pwd   │                               │    amount           │ │
│  │    is_active    │                               │    payment_date     │ │
│  │    created_at   │                               │    method           │ │
│  └─────────────────┘                               │    reference        │ │
│                                                    │    created_at       │ │
│                                                    └─────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Tables

### 1. schools

Represents educational institutions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT uuid_generate_v4() | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL | School name |
| `address` | VARCHAR(500) | NULL | Physical address |
| `phone` | VARCHAR(50) | NULL | Contact phone |
| `email` | VARCHAR(255) | NULL | Contact email |
| `is_active` | BOOLEAN | DEFAULT TRUE | Soft delete flag |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `schools_pkey` (PRIMARY KEY) on `id`
- `ix_schools_is_active` on `is_active`
- `ix_schools_name` on `name`

### 2. students

Represents students enrolled in schools.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT uuid_generate_v4() | Unique identifier |
| `school_id` | UUID | FK → schools.id, NOT NULL | Parent school |
| `first_name` | VARCHAR(100) | NOT NULL | First name |
| `last_name` | VARCHAR(100) | NOT NULL | Last name |
| `email` | VARCHAR(255) | NULL | Contact email |
| `grade` | VARCHAR(50) | NULL | Current grade/level |
| `enrolled_at` | DATE | DEFAULT CURRENT_DATE | Enrollment date |
| `is_active` | BOOLEAN | DEFAULT TRUE | Soft delete flag |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `students_pkey` (PRIMARY KEY) on `id`
- `ix_students_school_id` on `school_id`
- `ix_students_is_active` on `is_active`
- `ix_students_school_active` on `(school_id, is_active)` - Composite for filtered queries

**Foreign Keys:**
- `school_id` → `schools.id` (ON DELETE RESTRICT)

### 3. invoices

Represents billing documents for students.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT uuid_generate_v4() | Unique identifier |
| `student_id` | UUID | FK → students.id, NOT NULL | Billed student |
| `amount` | NUMERIC(12,2) | NOT NULL | Invoice amount |
| `due_date` | DATE | NOT NULL | Payment due date |
| `status` | VARCHAR(20) | DEFAULT 'PENDING' | Invoice status |
| `description` | TEXT | NULL | Charge description |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `invoices_pkey` (PRIMARY KEY) on `id`
- `ix_invoices_student_id` on `student_id`
- `ix_invoices_status` on `status`
- `ix_invoices_due_date` on `due_date`
- `ix_invoices_student_status` on `(student_id, status)` - Composite for filtered queries

**Foreign Keys:**
- `student_id` → `students.id` (ON DELETE RESTRICT)

**Status Values:**
- `PENDING` - No payments made
- `PARTIAL` - Partially paid
- `PAID` - Fully paid
- `OVERDUE` - Past due date, not fully paid
- `CANCELLED` - Invoice voided

### 4. payments

Represents payment transactions against invoices.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT uuid_generate_v4() | Unique identifier |
| `invoice_id` | UUID | FK → invoices.id, NOT NULL | Paid invoice |
| `amount` | NUMERIC(12,2) | NOT NULL | Payment amount |
| `payment_date` | DATE | DEFAULT CURRENT_DATE | Payment date |
| `method` | VARCHAR(20) | DEFAULT 'CASH' | Payment method |
| `reference` | VARCHAR(255) | NULL | External reference |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |

**Indexes:**
- `payments_pkey` (PRIMARY KEY) on `id`
- `ix_payments_invoice_id` on `invoice_id`
- `ix_payments_payment_date` on `payment_date`
- `ix_payments_method` on `method`

**Foreign Keys:**
- `invoice_id` → `invoices.id` (ON DELETE RESTRICT)

**Payment Methods:**
- `CASH`
- `BANK_TRANSFER`
- `CREDIT_CARD`
- `DEBIT_CARD`
- `OTHER`

### 5. users

Represents API users for authentication.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT uuid_generate_v4() | Unique identifier |
| `username` | VARCHAR(100) | UNIQUE, NOT NULL | Login username |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | Email address |
| `hashed_password` | VARCHAR(255) | NOT NULL | Bcrypt hash |
| `is_active` | BOOLEAN | DEFAULT TRUE | Account active |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |

**Indexes:**
- `users_pkey` (PRIMARY KEY) on `id`
- `ix_users_username` (UNIQUE) on `username`
- `ix_users_email` (UNIQUE) on `email`

## Relationships

### School → Students (One-to-Many)
- One school can have many students
- A student belongs to exactly one school
- Deleting a school is restricted if students exist

### Student → Invoices (One-to-Many)
- One student can have many invoices
- An invoice belongs to exactly one student
- Deleting a student is restricted if invoices exist

### Invoice → Payments (One-to-Many)
- One invoice can have many payments (partial payments)
- A payment belongs to exactly one invoice
- Deleting an invoice is restricted if payments exist

## Design Decisions

### 1. UUID Primary Keys

**Why:** UUIDs provide several advantages over auto-increment integers:
- No sequential guessing (security)
- Client-side ID generation possible
- Better for distributed systems
- No conflicts when merging databases

**Trade-off:** Slightly larger storage and index size (16 bytes vs 4-8 bytes)

### 2. Soft Deletes (is_active flag)

**Why:** Instead of hard deleting records:
- Maintains audit trail
- Prevents orphaned references
- Allows data recovery
- Historical reporting remains accurate

**Implementation:** All queries filter by `is_active = TRUE` by default

### 3. Numeric(12,2) for Money

**Why:** Using NUMERIC/DECIMAL instead of FLOAT:
- Exact decimal representation
- No floating-point rounding errors
- Standard for financial applications
- Range: up to $9,999,999,999.99

### 4. Timestamp with Time Zone

**Why:** Using TIMESTAMPTZ for all timestamps:
- Stores in UTC internally
- Converts automatically based on client timezone
- Prevents timezone confusion
- Best practice for distributed systems

### 5. Computed Properties in ORM

**Why:** `paid_amount` and `pending_amount` as properties:
- Always accurate (calculated from payments)
- No data duplication
- No sync issues
- Can be optimized to SQL if needed

### 6. Immutable Payments

**Why:** Payments have no `updated_at` and cannot be modified:
- Financial audit requirements
- Prevents accidental modifications
- Corrections require new adjustment entries
- Simpler data integrity

### 7. Composite Indexes

**Why:** Created composite indexes for common query patterns:
- `(school_id, is_active)` - Get active students per school
- `(student_id, status)` - Get invoices by status per student

## Data Flow

### Invoice Payment Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Invoice Created                                                     │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────┐                                                         │
│  │ PENDING │ ◄── Initial state (no payments)                        │
│  └────┬────┘                                                         │
│       │                                                              │
│       │ Payment received (amount < pending)                          │
│       ▼                                                              │
│  ┌─────────┐                                                         │
│  │ PARTIAL │ ◄── Partial payment made                               │
│  └────┬────┘                                                         │
│       │                                                              │
│       │ Payment received (paid >= amount)                            │
│       ▼                                                              │
│  ┌─────────┐                                                         │
│  │  PAID   │ ◄── Fully paid                                         │
│  └─────────┘                                                         │
│                                                                      │
│  Alternative paths:                                                  │
│                                                                      │
│  PENDING/PARTIAL ──(past due_date)──▶ OVERDUE                       │
│  PENDING/PARTIAL ──(cancelled)──────▶ CANCELLED                     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Statement Calculation Flow

```
School Statement                          Student Statement
      │                                         │
      ▼                                         ▼
┌─────────────────┐                    ┌─────────────────┐
│ Get all students│                    │ Get all invoices│
│ for school      │                    │ for student     │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────┐                    ┌─────────────────┐
│ For each student│                    │ For each invoice│
│ get invoices    │                    │ get payments    │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────┐                    ┌─────────────────┐
│ Calculate:      │                    │ Calculate:      │
│ - total_invoiced│                    │ - paid_amount   │
│ - total_paid    │                    │ - pending_amount│
│ - total_pending │                    └────────┬────────┘
│ - total_overdue │                             │
└────────┬────────┘                             ▼
         │                             ┌─────────────────┐
         ▼                             │ Aggregate:      │
┌─────────────────┐                    │ - total_invoiced│
│ Return statement│                    │ - total_paid    │
│ with summary    │                    │ - total_pending │
└─────────────────┘                    │ - total_overdue │
                                       └─────────────────┘
```

## Migrations

Migrations are managed with **Alembic** and stored in `alembic/versions/`.

### Current Migrations

1. `001_initial_migration.py` - Creates schools, students, invoices, payments tables
2. `002_add_users_table.py` - Adds users table for authentication

### Migration Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current revision
alembic current
```

## Query Examples

### Get School with Student Count and Financial Summary

```sql
SELECT
    s.id,
    s.name,
    COUNT(DISTINCT st.id) FILTER (WHERE st.is_active) as active_students,
    COUNT(DISTINCT st.id) as total_students,
    COALESCE(SUM(i.amount), 0) as total_invoiced,
    COALESCE(SUM(p.amount), 0) as total_paid
FROM schools s
LEFT JOIN students st ON st.school_id = s.id
LEFT JOIN invoices i ON i.student_id = st.id AND i.status != 'CANCELLED'
LEFT JOIN payments p ON p.invoice_id = i.id
WHERE s.id = :school_id
GROUP BY s.id, s.name;
```

### Get Overdue Invoices

```sql
SELECT
    i.*,
    st.first_name || ' ' || st.last_name as student_name,
    i.amount - COALESCE(SUM(p.amount), 0) as pending_amount
FROM invoices i
JOIN students st ON st.id = i.student_id
LEFT JOIN payments p ON p.invoice_id = i.id
WHERE i.due_date < CURRENT_DATE
  AND i.status NOT IN ('PAID', 'CANCELLED')
GROUP BY i.id, st.first_name, st.last_name
HAVING i.amount > COALESCE(SUM(p.amount), 0);
```

### Get Student Debt

```sql
SELECT
    SUM(i.amount) - COALESCE(SUM(p.amount), 0) as total_debt
FROM invoices i
LEFT JOIN payments p ON p.invoice_id = i.id
WHERE i.student_id = :student_id
  AND i.status NOT IN ('PAID', 'CANCELLED');
```

## Performance Considerations

### Indexes Strategy

1. **Foreign Keys**: All FK columns are indexed for JOIN performance
2. **Status Filters**: Index on status for common WHERE clauses
3. **Date Ranges**: Index on due_date and payment_date for date queries
4. **Composite**: Combined indexes for frequent multi-column filters

### Eager Loading

The ORM uses `selectinload` strategy for relationships:
- Executes separate SELECT queries per relationship
- Avoids N+1 query problem
- Better for varying result set sizes

### Caching

Redis cache is implemented for:
- School details (TTL: 5 minutes)
- Student details (TTL: 5 minutes)
- Invoice lists (TTL: 2 minutes)

Cache is invalidated on writes.

## Security

### Data Protection

1. **Passwords**: Stored as bcrypt hashes (cost factor: default)
2. **UUIDs**: Prevent enumeration attacks
3. **Soft Deletes**: Maintain audit trail
4. **Timestamps**: Track all changes

### Access Control

- JWT authentication required for all endpoints
- Token expiration configurable (default: 30 minutes)
- User status checked on each request

## Database Views

The database includes pre-built views for common reporting queries. These views are exposed through the `/api/v1/reports/*` endpoints.

### v_student_balance

**Purpose:** Current financial balance for each student.

| Column | Description |
|--------|-------------|
| student_id | Student UUID |
| full_name | First + Last name |
| school_name | School name |
| total_invoices | Count of non-cancelled invoices |
| total_invoiced | Sum of invoice amounts |
| total_paid | Sum of payments |
| balance_due | Amount still owed |
| overdue_invoices | Count of overdue invoices |

**API Endpoint:** `GET /api/v1/reports/students/balance`

---

### v_school_summary

**Purpose:** Financial summary aggregated by school.

| Column | Description |
|--------|-------------|
| school_id | School UUID |
| school_name | School name |
| total_students | Total enrolled students |
| active_students | Currently active students |
| total_invoiced | Sum of all invoices |
| total_collected | Sum of all payments |
| total_pending | Outstanding balance |
| total_overdue | Amount past due date |

**API Endpoint:** `GET /api/v1/reports/schools/summary`

---

### v_invoice_details

**Purpose:** Complete invoice information with payment status.

| Column | Description |
|--------|-------------|
| invoice_id | Invoice UUID |
| description | Invoice description |
| invoice_amount | Original amount |
| status | Current status |
| student_name | Student full name |
| school_name | School name |
| paid_amount | Amount paid so far |
| pending_amount | Remaining balance |
| days_overdue | Days past due date |

**API Endpoint:** `GET /api/v1/reports/invoices/details`

---

### v_payment_history

**Purpose:** Complete payment history with all related details.

| Column | Description |
|--------|-------------|
| payment_id | Payment UUID |
| payment_amount | Payment amount |
| payment_date | Date of payment |
| payment_method | CASH, BANK_TRANSFER, etc. |
| reference | External reference number |
| invoice_description | Related invoice |
| student_name | Student who paid |
| school_name | School receiving payment |

**API Endpoint:** `GET /api/v1/reports/payments/history`

---

### v_overdue_invoices

**Purpose:** All overdue invoices for collections follow-up.

| Column | Description |
|--------|-------------|
| invoice_id | Invoice UUID |
| days_overdue | Days past due date |
| pending_amount | Amount still owed |
| student_name | Student name |
| student_email | Contact email |
| school_name | School name |
| school_phone | School contact |

**API Endpoint:** `GET /api/v1/reports/invoices/overdue`

---

### v_daily_collections

**Purpose:** Daily payment totals grouped by school and payment method.

| Column | Description |
|--------|-------------|
| payment_date | Collection date |
| school_name | School name |
| payment_count | Number of payments |
| total_collected | Total amount |
| cash_amount | Cash payments |
| transfer_amount | Bank transfers |
| credit_card_amount | Credit card payments |

**API Endpoint:** `GET /api/v1/reports/collections/daily`

---

### v_monthly_revenue

**Purpose:** Monthly revenue statistics by school.

| Column | Description |
|--------|-------------|
| month | Month (first day) |
| school_name | School name |
| students_with_payments | Unique students who paid |
| payment_count | Total payments |
| total_revenue | Sum of payments |
| avg_payment_amount | Average payment |

**API Endpoint:** `GET /api/v1/reports/revenue/monthly`

---

## Future Considerations

If extending this schema, consider:

1. **Multi-tenancy**: Add `tenant_id` to all tables
2. **Audit Log**: Separate table for all changes
3. **Invoice Items**: Line items for invoices
4. **Payment Adjustments**: Refunds and corrections
5. **School Admins**: Link users to schools with roles
6. **Recurring Invoices**: Schedule automatic invoice generation
