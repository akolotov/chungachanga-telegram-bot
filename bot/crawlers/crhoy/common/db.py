"""Database connection and session management for CRHoy crawler."""

from contextlib import contextmanager
from typing import Generator, Optional
import logging

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from .logger import get_component_logger
from .models import Base

logger = get_component_logger("db")

class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, database_url: str):
        """
        Initialize database manager.

        Args:
            database_url: SQLAlchemy database URL
        """
        self._engine: Optional[Engine] = None
        self._session_factory = None
        self._database_url = database_url
        
    def initialize(self, echo: bool = False) -> None:
        """
        Initialize database connection and create tables if they don't exist.

        Args:
            echo: If True, enables SQLAlchemy query logging
        """
        try:
            self._engine = create_engine(
                self._database_url,
                echo=echo,
                pool_pre_ping=True  # Enables connection health checks
            )
            
            # Create all tables if they don't exist
            Base.metadata.create_all(self._engine)
            
            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                expire_on_commit=False
            )
            
            logger.info("Database connection initialized successfully")
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        
        Yields:
            SQLAlchemy session

        Raises:
            SQLAlchemyError: If there's a database error
        """
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
            
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error during database transaction: {e}")
            raise
        finally:
            session.close()
    
    def close(self) -> None:
        """Close database connection pool."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connection closed")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def init_db(database_url: str, echo: bool = False) -> None:
    """
    Initialize global database manager.

    Args:
        database_url: SQLAlchemy database URL
        echo: If True, enables SQLAlchemy query logging
    """
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    _db_manager.initialize(echo=echo)


def get_db() -> DatabaseManager:
    """
    Get global database manager instance.

    Returns:
        DatabaseManager instance

    Raises:
        RuntimeError: If database is not initialized
    """
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db_manager


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Convenience context manager for database sessions using global manager.

    Yields:
        SQLAlchemy session

    Raises:
        RuntimeError: If database is not initialized
        SQLAlchemyError: If there's a database error
    """
    with get_db().session() as session:
        yield session


def cleanup_database(database_url: str) -> None:
    """
    Clean up the database by dropping and recreating all tables.

    Args:
        database_url: SQLAlchemy database URL
    """
    engine = create_engine(database_url)
    logger.info("Dropping all tables...")
    Base.metadata.drop_all(engine)
    logger.info("Recreating all tables...")
    Base.metadata.create_all(engine)
    engine.dispose()
    logger.info("Database cleanup completed successfully")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database management utilities")
    parser.add_argument(
        "--database-url",
        required=True,
        help="SQLAlchemy database URL"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up the database by dropping and recreating all tables"
    )
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_database(args.database_url)
    else:
        parser.print_help()
