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
from src.infrastructure.database.models import (
    Base, School, Grade, BillingItem, Student, Invoice, Payment
)
from src.infrastructure.database.models_user import User
from src.api.auth.jwt import get_password_hash
from src.domain.enums import InvoiceStatus, InvoiceType, PaymentMethod

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
    "Inicial 3 años",
    "Inicial 4 años",
    "Inicial 5 años",
    "1ero Primaria",
    "2do Primaria",
    "3ero Primaria",
    "4to Primaria",
    "5to Primaria",
    "6to Primaria",
    "1ero Secundaria",
    "2do Secundaria",
    "3ero Secundaria",
    "4to Secundaria",
    "5to Secundaria",
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

BILLING_ITEMS_TEMPLATE = [
    ("Matrícula 2024", "Derecho de matrícula año escolar 2024", Decimal("350.00"), False, "2024"),
    ("Matrícula 2025", "Derecho de matrícula año escolar 2025", Decimal("380.00"), False, "2025"),
    ("Almuerzo Escolar", "Servicio de almuerzo mensual", Decimal("180.00"), True, None),
    ("Transporte Zona Norte", "Servicio de transporte escolar - Zona Norte", Decimal("250.00"), True, None),
    ("Transporte Zona Sur", "Servicio de transporte escolar - Zona Sur", Decimal("280.00"), True, None),
    ("Material Didáctico", "Kit de materiales escolares", Decimal("120.00"), False, "2024"),
    ("Uniforme Completo", "Set completo de uniformes", Decimal("450.00"), False, None),
    ("Actividades Extracurriculares", "Talleres y actividades extra", Decimal("150.00"), True, None),
    ("Seguro Escolar", "Seguro médico estudiantil anual", Decimal("200.00"), False, "2024"),
    ("Cuota APAFA", "Asociación de Padres de Familia", Decimal("100.00"), False, "2024"),
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
    print(f"Created admin user: admin / admin123")
    return user


async def create_schools(session: AsyncSession) -> list[School]:
    """Create schools."""
    schools = []
    for name, address, phone, email in SCHOOL_NAMES:
        school = School(
            id=uuid4(),
            name=name,
            address=address,
            phone=phone,
            email=email,
            is_active=True,
        )
        session.add(school)
        schools.append(school)

    await session.flush()
    print(f"Created {len(schools)} schools")
    return schools


async def create_grades(session: AsyncSession, schools: list[School]) -> dict:
    """Create grades for each school with different pricing."""
    grades_by_school = {}

    for school in schools:
        grades_by_school[school.id] = []
        base_price = Decimal(str(random.randint(300, 500)))

        for i, grade_name in enumerate(GRADE_NAMES):
            # Price increases with grade level
            price_multiplier = Decimal("1.0") + (Decimal(str(i)) * Decimal("0.05"))
            monthly_fee = (base_price * price_multiplier).quantize(Decimal("0.01"))

            grade = Grade(
                id=uuid4(),
                school_id=school.id,
                name=grade_name,
                monthly_fee=monthly_fee,
                is_active=True,
            )
            session.add(grade)
            grades_by_school[school.id].append(grade)

    await session.flush()
    total_grades = sum(len(g) for g in grades_by_school.values())
    print(f"Created {total_grades} grades across {len(schools)} schools")
    return grades_by_school


async def create_billing_items(session: AsyncSession, schools: list[School]) -> dict:
    """Create billing items for each school."""
    items_by_school = {}

    for school in schools:
        items_by_school[school.id] = []

        for name, desc, base_amount, is_recurring, academic_year in BILLING_ITEMS_TEMPLATE:
            # Vary prices slightly between schools
            variation = Decimal(str(random.uniform(0.9, 1.1)))
            amount = (base_amount * variation).quantize(Decimal("0.01"))

            item = BillingItem(
                id=uuid4(),
                school_id=school.id,
                name=name,
                description=desc,
                amount=amount,
                is_recurring=is_recurring,
                academic_year=academic_year,
                is_active=True,
            )
            session.add(item)
            items_by_school[school.id].append(item)

    await session.flush()
    total_items = sum(len(i) for i in items_by_school.values())
    print(f"Created {total_items} billing items across {len(schools)} schools")
    return items_by_school


async def create_students(
    session: AsyncSession,
    schools: list[School],
    grades_by_school: dict,
    students_per_school: int = 50
) -> list[Student]:
    """Create students for each school."""
    students = []

    for school in schools:
        school_grades = grades_by_school[school.id]

        for _ in range(students_per_school):
            first_name = random.choice(FIRST_NAMES)
            last_name1 = random.choice(LAST_NAMES)
            last_name2 = random.choice(LAST_NAMES)
            grade = random.choice(school_grades)

            # Random enrollment date in the last 3 years
            days_ago = random.randint(0, 1095)
            enrolled_at = date.today() - timedelta(days=days_ago)

            student = Student(
                id=uuid4(),
                school_id=school.id,
                grade_id=grade.id,
                first_name=first_name,
                last_name=f"{last_name1} {last_name2}",
                email=f"{first_name.lower()}.{last_name1.lower()}@email.com",
                grade=grade.name,  # Also set legacy field
                enrolled_at=enrolled_at,
                is_active=random.random() > 0.05,  # 95% active
            )
            session.add(student)
            students.append(student)

    await session.flush()
    print(f"Created {len(students)} students across {len(schools)} schools")
    return students


async def create_invoices_and_payments(
    session: AsyncSession,
    students: list[Student],
    grades_by_school: dict,
    items_by_school: dict,
) -> tuple[list[Invoice], list[Payment]]:
    """Create invoices and payments for students."""
    invoices = []
    payments = []

    today = date.today()

    for student in students:
        if not student.is_active:
            continue

        school_items = items_by_school.get(student.school_id, [])

        # Find student's grade for tuition
        student_grade = None
        for grade in grades_by_school.get(student.school_id, []):
            if grade.id == student.grade_id:
                student_grade = grade
                break

        # Generate invoices for the last 6 months
        for month_offset in range(6):
            invoice_date = today.replace(day=1) - timedelta(days=30 * month_offset)
            due_date = invoice_date + timedelta(days=15)

            # Monthly tuition invoice
            if student_grade:
                tuition_invoice = Invoice(
                    id=uuid4(),
                    student_id=student.id,
                    invoice_type=InvoiceType.TUITION,
                    amount=student_grade.monthly_fee,
                    due_date=due_date,
                    status=InvoiceStatus.PENDING,
                    description=f"Mensualidad {invoice_date.strftime('%B %Y')} - {student_grade.name}",
                )
                session.add(tuition_invoice)
                invoices.append(tuition_invoice)

                # Generate payment for older invoices (higher probability)
                payment_probability = 0.9 - (month_offset * 0.05)
                if random.random() < payment_probability:
                    # Determine payment status
                    if random.random() < 0.8:  # 80% full payment
                        paid_amount = student_grade.monthly_fee
                        tuition_invoice.status = InvoiceStatus.PAID
                    else:  # 20% partial payment
                        paid_amount = (student_grade.monthly_fee * Decimal(str(random.uniform(0.3, 0.7)))).quantize(Decimal("0.01"))
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

        # Add enrollment fee (one-time)
        enrollment_items = [i for i in school_items if "Matrícula" in i.name and i.academic_year == "2024"]
        if enrollment_items and random.random() < 0.9:
            item = enrollment_items[0]
            enrollment_invoice = Invoice(
                id=uuid4(),
                student_id=student.id,
                billing_item_id=item.id,
                invoice_type=InvoiceType.ENROLLMENT,
                amount=item.amount,
                due_date=date(2024, 2, 15),
                status=InvoiceStatus.PAID,
                description=item.name,
            )
            session.add(enrollment_invoice)
            invoices.append(enrollment_invoice)

            # Payment for enrollment
            payment = Payment(
                id=uuid4(),
                invoice_id=enrollment_invoice.id,
                amount=item.amount,
                payment_date=date(2024, 2, random.randint(1, 14)),
                method=random.choice([PaymentMethod.BANK_TRANSFER, PaymentMethod.CREDIT_CARD]),
                reference=f"MAT-{random.randint(10000, 99999)}",
            )
            session.add(payment)
            payments.append(payment)

        # Add some recurring services (lunch, transport)
        recurring_items = [i for i in school_items if i.is_recurring]
        selected_services = random.sample(recurring_items, min(len(recurring_items), random.randint(0, 2)))

        for item in selected_services:
            for month_offset in range(3):  # Last 3 months
                invoice_date = today.replace(day=1) - timedelta(days=30 * month_offset)
                due_date = invoice_date + timedelta(days=20)

                service_invoice = Invoice(
                    id=uuid4(),
                    student_id=student.id,
                    billing_item_id=item.id,
                    invoice_type=InvoiceType.FEE,
                    amount=item.amount,
                    due_date=due_date,
                    status=InvoiceStatus.PAID if random.random() < 0.85 else InvoiceStatus.PENDING,
                    description=f"{item.name} - {invoice_date.strftime('%B %Y')}",
                )
                session.add(service_invoice)
                invoices.append(service_invoice)

                if service_invoice.status == InvoiceStatus.PAID:
                    payment = Payment(
                        id=uuid4(),
                        invoice_id=service_invoice.id,
                        amount=item.amount,
                        payment_date=due_date - timedelta(days=random.randint(0, 15)),
                        method=random.choice(list(PaymentMethod)),
                        reference=f"SVC-{random.randint(10000, 99999)}",
                    )
                    session.add(payment)
                    payments.append(payment)

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
            # Create all data
            await create_admin_user(session)
            schools = await create_schools(session)
            grades_by_school = await create_grades(session, schools)
            items_by_school = await create_billing_items(session, schools)
            students = await create_students(session, schools, grades_by_school, students_per_school=50)
            await create_invoices_and_payments(session, students, grades_by_school, items_by_school)

            # Commit all changes
            await session.commit()

            print("=" * 60)
            print("SEED COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("\nSummary:")
            print(f"  - Schools: {len(schools)}")
            print(f"  - Grades: {sum(len(g) for g in grades_by_school.values())}")
            print(f"  - Billing Items: {sum(len(i) for i in items_by_school.values())}")
            print(f"  - Students: {len(students)}")
            print("\nLogin credentials:")
            print("  - Username: admin")
            print("  - Password: admin123")

        except Exception as e:
            await session.rollback()
            print(f"Error during seeding: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
