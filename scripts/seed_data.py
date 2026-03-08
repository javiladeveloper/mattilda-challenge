"""
Seed script to populate the database with test data.

Run with: docker-compose exec api python scripts/seed_data.py
"""

import asyncio
import random
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.config import settings
from src.infrastructure.database.models import Base, School, Student, Invoice, Payment
from src.infrastructure.database.models_user import User
from src.api.auth.jwt import get_password_hash
from src.domain.enums import InvoiceStatus, PaymentMethod

# Database connection
engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Sample data
SCHOOL_NAMES = [
    ("Colegio San Ignacio", "Av. Principal 123, Lima", "+51 1 234 5678", "contacto@sanignacio.edu.pe"),
    ("Instituto Santa María", "Jr. Los Olivos 456, Lima", "+51 1 345 6789", "info@santamaria.edu.pe"),
    ("Escuela Bilingüe del Sol", "Calle Las Flores 789, Miraflores", "+51 1 456 7890", "admin@bilinguesol.edu.pe"),
    ("Colegio Peruano Británico", "Av. La Marina 321, San Miguel", "+51 1 567 8901", "admision@peruanobritanico.edu.pe"),
    ("Academia Científica Einstein", "Jr. Newton 654, Surco", "+51 1 678 9012", "secretaria@einstein.edu.pe"),
]

GRADE_NAMES = [
    "Inicial 3 años", "Inicial 4 años", "Inicial 5 años",
    "1ero Primaria", "2do Primaria", "3ero Primaria",
    "4to Primaria", "5to Primaria", "6to Primaria",
    "1ero Secundaria", "2do Secundaria", "3ero Secundaria",
    "4to Secundaria", "5to Secundaria",
]

FIRST_NAMES = [
    "María", "José", "Luis", "Ana", "Carlos", "Carmen", "Juan", "Rosa",
    "Miguel", "Patricia", "Jorge", "Lucía", "Pedro", "Sofía", "Diego",
    "Valentina", "Andrés", "Isabella", "Gabriel", "Camila", "Daniel",
    "Mariana", "Sebastián", "Paula", "Alejandro", "Daniela", "Fernando",
    "Natalia", "Ricardo", "Valeria", "Eduardo", "Adriana", "Roberto",
    "Fernanda", "Francisco", "Gabriela", "Javier", "Andrea", "Manuel",
    "Claudia", "Antonio", "Victoria", "Sergio", "Ximena", "Raúl",
    "Carolina", "Alberto", "Jimena", "Enrique", "Paola"
]

LAST_NAMES = [
    "García", "Rodríguez", "Martínez", "López", "González", "Hernández",
    "Pérez", "Sánchez", "Ramírez", "Torres", "Flores", "Rivera", "Gómez",
    "Díaz", "Reyes", "Morales", "Cruz", "Ortiz", "Gutiérrez", "Chávez",
    "Ramos", "Mendoza", "Ruiz", "Aguilar", "Medina", "Castro", "Vargas",
    "Romero", "Jiménez", "Herrera", "Muñoz", "Núñez", "Silva", "Rojas",
    "Vega", "Campos", "Delgado", "Ríos", "Suárez", "Guerrero"
]


async def create_admin_user(session: AsyncSession) -> User:
    """Create admin user if not exists."""
    from sqlalchemy import select

    result = await session.execute(select(User).where(User.username == "admin"))
    existing = result.scalar_one_or_none()

    if existing:
        print("Admin user already exists")
        return existing

    user = User(
        id=uuid4(),
        username="admin",
        email="admin@mattilda.com",
        hashed_password=get_password_hash("admin123"),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    print("Created admin user: admin / admin123")
    return user


async def create_schools(session: AsyncSession) -> list[School]:
    """Create schools."""
    schools = []
    for name, address, phone, email in SCHOOL_NAMES:
        school = School(
            id=uuid4(), name=name, address=address, phone=phone, email=email, is_active=True,
        )
        session.add(school)
        schools.append(school)

    await session.flush()
    print(f"Created {len(schools)} schools")
    return schools


async def create_students(
    session: AsyncSession, schools: list[School], students_per_school: int = 50
) -> list[Student]:
    """Create students for each school."""
    students = []

    for school in schools:
        for _ in range(students_per_school):
            first_name = random.choice(FIRST_NAMES)
            last_name1 = random.choice(LAST_NAMES)
            last_name2 = random.choice(LAST_NAMES)
            grade = random.choice(GRADE_NAMES)

            days_ago = random.randint(0, 1095)
            enrolled_at = date.today() - timedelta(days=days_ago)

            student = Student(
                id=uuid4(),
                school_id=school.id,
                first_name=first_name,
                last_name=f"{last_name1} {last_name2}",
                email=f"{first_name.lower()}.{last_name1.lower()}@email.com",
                grade=grade,
                enrolled_at=enrolled_at,
                is_active=random.random() > 0.05,
            )
            session.add(student)
            students.append(student)

    await session.flush()
    print(f"Created {len(students)} students across {len(schools)} schools")
    return students


async def create_invoices_and_payments(
    session: AsyncSession, students: list[Student],
) -> tuple[list[Invoice], list[Payment]]:
    """Create invoices and payments for students."""
    invoices = []
    payments = []
    today = date.today()

    for student in students:
        if not student.is_active:
            continue

        base_tuition = Decimal(str(random.randint(300, 600)))

        # Generate monthly tuition invoices for the last 6 months
        for month_offset in range(6):
            invoice_date = today.replace(day=1) - timedelta(days=30 * month_offset)
            due_date = invoice_date + timedelta(days=15)

            tuition_invoice = Invoice(
                id=uuid4(),
                student_id=student.id,
                amount=base_tuition,
                due_date=due_date,
                status=InvoiceStatus.PENDING,
                description=f"Mensualidad {invoice_date.strftime('%B %Y')} - {student.grade or 'General'}",
            )
            session.add(tuition_invoice)
            invoices.append(tuition_invoice)

            payment_probability = 0.9 - (month_offset * 0.05)
            if random.random() < payment_probability:
                if random.random() < 0.8:
                    paid_amount = base_tuition
                    tuition_invoice.status = InvoiceStatus.PAID
                else:
                    paid_amount = (base_tuition * Decimal(str(random.uniform(0.3, 0.7)))).quantize(Decimal("0.01"))
                    tuition_invoice.status = InvoiceStatus.PARTIAL

                payment = Payment(
                    id=uuid4(),
                    invoice_id=tuition_invoice.id,
                    amount=paid_amount,
                    payment_date=due_date - timedelta(days=random.randint(0, 10)),
                    method=random.choice(list(PaymentMethod)),
                    reference=f"PAY-{random.randint(10000, 99999)}",
                )
                session.add(payment)
                payments.append(payment)
            elif due_date < today:
                tuition_invoice.status = InvoiceStatus.OVERDUE

    await session.flush()
    print(f"Created {len(invoices)} invoices and {len(payments)} payments")
    return invoices, payments


async def main():
    """Main seed function."""
    print("=" * 60)
    print("MATTILDA - Database Seeding Script")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        try:
            await create_admin_user(session)
            schools = await create_schools(session)
            students = await create_students(session, schools, students_per_school=50)
            await create_invoices_and_payments(session, students)

            await session.commit()

            print("=" * 60)
            print("SEED COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"\nSummary:")
            print(f"  - Schools: {len(schools)}")
            print(f"  - Students: {len(students)}")
            print(f"\nLogin credentials:")
            print(f"  - Username: admin")
            print(f"  - Password: admin123")

        except Exception as e:
            await session.rollback()
            print(f"Error during seeding: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
