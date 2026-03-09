from datetime import datetime, timezone

from sqlalchemy import true
from sqlmodel import select

from app.db import get_session
from app.models import RoomParticipant


def set_participant_online(room: str, username: str, is_online: bool) -> RoomParticipant:
    now = datetime.now(timezone.utc)
    statement = select(RoomParticipant).where(
        RoomParticipant.room == room,
        RoomParticipant.username == username,
    )
    with get_session() as session:
        participant = session.exec(statement).first()
        if participant is None:
            participant = RoomParticipant(
                room=room,
                username=username,
                is_online=is_online,
                joined_at=now,
                last_seen_at=now,
            )
            session.add(participant)
        else:
            participant.is_online = is_online
            participant.last_seen_at = now
            session.add(participant)

        session.commit()
        session.refresh(participant)
        return participant


def get_online_users(room: str) -> list[str]:
    statement = (
        select(RoomParticipant.username)
        .where(RoomParticipant.room == room, RoomParticipant.is_online == true())
        .order_by(RoomParticipant.username)
    )
    with get_session() as session:
        return list(session.exec(statement).all())
