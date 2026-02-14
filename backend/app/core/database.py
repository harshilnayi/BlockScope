"""
BlockScope Database Configuration
Provides database connection, session management, and base model
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Try to import settings, fall back to environment variables
try:
    from app.core.config import settings

    DATABASE_URL = settings.database_url_sync
    DB_POOL_SIZE = settings.DB_POOL_SIZE
    DB_MAX_OVERFLOW = settings.DB_MAX_OVERFLOW
    DB_POOL_TIMEOUT = settings.DB_POOL_TIMEOUT
    DB_POOL_RECYCLE = settings.DB_POOL_RECYCLE
    DB_ECHO = settings.DB_ECHO

except ImportError:
    # Fallback to environment variables if config not available
    import os

    from dotenv import load_dotenv

    load_dotenv()

    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://blockscope_dev:dev_password@localhost:5432/blockscope_dev"
    )
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    DB_ECHO = os.getenv("DB_ECHO", "False").lower() == "true"

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    echo=DB_ECHO,
    pool_pre_ping=True,  # Verify connections before using
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


# Dependency for FastAPI
def get_db():
    """
    Database session dependency for FastAPI.

    Yields a database session and ensures it's closed after use.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper function to test database connection
def test_connection():
    """
    Test database connection.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


# Initialize database tables
def init_db():
    """
    Initialize database tables.

    Creates all tables defined by models that inherit from Base.
    """
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    # Test connection when run directly
    print("Testing database connection...")
    if test_connection():
        print("✅ Database connection successful!")
    else:
        print("❌ Database connection failed!")
