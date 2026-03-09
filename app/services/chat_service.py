import json
from typing import Optional

from sqlmodel import select

from app.db import get_session
from app.models import Message


def parse_incoming_message(raw: str) -> tuple[str, Optional[str]]:
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            text = str(data.get("msg", "")).strip()
            recipient = str(data.get("to", "")).strip() or None
            if text:
                return text, recipient
    except json.JSONDecodeError:
        pass

    if raw.startswith("/w "):
        parts = raw.split(maxsplit=2)
        if len(parts) == 3:
            recipient = parts[1].strip() or None
            text = parts[2].strip()
            return text, recipient
    return raw.strip(), None


def save_message(
    room: str,
    sender: str,
    text: str,
    recipient: Optional[str] = None,
) -> Message:
    with get_session() as session:
        message = Message(room=room, sender=sender, recipient=recipient, text=text)
        session.add(message)
        session.commit()
        session.refresh(message)
        return message


def get_room_history(room: str, limit: int, user: Optional[str] = None) -> list[Message]:
    statement = select(Message).where(Message.room == room)
    with get_session() as session:
        messages = list(session.exec(statement).all())

    if user:
        visible_messages = []
        for msg in messages:
            is_public = msg.recipient is None
            is_participant = msg.sender == user or msg.recipient == user
            if is_public or is_participant:
                visible_messages.append(msg)
        messages = visible_messages

    messages.sort(key=lambda msg: msg.id or 0)
    if len(messages) > limit:
        return messages[-limit:]
    return messages
