"""Database restore tools for CRHoy crawler.

Provides functionality to import database tables from JSON files while preserving
relationships and data integrity.
"""

import json
import traceback
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Type

from sqlalchemy import Integer, String, Boolean, DateTime, Date
from sqlalchemy.orm import Session, DeclarativeBase
from sqlalchemy.dialects.postgresql import DATERANGE
from sqlalchemy.exc import SQLAlchemyError

from ..common.db import db_session, init_db, Base
from ..common.models import (
    CRHoyNews,
    CRHoyCategoriesCatalog,
    CRHoyNewsCategories,
    CRHoyMetadata,
    MissedCRHoyMetadata,
    CRHoySmartCategories,
    CRHoySummary,
    CRHoyNotifierNews,
)
from ..settings import settings

# Tables to import, in order of dependencies
TABLES_TO_IMPORT = [
    CRHoyCategoriesCatalog,  # No dependencies
    CRHoyNews,  # No dependencies
    CRHoyNewsCategories,  # Depends on CRHoyNews and CRHoyCategoriesCatalog
    CRHoyMetadata,  # No dependencies
    MissedCRHoyMetadata,  # No dependencies
    CRHoySmartCategories,  # No dependencies
    CRHoySummary,  # Depends on CRHoyNews
    CRHoyNotifierNews,  # Depends on CRHoyNews and CRHoySmartCategories
]

def get_python_type(column_type: Any) -> Type:
    """Get the appropriate Python type for a SQLAlchemy column type."""
    if isinstance(column_type, (String, DATERANGE)):
        return str
    if isinstance(column_type, Integer):
        return int
    if isinstance(column_type, Boolean):
        return bool
    if isinstance(column_type, DateTime):
        return datetime
    if isinstance(column_type, Date):
        return date
    # Default to string for unknown types
    return str

def deserialize_value(value: Any, column_type: Any) -> Any:
    """Deserialize JSON data to appropriate Python/SQLAlchemy types."""
    if value is None:
        return None
        
    if isinstance(column_type, DateTime):
        return datetime.fromisoformat(value)
    if isinstance(column_type, Date):
        return date.fromisoformat(value)
    if isinstance(column_type, DATERANGE):
        from psycopg2.extras import DateRange
        try:
            lower = date.fromisoformat(value['lower']) if value.get('lower') else None
            upper = date.fromisoformat(value['upper']) if value.get('upper') else None
            return DateRange(lower, upper)
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid DateRange format: {value}. Error: {e}")
    if isinstance(column_type, Boolean):
        return bool(value)
    if isinstance(column_type, Integer):
        return int(value)
    return value

def import_table(session: Session, model: Type[DeclarativeBase], records: List[Dict[str, Any]]) -> None:
    """
    Import records into a table.

    Args:
        session: Database session
        model: SQLAlchemy model class
        records: List of dictionaries containing the table data
    """
    try:
        # Get column types directly from the model
        column_types = {
            column.key: column.type
            for column in model.__table__.columns
        }
        
        # Create new instances and add them to session
        for i, record in enumerate(records):
            try:
                # Deserialize values
                deserialized_data = {
                    key: deserialize_value(value, column_types.get(key))
                    for key, value in record.items()
                }
                
                # Create and add instance
                instance = model(**deserialized_data)
                session.add(instance)
            except Exception as e:
                print(f"Error processing record {i} in table {model.__tablename__}:")
                print(f"Record data: {record}")
                print(f"Error: {str(e)}")
                raise
                
    except Exception as e:
        print(f"Error importing table {model.__tablename__}:")
        print(traceback.format_exc())
        raise

def import_database(input_dir: Path, clear_existing: bool = False) -> None:
    """
    Initialize database and import all configured tables from JSON files.

    Args:
        input_dir: Directory containing the JSON files
        clear_existing: If True, delete existing records before import
    """
    # Initialize database and create tables
    print("Initializing database...")
    init_db(settings.database_url)
    
    print(f"Starting data import from {input_dir}...")
    with db_session() as session:
        try:
            for model in TABLES_TO_IMPORT:
                table_name = model.__tablename__
                input_file = input_dir / f"{table_name}.json"
                
                if not input_file.exists():
                    print(f"Warning: No data file found for table {table_name}")
                    continue
                
                print(f"Processing table {table_name}...")
                
                # Read records from JSON file
                try:
                    with open(input_file, 'r', encoding='utf-8') as f:
                        records = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"Error reading {input_file}: Invalid JSON format")
                    raise
                except Exception as e:
                    print(f"Error reading {input_file}: {str(e)}")
                    raise
                
                # Optionally clear existing records
                if clear_existing:
                    print(f"Clearing existing records from {table_name}")
                    session.query(model).delete()
                
                # Import records
                import_table(session, model, records)
                
                print(f"Imported {len(records)} records into {table_name}")
                
            print("All tables imported successfully")
            print("Committing changes...")
            session.commit()
            print("Database import completed successfully")
            
        except Exception as e:
            print("Rolling back due to error...")
            session.rollback()
            raise

if __name__ == "__main__":
    import argparse
    from pydantic import ValidationError
    
    try:
        parser = argparse.ArgumentParser(description="Import CRHoy database tables")
        parser.add_argument(
            "--input-dir",
            type=Path,
            default=settings.data_dir / "backup",
            help=f"Directory containing the JSON files to import (default: {settings.data_dir}/backup)"
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing records before import"
        )
        
        args = parser.parse_args()
        import_database(args.input_dir, args.clear_existing)
        
    except ValidationError as e:
        print("Error in settings validation:")
        print(e)
        exit(1)
    except Exception as e:
        print(f"Error during database import: {str(e)}")
        print(traceback.format_exc())
        exit(1) 