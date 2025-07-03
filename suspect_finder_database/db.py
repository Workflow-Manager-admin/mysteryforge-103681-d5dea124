"""
Database engine and session management for Suspect Finder.
Reads database URL from environment variable DATABASE_URL or .env file.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load variables from .env if available
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///suspect_finder.db")

engine = create_engine(DATABASE_URL, future=True, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Dependency for use in FastAPI or scripts
# PUBLIC_INTERFACE
def get_db():
    """Yields a SQLAlchemy DB session for use in dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
