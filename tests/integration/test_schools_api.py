"""Integration tests for Schools API endpoints."""

import pytest
from httpx import AsyncClient


class TestSchoolsCRUD:
    """Test Schools CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_school(self, client: AsyncClient):
        """Test creating a new school."""
        school_data = {
            "name": "Test School",
            "address": "123 Test Street",
            "phone": "+1234567890",
            "email": "test@school.com",
        }

        response = await client.post("/api/v1/schools", json=school_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == school_data["name"]
        assert data["email"] == school_data["email"]
        assert data["is_active"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_school_minimal(self, client: AsyncClient):
        """Test creating school with only required fields."""
        school_data = {"name": "Minimal School"}

        response = await client.post("/api/v1/schools", json=school_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal School"
        assert data["address"] is None
        assert data["phone"] is None

    @pytest.mark.asyncio
    async def test_create_school_invalid_email(self, client: AsyncClient):
        """Test creating school with invalid email fails."""
        school_data = {
            "name": "Bad Email School",
            "email": "not-an-email",
        }

        response = await client.post("/api/v1/schools", json=school_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_list_schools(self, client: AsyncClient):
        """Test listing schools with pagination."""
        # Create some schools first
        for i in range(3):
            await client.post("/api/v1/schools", json={"name": f"School {i}"})

        response = await client.get("/api/v1/schools?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_get_school_by_id(self, client: AsyncClient):
        """Test getting a school by ID."""
        # Create a school
        create_response = await client.post(
            "/api/v1/schools", json={"name": "Get By ID School"}
        )
        school_id = create_response.json()["id"]

        # Get the school
        response = await client.get(f"/api/v1/schools/{school_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == school_id
        assert data["name"] == "Get By ID School"

    @pytest.mark.asyncio
    async def test_get_school_not_found(self, client: AsyncClient):
        """Test getting non-existent school returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await client.get(f"/api/v1/schools/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_school(self, client: AsyncClient):
        """Test updating a school."""
        # Create a school
        create_response = await client.post(
            "/api/v1/schools", json={"name": "Original Name"}
        )
        school_id = create_response.json()["id"]

        # Update the school
        response = await client.put(
            f"/api/v1/schools/{school_id}",
            json={"name": "Updated Name", "phone": "+9876543210"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["phone"] == "+9876543210"

    @pytest.mark.asyncio
    async def test_delete_school(self, client: AsyncClient):
        """Test soft deleting a school."""
        # Create a school
        create_response = await client.post(
            "/api/v1/schools", json={"name": "To Delete School"}
        )
        school_id = create_response.json()["id"]

        # Delete the school
        response = await client.delete(f"/api/v1/schools/{school_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False


class TestSchoolStudents:
    """Test school students listing."""

    @pytest.mark.asyncio
    async def test_list_school_students_empty(self, client: AsyncClient):
        """Test listing students for school with no students."""
        # Create a school
        create_response = await client.post(
            "/api/v1/schools", json={"name": "Empty School"}
        )
        school_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/schools/{school_id}/students")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_school_students(self, client: AsyncClient):
        """Test listing students for a school."""
        # Create a school
        school_response = await client.post(
            "/api/v1/schools", json={"name": "School With Students"}
        )
        school_id = school_response.json()["id"]

        # Create students
        for i in range(2):
            await client.post(
                "/api/v1/students",
                json={
                    "first_name": f"Student{i}",
                    "last_name": "Test",
                    "school_id": school_id,
                },
            )

        response = await client.get(f"/api/v1/schools/{school_id}/students")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
