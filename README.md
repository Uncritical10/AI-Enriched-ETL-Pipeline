# Zomato Food Delivery Data Pipeline

A production-style daily batch pipeline that turns raw Zomato-style CSV files into
clean, tested, analytics-ready tables, orchestrated end to end with Airflow in Docker.

> Originally built on Snowflake. Migrated to DuckDB after the Snowflake trial ended;
> the dbt models were ported and all tests pass on the new engine.

## Architecture

CSV files → **DuckDB** (raw) → **dbt** (staging → marts) → **Airflow** (Docker)

| Layer | What it holds |
|---|---|
| Bronze (`raw`) | CSVs loaded as-is with DuckDB `read_csv` |
| Silver (`staging`) | Cleaned, typed views, one per source table |
| Gold (`marts`) | Dimensions, incremental facts, business marts |

## Data

About 10M orders, 23M order items, 300K reviews, 100K users, 148K restaurants,
plus menu and food tables. The source data is not included in this repo.

## What's inside

- **Loader:** `pipeline/load.py` replaces all raw tables in one transaction, so a failed load leaves the old data intact.
- **dbt project:** 16 models and 16 data tests (`unique`, `not_null`, `relationships`, `accepted_values`).
- **Gold layer:** date, restaurant, customer and food dimensions; incremental `fct_orders` and `fct_order_items`; marts for daily city revenue (GMV, AOV, cancel rate), restaurant performance and delivery SLA (p50/p90).
- **Orchestration:** Airflow 3 DAG `zomato_batch` (`reload_raw` → `dbt_build_core`), scheduled daily.

## Run it locally

Requires Python 3.12 and the source CSVs.

```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\Activate.ps1
pip install dbt-duckdb duckdb
python pipeline/load.py                             # load raw tables
dbt build                                           # build models and run tests
```

Set `DATA_DIR` and `DUCKDB_PATH` to point at your CSV folder and database file.
dbt reads its connection from a `profiles.yml` with `type: duckdb`.

## Run it with Airflow (Docker)

```bash
cd airflow
docker compose build
docker compose up -d
```

Open `http://localhost:8080`, unpause `zomato_batch`, and trigger it. Copy the CSVs into
the `duckdata` volume first, and give the container 8 GB of RAM (Docker Desktop / WSL2).

## Status

- [x] Raw load, staging and marts, data tests
- [x] Airflow DAG running end to end in Docker
- [ ] LLM review enrichment (sentiment and topic)
- [ ] RAG chat over reviews (Streamlit)
- [ ] Text-to-SQL app with read-only safeguards
- [ ] CI for dbt

## Notes

DuckDB allows one writer at a time, so the pipeline runs as a single task chain and the
apps will read published Parquet snapshots instead of the live database file.
