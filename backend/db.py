import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Get Neon DB connection string from environment
raw_url = os.getenv("DATABASE_URL")

# Make sure to replace "postgres://" with psycopg3 driver string
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql+psycopg://", 1)

SQLALCHEMY_DATABASE_URL = raw_url

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)