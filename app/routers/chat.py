import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from app.config import get_settings
from app.models import User
from app.schemas import ChatMessageOut, RoomHistoryResponse
from app.services.auth_service import get_current_user, get_user_by_token
from app.services.chat_service import (
    get_room_history,
    parse_incoming_message,
    save_message,
)
from app.services.participant_service import get_online_users, set_participant_online

logger = logging.getLogger(__name__)
router = APIRouter()
rooms: dict[str, list[WebSocket]] = {}
client_users: dict[WebSocket, str] = {}
CurrentUser = Annotated[User, Depends(get_current_user)]


async def broadcast_presence(room: str) -> None:
    payload = json.dumps(
        {
            "type": "presence",
            "room": room,
            "users": get_online_users(room),
        },
        ensure_ascii=False,
    )
    dead = []
    for client in rooms.get(room, []):
        try:
            await client.send_text(payload)
        except Exception:
            dead.append(client)

    for client in dead:
        if client in rooms.get(room, []):
            rooms[room].remove(client)
        client_users.pop(client, None)


@router.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(get_settings().static_dir / "index.html")


@router.get("/history/{room}", response_model=RoomHistoryResponse)
def room_history(
    room: str,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
):
    messages = [
        ChatMessageOut(
            sender=msg.sender,
            recipient=msg.recipient,
            text=msg.text,
            created_at=msg.created_at,
        )
        for msg in get_room_history(room, limit, user=user.username)
    ]
    return RoomHistoryResponse(room=room, messages=messages)


@router.get("/participants/{room}")
def participants(room: str, _: CurrentUser):
    return {"room": room, "users": get_online_users(room)}


@router.websocket("/ws/{room}")
async def ws_chat(websocket: WebSocket, room: str):
    token = websocket.query_params.get("token", "").strip()
    user_model = get_user_by_token(token)
    if not user_model:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    username = user_model.username
    client_users[websocket] = username
    set_participant_online(room=room, username=username, is_online=True)

    if room not in rooms:
        rooms[room] = []
    rooms[room].append(websocket)
    logger.info("WebSocket connected room=%s user=%s clients=%s", room, username, len(rooms[room]))
    await broadcast_presence(room)

    try:
        while True:
            raw_message = await websocket.receive_text()
            text, recipient = parse_incoming_message(raw_message)
            if not text:
                continue

            sender = client_users.get(websocket, username)
            saved = save_message(room=room, sender=sender, text=text, recipient=recipient)
            payload = {
                "type": "message",
                "room": saved.room,
                "sender": saved.sender,
                "recipient": saved.recipient,
                "text": saved.text,
                "created_at": saved.created_at.isoformat(),
            }
            message = json.dumps(payload, ensure_ascii=False)
            logger.info("Message saved room=%s sender=%s recipient=%s", room, sender, recipient)

            dead = []
            for client in rooms[room]:
                try:
                    if recipient:
                        target = client_users.get(client, "")
                        if target not in {sender, recipient}:
                            continue
                    await client.send_text(message)
                except Exception:
                    dead.append(client)

            for client in dead:
                if client in rooms[room]:
                    rooms[room].remove(client)
                client_users.pop(client, None)
            if dead:
                await broadcast_presence(room)

    except WebSocketDisconnect:
        if websocket in rooms.get(room, []):
            rooms[room].remove(websocket)
        client_users.pop(websocket, None)
        still_online = any(client_users.get(client) == username for client in rooms.get(room, []))
        if not still_online:
            set_participant_online(room=room, username=username, is_online=False)
        logger.info("WebSocket disconnected room=%s clients=%s", room, len(rooms.get(room, [])))
        await broadcast_presence(room)
