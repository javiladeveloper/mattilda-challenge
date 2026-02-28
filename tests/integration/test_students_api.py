"""Integration tests for Students API endpoints."""

import pytest
from httpx import AsyncClient


class TestStudentsCRUD:
    """Test Students CRUD operations."""

    @pytest.fixture
    async def school_id(self, auth_client: AsyncClient) -> str:
        """Create a school and return its ID."""
        response = await auth_client.post(
            "/api/v1/schools", json={"name": "Test School for Students"}
        )
        return response.json()["id"]

    @pytest.fixture
    async def grade_id(self, auth_client: AsyncClient, school_id: str) -> str:
        """Create a grade and return its ID."""
        response = await auth_client.post(
            "/api/v1/grades",
            json={"name": "5th Grade", "monthly_fee": 500.00, "school_id": school_id},
        )
        return response.json()["id"]

    async def create_grade_for_school(self, auth_client: AsyncClient, school_id: str, name: str = "Test Grade") -> str:
        """Helper to create a grade for a school."""
        response = await auth_client.post(
            "/api/v1/grades",
            json={"name": name, "monthly_fee": 500.00, "school_id": school_id},
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_create_student(self, auth_client: AsyncClient, school_id: str, grade_id: str):
        """Test creating a new student."""
        student_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@email.com",
            "grade_id": grade_id,
            "school_id": school_id,
        }

        response = await auth_client.post("/api/v1/students", json=student_data)

        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["school_id"] == school_id
        assert data["grade_id"] == grade_id
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_student_invalid_school(self, auth_client: AsyncClient):
        """Test creating student with non-existent school fails."""
        fake_school_id = "00000000-0000-0000-0000-000000000000"
        fake_grade_id = "00000000-0000-0000-0000-000000000001"
        student_data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "school_id": fake_school_id,
            "grade_id": fake_grade_id,
        }

        response = await auth_client.post("/api/v1/students", json=student_data)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_students(self, auth_client: AsyncClient, school_id: str, grade_id: str):
        """Test listing students with pagination."""
        # Create students
        for i in range(3):
            await auth_client.post(
                "/api/v1/students",
                json={
                    "first_name": f"Student{i}",
                    "last_name": "Test",
                    "school_id": school_id,
                    "grade_id": grade_id,
                },
            )

        response = await auth_client.get("/api/v1/students?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_list_students_filter_by_school(self, auth_client: AsyncClient):
        """Test filtering students by school."""
        # Create two schools
        school1 = await auth_client.post("/api/v1/schools", json={"name": "School 1"})
        school2 = await auth_client.post("/api/v1/schools", json={"name": "School 2"})
        school1_id = school1.json()["id"]
        school2_id = school2.json()["id"]

        # Create grades for each school
        grade1_id = await self.create_grade_for_school(auth_client, school1_id, "Grade 1")
        grade2_id = await self.create_grade_for_school(auth_client, school2_id, "Grade 2")

        # Create students in each school
        await auth_client.post(
            "/api/v1/students",
            json={"first_name": "S1", "last_name": "Student", "school_id": school1_id, "grade_id": grade1_id},
        )
        await auth_client.post(
            "/api/v1/students",
            json={"first_name": "S2", "last_name": "Student", "school_id": school2_id, "grade_id": grade2_id},
        )

        response = await auth_client.get(f"/api/v1/students?school_id={school1_id}")

        assert response.status_code == 200
        data = response.json()
        for student in data["items"]:
            assert student["school_id"] == school1_id

    @pytest.mark.asyncio
    async def test_get_student_by_id(self, auth_client: AsyncClient, school_id: str, grade_id: str):
        """Test getting a student by ID."""
        # Create a student
        create_response = await auth_client.post(
            "/api/v1/students",
            json={
                "first_name": "Get",
                "last_name": "ById",
                "school_id": school_id,
                "grade_id": grade_id,
            },
        )
        student_id = create_response.json()["id"]

        response = await auth_client.get(f"/api/v1/students/{student_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == student_id
        assert data["first_name"] == "Get"

    @pytest.mark.asyncio
    async def test_update_student(self, auth_client: AsyncClient, school_id: str, grade_id: str):
        """Test updating a student."""
        # Create a student
        create_response = await auth_client.post(
            "/api/v1/students",
            json={
                "first_name": "Original",
                "last_name": "Name",
                "school_id": school_id,
                "grade_id": grade_id,
            },
        )
        student_id = create_response.json()["id"]

        # Create another grade to update to
        new_grade = await auth_client.post(
            "/api/v1/grades",
            json={"name": "6th Grade", "monthly_fee": 550.00, "school_id": school_id},
        )
        new_grade_id = new_grade.json()["id"]

        response = await auth_client.put(
            f"/api/v1/students/{student_id}",
            json={"first_name": "Updated", "grade_id": new_grade_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["grade_id"] == new_grade_id

    @pytest.mark.asyncio
    async def test_delete_student(self, auth_client: AsyncClient, school_id: str, grade_id: str):
        """Test soft deleting a student."""
        # Create a student
        create_response = await auth_client.post(
            "/api/v1/students",
            json={
                "first_name": "ToDelete",
                "last_name": "Student",
                "school_id": school_id,
                "grade_id": grade_id,
            },
        )
        student_id = create_response.json()["id"]

        response = await auth_client.delete(f"/api/v1/students/{student_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
