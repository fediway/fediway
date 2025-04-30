
from sqlmodel import Session, func, select, exists
from sqlalchemy.schema import CreateTable
from sqlalchemy import label, and_, text, MetaData, Table, DateTime, Column, Integer, BigInteger, String, Float, insert, Boolean

import app.utils as utils

def create_dataset_table(name: str, db: Session) -> Table:
    table = Table(name, MetaData(),
        Column('account_id', BigInteger, primary_key=True),
        Column('status_id', BigInteger, primary_key=True),
        Column('author_id', BigInteger, primary_key=True),
        Column('time', DateTime),
    )

    db.exec(text(f"DROP TABLE IF EXISTS {table.name};"))
    db.exec(text(
        utils.compile_sql(CreateTable(table))
        .replace(" NOT NULL", "")
        .replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")
    ))
    db.exec(text(f"DELETE FROM {table.name};"))
    db.commit()

    return table