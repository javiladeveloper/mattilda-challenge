"""Integration tests for Account Statement endpoints."""

import pytest
from datetime import date
from httpx import AsyncClient


class TestSchoolStatement:
    """Test School account statement endpoint."""

    @pytest.mark.asyncio
    async def test_school_statement_empty(self, auth_client: AsyncClient):
        """Test statement for school with no students."""
        school = await auth_client.post("/api/v1/schools", json={"name": "Empty Statement School"})
        school_id = school.json()["id"]

        response = await auth_client.get(f"/api/v1/schools/{school_id}/statement")

        assert response.status_code == 200
        data = response.json()
        assert data["school_id"] == school_id
        assert data["total_students"] == 0
        assert data["active_students"] == 0
        assert float(data["summary"]["total_invoiced"]) == 0
        assert float(data["summary"]["total_paid"]) == 0
        assert float(data["summary"]["total_pending"]) == 0
        assert data["invoices"] == []

    @pytest.mark.asyncio
    async def test_school_statement_with_data(self, auth_client: AsyncClient):
        """Test statement for school with students and invoices."""
        # Create school
        school = await auth_client.post("/api/v1/schools", json={"name": "Full Statement School"})
        school_id = school.json()["id"]

        # Create student
        student = await auth_client.post(
            "/api/v1/students",
            json={"first_name": "Test", "last_name": "Student", "school_id": school_id},
        )
        student_id = student.json()["id"]

        # Create invoices
        await auth_client.post(
            "/api/v1/invoices",
            json={
                "student_id": student_id,
                "amount": 500.00,
                "due_date": date.today().isoformat(),
            },
        )
        invoice2 = await auth_client.post(
            "/api/v1/invoices",
            json={
                "student_id": student_id,
                "amount": 300.00,
                "due_date": date.today().isoformat(),
            },
        )

        # Make a payment
        await auth_client.post(
            "/api/v1/payments",
            json={
                "invoice_id": invoice2.json()["id"],
                "amount": 300.00,
                "method": "CASH",
            },
        )

        response = await auth_client.get(f"/api/v1/schools/{school_id}/statement")

        assert response.status_code == 200
        data = response.json()
        assert data["total_students"] == 1
        assert data["active_students"] == 1
        assert float(data["summary"]["total_invoiced"]) == 800.00
        assert float(data["summary"]["total_paid"]) == 300.00
        assert float(data["summary"]["total_pending"]) == 500.00
        assert len(data["invoices"]) == 2


class TestStudentStatement:
    """Test Student account statement endpoint."""

    @pytest.mark.asyncio
    async def test_student_statement_empty(self, auth_client: AsyncClient):
        """Test statement for student with no invoices."""
        school = await auth_client.post("/api/v1/schools", json={"name": "Statement School"})
        student = await auth_client.post(
            "/api/v1/students",
            json={
                "first_name": "No",
                "last_name": "Invoices",
                "school_id": school.json()["id"],
            },
        )
        student_id = student.json()["id"]

        response = await auth_client.get(f"/api/v1/students/{student_id}/statement")

        assert response.status_code == 200
        data = response.json()
        assert data["student_id"] == student_id
        assert data["student_name"] == "No Invoices"
        assert float(data["summary"]["total_invoiced"]) == 0
        assert data["invoices"] == []

    @pytest.mark.asyncio
    async def test_student_statement_with_payments(self, auth_client: AsyncClient):
        """Test statement showing invoices and payments."""
        school = await auth_client.post("/api/v1/schools", json={"name": "Pay School"})
        student = await auth_client.post(
            "/api/v1/students",
            json={
                "first_name": "Paying",
                "last_name": "Student",
                "school_id": school.json()["id"],
            },
        )
        student_id = student.json()["id"]

        # Create invoice
        invoice = await auth_client.post(
            "/api/v1/invoices",
            json={
                "student_id": student_id,
                "amount": 1000.00,
                "due_date": date.today().isoformat(),
                "description": "Tuition",
            },
        )
        invoice_id = invoice.json()["id"]

        # Make payments
        await auth_client.post(
            "/api/v1/payments",
            json={"invoice_id": invoice_id, "amount": 400.00, "method": "CASH"},
        )
        await auth_client.post(
            "/api/v1/payments",
            json={"invoice_id": invoice_id, "amount": 300.00, "method": "BANK_TRANSFER"},
        )

        response = await auth_client.get(f"/api/v1/students/{student_id}/statement")

        assert response.status_code == 200
        data = response.json()
        assert float(data["summary"]["total_invoiced"]) == 1000.00
        assert float(data["summary"]["total_paid"]) == 700.00
        assert float(data["summary"]["total_pending"]) == 300.00

        # Check invoice has payments
        invoice_data = data["invoices"][0]
        assert len(invoice_data["payments"]) == 2
        assert float(invoice_data["paid_amount"]) == 700.00
        assert float(invoice_data["pending_amount"]) == 300.00
