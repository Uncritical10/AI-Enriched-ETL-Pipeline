from datetime import datetime
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

PROJ = "/opt/airflow/dbt_project"
PY   = "/home/airflow/dbt_venv/bin/python"
DBT  = f"cd {PROJ} && /home/airflow/dbt_venv/bin/dbt"

with DAG(
    dag_id="zomato_batch",
    start_date=datetime(2026, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    max_active_runs=1,
) as dag:
    reload_raw     = BashOperator(task_id="reload_raw",     bash_command=f"{PY} {PROJ}/pipeline/load.py")
    enrich_reviews = BashOperator(
        task_id="enrich_reviews",
        bash_command=f"{PY} {PROJ}/ai/enrich_review.py",
        env={
            "DUCKDB_PATH": "/opt/airflow/duck/zomato.duckdb",
            "ENRICH_SAMPLE_N": "50",
        },
    )
    dbt_build_core = BashOperator(task_id="dbt_build_core", bash_command=f"{DBT} build")

    reload_raw >> enrich_reviews >> dbt_build_core
