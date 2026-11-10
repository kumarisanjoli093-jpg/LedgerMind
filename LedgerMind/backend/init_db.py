from backend.database import Base, engine
import backend.models  # Ensures all tables are registered before creation


def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()