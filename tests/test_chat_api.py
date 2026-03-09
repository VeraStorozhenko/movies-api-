import json

from conftest import register_and_login

from app.services.chat_service import save_message


def receive_by_type(ws, expected_type: str, attempts: int = 6):
    for _ in range(attempts):
        payload = json.loads(ws.receive_text())
        if payload.get("type") == expected_type:
            return payload
    raise AssertionError(f"Did not receive payload type={expected_type}")


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_room_history_returns_saved_messages(client):
    alice_token, _ = register_and_login(client, "alice")
    register_and_login(client, "bob")

    save_message("general", "alice", "first")
    save_message("general", "bob", "second")

    response = client.get("/history/general?limit=10", headers=auth_headers(alice_token))
    assert response.status_code == 200

    data = response.json()
    assert data["room"] == "general"
    assert [m["text"] for m in data["messages"]][-2:] == ["first", "second"]


def test_websocket_message_is_broadcast_and_persisted(client):
    vera_token, _ = register_and_login(client, "vera")

    with client.websocket_connect(f"/ws/qa?token={vera_token}") as ws:
        receive_by_type(ws, "presence")
        ws.send_text(json.dumps({"msg": "ping"}))
        payload = receive_by_type(ws, "message")

    assert payload["type"] == "message"
    assert payload["room"] == "qa"
    assert payload["sender"] == "vera"
    assert payload["text"] == "ping"

    response = client.get("/history/qa?limit=10", headers=auth_headers(vera_token))
    assert response.status_code == 200
    messages = response.json()["messages"]
    assert any(m["sender"] == "vera" and m["text"] == "ping" for m in messages)


def test_private_message_visibility_and_delivery(client):
    alice_token, _ = register_and_login(client, "alice")
    bob_token, _ = register_and_login(client, "bob")
    eve_token, _ = register_and_login(client, "eve")

    with client.websocket_connect(f"/ws/pm?token={alice_token}") as ws_alice:
        receive_by_type(ws_alice, "presence")
        with client.websocket_connect(f"/ws/pm?token={bob_token}") as ws_bob:
            receive_by_type(ws_bob, "presence")
            receive_by_type(ws_alice, "presence")
            with client.websocket_connect(f"/ws/pm?token={eve_token}") as ws_eve:
                receive_by_type(ws_eve, "presence")
                receive_by_type(ws_alice, "presence")
                receive_by_type(ws_bob, "presence")

                ws_alice.send_text(json.dumps({"msg": "secret", "to": "bob"}))
                alice_payload = receive_by_type(ws_alice, "message")
                bob_payload = receive_by_type(ws_bob, "message")

                assert alice_payload["recipient"] == "bob"
                assert bob_payload["recipient"] == "bob"

                ws_eve.send_text(json.dumps({"msg": "probe"}))
                eve_payload = receive_by_type(ws_eve, "message")
                assert eve_payload["sender"] == "eve"
                assert eve_payload["text"] == "probe"

    alice_history = client.get("/history/pm?limit=20", headers=auth_headers(alice_token)).json()["messages"]
    bob_history = client.get("/history/pm?limit=20", headers=auth_headers(bob_token)).json()["messages"]
    eve_history = client.get("/history/pm?limit=20", headers=auth_headers(eve_token)).json()["messages"]

    assert any(m["sender"] == "alice" and m["recipient"] == "bob" for m in alice_history)
    assert any(m["sender"] == "alice" and m["recipient"] == "bob" for m in bob_history)
    assert not any(m.get("recipient") == "bob" and m["sender"] == "alice" for m in eve_history)


def test_presence_updates_for_room_users(client):
    alice_token, _ = register_and_login(client, "alice")
    bob_token, _ = register_and_login(client, "bob")

    with client.websocket_connect(f"/ws/presence?token={alice_token}") as ws_alice:
        first = receive_by_type(ws_alice, "presence")
        assert first["users"] == ["alice"]

        with client.websocket_connect(f"/ws/presence?token={bob_token}") as ws_bob:
            bob_view = receive_by_type(ws_bob, "presence")
            alice_view = receive_by_type(ws_alice, "presence")
            assert bob_view["users"] == ["alice", "bob"]
            assert alice_view["users"] == ["alice", "bob"]


def test_participants_endpoint_tracks_online_status(client):
    alice_token, _ = register_and_login(client, "alice")
    bob_token, _ = register_and_login(client, "bob")

    with client.websocket_connect(f"/ws/online?token={alice_token}") as ws_alice:
        receive_by_type(ws_alice, "presence")
        with client.websocket_connect(f"/ws/online?token={bob_token}") as ws_bob:
            receive_by_type(ws_bob, "presence")
            receive_by_type(ws_alice, "presence")
            response = client.get("/participants/online", headers=auth_headers(alice_token))
            assert response.status_code == 200
            assert response.json()["users"] == ["alice", "bob"]

    response = client.get("/participants/online", headers=auth_headers(alice_token))
    assert response.status_code == 200
    assert response.json()["users"] == []


def test_auth_flow_register_login_me_logout_refresh(client):
    access_token, refresh_token = register_and_login(client, "vera")

    me_response = client.get("/auth/me", headers=auth_headers(access_token))
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "vera"

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    new_access_token = refresh_response.json()["access_token"]
    assert new_access_token != access_token

    me_with_new_token = client.get("/auth/me", headers=auth_headers(new_access_token))
    assert me_with_new_token.status_code == 200

    logout_response = client.post(
        "/auth/logout",
        headers=auth_headers(new_access_token),
        json={"refresh_token": refresh_token},
    )
    assert logout_response.status_code == 200

    unauthorized = client.get("/auth/me", headers=auth_headers(new_access_token))
    assert unauthorized.status_code == 401

    refresh_after_logout = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_after_logout.status_code == 401
