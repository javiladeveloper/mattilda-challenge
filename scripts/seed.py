"""
Seed script to populate the database with sample data.

Run with: python scripts/seed.py
Or inside Docker: docker-compose exec api python scripts/seed.py
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import AsyncSessionLocal
from src.infrastructure.database.models import School, Student, Invoice, Payment
from src.domain.enums import InvoiceStatus, PaymentMethod


async def seed_data():
    async with AsyncSessionLocal() as session:
        # Create Schools
        schools = [
            School(
                id=uuid.uuid4(),
                name="Colegio San Patricio",
                address="Av. Principal 123, Lima",
                phone="+51 1 234 5678",
                email="contacto@sanpatricio.edu.pe",
            ),
            School(
                id=uuid.uuid4(),
                name="Instituto Educativo Santa María",
                address="Jr. Los Pinos 456, Lima",
                phone="+51 1 876 5432",
                email="info@santamaria.edu.pe",
            ),
        ]

        for school in schools:
            session.add(school)

        await session.flush()

        # Create Students for each school
        students_data = [
            # School 1 students
            {"school": schools[0], "first_name": "Juan", "last_name": "García", "grade": "5to Primaria"},
            {"school": schools[0], "first_name": "María", "last_name": "López", "grade": "3ro Secundaria"},
            {"school": schools[0], "first_name": "Carlos", "last_name": "Rodríguez", "grade": "1ro Secundaria"},
            {"school": schools[0], "first_name": "Ana", "last_name": "Martínez", "grade": "4to Primaria"},
            # School 2 students
            {"school": schools[1], "first_name": "Luis", "last_name": "Pérez", "grade": "2do Secundaria"},
            {"school": schools[1], "first_name": "Sofia", "last_name": "Fernández", "grade": "6to Primaria"},
            {"school": schools[1], "first_name": "Diego", "last_name": "Torres", "grade": "5to Secundaria"},
        ]

        students = []
        for data in students_data:
            student = Student(
                id=uuid.uuid4(),
                school_id=data["school"].id,
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=f"{data['first_name'].lower()}.{data['last_name'].lower()}@email.com",
                grade=data["grade"],
                enrolled_at=date.today() - timedelta(days=365),
            )
            session.add(student)
            students.append(student)

        await session.flush()

        # Create Invoices for students
        today = date.today()
        invoices = []

        # Student 1: Has paid invoices
        inv1 = Invoice(
            id=uuid.uuid4(),
            student_id=students[0].id,
            amount=Decimal("500.00"),
            due_date=today - timedelta(days=30),
            status=InvoiceStatus.PAID,
            description="Mensualidad Enero 2024",
        )
        invoices.append(inv1)

        # Student 1: Has partial payment
        inv2 = Invoice(
            id=uuid.uuid4(),
            student_id=students[0].id,
            amount=Decimal("500.00"),
            due_date=today - timedelta(days=15),
            status=InvoiceStatus.PARTIAL,
            description="Mensualidad Febrero 2024",
        )
        invoices.append(inv2)

        # Student 2: Has overdue invoice
        inv3 = Invoice(
            id=uuid.uuid4(),
            student_id=students[1].id,
            amount=Decimal("750.00"),
            due_date=today - timedelta(days=45),
            status=InvoiceStatus.OVERDUE,
            description="Mensualidad Enero 2024",
        )
        invoices.append(inv3)

        # Student 2: Has pending invoice
        inv4 = Invoice(
            id=uuid.uuid4(),
            student_id=students[1].id,
            amount=Decimal("750.00"),
            due_date=today + timedelta(days=15),
            status=InvoiceStatus.PENDING,
            description="Mensualidad Marzo 2024",
        )
        invoices.append(inv4)

        # Student 3: Multiple invoices
        inv5 = Invoice(
            id=uuid.uuid4(),
            student_id=students[2].id,
            amount=Decimal("600.00"),
            due_date=today - timedelta(days=60),
            status=InvoiceStatus.PAID,
            description="Mensualidad Diciembre 2023",
        )
        invoices.append(inv5)

        inv6 = Invoice(
            id=uuid.uuid4(),
            student_id=students[2].id,
            amount=Decimal("600.00"),
            due_date=today + timedelta(days=5),
            status=InvoiceStatus.PENDING,
            description="Mensualidad Febrero 2024",
        )
        invoices.append(inv6)

        # Student 4 (School 2): Has pending
        inv7 = Invoice(
            id=uuid.uuid4(),
            student_id=students[4].id,
            amount=Decimal("450.00"),
            due_date=today + timedelta(days=10),
            status=InvoiceStatus.PENDING,
            description="Mensualidad Febrero 2024",
        )
        invoices.append(inv7)

        for invoice in invoices:
            session.add(invoice)

        await session.flush()

        # Create Payments
        payments = [
            # Full payment for invoice 1
            Payment(
                id=uuid.uuid4(),
                invoice_id=inv1.id,
                amount=Decimal("500.00"),
                payment_date=today - timedelta(days=25),
                method=PaymentMethod.BANK_TRANSFER,
                reference="TRF-001-2024",
            ),
            # Partial payment for invoice 2
            Payment(
                id=uuid.uuid4(),
                invoice_id=inv2.id,
                amount=Decimal("200.00"),
                payment_date=today - timedelta(days=10),
                method=PaymentMethod.CASH,
                reference="REC-002-2024",
            ),
            # Full payment for invoice 5
            Payment(
                id=uuid.uuid4(),
                invoice_id=inv5.id,
                amount=Decimal("600.00"),
                payment_date=today - timedelta(days=55),
                method=PaymentMethod.CREDIT_CARD,
                reference="CC-003-2024",
            ),
        ]

        for payment in payments:
            session.add(payment)

        await session.commit()

        print("Seed data created successfully!")
        print(f"  - {len(schools)} schools")
        print(f"  - {len(students)} students")
        print(f"  - {len(invoices)} invoices")
        print(f"  - {len(payments)} payments")


if __name__ == "__main__":
    asyncio.run(seed_data())
