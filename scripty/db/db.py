"""
This module contains the database connection for the scripty api.
"""

from typing import Generator
from requests import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from scripty.models.script import Base

# Create an in-memory SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///data/db.sqlite3"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Get a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
