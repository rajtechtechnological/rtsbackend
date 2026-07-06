"""
DB-backed per-IP rate limiter for the public (unauthenticated) chatbot
endpoints. In-memory counters would reset on every serverless cold start
(same reasoning as the login-lockout columns added in migration 0002), so
counts live in the chatbot_rate_limits table instead.
"""

import hashlib
import time
from datetime import date

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import settings
from app.models.chatbot_rate_limit import ChatbotRateLimit

PER_MINUTE_LIMIT = 15
PER_DAY_LIMIT = 200


def client_ip(request: Request) -> str:
    """Best-effort caller IP. Vercel sets X-Forwarded-For; the first entry
    is the original client (subsequent entries are intermediate proxies)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _hash_ip(ip: str) -> str:
    # JWT_SECRET_KEY doubles as the pepper so raw IPs are never stored.
    return hashlib.sha256(f"{ip}:{settings.JWT_SECRET_KEY}".encode()).hexdigest()


def check_and_increment(
    db: Session,
    ip: str,
    per_minute: int = PER_MINUTE_LIMIT,
    per_day: int = PER_DAY_LIMIT,
) -> bool:
    """Returns True if this request is allowed (and records it), False if the
    caller is over either cap. Row-locked so concurrent requests from the
    same IP can't race past the limit."""
    ip_hash = _hash_ip(ip)
    now = time.time()
    minute_bucket = int(now // 60)
    today = date.today()

    row = (
        db.query(ChatbotRateLimit)
        .filter(ChatbotRateLimit.ip_hash == ip_hash)
        .with_for_update()
        .first()
    )

    if row is None:
        db.add(
            ChatbotRateLimit(
                ip_hash=ip_hash,
                minute_bucket=minute_bucket,
                minute_count=1,
                day_bucket=today,
                day_count=1,
            )
        )
        db.commit()
        return True

    if row.day_bucket != today:
        row.day_bucket = today
        row.day_count = 0
    if row.minute_bucket != minute_bucket:
        row.minute_bucket = minute_bucket
        row.minute_count = 0

    if row.minute_count >= per_minute or row.day_count >= per_day:
        db.commit()  # persist any bucket reset above even on rejection
        return False

    row.minute_count += 1
    row.day_count += 1
    db.commit()
    return True
