"""Remove grades and billing_items tables, simplify schema.

Revision ID: 005
Revises: 004
Create Date: 2026-03-06

This migration:
1. Drops all views (they reference grades)
2. Drops FK columns: invoices.billing_item_id, invoices.invoice_type, students.grade_id
3. Drops tables: grades, billing_items
4. Drops index: ix_students_grade_id, ix_invoices_invoice_type
5. Recreates 7 views without grade/billing_item references
"""

from alembic import op
import sqlalchemy as sa


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop all views first (they depend on grades)
    op.execute("DROP VIEW IF EXISTS v_monthly_revenue;")
    op.execute("DROP VIEW IF EXISTS v_daily_collections;")
    op.execute("DROP VIEW IF EXISTS v_overdue_invoices;")
    op.execute("DROP VIEW IF EXISTS v_payment_history;")
    op.execute("DROP VIEW IF EXISTS v_invoice_details;")
    op.execute("DROP VIEW IF EXISTS v_school_summary;")
    op.execute("DROP VIEW IF EXISTS v_student_balance;")

    # 2. Drop FK columns and indexes from invoices
    op.drop_index("ix_invoices_invoice_type", table_name="invoices")
    op.drop_column("invoices", "billing_item_id")
    op.drop_column("invoices", "invoice_type")

    # 3. Drop FK column and index from students
    op.drop_index("ix_students_grade_id", table_name="students")
    op.drop_column("students", "grade_id")

    # 4. Drop tables
    op.drop_table("billing_items")
    op.drop_table("grades")

    # 5. Recreate views without grade/billing_item references

    op.execute("""
        CREATE OR REPLACE VIEW v_student_balance AS
        SELECT
            est.id AS student_id,
            est.first_name,
            est.last_name,
            est.first_name || ' ' || est.last_name AS full_name,
            est.email,
            est.grade,
            est.is_active,
            esc.id AS school_id,
            esc.name AS school_name,
            COUNT(inv.id) AS total_invoices,
            COALESCE(SUM(inv.amount), 0) AS total_invoiced,
            COALESCE(SUM(pag.total_paid), 0) AS total_paid,
            COALESCE(SUM(inv.amount), 0) - COALESCE(SUM(pag.total_paid), 0) AS balance_due,
            COUNT(inv.id) FILTER (WHERE inv.status = 'OVERDUE') AS overdue_invoices,
            COUNT(inv.id) FILTER (WHERE inv.status = 'PENDING') AS pending_invoices,
            COUNT(inv.id) FILTER (WHERE inv.status = 'PARTIAL') AS partial_invoices,
            COUNT(inv.id) FILTER (WHERE inv.status = 'PAID') AS paid_invoices
        FROM students est
        JOIN schools esc ON esc.id = est.school_id
        LEFT JOIN invoices inv ON inv.student_id = est.id AND inv.status != 'CANCELLED'
        LEFT JOIN (
            SELECT invoice_id, SUM(amount) AS total_paid
            FROM payments
            GROUP BY invoice_id
        ) pag ON pag.invoice_id = inv.id
        GROUP BY est.id, est.first_name, est.last_name, est.email, est.grade,
                 est.is_active, esc.id, esc.name;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_school_summary AS
        SELECT
            esc.id AS school_id,
            esc.name AS school_name,
            esc.email AS school_email,
            esc.phone AS school_phone,
            esc.is_active,
            COUNT(DISTINCT est.id) AS total_students,
            COUNT(DISTINCT est.id) FILTER (WHERE est.is_active) AS active_students,
            COUNT(inv.id) FILTER (WHERE inv.status != 'CANCELLED') AS total_invoices,
            COALESCE(SUM(inv.amount) FILTER (WHERE inv.status != 'CANCELLED'), 0) AS total_invoiced,
            COALESCE(SUM(pag.amount), 0) AS total_collected,
            COALESCE(SUM(inv.amount) FILTER (WHERE inv.status != 'CANCELLED'), 0) - COALESCE(SUM(pag.amount), 0) AS total_pending,
            COALESCE(
                SUM(inv.amount - COALESCE(inv_payments.paid, 0))
                FILTER (WHERE inv.status = 'OVERDUE' OR (inv.status IN ('PENDING', 'PARTIAL') AND inv.due_date < CURRENT_DATE)),
                0
            ) AS total_overdue,
            COUNT(inv.id) FILTER (WHERE inv.status = 'OVERDUE' OR (inv.status IN ('PENDING', 'PARTIAL') AND inv.due_date < CURRENT_DATE)) AS overdue_invoice_count,
            COUNT(inv.id) FILTER (WHERE inv.status = 'PENDING') AS pending_invoice_count,
            COUNT(inv.id) FILTER (WHERE inv.status = 'PAID') AS paid_invoice_count
        FROM schools esc
        LEFT JOIN students est ON est.school_id = esc.id
        LEFT JOIN invoices inv ON inv.student_id = est.id
        LEFT JOIN payments pag ON pag.invoice_id = inv.id
        LEFT JOIN (
            SELECT invoice_id, SUM(amount) AS paid
            FROM payments
            GROUP BY invoice_id
        ) inv_payments ON inv_payments.invoice_id = inv.id
        GROUP BY esc.id, esc.name, esc.email, esc.phone, esc.is_active;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_invoice_details AS
        SELECT
            inv.id AS invoice_id,
            inv.description,
            inv.amount AS invoice_amount,
            inv.due_date,
            inv.status,
            inv.created_at AS invoice_created_at,
            est.id AS student_id,
            est.first_name || ' ' || est.last_name AS student_name,
            est.email AS student_email,
            est.grade,
            esc.id AS school_id,
            esc.name AS school_name,
            COALESCE(pag.total_paid, 0) AS paid_amount,
            inv.amount - COALESCE(pag.total_paid, 0) AS pending_amount,
            pag.payment_count,
            pag.last_payment_date,
            CASE
                WHEN inv.status = 'PAID' THEN 0
                WHEN inv.due_date < CURRENT_DATE THEN CURRENT_DATE - inv.due_date
                ELSE 0
            END AS days_overdue
        FROM invoices inv
        JOIN students est ON est.id = inv.student_id
        JOIN schools esc ON esc.id = est.school_id
        LEFT JOIN (
            SELECT
                invoice_id,
                SUM(amount) AS total_paid,
                COUNT(*) AS payment_count,
                MAX(payment_date) AS last_payment_date
            FROM payments
            GROUP BY invoice_id
        ) pag ON pag.invoice_id = inv.id;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_payment_history AS
        SELECT
            pag.id AS payment_id,
            pag.amount AS payment_amount,
            pag.payment_date,
            pag.method AS payment_method,
            pag.reference,
            pag.created_at AS payment_created_at,
            inv.id AS invoice_id,
            inv.description AS invoice_description,
            inv.amount AS invoice_amount,
            inv.status AS invoice_status,
            inv.due_date,
            est.id AS student_id,
            est.first_name || ' ' || est.last_name AS student_name,
            est.email AS student_email,
            esc.id AS school_id,
            esc.name AS school_name
        FROM payments pag
        JOIN invoices inv ON inv.id = pag.invoice_id
        JOIN students est ON est.id = inv.student_id
        JOIN schools esc ON esc.id = est.school_id;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_overdue_invoices AS
        SELECT
            inv.id AS invoice_id,
            inv.description,
            inv.amount AS invoice_amount,
            inv.due_date,
            CURRENT_DATE - inv.due_date AS days_overdue,
            COALESCE(pag.total_paid, 0) AS paid_amount,
            inv.amount - COALESCE(pag.total_paid, 0) AS pending_amount,
            est.id AS student_id,
            est.first_name || ' ' || est.last_name AS student_name,
            est.email AS student_email,
            est.grade,
            esc.id AS school_id,
            esc.name AS school_name,
            esc.phone AS school_phone
        FROM invoices inv
        JOIN students est ON est.id = inv.student_id
        JOIN schools esc ON esc.id = est.school_id
        LEFT JOIN (
            SELECT invoice_id, SUM(amount) AS total_paid
            FROM payments
            GROUP BY invoice_id
        ) pag ON pag.invoice_id = inv.id
        WHERE inv.status IN ('OVERDUE', 'PENDING', 'PARTIAL')
          AND inv.due_date < CURRENT_DATE
          AND inv.amount > COALESCE(pag.total_paid, 0);
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_daily_collections AS
        SELECT
            pag.payment_date,
            esc.id AS school_id,
            esc.name AS school_name,
            COUNT(pag.id) AS payment_count,
            SUM(pag.amount) AS total_collected,
            SUM(pag.amount) FILTER (WHERE pag.method = 'CASH') AS cash_amount,
            SUM(pag.amount) FILTER (WHERE pag.method = 'BANK_TRANSFER') AS transfer_amount,
            SUM(pag.amount) FILTER (WHERE pag.method = 'CREDIT_CARD') AS credit_card_amount,
            SUM(pag.amount) FILTER (WHERE pag.method = 'DEBIT_CARD') AS debit_card_amount,
            SUM(pag.amount) FILTER (WHERE pag.method = 'OTHER') AS other_amount
        FROM payments pag
        JOIN invoices inv ON inv.id = pag.invoice_id
        JOIN students est ON est.id = inv.student_id
        JOIN schools esc ON esc.id = est.school_id
        GROUP BY pag.payment_date, esc.id, esc.name;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_monthly_revenue AS
        SELECT
            DATE_TRUNC('month', pag.payment_date)::date AS month,
            esc.id AS school_id,
            esc.name AS school_name,
            COUNT(DISTINCT inv.student_id) AS students_with_payments,
            COUNT(pag.id) AS payment_count,
            SUM(pag.amount) AS total_revenue,
            AVG(pag.amount) AS avg_payment_amount,
            MIN(pag.amount) AS min_payment,
            MAX(pag.amount) AS max_payment
        FROM payments pag
        JOIN invoices inv ON inv.id = pag.invoice_id
        JOIN students est ON est.id = inv.student_id
        JOIN schools esc ON esc.id = est.school_id
        GROUP BY DATE_TRUNC('month', pag.payment_date), esc.id, esc.name;
    """)


def downgrade() -> None:
    # 1. Drop views (will be recreated by migration 004's state)
    op.execute("DROP VIEW IF EXISTS v_monthly_revenue;")
    op.execute("DROP VIEW IF EXISTS v_daily_collections;")
    op.execute("DROP VIEW IF EXISTS v_overdue_invoices;")
    op.execute("DROP VIEW IF EXISTS v_payment_history;")
    op.execute("DROP VIEW IF EXISTS v_invoice_details;")
    op.execute("DROP VIEW IF EXISTS v_school_summary;")
    op.execute("DROP VIEW IF EXISTS v_student_balance;")

    # 2. Recreate grades table (structure only, data is lost)
    op.create_table(
        "grades",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("school_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("monthly_fee", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grades_is_active", "grades", ["is_active"])
    op.create_index("ix_grades_school_id", "grades", ["school_id"])

    # 3. Recreate billing_items table (structure only, data is lost)
    op.create_table(
        "billing_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("school_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_recurring", sa.Boolean(), nullable=False),
        sa.Column("academic_year", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_items_is_active", "billing_items", ["is_active"])
    op.create_index("ix_billing_items_school_id", "billing_items", ["school_id"])

    # 4. Re-add FK columns to students and invoices
    op.add_column("students", sa.Column("grade_id", sa.UUID(), nullable=True))
    op.create_index("ix_students_grade_id", "students", ["grade_id"])
    op.create_foreign_key(None, "students", "grades", ["grade_id"], ["id"], ondelete="SET NULL")

    op.add_column("invoices", sa.Column("billing_item_id", sa.UUID(), nullable=True))
    op.add_column("invoices", sa.Column("invoice_type", sa.String(length=20), nullable=False, server_default=sa.text("'CUSTOM'")))
    op.create_index("ix_invoices_invoice_type", "invoices", ["invoice_type"])
    op.create_foreign_key(None, "invoices", "billing_items", ["billing_item_id"], ["id"], ondelete="SET NULL")
