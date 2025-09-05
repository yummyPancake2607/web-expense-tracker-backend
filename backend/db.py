import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

raw_url = os.getenv("DATABASE_URL")

# Force psycopg3 instead of psycopg2
if raw_url and raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql+psycopg://", 1)
elif raw_url and raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(raw_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)