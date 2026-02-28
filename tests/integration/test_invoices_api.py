"""Integration tests for Invoices API endpoints."""

import pytest
from datetime import date, timedelta
from httpx import AsyncClient


class TestInvoicesCRUD:
    """Test Invoices CRUD operations."""

    @pytest.fixture
    async def student_id(self, auth_client: AsyncClient) -> str:
        """Create a school, grade and student, return student ID."""
        school = await auth_client.post("/api/v1/schools", json={"name": "Invoice Test School"})
        school_id = school.json()["id"]

        grade = await auth_client.post(
            "/api/v1/grades",
            json={"name": "Test Grade", "monthly_fee": 500.00, "school_id": school_id},
        )
        grade_id = grade.json()["id"]

        student = await auth_client.post(
            "/api/v1/students",
            json={
                "first_name": "Invoice",
                "last_name": "Student",
                "school_id": school_id,
                "grade_id": grade_id,
            },
        )
        return student.json()["id"]

    @pytest.mark.asyncio
    async def test_create_invoice(self, auth_client: AsyncClient, student_id: str):
        """Test creating a new invoice."""
        due_date = (date.today() + timedelta(days=30)).isoformat()
        invoice_data = {
            "student_id": student_id,
            "amount": 500.00,
            "due_date": due_date,
            "description": "Monthly tuition",
        }

        response = await auth_client.post("/api/v1/invoices", json=invoice_data)

        assert response.status_code == 201
        data = response.json()
        assert float(data["amount"]) == 500.00
        assert data["status"] == "PENDING"
        assert data["student_id"] == student_id

    @pytest.mark.asyncio
    async def test_create_invoice_invalid_student(self, auth_client: AsyncClient):
        """Test creating invoice for non-existent student fails."""
        fake_student_id = "00000000-0000-0000-0000-000000000000"
        invoice_data = {
            "student_id": fake_student_id,
            "amount": 500.00,
            "due_date": date.today().isoformat(),
        }

        response = await auth_client.post("/api/v1/invoices", json=invoice_data)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_invoice_invalid_amount(self, auth_client: AsyncClient, student_id: str):
        """Test creating invoice with negative amount fails."""
        invoice_data = {
            "student_id": student_id,
            "amount": -100.00,
            "due_date": date.today().isoformat(),
        }

        response = await auth_client.post("/api/v1/invoices", json=invoice_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_invoices(self, auth_client: AsyncClient, student_id: str):
        """Test listing invoices."""
        # Create invoices
        for i in range(3):
            await auth_client.post(
                "/api/v1/invoices",
                json={
                    "student_id": student_id,
                    "amount": 100.00 * (i + 1),
                    "due_date": date.today().isoformat(),
                },
            )

        response = await auth_client.get("/api/v1/invoices?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_get_invoice_detail(self, auth_client: AsyncClient, student_id: str):
        """Test getting invoice with paid/pending amounts."""
        create_response = await auth_client.post(
            "/api/v1/invoices",
            json={
                "student_id": student_id,
                "amount": 1000.00,
                "due_date": date.today().isoformat(),
            },
        )
        invoice_id = create_response.json()["id"]

        response = await auth_client.get(f"/api/v1/invoices/{invoice_id}")

        assert response.status_code == 200
        data = response.json()
        assert "paid_amount" in data
        assert "pending_amount" in data
        assert float(data["paid_amount"]) == 0.00
        assert float(data["pending_amount"]) == 1000.00

    @pytest.mark.asyncio
    async def test_cancel_invoice(self, auth_client: AsyncClient, student_id: str):
        """Test cancelling an invoice."""
        create_response = await auth_client.post(
            "/api/v1/invoices",
            json={
                "student_id": student_id,
                "amount": 500.00,
                "due_date": date.today().isoformat(),
            },
        )
        invoice_id = create_response.json()["id"]

        response = await auth_client.delete(f"/api/v1/invoices/{invoice_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CANCELLED"
