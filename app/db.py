import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Get Neon connection string from env variable
raw_url = os.getenv("DATABASE_URL")

# Force psycopg driver
SQLALCHEMY_DATABASE_URL = raw_url.replace("postgres://", "postgresql+psycopg://")

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)