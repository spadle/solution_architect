import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_modes(client: AsyncClient):
    response = await client.get("/api/modes")
    assert response.status_code == 200
    modes = response.json()
    assert len(modes) >= 5
    assert modes[0]["id"] == "software_architecture"


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient):
    response = await client.post(
        "/api/sessions",
        json={"mode_id": "software_architecture", "title": "Test Session"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["mode_id"] == "software_architecture"
    assert data["title"] == "Test Session"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient):
    # Create a session first
    await client.post(
        "/api/sessions",
        json={"mode_id": "api_design"},
    )
    response = await client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) >= 1


@pytest.mark.asyncio
async def test_delete_session(client: AsyncClient):
    create_response = await client.post(
        "/api/sessions",
        json={"mode_id": "software_architecture"},
    )
    session_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/sessions/{session_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/sessions/{session_id}")
    assert get_response.status_code == 404
