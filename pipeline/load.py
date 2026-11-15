import os
import duckdb

DB   = os.environ.get("DUCKDB_PATH", r"C:\duck\zomato.duckdb")
DATA = os.environ.get("DATA_DIR", r"C:\ETL-Zomato").replace("\\", "/")
MEM  = os.environ.get("DUCKDB_MEMORY", "6GB")
TMP  = os.environ.get("DUCKDB_TMP", "C:/duck/tmp")

STD = "header = true, sample_size = -1, nullstr = ['', 'NULL']"
TABLES = {  # table -> (file, read_csv options)
    "restaurant":  ("restaurant.csv",  "header = true, all_varchar = true"),
    "orders":      ("orderss.csv",      STD),
    "order_items": ("order_items.csv", STD),
    "users":       ("users.csv",       STD),
    "reviews":     ("reviews.csv",     STD),
    "menu":        ("menu.csv",        STD),
    "food":        ("food.csv",        STD),
}

def main():
    con = duckdb.connect(DB)
    con.execute(f"SET memory_limit = '{MEM}'")
    con.execute(f"SET temp_directory = '{TMP}'")
    con.execute("SET preserve_insertion_order = false")
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("BEGIN")
    try:
        for tbl, (fname, opts) in TABLES.items():
            con.execute(f"CREATE OR REPLACE TABLE raw.{tbl} AS "
                        f"SELECT * FROM read_csv('{DATA}/{fname}', {opts})")
            n = con.execute(f"SELECT count(*) FROM raw.{tbl}").fetchone()[0]
            if n == 0:
                raise RuntimeError(f"raw.{tbl} loaded 0 rows")
            print(f"raw.{tbl}: {n:,} rows", flush=True)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    con.execute("CHECKPOINT")
    con.close()

if __name__ == "__main__":
    main()
