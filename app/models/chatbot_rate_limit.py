from sqlalchemy import Column, String, Integer, BigInteger, Date, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ChatbotRateLimit(Base):
    """
    Per-IP throttle for the public (unauthenticated) chatbot endpoints.

    DB-backed, not in-memory: the backend runs as a Vercel serverless
    function, so an in-process counter would reset every cold start (same
    reasoning as the login-lockout columns in migration 0002). ip_hash is
    sha256(ip + JWT_SECRET_KEY) — raw IPs are never stored.
    """
    __tablename__ = "chatbot_rate_limits"

    ip_hash = Column(String, primary_key=True)
    minute_bucket = Column(BigInteger, nullable=False)
    minute_count = Column(Integer, nullable=False, server_default="0")
    day_bucket = Column(Date, nullable=False)
    day_count = Column(Integer, nullable=False, server_default="0")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
