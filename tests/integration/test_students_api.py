"""Integration tests for Students API endpoints."""

import pytest
from httpx import AsyncClient


class TestStudentsCRUD:
    """Test Students CRUD operations."""

    @pytest.fixture
    async def school_id(self, client: AsyncClient) -> str:
        """Create a school and return its ID."""
        response = await client.post(
            "/api/v1/schools", json={"name": "Test School for Students"}
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_create_student(self, client: AsyncClient, school_id: str):
        """Test creating a new student."""
        student_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@email.com",
            "grade": "5th Grade",
            "school_id": school_id,
        }

        response = await client.post("/api/v1/students", json=student_data)

        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["school_id"] == school_id
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_student_invalid_school(self, client: AsyncClient):
        """Test creating student with non-existent school fails."""
        fake_school_id = "00000000-0000-0000-0000-000000000000"
        student_data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "school_id": fake_school_id,
        }

        response = await client.post("/api/v1/students", json=student_data)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_students(self, client: AsyncClient, school_id: str):
        """Test listing students with pagination."""
        # Create students
        for i in range(3):
            await client.post(
                "/api/v1/students",
                json={
                    "first_name": f"Student{i}",
                    "last_name": "Test",
                    "school_id": school_id,
                },
            )

        response = await client.get("/api/v1/students?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_list_students_filter_by_school(self, client: AsyncClient):
        """Test filtering students by school."""
        # Create two schools
        school1 = await client.post("/api/v1/schools", json={"name": "School 1"})
        school2 = await client.post("/api/v1/schools", json={"name": "School 2"})
        school1_id = school1.json()["id"]
        school2_id = school2.json()["id"]

        # Create students in each school
        await client.post(
            "/api/v1/students",
            json={"first_name": "S1", "last_name": "Student", "school_id": school1_id},
        )
        await client.post(
            "/api/v1/students",
            json={"first_name": "S2", "last_name": "Student", "school_id": school2_id},
        )

        response = await client.get(f"/api/v1/students?school_id={school1_id}")

        assert response.status_code == 200
        data = response.json()
        for student in data["items"]:
            assert student["school_id"] == school1_id

    @pytest.mark.asyncio
    async def test_get_student_by_id(self, client: AsyncClient, school_id: str):
        """Test getting a student by ID."""
        # Create a student
        create_response = await client.post(
            "/api/v1/students",
            json={
                "first_name": "Get",
                "last_name": "ById",
                "school_id": school_id,
            },
        )
        student_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/students/{student_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == student_id
        assert data["first_name"] == "Get"

    @pytest.mark.asyncio
    async def test_update_student(self, client: AsyncClient, school_id: str):
        """Test updating a student."""
        # Create a student
        create_response = await client.post(
            "/api/v1/students",
            json={
                "first_name": "Original",
                "last_name": "Name",
                "school_id": school_id,
            },
        )
        student_id = create_response.json()["id"]

        response = await client.put(
            f"/api/v1/students/{student_id}",
            json={"first_name": "Updated", "grade": "6th Grade"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["grade"] == "6th Grade"

    @pytest.mark.asyncio
    async def test_delete_student(self, client: AsyncClient, school_id: str):
        """Test soft deleting a student."""
        # Create a student
        create_response = await client.post(
            "/api/v1/students",
            json={
                "first_name": "ToDelete",
                "last_name": "Student",
                "school_id": school_id,
            },
        )
        student_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/students/{student_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
