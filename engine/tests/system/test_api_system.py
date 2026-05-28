from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def unique_login(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_user(prefix: str = "system-api") -> tuple[str, str]:
    login = unique_login(prefix)
    response = client.post(
        "/auth/register",
        json={"login": login, "password": "password123"},
    )
    assert response.status_code == 200, response.text
    return login, response.json()["access_token"]


def test_auth_generation_history_lifecycle():
    login, token = register_user()

    profile_response = client.get("/auth/me", headers=auth_headers(token))
    assert profile_response.status_code == 200
    assert profile_response.json()["login"] == login

    generate_response = client.post(
        "/generate",
        json={
            "prompt": "хочу встроенную технику и посудомойку 60 см",
            "module_options": {
                "room": {
                    "layout_shape": "straight",
                    "wall_length_mm": 3000,
                    "kitchen_height_mm": 2700,
                    "wall_cabinets_enabled": True,
                    "mezzanine_enabled": True,
                },
                "optional": {"dishwasher": {"enabled": True}},
                "locked": {},
            },
        },
    )
    assert generate_response.status_code == 200, generate_response.text
    generated = generate_response.json()
    assert "<svg" in generated["front_view_svg"]
    assert generated["generated_layout"]["modules"]

    create_history_response = client.post(
        "/generations",
        headers=auth_headers(token),
        json={
            "title": "Системная проверка прямой кухни",
            "shape": "straight",
            "width_label": "3000 мм",
            "auto_fields": ["варочная", "мойка", "верхние шкафы"],
            "locked_fields": ["посудомоечная машина"],
            "adjustment_count": len(
                generated["generated_layout"].get("size_adjustments", [])
            ),
            "details": {
                "module_options": generated["module_options"],
                "generated_layout": generated["generated_layout"],
            },
        },
    )
    assert create_history_response.status_code == 200, create_history_response.text
    generation_id = create_history_response.json()["id"]

    list_response = client.get("/generations", headers=auth_headers(token))
    assert list_response.status_code == 200
    assert any(item["id"] == generation_id for item in list_response.json())

    delete_response = client.delete(
        f"/generations/{generation_id}",
        headers=auth_headers(token),
    )
    assert delete_response.status_code == 200

    empty_list_response = client.get("/generations", headers=auth_headers(token))
    assert empty_list_response.status_code == 200
    assert all(item["id"] != generation_id for item in empty_list_response.json())


def test_corner_generation_and_password_change():
    login, token = register_user("corner-api")

    response = client.post(
        "/generate",
        json={
            "prompt": "угловая кухня, подъемные верхние шкафы",
            "module_options": {
                "room": {
                    "layout_shape": "corner",
                    "side_1_width_mm": 3000,
                    "side_2_width_mm": 2300,
                    "wall_length_mm": 3000,
                    "kitchen_height_mm": 2700,
                    "wall_cabinets_enabled": True,
                    "mezzanine_enabled": True,
                    "upper_cabinet_opening": "lift",
                },
                "locked": {"room.layout_shape": True, "room.upper_cabinet_opening": True},
            },
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["generated_layout"]["shape"] == "corner"
    assert "<svg" in payload["side_view_svg"]

    change_response = client.post(
        "/auth/change-password",
        headers=auth_headers(token),
        json={"new_password": "new-password-123"},
    )
    assert change_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={"login": login, "password": "new-password-123"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["login"] == login


def test_history_requires_authorization():
    response = client.get("/generations")
    assert response.status_code == 401
