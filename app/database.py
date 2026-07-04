from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings

# URL selection (docs/01 §2 / §7):
# - prod: DATABASE_URL = Supabase transaction-mode pooler URL (Supavisor,
#   port 6543) — set on Vercel.
# - dev:  LOCAL_DB_URL = local Postgres.
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL or settings.LOCAL_DB_URL

if settings.SERVERLESS:
    # Vercel Python functions are short-lived and may run many instances in
    # parallel; none of them may hold a persistent Postgres connection or the
    # free-tier connection limit is exhausted. NullPool opens a connection per
    # checkout and closes it on release — the *real* pooling happens
    # server-side in Supavisor (transaction mode, port 6543), which also means
    # session state (e.g. non-transaction-scoped SET) must not be relied on
    # across transactions. pool_pre_ping is disabled: every NullPool checkout
    # is a fresh connection, so the ping would only add a wasted round-trip.
    engine = create_engine(SQLALCHEMY_DATABASE_URL, poolclass=NullPool)
else:
    # Long-lived dev server: normal pool; pre-ping recovers from Postgres
    # restarts without "server closed the connection unexpectedly" errors.
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Dependency for routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
