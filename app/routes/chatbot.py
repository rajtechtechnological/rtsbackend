"""
Deterministic Chatbot API — plain HTTP, no AI, no WebSockets.

POST /api/chatbot/message  {"text": "..."} or {"intent": "...", "entity": {...}}
                           -> {"reply", "source", "chips"}
GET  /api/chatbot/menu     -> role-specific top-level chips for the empty state
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.chatbot_engine import handle_message, menu_chips

router = APIRouter()


class Chip(BaseModel):
    label: str
    intent: str
    entity: Optional[Dict[str, Any]] = None


class MessageIn(BaseModel):
    text: Optional[str] = None
    intent: Optional[str] = None
    entity: Optional[Dict[str, Any]] = None


class MessageOut(BaseModel):
    reply: str
    source: str
    chips: List[Chip]


class MenuOut(BaseModel):
    chips: List[Chip]


@router.post("/message", response_model=MessageOut)
def post_message(
    payload: MessageIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Answer a free-text question or a structured chip click. Deterministic:
    the same input always produces the same reply."""
    if not (payload.text and payload.text.strip()) and not payload.intent:
        raise HTTPException(status_code=400, detail="Provide 'text' or 'intent'.")
    return handle_message(
        db,
        current_user,
        text=payload.text,
        intent_id=payload.intent,
        entity=payload.entity,
    )


@router.get("/menu", response_model=MenuOut)
def get_menu(current_user: User = Depends(get_current_user)):
    """Role-specific top-level chips for the chat empty state."""
    return {"chips": menu_chips(current_user.role)}
