import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Uses SQLite locally for the hackathon (creates a local file named 'ledgermind.db')
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ledgermind.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency to get DB session in FastAPI routes
def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()
