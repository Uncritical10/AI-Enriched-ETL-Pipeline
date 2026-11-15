FROM apache/airflow:3.0.6
USER root
RUN mkdir -p /opt/airflow/duck && chown airflow:0 /opt/airflow/duck
USER airflow
RUN python -m venv /home/airflow/dbt_venv && \
    /home/airflow/dbt_venv/bin/pip install --no-cache-dir dbt-duckdb duckdb pandas openai
