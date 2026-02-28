"""Update report views to use grades table.

Revision ID: 004
Revises: 1c309ae71d2f
Create Date: 2026-02-27

This migration updates the database views to:
1. Use grade name from grades table (with fallback to legacy grade field)
2. Fix total_overdue calculation in v_school_summary
3. Add monthly_fee to student balance view
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "004"
down_revision = "1c309ae71d2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # VIEW: v_student_balance (UPDATED)
    # Purpose: Current balance for each student
    # Changes: Uses grades table for grade name
    # ============================================
    op.execute("DROP VIEW IF EXISTS v_student_balance;")
    op.execute("""
        CREATE OR REPLACE VIEW v_student_balance AS
        SELECT
            est.id AS student_id,
            est.first_name,
            est.last_name,
            est.first_name || ' ' || est.last_name AS full_name,
            est.email,
            COALESCE(g.name, est.grade) AS grade,
            g.monthly_fee,
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
        LEFT JOIN grades g ON g.id = est.grade_id
        LEFT JOIN invoices inv ON inv.student_id = est.id AND inv.status != 'CANCELLED'
        LEFT JOIN (
            SELECT invoice_id, SUM(amount) AS total_paid
            FROM payments
            GROUP BY invoice_id
        ) pag ON pag.invoice_id = inv.id
        GROUP BY est.id, est.first_name, est.last_name, est.email, g.name, est.grade,
                 g.monthly_fee, est.is_active, esc.id, esc.name;
    """)

    # ============================================
    # VIEW: v_school_summary (UPDATED)
    # Purpose: Financial summary per school
    # Changes: Fixed total_overdue calculation
    # ============================================
    op.execute("DROP VIEW IF EXISTS v_school_summary;")
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

    # ============================================
    # VIEW: v_invoice_details (UPDATED)
    # Purpose: Complete invoice information with payments
    # Changes: Uses grades table for grade name
    # ============================================
    op.execute("DROP VIEW IF EXISTS v_invoice_details;")
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
            COALESCE(g.name, est.grade) AS grade,
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
        LEFT JOIN grades g ON g.id = est.grade_id
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

    # ============================================
    # VIEW: v_payment_history (UPDATED)
    # Purpose: Complete payment history with all details
    # Changes: Removed ORDER BY from view definition
    # ============================================
    op.execute("DROP VIEW IF EXISTS v_payment_history;")
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

    # ============================================
    # VIEW: v_overdue_invoices (UPDATED)
    # Purpose: All overdue invoices for collections
    # Changes: Uses grades table for grade name
    # ============================================
    op.execute("DROP VIEW IF EXISTS v_overdue_invoices;")
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
            COALESCE(g.name, est.grade) AS grade,
            esc.id AS school_id,
            esc.name AS school_name,
            esc.phone AS school_phone
        FROM invoices inv
        JOIN students est ON est.id = inv.student_id
        JOIN schools esc ON esc.id = est.school_id
        LEFT JOIN grades g ON g.id = est.grade_id
        LEFT JOIN (
            SELECT invoice_id, SUM(amount) AS total_paid
            FROM payments
            GROUP BY invoice_id
        ) pag ON pag.invoice_id = inv.id
        WHERE inv.status IN ('OVERDUE', 'PENDING', 'PARTIAL')
          AND inv.due_date < CURRENT_DATE
          AND inv.amount > COALESCE(pag.total_paid, 0);
    """)

    # v_daily_collections and v_monthly_revenue remain unchanged
    # as they don't reference the grade field


def downgrade() -> None:
    # Restore original views from migration 003
    op.execute("DROP VIEW IF EXISTS v_overdue_invoices;")
    op.execute("DROP VIEW IF EXISTS v_payment_history;")
    op.execute("DROP VIEW IF EXISTS v_invoice_details;")
    op.execute("DROP VIEW IF EXISTS v_school_summary;")
    op.execute("DROP VIEW IF EXISTS v_student_balance;")

    # Recreate original v_student_balance
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

    # Recreate original v_school_summary
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
            COUNT(inv.id) AS total_invoices,
            COALESCE(SUM(inv.amount), 0) AS total_invoiced,
            COALESCE(SUM(pag.amount), 0) AS total_collected,
            COALESCE(SUM(inv.amount), 0) - COALESCE(SUM(pag.amount), 0) AS total_pending,
            COALESCE(SUM(inv.amount) FILTER (WHERE inv.status = 'OVERDUE'), 0) AS total_overdue,
            COUNT(inv.id) FILTER (WHERE inv.status = 'OVERDUE') AS overdue_invoice_count,
            COUNT(inv.id) FILTER (WHERE inv.status = 'PENDING') AS pending_invoice_count,
            COUNT(inv.id) FILTER (WHERE inv.status = 'PAID') AS paid_invoice_count
        FROM schools esc
        LEFT JOIN students est ON est.school_id = esc.id
        LEFT JOIN invoices inv ON inv.student_id = est.id AND inv.status != 'CANCELLED'
        LEFT JOIN payments pag ON pag.invoice_id = inv.id
        GROUP BY esc.id, esc.name, esc.email, esc.phone, esc.is_active;
    """)

    # Recreate original v_invoice_details
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

    # Recreate original v_payment_history
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
        JOIN schools esc ON esc.id = est.school_id
        ORDER BY pag.created_at DESC;
    """)

    # Recreate original v_overdue_invoices
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
          AND inv.amount > COALESCE(pag.total_paid, 0)
        ORDER BY days_overdue DESC;
    """)
