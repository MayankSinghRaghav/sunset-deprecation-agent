"""ORM must match the live schema. schema.sql is the source of truth; this is the
tripwire that catches models.py drifting away from it.
"""

from __future__ import annotations

from sqlalchemy import inspect

from sunset.models import Base
from tests.conftest import requires_db


@requires_db
def test_orm_tables_exist_in_db(app_engine):
    insp = inspect(app_engine)
    db_tables = set(insp.get_table_names(schema="public"))
    orm_tables = set(Base.metadata.tables.keys())
    missing = orm_tables - db_tables
    assert not missing, f"ORM declares tables not in DB: {missing}"


@requires_db
def test_orm_columns_match_db(app_engine):
    insp = inspect(app_engine)
    mismatches: list[str] = []
    for table_name, table in Base.metadata.tables.items():
        db_cols = {c["name"] for c in insp.get_columns(table_name, schema="public")}
        orm_cols = {c.name for c in table.columns}
        # The ORM maps a Python attr `model_config_json` to DB column
        # `model_config`; compare on DB column names, which is what .name is.
        missing = orm_cols - db_cols
        if missing:
            mismatches.append(f"{table_name}: ORM has {missing} not in DB")
    assert not mismatches, "; ".join(mismatches)
