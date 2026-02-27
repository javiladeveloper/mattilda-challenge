"""Integration tests for Payments API endpoints."""

import pytest
from datetime import date
from httpx import AsyncClient


class TestPaymentsCRUD:
    """Test Payments CRUD operations."""

    @pytest.fixture
    async def invoice_id(self, client: AsyncClient) -> str:
        """Create school, student, and invoice. Return invoice ID."""
        school = await client.post("/api/v1/schools", json={"name": "Payment Test School"})
        school_id = school.json()["id"]

        student = await client.post(
            "/api/v1/students",
            json={
                "first_name": "Payment",
                "last_name": "Student",
                "school_id": school_id,
            },
        )
        student_id = student.json()["id"]

        invoice = await client.post(
            "/api/v1/invoices",
            json={
                "student_id": student_id,
                "amount": 1000.00,
                "due_date": date.today().isoformat(),
                "description": "Test Invoice",
            },
        )
        return invoice.json()["id"]

    @pytest.mark.asyncio
    async def test_create_payment(self, client: AsyncClient, invoice_id: str):
        """Test creating a payment."""
        payment_data = {
            "invoice_id": invoice_id,
            "amount": 500.00,
            "method": "BANK_TRANSFER",
            "reference": "TRF-001",
        }

        response = await client.post("/api/v1/payments", json=payment_data)

        assert response.status_code == 201
        data = response.json()
        assert float(data["amount"]) == 500.00
        assert data["method"] == "BANK_TRANSFER"
        assert data["reference"] == "TRF-001"

    @pytest.mark.asyncio
    async def test_create_payment_updates_invoice_status(self, client: AsyncClient, invoice_id: str):
        """Test that payment updates invoice status."""
        # Make partial payment
        await client.post(
            "/api/v1/payments",
            json={"invoice_id": invoice_id, "amount": 300.00, "method": "CASH"},
        )

        # Check invoice is PARTIAL
        invoice_response = await client.get(f"/api/v1/invoices/{invoice_id}")
        assert invoice_response.json()["status"] == "PARTIAL"

        # Complete payment
        await client.post(
            "/api/v1/payments",
            json={"invoice_id": invoice_id, "amount": 700.00, "method": "CASH"},
        )

        # Check invoice is PAID
        invoice_response = await client.get(f"/api/v1/invoices/{invoice_id}")
        assert invoice_response.json()["status"] == "PAID"

    @pytest.mark.asyncio
    async def test_payment_exceeds_pending_amount(self, client: AsyncClient, invoice_id: str):
        """Test that payment cannot exceed pending amount."""
        # Invoice is 1000.00, try to pay 1500.00
        payment_data = {
            "invoice_id": invoice_id,
            "amount": 1500.00,
            "method": "CASH",
        }

        response = await client.post("/api/v1/payments", json=payment_data)

        assert response.status_code == 400
        assert "exceeds" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_cannot_pay_cancelled_invoice(self, client: AsyncClient):
        """Test that payment to cancelled invoice fails."""
        # Create a new invoice and cancel it
        school = await client.post("/api/v1/schools", json={"name": "Cancel Test"})
        student = await client.post(
            "/api/v1/students",
            json={"first_name": "A", "last_name": "B", "school_id": school.json()["id"]},
        )
        invoice = await client.post(
            "/api/v1/invoices",
            json={
                "student_id": student.json()["id"],
                "amount": 500.00,
                "due_date": date.today().isoformat(),
            },
        )
        invoice_id = invoice.json()["id"]

        # Cancel the invoice
        await client.delete(f"/api/v1/invoices/{invoice_id}")

        # Try to pay
        response = await client.post(
            "/api/v1/payments",
            json={"invoice_id": invoice_id, "amount": 100.00, "method": "CASH"},
        )

        assert response.status_code == 400
        assert "cancelled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_invoice_payments(self, client: AsyncClient, invoice_id: str):
        """Test listing payments for an invoice."""
        # Create payments
        for i in range(3):
            await client.post(
                "/api/v1/payments",
                json={
                    "invoice_id": invoice_id,
                    "amount": 100.00,
                    "method": "CASH",
                },
            )

        response = await client.get(f"/api/v1/payments/invoice/{invoice_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
