"""
Deterministic Chatbot API — plain HTTP, no AI, no WebSockets.

POST /api/chatbot/message  {"text": "..."} or {"intent": "...", "entity": {...}}
                           Accepts optional "lang": "hi" | "en" (default "hi")
                           -> {"reply", "source", "chips"}
GET  /api/chatbot/menu     Accepts optional query param ?lang=hi|en (default "hi")
                           -> role-specific top-level chips for the empty state
"""

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import rate_limit
from app.services.chatbot_engine import (
    handle_message,
    handle_public_message,
    menu_chips,
    menu_chips_public,
)
from app.tenancy import TenantContext, get_tenant

router = APIRouter()


def enforce_public_rate_limit(request: Request, db: Session = Depends(get_db)) -> None:
    """Per-IP throttle for the unauthenticated /public endpoints (DB-backed —
    see app/services/rate_limit.py for why in-memory counters don't work on
    Vercel's serverless functions)."""
    ip = rate_limit.client_ip(request)
    if not rate_limit.check_and_increment(db, ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment and try again.",
            headers={"Retry-After": "60"},
        )


class Chip(BaseModel):
    label: str
    intent: str
    entity: Optional[Dict[str, Any]] = None


class MessageIn(BaseModel):
    text: Optional[str] = Field(default=None, max_length=300)
    intent: Optional[str] = None
    entity: Optional[Dict[str, Any]] = None
    lang: Literal["hi", "en"] = "hi"


class MessageOut(BaseModel):
    reply: str
    source: str
    chips: List[Chip]


class MenuOut(BaseModel):
    chips: List[Chip]


@router.post("/message", response_model=MessageOut)
def post_message(
    payload: MessageIn,
    ctx: TenantContext = Depends(get_tenant),
):
    """Answer a free-text question or a structured chip click. Deterministic:
    the same input always produces the same reply. get_tenant arms RLS as a
    backstop; the data handlers additionally filter inline by institution.
    lang defaults to 'hi' (Hindi); pass lang='en' for English responses."""
    if not (payload.text and payload.text.strip()) and not payload.intent:
        raise HTTPException(status_code=400, detail="Provide 'text' or 'intent'.")
    return handle_message(
        ctx.db,
        ctx.user,
        text=payload.text,
        intent_id=payload.intent,
        entity=payload.entity,
        lang=payload.lang,
    )


@router.get("/menu", response_model=MenuOut)
def get_menu(
    current_user: User = Depends(get_current_user),
    lang: Literal["hi", "en"] = Query(default="hi"),
):
    """Role-specific top-level chips for the chat empty state.
    lang defaults to 'hi' (Hindi); pass ?lang=en for English chip labels."""
    return {"chips": menu_chips(current_user.role, lang)}


# ---------------------------------------------------------------------------
# Public (unauthenticated) endpoints — for the marketing homepage. No login,
# no TenantContext/RLS (there's no tenant), rate-limited per IP. Only
# public=True intents are reachable (enforced in handle_public_message /
# menu_chips_public) — this is what keeps every account-specific answer
# (fee balance, exam dates, results, collections, ...) behind login.
# ---------------------------------------------------------------------------
class PublicEntity(BaseModel):
    course_id: Optional[str] = None


class PublicMessageIn(BaseModel):
    text: Optional[str] = Field(default=None, max_length=300)
    intent: Optional[str] = None
    entity: Optional[PublicEntity] = None
    lang: Literal["hi", "en"] = "en"


@router.post("/public/message", response_model=MessageOut)
def post_public_message(
    payload: PublicMessageIn,
    db: Session = Depends(get_db),
    _rate_limited: None = Depends(enforce_public_rate_limit),
):
    """Same contract as POST /message, but for anonymous visitors. Restricted
    to a small whitelist of public intents (general FAQ + live course/fee
    lookup) — see app/config_data/intents.py `public=True`."""
    if not (payload.text and payload.text.strip()) and not payload.intent:
        raise HTTPException(status_code=400, detail="Provide 'text' or 'intent'.")
    return handle_public_message(
        db,
        text=payload.text,
        intent_id=payload.intent,
        entity=payload.entity.model_dump() if payload.entity else None,
        lang=payload.lang,
    )


@router.get("/public/menu", response_model=MenuOut)
def get_public_menu(
    lang: Literal["hi", "en"] = Query(default="en"),
    db: Session = Depends(get_db),
    _rate_limited: None = Depends(enforce_public_rate_limit),
):
    """Top-level chips for the anonymous chat empty state."""
    return {"chips": menu_chips_public(lang)}
