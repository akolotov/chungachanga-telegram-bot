"""Database backup tools for CRHoy crawler.

Provides functionality to export database tables to JSON files while preserving
relationships and data integrity.
"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import inspect
from sqlalchemy.orm import Session, DeclarativeBase
from psycopg2.extras import DateRange

from ..common.db import db_session, init_db
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

# Tables to export, in order of dependencies
TABLES_TO_EXPORT = [
    CRHoyCategoriesCatalog,
    CRHoyNews,
    CRHoyNewsCategories,
    CRHoyMetadata,
    MissedCRHoyMetadata,
    CRHoySmartCategories,
    CRHoySummary,
    CRHoyNotifierNews,
]

def serialize_value(value: Any) -> Any:
    """Serialize special data types to JSON-compatible format."""
    if value is None:
        return None
        
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, DateRange):
        return {
            'lower': value.lower.isoformat() if value.lower else None,
            'upper': value.upper.isoformat() if value.upper else None
        }
    return value

def export_table(session: Session, model: Type[DeclarativeBase]) -> List[Dict[str, Any]]:
    """
    Export all records from a table.

    Args:
        session: Database session
        model: SQLAlchemy model class

    Returns:
        List of dictionaries containing the table data
    """
    inspector = inspect(model)
    pk_columns = [col.key for col in inspector.primary_key]
    
    records = []
    for instance in session.query(model).all():
        record = {}
        for column in inspector.columns:
            value = getattr(instance, column.key)
            record[column.key] = serialize_value(value)
        records.append(record)
    
    return records

def export_database(output_dir: Path) -> None:
    """
    Export all configured tables to JSON files.

    Args:
        output_dir: Directory to save the exported files
    """
    # Initialize database connection
    print("Initializing database connection...")
    init_db(settings.database_url)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Exporting database to {output_dir}")
    
    with db_session() as session:
        for model in TABLES_TO_EXPORT:
            table_name = model.__tablename__
            print(f"Exporting table {table_name}...")
            
            records = export_table(session, model)
            
            output_file = output_dir / f"{table_name}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
            
            print(f"Exported {len(records)} records from {table_name}")
    
    print("Database export completed successfully")

if __name__ == "__main__":
    import argparse
    from pydantic import ValidationError
    
    try:
        parser = argparse.ArgumentParser(description="Export CRHoy database tables")
        parser.add_argument(
            "--output-dir",
            type=Path,
            default=settings.data_dir / "backup",
            help=f"Directory to save the exported JSON files (default: {settings.data_dir}/backup)"
        )
        
        args = parser.parse_args()
        export_database(args.output_dir)
        
    except ValidationError as e:
        print("Error in settings validation:")
        print(e)
        exit(1)
    except Exception as e:
        print(f"Error during database export: {e}")
        exit(1) 