"""
staging.py — Generic loader that truncates a staging table and reloads it from a file.

All three sources (Excel, Ads CSV, Weather CSV) share the same load pattern:
truncate the staging table → bulk insert raw text rows. Only the file path,
table name, and file format differ.
"""
import pandas as pd
from psycopg2.extras import execute_values
from config import STG
from utils import tbl


def load_file_to_staging(conn, file_path, stg_table, reader="csv"):
    print(f"Staging: {file_path} → {STG}.{stg_table}")

    df = (pd.read_excel(file_path, dtype=str) if reader == "excel"
          else pd.read_csv(file_path, dtype=str))
    df = df.where(pd.notnull(df), None)   # NaN → None for psycopg2

    col_list = ", ".join(f'"{c}"' for c in df.columns)
    rows = [tuple(row) for row in df.itertuples(index=False, name=None)]

    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {tbl(STG, stg_table)}")
        if rows:
            execute_values(
                cur,
                f'INSERT INTO {tbl(STG, stg_table)} ({col_list}) VALUES %s',
                rows,
            )
    conn.commit()
    print(f"  {len(df)} rows loaded")
